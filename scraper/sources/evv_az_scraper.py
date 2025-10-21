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

class EvvAzScraperAsync:
    # EVV.AZ-specific constants
    ITEMS_PER_PAGE = 24
    LISTING_TYPES = {
        1: "Sale",
        2: "Rent",
        3: "Daily"
    }

    def __init__(self, max_concurrent: int = 10):
        self.base_url = "https://www.evv.az"
        self.phone_api_url = f"{self.base_url}/evvaz/get_phone"
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
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }

    def build_urls(self, listing_type: int, start_page: int, end_page: int) -> List[str]:
        """Build URLs for EVV.AZ scraping"""
        base_url = f"{self.base_url}/dasinmaz-emlak-satis?type={listing_type}"

        urls = []
        for page_num in range(start_page, end_page + 1):
            if page_num == 1:
                urls.append(base_url)
            else:
                page_offset = (page_num - 1) * self.ITEMS_PER_PAGE
                urls.append(f"{base_url}&page={page_offset}")

        return urls

    async def scrape(self, **kwargs) -> Dict[str, int]:
        """
        High-level scraping method that handles all scraping logic

        Kwargs:
            url (str): Custom URL to scrape
            page (int): Single page number to scrape
            start (int): Start page for multi-page scraping
            end (int): End page for multi-page scraping
            listing_type (int): Listing type (1=Sale, 2=Rent, 3=Daily)
            all_types (bool): Scrape all 3 types
            pages_per_type (int): Number of pages per type when all_types=True (default: 3)
        """
        start_time = datetime.now()
        print(f"Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Handle all-types scraping
        if kwargs.get('all_types', False):
            total_stats = {'total': 0, 'success': 0, 'failed': 0, 'saved': 0}
            pages_per_type = kwargs.get('pages_per_type', 3)

            for listing_type in [1, 2, 3]:
                urls = self.build_urls(listing_type, 1, pages_per_type)
                stats = await self.scrape_multiple_pages(urls)

                # Aggregate stats
                total_stats['total'] += stats['total']
                total_stats['success'] += stats['success']
                total_stats['failed'] += stats['failed']
                total_stats['saved'] += stats['saved']

            stats = total_stats

        else:
            # Single type scraping
            listing_type = kwargs.get('listing_type', 1)

            # Determine URLs to scrape
            if kwargs.get('url'):
                urls = [kwargs['url']]
            elif kwargs.get('start') and kwargs.get('end'):
                urls = self.build_urls(listing_type, kwargs['start'], kwargs['end'])
            else:
                page_num = kwargs.get('page', 1)
                urls = self.build_urls(listing_type, page_num, page_num)

            # Run scraper
            if len(urls) == 1:
                stats = await self.scrape_from_url(urls[0])
            else:
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
        """Extract listing URLs and IDs from the main page HTML"""
        soup = BeautifulSoup(html_content, 'lxml')
        listings = []

        # Find all listing links
        listing_links = soup.find_all('a', class_='img_link')

        for link in listing_links:
            href = link.get('href')
            if href:
                # Extract listing ID from href
                # Format: /2-otaqli-menzil-yeni-tikili-satilir-gence-51654
                listing_id = href.split('-')[-1]
                full_url = f"{self.base_url}{href}"

                listings.append({
                    'id': listing_id,
                    'url': full_url
                })

        return listings

    async def get_phone_number(self, session: aiohttp.ClientSession, listing_id: str, listing_url: str) -> Optional[str]:
        """Fetch phone number for a specific listing"""
        try:
            # Update headers for this specific listing
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

                    # Parse the phone number from response
                    soup = BeautifulSoup(text, 'lxml')
                    phone_link = soup.find('a', href=re.compile(r'tel:\+994'))

                    if phone_link:
                        # Extract phone from href attribute (tel:+994506271539)
                        phone_full = phone_link.get('href').replace('tel:+994', '')

                        # Get last 9 digits only
                        phone_formatted = phone_full[-9:]

                        return phone_formatted
                else:
                    print(f"Failed to get phone (HTTP {response.status}): {listing_url}")

            return None

        except Exception as e:
            print(f"Error fetching phone: {listing_url} - {e}")
            return None

    async def fetch_listing_details(self, session: aiohttp.ClientSession, listing_url: str) -> Optional[Dict]:
        """Fetch and parse the full listing page to extract all details"""
        try:
            async with session.get(listing_url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    print(f"Failed to fetch listing page (HTTP {response.status}): {listing_url}")
                    return None

                html_content = await response.text(encoding='utf-8', errors='ignore')
                soup = BeautifulSoup(html_content, 'lxml')

                # Initialize full_data structure
                full_data = {
                    "listing_type": "real_estate",
                    "title": None,
                    "price": {},
                    "property_details": {},
                    "description": None,
                    "seller": {},
                    "listing_info": {},
                    "images": [],
                    "price_comparison": {}
                }

                # Extract title
                title_elem = soup.find('h1', class_='prop_title')
                if title_elem:
                    full_data['title'] = title_elem.get_text(strip=True)

                # Extract price information
                price_elem = soup.find('div', class_='price')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # Parse price (e.g., "98 000 AZN")
                    price_match = re.search(r'([\d\s]+)\s*([A-Z]+)', price_text)
                    if price_match:
                        amount_str = price_match.group(1).replace(' ', '').replace('\xa0', '')
                        full_data['price']['amount'] = int(amount_str) if amount_str.isdigit() else None
                        full_data['price']['currency'] = price_match.group(2)

                # Extract price per sqm
                price_per_sqm_elem = soup.find('div', class_='square')
                if price_per_sqm_elem:
                    price_per_sqm_text = price_per_sqm_elem.get_text(strip=True)
                    # Parse "1 531 AZN/m²"
                    price_per_sqm_match = re.search(r'([\d\s]+)', price_per_sqm_text)
                    if price_per_sqm_match:
                        per_sqm_str = price_per_sqm_match.group(1).replace(' ', '').replace('\xa0', '')
                        full_data['price']['price_per_sqm'] = int(per_sqm_str) if per_sqm_str.isdigit() else None

                # Extract property details - EVV.AZ uses divs with float-start/float-end spans
                # Find all divs that contain property details
                for div in soup.find_all('div'):
                    # Look for divs with float-start and float-end spans
                    label_span = div.find('span', class_='float-start')
                    value_span = div.find('span', class_='float-end')

                    if label_span and value_span:
                        label = label_span.get_text(strip=True)
                        value = value_span.get_text(strip=True)

                        # Map Azerbaijani field names to English keys
                        field_mapping = {
                            'Şəhər': 'city',
                            'Bina': 'property_type',
                            'Ünvan': 'location',
                            'Sənədi': 'document',
                            'Mərtəbə': 'floor',
                            'Sahəsi': 'area',
                            'Otaq sayı': 'rooms',
                            'İpoteka': 'mortgage'
                        }

                        english_key = field_mapping.get(label)
                        if english_key:
                            full_data['property_details'][english_key] = value

                # Extract rooms from title if not in details
                if 'rooms' not in full_data['property_details'] and full_data['title']:
                    rooms_match = re.search(r'(\d+)\s*otaq', full_data['title'], re.IGNORECASE)
                    if rooms_match:
                        full_data['property_details']['rooms'] = int(rooms_match.group(1))

                # Extract description from blockquote
                description_elem = soup.find('blockquote', class_='mt-3')
                if description_elem:
                    # Remove script tags and get clean text
                    for script in description_elem.find_all('script'):
                        script.decompose()
                    full_data['description'] = description_elem.get_text(strip=True)

                # Extract seller information
                seller_name_elem = soup.find('h5')  # Seller name is in h5
                if seller_name_elem:
                    full_data['seller']['name'] = seller_name_elem.get_text(strip=True)

                seller_type_elem = soup.find('p', class_='text-muted')
                if seller_type_elem:
                    small_tag = seller_type_elem.find('small')
                    if small_tag:
                        full_data['seller']['type'] = small_tag.get_text(strip=True)

                # Extract listing ID from URL
                # URL format: /3-otaqli-menzil-yeni-tikili-satilir-xirdalan-51945
                listing_id_match = re.search(r'-(\d+)$', listing_url)
                if listing_id_match:
                    full_data['listing_info']['ad_id'] = listing_id_match.group(1)

                # Extract images from gallery
                # Images are in <a class="estate_thumb_item" data-fancybox="gallery" href="...">
                image_links = soup.find_all('a', {'data-fancybox': 'gallery'})
                for link in image_links:
                    href = link.get('href')
                    if href and '/uploads/' in href:
                        # Make sure URL is absolute
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif href.startswith('/'):
                            href = self.base_url + href
                        full_data['images'].append(href)

                # Extract price comparison data if available
                price_comparison_elem = soup.find('div', class_='price-comparison')
                if price_comparison_elem:
                    avg_price_elem = price_comparison_elem.find('span', class_='avg-price')
                    if avg_price_elem:
                        full_data['price_comparison']['average_price'] = avg_price_elem.get_text(strip=True)

                return full_data

        except Exception as e:
            print(f"Error fetching listing details: {listing_url} - {e}")
            return None

    def save_to_database(self, phone_number: str, source_url: str, full_data: Optional[Dict] = None) -> bool:
        """
        Save lead to database with validation and connection pooling

        Validates phone number before insertion:
        - Only numeric digits
        - Exactly 9 digits (last 9)
        - First 2 digits: 10, 50, 51, 55, 60, 70, 77, 99
        - 3rd digit cannot be 0 or 1
        - Must be unique (handled by DB constraint)

        Args:
            phone_number: Phone number to save
            source_url: URL of the listing
            full_data: Complete listing data as JSON/dict
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

                # Insert lead with full_data (ignore duplicates by phone number)
                query = """
                    INSERT INTO leads.leads (phone_number, website, source, full_data)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (phone_number)
                    DO UPDATE SET
                        full_data = EXCLUDED.full_data,
                        source = EXCLUDED.source
                    RETURNING id
                """

                # Convert full_data dict to JSON string
                full_data_json = json.dumps(full_data) if full_data else None

                cur.execute(query, (validated_phone, 'evv.az', source_url, full_data_json))
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
        """Process a single listing - fetch phone number and full listing details"""
        result = {
            'id': listing['id'],
            'url': listing['url'],
            'phone': None,
            'success': False,
            'saved': False
        }

        # Fetch phone number and listing details in parallel
        phone_task = self.get_phone_number(session, listing['id'], listing['url'])
        details_task = self.fetch_listing_details(session, listing['url'])

        phone, full_data = await asyncio.gather(phone_task, details_task)

        if phone:
            result['phone'] = phone
            result['success'] = True

            # Save to database with full_data (sync operation)
            if self.save_to_database(phone, listing['url'], full_data):
                result['saved'] = True
        # Don't log individual failures - only exceptions

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

                    if result.get('saved'):
                        stats['saved'] += 1

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


async def main():
    """Main function to run the scraper"""
    # Initialize scraper with max 10 concurrent requests
    scraper = EvvAzScraperAsync(max_concurrent=10)

    # Example: Scrape from the sale listings page
    url = "https://www.evv.az/dasinmaz-emlak-satis?type=1"

    start_time = datetime.now()
    stats = await scraper.scrape_from_url(url)
    end_time = datetime.now()

    # Print summary
    print("\n" + "="*50)
    print("SCRAPING SUMMARY")
    print("="*50)
    print(f"Total listings found: {stats['total']}")
    print(f"Successfully extracted: {stats['success']}")
    print(f"Failed to extract: {stats['failed']}")
    print(f"Saved to database: {stats['saved']}")
    print(f"Time taken: {(end_time - start_time).total_seconds():.2f} seconds")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
