"""
BiTurbo.az Car Listings Scraper
Extracts car listings from biturbo.az with detailed information
"""

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


class BiTurboAzScraperAsync:
    """Async scraper for biturbo.az car listings"""

    def __init__(self, max_concurrent: int = 10):
        """
        Initialize scraper

        Args:
            max_concurrent: Maximum number of concurrent requests (default: 10)
        """
        self.base_url = "https://www.biturbo.az"
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
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'DNT': '1'
        }

    def build_urls(self, start_page: int, end_page: int) -> List[str]:
        """
        Build URLs for BiTurbo.AZ scraping

        Args:
            start_page: Start page number
            end_page: End page number

        Returns:
            List of URLs to scrape
        """
        urls = []
        for page_num in range(start_page, end_page + 1):
            if page_num == 1:
                # First page doesn't have page number in URL
                urls.append(f"{self.base_url}/az/axtar/")
            else:
                urls.append(f"{self.base_url}/az/axtar/{page_num}/")
        return urls

    async def scrape(self, pages: int = 5) -> Dict[str, int]:
        """
        Main entry point for scraping

        Args:
            pages: Number of pages to scrape (default: 5)

        Returns:
            Dictionary with statistics
        """
        start_time = datetime.now()
        print(f"Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        urls = self.build_urls(1, pages)
        stats = await self.scrape_multiple_pages(urls)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\nCompleted in {duration:.2f}s | Found: {stats['total']} | Saved: {stats['saved']} | Failed: {stats['failed']}")

        # Add timing info to stats
        stats['duration'] = duration
        stats['start_time'] = start_time

        return stats

    def extract_listing_urls(self, html_content: str) -> List[Dict[str, str]]:
        """
        Extract listing URLs from the main page HTML

        Args:
            html_content: HTML content of the listings page

        Returns:
            List of dictionaries with listing URLs
        """
        soup = BeautifulSoup(html_content, 'lxml')
        listings = []

        # Find all listing divs
        listing_divs = soup.find_all('div', class_='products-i')

        for div in listing_divs:
            # Find the link inside each listing
            link = div.find('a', class_='products-i-link')
            if link and link.get('href'):
                full_url = link['href']  # Already absolute URL
                listings.append({'url': full_url})

        return listings

    def _clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return ' '.join(text.strip().split())

    async def get_phone_numbers(self, session: aiohttp.ClientSession, soup: BeautifulSoup) -> List[str]:
        """
        Extract phone numbers from listing detail page

        Args:
            session: aiohttp session
            soup: BeautifulSoup object of the listing page

        Returns:
            List of phone numbers
        """
        phones = []

        # Find phone in seller-phone div
        # <a class="phone" title="İlqar zəng et" href="tel:0775062013">0775062013</a>
        phone_link = soup.find('a', class_='phone')
        if phone_link:
            phone_text = phone_link.get_text(strip=True)
            if phone_text:
                phones.append(phone_text)

        return phones

    def save_to_database(self, phone_number: str, source_url: str, full_data: Optional[Dict] = None) -> bool:
        """
        Save lead to database with validation and connection pooling

        Args:
            phone_number: Phone number to save
            source_url: URL of the listing
            full_data: Complete listing data as JSON/dict

        Returns:
            True if saved successfully, False otherwise
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
                full_data_json = json.dumps(full_data, ensure_ascii=False) if full_data else None

                cur.execute(query, (validated_phone, 'biturbo.az', source_url, full_data_json))
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
        """
        Process a single listing - fetch phone numbers and full listing details

        Args:
            session: aiohttp session
            listing: Listing dictionary with URL
            idx: Current index
            total: Total number of listings

        Returns:
            Dictionary with processing results
        """
        result = {
            'url': listing['url'],
            'phones': [],
            'success': False,
            'saved': 0
        }

        try:
            # Fetch listing page once
            async with session.get(listing['url'], headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    print(f"Failed to fetch listing page (HTTP {response.status}): {listing['url']}")
                    return result

                html_content = await response.text(encoding='utf-8', errors='ignore')
                soup = BeautifulSoup(html_content, 'lxml')

                # Extract phone numbers
                phones = await self.get_phone_numbers(session, soup)

                # Extract full data (pass soup to avoid re-parsing)
                full_data = self.extract_full_data_from_soup(soup)

                if phones:
                    result['phones'] = phones
                    result['success'] = True

                    # Save each phone to database with the same full_data
                    for phone in phones:
                        # Clean phone number (remove spaces and formatting)
                        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)

                        if self.save_to_database(clean_phone, listing['url'], full_data):
                            result['saved'] += 1

        except Exception as e:
            import traceback
            print(f"Error processing listing: {listing['url']} - {e}")
            traceback.print_exc()

        return result

    def extract_full_data_from_soup(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Extract full data from BeautifulSoup object

        Args:
            soup: BeautifulSoup object of the listing page

        Returns:
            Dictionary with all listing data or None if failed
        """
        try:
            # Initialize full_data structure
            full_data = {
                "listing_type": "car",
                "title": None,
                "price": {},
                "car_details": {},
                "description": None,
                "seller": {},
                "listing_info": {},
                "images": [],
                "features": []
            }

            # Extract title from h2.product-name
            title_elem = soup.find('h2', class_='product-name')
            if title_elem:
                full_data['title'] = self._clean_text(title_elem.get_text())

            # Extract price from div.product-price
            price_elem = soup.find('div', class_='product-price')
            if price_elem:
                price_text = self._clean_text(price_elem.get_text())
                # Parse "21500 AZN"
                price_match = re.search(r'([\d\s]+)\s*([A-Z]+)', price_text)
                if price_match:
                    amount_str = price_match.group(1).replace(' ', '').replace('\xa0', '')
                    full_data['price']['amount'] = int(amount_str) if amount_str.isdigit() else None
                    full_data['price']['currency'] = price_match.group(2)

            # Extract seller information
            seller_name_elem = soup.find('div', class_='seller-name')
            if seller_name_elem:
                name_p = seller_name_elem.find('p')
                if name_p:
                    full_data['seller']['name'] = self._clean_text(name_p.get_text())

            # Extract statistics
            stats_div = soup.find('div', class_='product-statistics')
            if stats_div:
                # Extract views
                views_p = stats_div.find('label', string=re.compile(r'Baxışların sayı'))
                if views_p and views_p.parent:
                    views_text = views_p.parent.get_text()
                    views_match = re.search(r':\s*(\d+)', views_text)
                    if views_match:
                        full_data['listing_info']['views'] = int(views_match.group(1))

                # Extract update date
                updated_p = stats_div.find('label', string=re.compile(r'Yeniləndi'))
                if updated_p and updated_p.parent:
                    date_text = updated_p.parent.get_text()
                    date_match = re.search(r':\s*(.+)', date_text)
                    if date_match:
                        full_data['listing_info']['date_updated'] = self._clean_text(date_match.group(1))

                # Extract ad ID
                id_p = stats_div.find('label', string=re.compile(r'Elanın nömrəsi'))
                if id_p and id_p.parent:
                    id_text = id_p.parent.get_text()
                    id_match = re.search(r':\s*(\d+)', id_text)
                    if id_match:
                        full_data['listing_info']['ad_id'] = id_match.group(1)

            # Extract car properties from ul.product-properties
            properties_ul = soup.find('ul', class_='product-properties')
            if properties_ul:
                property_items = properties_ul.find_all('li', class_='product-properties-i')
                for item in property_items:
                    label_elem = item.find('label')
                    value_elem = item.find('div', class_='product-properties-value')

                    if label_elem and value_elem:
                        label = self._clean_text(label_elem.get_text())
                        value = self._clean_text(value_elem.get_text())

                        # Map Azerbaijani field names to English keys
                        field_mapping = {
                            'Marka': 'make',
                            'Model': 'model',
                            'Buraxılış ili': 'year',
                            'Ban növü': 'body_type',
                            'Rəng': 'color',
                            'Mühərrikin həcmi': 'engine',
                            'Mühərrikin gücü': 'power',
                            'Yanacaq növü': 'fuel_type',
                            'Yürüş': 'mileage',
                            'Sürətlər qutusu': 'transmission',
                            'Ötürücü': 'gear',
                            'Qiymət': 'price_text'
                        }

                        english_key = field_mapping.get(label)
                        if english_key and english_key != 'price_text':  # Skip price as we already have it
                            full_data['car_details'][english_key] = value

            # Extract features from product-extras
            extras_div = soup.find('div', class_='product-extras')
            if extras_div:
                feature_items = extras_div.find_all('p', class_='product-extras-i')
                for item in feature_items:
                    feature_text = self._clean_text(item.get_text())
                    if feature_text:
                        full_data['features'].append(feature_text)

            # Extract description from product-text
            desc_p = soup.find('p', class_='product-text')
            if desc_p:
                # Get text and preserve line breaks
                description_html = str(desc_p)
                # Replace <br> with newlines
                description_html = description_html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                # Parse again to get clean text
                desc_soup = BeautifulSoup(description_html, 'lxml')
                full_data['description'] = self._clean_text(desc_soup.get_text())

            # Extract images from eagle-gallery
            # Look for data-medium-img or data-big-img attributes
            gallery_div = soup.find('div', class_='eagle-gallery')
            if gallery_div:
                # Main image
                main_img = gallery_div.find('img', src=True)
                if main_img and main_img.get('src'):
                    img_url = main_img['src']
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = self.base_url + img_url
                    full_data['images'].append(img_url)

                # Thumbnail images
                thumb_imgs = gallery_div.find_all('img', attrs={'data-medium-img': True})
                for img in thumb_imgs:
                    img_url = img.get('data-medium-img') or img.get('data-big-img') or img.get('src')
                    if img_url:
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            img_url = self.base_url + img_url
                        if img_url not in full_data['images']:
                            full_data['images'].append(img_url)

            return full_data

        except Exception as e:
            print(f"Error extracting full data from soup: {e}")
            return None

    async def scrape_listings(self, html_content: str) -> Dict[str, int]:
        """
        Main scraping function with async processing

        Args:
            html_content: HTML content of the listings page

        Returns:
            Dictionary with statistics
        """
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
        """
        Scrape listings from a URL

        Args:
            url: URL to scrape

        Returns:
            Dictionary with statistics
        """
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
        """
        Scrape multiple pages concurrently

        Args:
            urls: List of URLs to scrape

        Returns:
            Aggregated statistics
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
    # Initialize scraper with max 10 concurrent requests
    scraper = BiTurboAzScraperAsync(max_concurrent=10)

    try:
        # Scrape first 5 pages
        stats = await scraper.scrape(pages=5)

        # Print summary
        print("\n" + "="*50)
        print("SCRAPING SUMMARY")
        print("="*50)
        print(f"Total listings found: {stats['total']}")
        print(f"Successfully extracted: {stats['success']}")
        print(f"Failed to extract: {stats['failed']}")
        print(f"Saved to database: {stats['saved']}")
        print(f"Time taken: {stats.get('duration', 0):.2f} seconds")
        print("="*50)

    finally:
        scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
