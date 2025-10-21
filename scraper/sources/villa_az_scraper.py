import asyncio
import aiohttp
from bs4 import BeautifulSoup
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import os
import re
import sys
from typing import List, Dict, Optional
from datetime import datetime
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.validator import PhoneValidator

# Load environment variables
load_dotenv()

class VillaAzScraperAsync:
    def __init__(self, max_concurrent: int = 10):
        self.base_url = "https://villa.az"
        self.database_url = os.getenv('DATABASE_URL')
        self.max_concurrent = max_concurrent

        # Initialize connection pool
        self.db_pool = psycopg2.pool.SimpleConnectionPool(
            1,  # minimum connections
            10,  # maximum connections
            self.database_url
        )

        # Headers to mimic a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def build_urls(self, start_page: int, end_page: int) -> List[str]:
        """Build URLs for Villa.AZ scraping"""
        urls = []
        for page_num in range(start_page, end_page + 1):
            urls.append(f"{self.base_url}/search?page={page_num}")
        return urls

    async def scrape(self, pages: int = 3) -> Dict[str, int]:
        """
        High-level scraping method that handles all scraping logic

        Args:
            pages (int): Number of pages to scrape (default: 3)
        """
        start_time = datetime.now()
        print(f"Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        urls = self.build_urls(1, pages)
        stats = await self.scrape_multiple_pages(urls)

        # Print summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\nCompleted in {duration:.2f}s | Found: {stats['total']} | Saved: {stats['saved']} | Failed: {stats['failed']}")

        # Add timing info to stats for main.py to use
        stats['duration'] = duration
        stats['start_time'] = start_time

        return stats

    def extract_listing_urls(self, html_content: str) -> List[Dict[str, str]]:
        """Extract listing URLs from the main page HTML"""
        soup = BeautifulSoup(html_content, 'lxml')
        listings = []

        # Find all listing links
        listing_divs = soup.find_all('div', class_='ads')

        for div in listing_divs:
            link = div.find('a')
            if link and link.get('href'):
                href = link.get('href')
                full_url = f"{self.base_url}{href}"

                listings.append({
                    'url': full_url
                })

        return listings

    async def get_phone_numbers(self, session: aiohttp.ClientSession, listing_url: str) -> List[str]:
        """Fetch phone numbers from listing detail page"""
        try:
            async with session.get(
                listing_url,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    text = await response.text(encoding='utf-8', errors='ignore')

                    # Parse the phone numbers from response
                    soup = BeautifulSoup(text, 'lxml')

                    # Find all phone links (tel: links with +994 country code)
                    # Handle both formats: tel:+994XXXXXXXXX and tel:(+994) XX XXX XX XX
                    phone_links = soup.find_all('a', href=re.compile(r'tel:.*\+994'))

                    phones = []
                    for phone_link in phone_links:
                        href = phone_link.get('href', '')

                        # Extract all digits from the phone number
                        # This handles both tel:+994558688686 and tel:(+994) 55 868 86 86
                        digits_only = re.sub(r'\D', '', href)

                        # Remove country code (994) to get the 9-digit number
                        if digits_only.startswith('994') and len(digits_only) >= 12:
                            phone_formatted = digits_only[3:]  # Remove '994' prefix

                            # Get last 9 digits only
                            phone_formatted = phone_formatted[-9:]

                            # Skip if undefined or invalid
                            if len(phone_formatted) == 9 and phone_formatted.isdigit():
                                if phone_formatted not in phones:
                                    phones.append(phone_formatted)

                    return phones
                else:
                    print(f"Failed to get phone (HTTP {response.status}): {listing_url}")

            return []

        except Exception as e:
            print(f"Error fetching phone: {listing_url} - {e}")
            return []

    def save_to_database(self, phone_number: str, source_url: str) -> bool:
        """
        Save lead to database with validation and connection pooling

        Validates phone number before insertion:
        - Only numeric digits
        - Exactly 9 digits (last 9)
        - First 2 digits: 10, 50, 51, 55, 60, 70, 77, 99
        - 3rd digit cannot be 0 or 1
        - Must be unique (handled by DB constraint)
        """
        # Validate phone number before attempting to save
        validated_phone = PhoneValidator.validate_phone(phone_number)

        if not validated_phone:
            # Phone number failed validation - do not insert
            return False

        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            conn = None
            try:
                # Get connection from pool
                conn = self.db_pool.getconn()
                cur = conn.cursor()

                # Insert lead (ignore duplicates by phone number)
                query = """
                    INSERT INTO leads.leads (phone_number, website, source)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (phone_number)
                    DO NOTHING
                    RETURNING id
                """

                cur.execute(query, (validated_phone, 'villa.az', source_url))
                conn.commit()

                result = cur.fetchone()
                cur.close()

                # Return connection to pool
                self.db_pool.putconn(conn)

                return True if result else False

            except Exception as e:
                # Return connection to pool if we got one
                if conn:
                    self.db_pool.putconn(conn)

                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"Database error after {max_retries} attempts: {e}")
                    return False

        return False

    async def process_listing(self, session: aiohttp.ClientSession, listing: Dict[str, str], idx: int, total: int) -> Dict[str, any]:
        """Process a single listing"""
        result = {
            'url': listing['url'],
            'phones': [],
            'success': False,
            'saved': 0
        }

        # Fetch phone numbers
        phones = await self.get_phone_numbers(session, listing['url'])

        if phones:
            result['phones'] = phones
            result['success'] = True

            # Save each phone to database
            for phone in phones:
                if self.save_to_database(phone, listing['url']):
                    result['saved'] += 1

        return result

    async def scrape_listings(self, html_content: str) -> Dict[str, int]:
        """Main scraping function with async processing"""
        # Extract listing URLs
        listings = self.extract_listing_urls(html_content)

        stats = {
            'total': len(listings),
            'success': 0,
            'failed': 0,
            'saved': 0
        }

        # Create aiohttp session
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create tasks for all listings
            tasks = []
            for idx, listing in enumerate(listings, 1):
                task = self.process_listing(session, listing, idx, len(listings))
                tasks.append(task)

            # Process all listings concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Calculate statistics
            for result in results:
                if isinstance(result, Exception):
                    stats['failed'] += 1
                    print(f"Exception during processing: {result}")
                elif isinstance(result, dict):
                    if result['success']:
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1

                    stats['saved'] += result.get('saved', 0)

        return stats

    async def scrape_from_url(self, url: str) -> Dict[str, int]:
        """Scrape listings from a URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        html_content = await response.text(encoding='utf-8', errors='ignore')
                        return await self.scrape_listings(html_content)
                    else:
                        print(f"Failed to fetch page (HTTP {response.status}): {url}")
                        return {'total': 0, 'success': 0, 'failed': 0, 'saved': 0}

        except Exception as e:
            print(f"Error fetching URL: {e}")
            return {'total': 0, 'success': 0, 'failed': 0, 'saved': 0}

    async def scrape_multiple_pages(self, urls: List[str]) -> Dict[str, int]:
        """Scrape multiple pages concurrently"""
        total_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'saved': 0
        }

        for url in urls:
            stats = await self.scrape_from_url(url)

            total_stats['total'] += stats['total']
            total_stats['success'] += stats['success']
            total_stats['failed'] += stats['failed']
            total_stats['saved'] += stats['saved']

        return total_stats

    def close(self):
        """Close database connection pool"""
        if self.db_pool:
            self.db_pool.closeall()
