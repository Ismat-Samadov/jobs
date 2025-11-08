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

class BinamAzScraperAsync:
    """
    Scraper for binam.az - Azerbaijan real estate website

    Pagination: Standard ?page=N format
    - Page 1: https://binam.az/items
    - Page 2: https://binam.az/items?page=2
    - Page 3: https://binam.az/items?page=3
    """

    def __init__(self, db_pool, max_concurrent: int = 10):
        self.base_url = "https://binam.az"
        self.listings_url = f"{self.base_url}/items"
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
        Build URLs for binam.az scraping

        Args:
            start_page: Starting page number (1-based)
            end_page: Ending page number (1-based)

        Returns:
            List of URLs to scrape
        """
        urls = []
        for page_num in range(start_page, end_page + 1):
            if page_num == 1:
                urls.append(self.listings_url)
            else:
                urls.append(f"{self.listings_url}?page={page_num}")

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
        print(f"[binam.az] Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

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

        print(f"[binam.az] Completed in {duration:.2f}s | Found: {raw_stats['total']} | Saved: {self.stats['new_leads']} | Failed: {raw_stats['failed']}")

        # Add timing info to stats for main.py to use
        self.stats['duration'] = duration
        self.stats['start_time'] = start_time

        return self.stats

    def extract_listing_urls(self, html_content: str) -> List[str]:
        """
        Extract listing URLs from the listings page HTML

        Returns:
            List of absolute listing URLs
        """
        soup = BeautifulSoup(html_content, 'lxml')
        listing_urls = []

        # Find all listing items
        listing_items = soup.find_all('div', class_='item')

        for item in listing_items:
            try:
                # Find the link in the item header
                header = item.find('div', class_='item-header')
                if header:
                    link = header.find('a', href=True)
                    if link:
                        href = link.get('href')
                        if href.startswith('/'):
                            full_url = f"{self.base_url}{href}"
                        else:
                            full_url = href
                        listing_urls.append(full_url)
            except Exception as e:
                print(f"[binam.az] Error extracting listing URL: {e}")
                continue

        return listing_urls

    def extract_listing_details(self, html_content: str, listing_url: str) -> Optional[Dict]:
        """
        Extract detailed data from a listing page

        Args:
            html_content: HTML content of the listing page
            listing_url: URL of the listing

        Returns:
            Dict with listing details or None
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            listing_data = {}

            # Extract price
            price_elem = soup.select_one('.sec_list2 h2')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Parse price like "239 000 AZN" or "1,047 000 AZN"
                price_match = re.search(r'([\d,\s]+)\s*AZN', price_text)
                if price_match:
                    amount_str = price_match.group(1).replace(' ', '').replace(',', '').replace('\xa0', '')
                    listing_data['price'] = int(amount_str) if amount_str.isdigit() else None

            # Extract listing code
            code_elem = soup.select_one('.sec_list2 h2:-soup-contains("Elanın kodu")')
            if code_elem:
                code_match = re.search(r'(\d+)', code_elem.get_text())
                if code_match:
                    listing_data['listing_code'] = code_match.group(1)

            # Extract table data
            table = soup.find('table', class_='table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True).replace(':', '')
                        value = cells[1].get_text(strip=True)

                        if 'Elanın növü' in key:
                            listing_data['listing_type'] = value
                        elif 'Elanın tarixi' in key:
                            listing_data['listing_date'] = value
                        elif 'Sahə' in key:
                            # Extract area like "70 m2"
                            area_match = re.search(r'(\d+)', value)
                            if area_match:
                                listing_data['area_sqm'] = int(area_match.group(1))
                        elif 'Mərtəbəsi' in key:
                            listing_data['floor'] = value
                        elif 'Otaq sayı' in key:
                            rooms_match = re.search(r'(\d+)', value)
                            if rooms_match:
                                listing_data['rooms'] = int(rooms_match.group(1))
                        elif 'Ölkə/Şəhər' in key:
                            listing_data['country_city'] = value
                        elif 'Rayon' in key:
                            listing_data['district'] = value
                        elif 'Metro' in key:
                            listing_data['metro'] = value
                        elif 'Ünvan' in key:
                            listing_data['address'] = value

            # Extract phone number from contact info
            sec_list3 = soup.find('div', class_='sec_list3')
            if sec_list3:
                # Look for phone in the structure
                phone_text = sec_list3.get_text()

                # Try to find phone numbers in various formats
                # Format: 0517445344 or (051) 744-53-44
                phone_matches = re.findall(r'(?:Telefon|Mobil nömrə)[:\s]*([0-9\(\)\-\s]+)', phone_text)

                for match in phone_matches:
                    # Clean the phone number
                    cleaned = re.sub(r'[^\d]', '', match)
                    if len(cleaned) >= 9:
                        listing_data['phone'] = cleaned[-9:]  # Get last 9 digits
                        break

                # Extract agent/company info
                company_match = re.search(r'Şirkətin adı[:\s]*<br>\s*<a[^>]*>([^<]+)</a>', str(sec_list3))
                if company_match:
                    listing_data['company'] = company_match.group(1).strip()

                name_match = re.search(r'Ad, soyad[:\s]*<br>([^<]+)<br>', str(sec_list3))
                if name_match:
                    listing_data['agent_name'] = name_match.group(1).strip()

            # Extract description
            page_contents = soup.find('div', class_='page-contents')
            if page_contents:
                desc_p = page_contents.find('p')
                if desc_p:
                    listing_data['description'] = desc_p.get_text(strip=True)

            # Extract title from h3 in item-header or page title
            title_elem = soup.select_one('h3 a, .property-data h2')
            if title_elem:
                listing_data['title'] = title_elem.get_text(strip=True)

            return listing_data

        except Exception as e:
            print(f"[binam.az] Error extracting listing details: {e}")
            return None

    async def fetch_listing_details(self, session: aiohttp.ClientSession, listing_url: str) -> Optional[Dict]:
        """
        Fetch and parse a single listing page

        Args:
            session: aiohttp session
            listing_url: URL of the listing

        Returns:
            Dict with listing details or None
        """
        try:
            async with session.get(listing_url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    html_content = await response.text(encoding='utf-8', errors='ignore')
                    return self.extract_listing_details(html_content, listing_url)
                else:
                    print(f"[binam.az] Failed to fetch listing (HTTP {response.status}): {listing_url}")
                    return None

        except Exception as e:
            print(f"[binam.az] Error fetching listing {listing_url}: {e}")
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

                cur.execute(query, (validated_phone, 'binam.az', source_url, full_data_json))
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
                    print(f"[binam.az] Database error after {max_retries} attempts: {e}")
                    self.stats['errors'] += 1
                    return False

        self.stats['errors'] += 1
        return False

    async def process_listing(self, session: aiohttp.ClientSession, listing_url: str, idx: int, total: int) -> Dict[str, any]:
        """
        Process a single listing - fetch details and save to database

        Args:
            session: aiohttp session
            listing_url: URL of the listing
            idx: Current index
            total: Total count

        Returns:
            Result dict with success/saved status
        """
        result = {
            'url': listing_url,
            'phone': None,
            'success': False,
            'saved': False
        }

        # Fetch listing details
        listing_data = await self.fetch_listing_details(session, listing_url)

        if listing_data and listing_data.get('phone'):
            phone = listing_data['phone']
            result['phone'] = phone
            result['success'] = True

            # Prepare full_data for database
            full_data = {
                'listing_type': 'real_estate',
                'title': listing_data.get('title'),
                'price': listing_data.get('price'),
                'listing_code': listing_data.get('listing_code'),
                'property_type': listing_data.get('listing_type'),
                'listing_date': listing_data.get('listing_date'),
                'area_sqm': listing_data.get('area_sqm'),
                'floor': listing_data.get('floor'),
                'rooms': listing_data.get('rooms'),
                'country_city': listing_data.get('country_city'),
                'district': listing_data.get('district'),
                'metro': listing_data.get('metro'),
                'address': listing_data.get('address'),
                'company': listing_data.get('company'),
                'agent_name': listing_data.get('agent_name'),
                'description': listing_data.get('description')
            }

            # Save to database
            if self.save_to_database(phone, listing_url, full_data):
                result['saved'] = True

        return result

    async def scrape_listings(self, listing_urls: List[str]) -> Dict[str, int]:
        """
        Scrape all listings from a list of URLs

        Args:
            listing_urls: List of listing URLs to scrape

        Returns:
            Statistics dict
        """
        stats = {
            'total': len(listing_urls),
            'success': 0,
            'failed': 0,
            'saved': 0
        }

        if not listing_urls:
            print(f"[binam.az] No listing URLs found")
            return stats

        # Create aiohttp session
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create tasks for all listings
            tasks = []
            for idx, url in enumerate(listing_urls, 1):
                task = self.process_listing(session, url, idx, len(listing_urls))
                tasks.append(task)

            # Process all listings concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Calculate statistics
            for result in results:
                if isinstance(result, Exception):
                    stats['failed'] += 1
                    print(f"[binam.az] Exception during processing: {result}")
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
        Scrape listings from a listings page URL

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
                        # Extract listing URLs from the page
                        listing_urls = self.extract_listing_urls(html_content)
                        print(f"[binam.az] Found {len(listing_urls)} listings on page: {url}")
                        # Scrape each listing
                        return await self.scrape_listings(listing_urls)
                    else:
                        print(f"[binam.az] Failed to fetch page (HTTP {response.status}): {url}")
                        return {'total': 0, 'success': 0, 'failed': 0, 'saved': 0}

        except Exception as e:
            print(f"[binam.az] Error fetching URL: {e}")
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
        async with BinamAzScraperAsync(db_pool, max_concurrent=10) as scraper:
            # Scrape first 3 pages
            stats = await scraper.scrape(max_pages=3)

            # Print summary
            print("\n" + "="*50)
            print("BINAM.AZ SCRAPING SUMMARY")
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
