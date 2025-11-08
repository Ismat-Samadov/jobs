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
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.validator import PhoneValidator

# Load environment variables
load_dotenv()

class BinalarAzScraperAsync:
    """
    Scraper for binalar.az - Azerbaijan real estate aggregator

    Pagination: +32 items per page
    - Page 1: https://binalar.az/
    - Page 2: https://binalar.az/?page=32
    - Page 3: https://binalar.az/?page=64
    """

    ITEMS_PER_PAGE = 32

    def __init__(self, db_pool, max_concurrent: int = 10):
        self.base_url = "https://binalar.az"
        self.phone_api_url = f"{self.base_url}/binalar/get_phone/"
        self.db_pool = db_pool
        self.max_concurrent = max_concurrent

        # Initialize stats tracking
        self.stats = {
            'new_leads': 0,
            'duplicates': 0,
            'errors': 0,
            'invalid_phones': 0
        }

        # Headers to mimic a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }

    def build_urls(self, start_page: int, end_page: int) -> List[str]:
        """
        Build URLs for binalar.az scraping

        Args:
            start_page: Starting page number (1-based)
            end_page: Ending page number (1-based)

        Returns:
            List of URLs to scrape
        """
        urls = []
        for page_num in range(start_page, end_page + 1):
            if page_num == 1:
                urls.append(self.base_url)
            else:
                # Pagination logic: page 2 = 32, page 3 = 64, etc.
                page_offset = (page_num - 1) * self.ITEMS_PER_PAGE
                urls.append(f"{self.base_url}/?page={page_offset}")

        return urls

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Nothing to clean up here since db_pool is managed externally
        pass

    async def scrape(self, max_pages: int = 5, **kwargs) -> Dict[str, int]:
        """
        High-level scraping method that handles all scraping logic

        Args:
            max_pages: Number of pages to scrape starting from page 1
        """
        start_time = datetime.now()
        print(f"[binalar.az] Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Reset stats
        self.stats = {
            'new_leads': 0,
            'duplicates': 0,
            'errors': 0,
            'invalid_phones': 0
        }

        # Build URLs for the specified number of pages
        urls = self.build_urls(1, max_pages)

        # Run scraper
        raw_stats = await self.scrape_multiple_pages(urls)

        # Print summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"[binalar.az] Completed in {duration:.2f}s | Found: {raw_stats['total']} | Saved: {self.stats['new_leads']} | Failed: {raw_stats['failed']}")

        # Add timing info to stats for main.py to use
        self.stats['duration'] = duration
        self.stats['start_time'] = start_time

        return self.stats

    def extract_listing_data(self, html_content: str) -> List[Dict[str, any]]:
        """
        Extract listing data from the main page HTML

        Returns:
            List of dicts containing listing ID, URL, and basic data
        """
        soup = BeautifulSoup(html_content, 'lxml')
        listings = []

        # Find all listing cards
        listing_cards = soup.find_all('div', class_='card style-6 prop_item')

        for card in listing_cards:
            try:
                listing_data = {}

                # Extract listing ID from phone button
                phone_btn = card.find('div', class_='phone_btn')
                if phone_btn and phone_btn.get('rel'):
                    listing_data['id'] = phone_btn.get('rel')
                else:
                    continue  # Skip if no ID found

                # Extract listing URL
                link = card.find('a', href=True)
                if link:
                    href = link.get('href')
                    if href.startswith('/'):
                        listing_data['url'] = f"{self.base_url}{href}"
                    else:
                        listing_data['url'] = href
                else:
                    continue  # Skip if no URL found

                # Extract price
                price_elem = card.find('span', class_='text-primary fw-bold')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # Parse price like "115 000 ₼" or "1 500 ₼ / ay"
                    price_match = re.search(r'([\d\s]+)\s*₼', price_text)
                    if price_match:
                        amount_str = price_match.group(1).replace(' ', '').replace('\xa0', '')
                        listing_data['price'] = int(amount_str) if amount_str.isdigit() else None

                        # Check if it's rental (per month)
                        if '/ ay' in price_text or '/ay' in price_text:
                            listing_data['rental_type'] = 'monthly'

                # Extract title
                title_elem = card.find('b', class_='prop_title')
                if title_elem:
                    listing_data['title'] = title_elem.get_text(strip=True)

                # Extract property details (rooms, area, floor)
                details = {}
                detail_items = card.find_all('li', class_='d-flex align-items-center flex-fill')
                for item in detail_items:
                    text = item.get_text(strip=True)

                    # Extract rooms
                    if 'otaq' in text:
                        rooms_match = re.search(r'(\d+)\s*otaq', text)
                        if rooms_match:
                            details['rooms'] = int(rooms_match.group(1))

                    # Extract area (m² or sot)
                    if 'm²' in text:
                        area_match = re.search(r'([\d.]+)\s*m²', text)
                        if area_match:
                            details['area_sqm'] = float(area_match.group(1))
                    elif 'sot' in text:
                        sot_match = re.search(r'([\d.]+)\s*sot', text)
                        if sot_match:
                            details['area_sot'] = float(sot_match.group(1))

                    # Extract floor
                    if 'mərtəbə' in text:
                        floor_match = re.search(r'(\d+)/(\d+)\s*mərtəbə', text)
                        if floor_match:
                            details['floor'] = f"{floor_match.group(1)}/{floor_match.group(2)}"

                listing_data['details'] = details

                # Extract location
                location_elem = card.find('p', class_='address')
                if location_elem:
                    listing_data['location'] = location_elem.get_text(strip=True).replace('Ünvan', '').strip()

                # Extract description
                desc_elem = card.find('p', class_='short_info')
                if desc_elem:
                    listing_data['description'] = desc_elem.get_text(strip=True)

                # Extract source website (bina.az, yeniemlak.az, etc.)
                source_link = card.find('span', class_='sites')
                if source_link:
                    source_a = source_link.find('a', href=True)
                    if source_a:
                        listing_data['original_source'] = source_a.get_text(strip=True)
                        listing_data['original_url'] = source_a.get('href')

                # Extract date
                date_elem = card.find('div', class_='col-auto text-end text-body-tertiary')
                if date_elem:
                    listing_data['listing_date'] = date_elem.get_text(strip=True)

                listings.append(listing_data)

            except Exception as e:
                print(f"[binalar.az] Error extracting listing data: {e}")
                continue

        return listings

    async def get_phone_number(self, session: aiohttp.ClientSession, listing_id: str, listing_url: str) -> Optional[str]:
        """
        Fetch phone number for a specific listing via API

        Args:
            session: aiohttp session
            listing_id: Listing ID from the website
            listing_url: URL of the listing (for referer)

        Returns:
            Phone number (9 digits) or None
        """
        try:
            # Update headers for phone API request
            headers = self.headers.copy()
            headers['Referer'] = listing_url
            headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            headers['X-Requested-With'] = 'XMLHttpRequest'
            headers['Origin'] = self.base_url

            # Make POST request to phone API
            payload = {'id': listing_id}

            async with session.post(
                self.phone_api_url,
                data=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    text = await response.text()

                    # Parse the phone number from HTML response
                    soup = BeautifulSoup(text, 'lxml')
                    phone_link = soup.find('a', href=re.compile(r'tel:\+994'))

                    if phone_link:
                        # Extract phone from href attribute (tel:+994506271539)
                        phone_full = phone_link.get('href').replace('tel:+994', '')
                        # Get last 9 digits only
                        phone_formatted = phone_full[-9:]
                        return phone_formatted
                    else:
                        # Try to find phone in text format like "(055) 353-46-08"
                        phone_match = re.search(r'\((\d{3})\)\s*(\d{3})-(\d{2})-(\d{2})', text)
                        if phone_match:
                            phone_formatted = ''.join(phone_match.groups())
                            return phone_formatted
                else:
                    print(f"[binalar.az] Failed to get phone (HTTP {response.status}): ID {listing_id}")

            return None

        except Exception as e:
            print(f"[binalar.az] Error fetching phone for ID {listing_id}: {e}")
            return None

    def save_to_database(self, phone_number: str, source_url: str, full_data: Optional[Dict] = None) -> bool:
        """
        Save lead to database with validation and connection pooling

        Args:
            phone_number: Phone number to save
            source_url: URL of the listing
            full_data: Complete listing data as JSON/dict

        Returns:
            True if saved as new lead, False if duplicate or error
        """
        # Validate phone number before attempting to save
        validated_phone = PhoneValidator.validate_phone(phone_number)

        if not validated_phone:
            # Phone number failed validation - do not insert
            self.stats['invalid_phones'] += 1
            return False

        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            conn = None
            try:
                # Get connection from pool
                conn = self.db_pool.getconn()
                cur = conn.cursor()

                # Check if phone already exists
                cur.execute("SELECT id FROM leads.leads WHERE phone_number = %s", (validated_phone,))
                existing = cur.fetchone()

                if existing:
                    # Phone already exists - this is a duplicate
                    self.stats['duplicates'] += 1
                    cur.close()
                    self.db_pool.putconn(conn)
                    return False

                # Insert new lead with full_data
                query = """
                    INSERT INTO leads.leads (phone_number, website, source, full_data)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """

                # Convert full_data dict to JSON string
                full_data_json = json.dumps(full_data) if full_data else None

                cur.execute(query, (validated_phone, 'binalar.az', source_url, full_data_json))
                conn.commit()

                result = cur.fetchone()
                cur.close()

                # Return connection to pool
                self.db_pool.putconn(conn)

                if result:
                    self.stats['new_leads'] += 1
                    return True

                return False

            except Exception as e:
                # Return connection to pool if we got one
                if conn:
                    self.db_pool.putconn(conn)

                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[binalar.az] Database error after {max_retries} attempts: {e}")
                    self.stats['errors'] += 1
                    return False

        self.stats['errors'] += 1
        return False

    async def process_listing(self, session: aiohttp.ClientSession, listing: Dict[str, any], idx: int, total: int) -> Dict[str, any]:
        """
        Process a single listing - fetch phone number

        Args:
            session: aiohttp session
            listing: Listing data dict
            idx: Current index
            total: Total count

        Returns:
            Result dict with success/saved status
        """
        result = {
            'id': listing['id'],
            'url': listing['url'],
            'phone': None,
            'success': False,
            'saved': False
        }

        # Fetch phone number
        phone = await self.get_phone_number(session, listing['id'], listing['url'])

        if phone:
            result['phone'] = phone
            result['success'] = True

            # Prepare full_data for database
            full_data = {
                'listing_type': 'real_estate',
                'title': listing.get('title'),
                'price': listing.get('price'),
                'rental_type': listing.get('rental_type'),
                'property_details': listing.get('details', {}),
                'location': listing.get('location'),
                'description': listing.get('description'),
                'original_source': listing.get('original_source'),
                'original_url': listing.get('original_url'),
                'listing_date': listing.get('listing_date')
            }

            # Save to database
            if self.save_to_database(phone, listing['url'], full_data):
                result['saved'] = True

        return result

    async def scrape_listings(self, html_content: str) -> Dict[str, int]:
        """
        Main scraping function with async processing

        Args:
            html_content: HTML content of the page

        Returns:
            Statistics dict
        """
        # Extract listing data
        listings = self.extract_listing_data(html_content)

        stats = {
            'total': len(listings),
            'success': 0,
            'failed': 0,
            'saved': 0
        }

        if not listings:
            print(f"[binalar.az] No listings found on page")
            return stats

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
                    print(f"[binalar.az] Exception during processing: {result}")
                elif isinstance(result, dict):
                    if result['success']:
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1

                    if result.get('saved'):
                        stats['saved'] += 1

        return stats

    async def scrape_from_url(self, url: str) -> Dict[str, int]:
        """
        Scrape listings from a URL

        Args:
            url: URL to scrape

        Returns:
            Statistics dict
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        html_content = await response.text(encoding='utf-8', errors='ignore')
                        return await self.scrape_listings(html_content)
                    else:
                        print(f"[binalar.az] Failed to fetch page (HTTP {response.status}): {url}")
                        return {'total': 0, 'success': 0, 'failed': 0, 'saved': 0}

        except Exception as e:
            print(f"[binalar.az] Error fetching URL: {e}")
            return {'total': 0, 'success': 0, 'failed': 0, 'saved': 0}

    async def scrape_multiple_pages(self, urls: List[str]) -> Dict[str, int]:
        """
        Scrape multiple pages sequentially

        Args:
            urls: List of URLs to scrape

        Returns:
            Aggregated statistics dict
        """
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


async def main():
    """Main function to run the scraper"""
    # Create database pool
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        # Initialize scraper with max 10 concurrent requests
        async with BinalarAzScraperAsync(db_pool, max_concurrent=10) as scraper:
            # Scrape first 3 pages
            stats = await scraper.scrape(max_pages=3)

            # Print summary
            print("\n" + "="*50)
            print("BINALAR.AZ SCRAPING SUMMARY")
            print("="*50)
            print(f"New leads: {stats['new_leads']}")
            print(f"Duplicates: {stats['duplicates']}")
            print(f"Invalid phones: {stats['invalid_phones']}")
            print(f"Errors: {stats['errors']}")
            print(f"Time taken: {stats.get('duration', 0):.2f} seconds")
            print("="*50)
    finally:
        db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
