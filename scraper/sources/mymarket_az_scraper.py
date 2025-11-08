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

class MymarketAzScraperAsync:
    """
    Scraper for mymarket.az - Azerbaijan marketplace website

    Two-step process:
    1. Get all shop links from https://mymarket.az/magazalar
    2. Visit each shop page and extract phone numbers
    """

    def __init__(self, db_pool, max_concurrent: int = 10):
        self.base_url = "https://mymarket.az"
        self.shops_url = f"{self.base_url}/magazalar"
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

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    async def scrape(self, max_pages: int = 5, **kwargs) -> Dict[str, int]:
        """
        High-level scraping method

        Args:
            max_pages: Number of pages to scrape from the load-more API
        """
        start_time = datetime.now()
        print(f"[mymarket.az] Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Reset stats
        self.stats = {
            'new_leads': 0,
            'duplicates': 0,
            'errors': 0,
            'invalid_phones': 0
        }

        # Get all shop links (with pagination)
        shop_urls = await self.get_shop_links(max_pages)

        if not shop_urls:
            print(f"[mymarket.az] No shop links found")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.stats['duration'] = duration
            self.stats['start_time'] = start_time
            return self.stats

        print(f"[mymarket.az] Found {len(shop_urls)} shops")

        # Scrape each shop
        await self.scrape_shops(shop_urls)

        # Print summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"[mymarket.az] Completed in {duration:.2f}s | Shops: {len(shop_urls)} | New: {self.stats['new_leads']} | Duplicates: {self.stats['duplicates']}")

        # Add timing info
        self.stats['duration'] = duration
        self.stats['start_time'] = start_time

        return self.stats

    async def get_shop_links(self) -> List[str]:
        """
        Extract all shop links from the shops listing page

        Returns:
            List of shop URLs
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.shops_url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status != 200:
                        print(f"[mymarket.az] Failed to fetch shops page (HTTP {response.status})")
                        return []

                    html = await response.text(encoding='utf-8', errors='ignore')
                    soup = BeautifulSoup(html, 'lxml')

                    # Find all shop links - they have class "my-store" and are <a> tags
                    shop_links = []
                    shop_elements = soup.find_all('a', class_='my-store')

                    for shop in shop_elements:
                        href = shop.get('href')
                        if href:
                            # href is already a full URL like https://mymarket.az/magaza/pixmart
                            shop_links.append(href)

                    return list(set(shop_links))  # Remove duplicates

        except Exception as e:
            print(f"[mymarket.az] Error getting shop links: {e}")
            return []

    def extract_shop_data(self, html_content: str, shop_url: str) -> Optional[Dict]:
        """
        Extract phone number and shop data from a shop page

        Args:
            html_content: HTML of the shop page
            shop_url: URL of the shop

        Returns:
            Dict with shop data or None
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            shop_data = {}

            # Extract shop name
            shop_name_elem = soup.find('span', class_='my-store__name')
            if shop_name_elem:
                shop_data['shop_name'] = shop_name_elem.get_text(strip=True)

            # Extract rating
            rating_elem = soup.find('span', class_='my-store__rating__value')
            if rating_elem:
                try:
                    shop_data['rating'] = float(rating_elem.get_text(strip=True))
                except:
                    pass

            # Extract post count
            post_count_elem = soup.find('span', class_='my-store__post-count')
            if post_count_elem:
                count_text = post_count_elem.get_text(strip=True)
                count_match = re.search(r'(\d+)', count_text)
                if count_match:
                    shop_data['post_count'] = int(count_match.group(1))

            # Extract description
            desc_elem = soup.find('span', class_='my-store__description')
            if desc_elem:
                shop_data['description'] = desc_elem.get_text(strip=True)

            # Extract phone numbers from contact section
            # Look for tel: links
            tel_links = soup.find_all('a', href=re.compile(r'tel:'))

            phones = []
            for tel_link in tel_links:
                href = tel_link.get('href')
                if href:
                    # Extract phone from href like "tel:0552595920"
                    phone = href.replace('tel:', '').strip()
                    # Clean the phone
                    cleaned = re.sub(r'[^\d]', '', phone)
                    if len(cleaned) >= 9:
                        phones.append(cleaned[-9:])  # Get last 9 digits

            if phones:
                shop_data['phone'] = phones[0]  # Take first phone

            # Also try to extract from WhatsApp links
            if 'phone' not in shop_data:
                wa_links = soup.find_all('a', href=re.compile(r'wa\.me'))
                for wa_link in wa_links:
                    href = wa_link.get('href')
                    if href:
                        # Extract phone from href like "https://wa.me/0552595920"
                        phone_match = re.search(r'wa\.me/([0-9]+)', href)
                        if phone_match:
                            phone = phone_match.group(1)
                            cleaned = re.sub(r'[^\d]', '', phone)
                            if len(cleaned) >= 9:
                                shop_data['phone'] = cleaned[-9:]
                                break

            return shop_data if shop_data.get('phone') else None

        except Exception as e:
            print(f"[mymarket.az] Error extracting shop data: {e}")
            return None

    async def fetch_shop_data(self, session: aiohttp.ClientSession, shop_url: str) -> Optional[Dict]:
        """
        Fetch and parse a shop page

        Args:
            session: aiohttp session
            shop_url: URL of the shop

        Returns:
            Dict with shop data or None
        """
        try:
            async with session.get(shop_url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    html = await response.text(encoding='utf-8', errors='ignore')
                    return self.extract_shop_data(html, shop_url)
                else:
                    print(f"[mymarket.az] Failed to fetch shop (HTTP {response.status}): {shop_url}")
                    return None

        except Exception as e:
            print(f"[mymarket.az] Error fetching shop {shop_url}: {e}")
            return None

    def save_to_database(self, phone_number: str, source_url: str, full_data: Optional[Dict] = None) -> bool:
        """
        Save lead to database with validation

        Args:
            phone_number: Phone number to save
            source_url: URL of the shop
            full_data: Shop data

        Returns:
            True if saved as new lead, False if duplicate or error
        """
        # Validate phone number
        validated_phone = PhoneValidator.validate_phone(phone_number)

        if not validated_phone:
            self.stats['invalid_phones'] += 1
            return False

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            conn = None
            try:
                conn = self.db_pool.getconn()
                cur = conn.cursor()

                # Check if phone already exists
                cur.execute("SELECT id FROM leads.leads WHERE phone_number = %s", (validated_phone,))
                existing = cur.fetchone()

                if existing:
                    self.stats['duplicates'] += 1
                    cur.close()
                    self.db_pool.putconn(conn)
                    return False

                # Insert new lead
                query = """
                    INSERT INTO leads.leads (phone_number, website, source, full_data)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """

                full_data_json = json.dumps(full_data) if full_data else None

                cur.execute(query, (validated_phone, 'mymarket.az', source_url, full_data_json))
                conn.commit()

                result = cur.fetchone()
                cur.close()
                self.db_pool.putconn(conn)

                if result:
                    self.stats['new_leads'] += 1
                    return True

                return False

            except Exception as e:
                if conn:
                    self.db_pool.putconn(conn)

                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[mymarket.az] Database error: {e}")
                    self.stats['errors'] += 1
                    return False

        self.stats['errors'] += 1
        return False

    async def process_shop(self, session: aiohttp.ClientSession, shop_url: str, idx: int, total: int) -> Dict:
        """
        Process a single shop

        Args:
            session: aiohttp session
            shop_url: URL of the shop
            idx: Current index
            total: Total count

        Returns:
            Result dict
        """
        result = {
            'url': shop_url,
            'phone': None,
            'success': False,
            'saved': False
        }

        # Fetch shop data
        shop_data = await self.fetch_shop_data(session, shop_url)

        if shop_data and shop_data.get('phone'):
            phone = shop_data['phone']
            result['phone'] = phone
            result['success'] = True

            # Prepare full_data
            full_data = {
                'listing_type': 'marketplace_shop',
                'shop_name': shop_data.get('shop_name'),
                'rating': shop_data.get('rating'),
                'post_count': shop_data.get('post_count'),
                'description': shop_data.get('description')
            }

            # Save to database
            if self.save_to_database(phone, shop_url, full_data):
                result['saved'] = True

        return result

    async def scrape_shops(self, shop_urls: List[str]):
        """
        Scrape all shops concurrently

        Args:
            shop_urls: List of shop URLs to scrape
        """
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for idx, url in enumerate(shop_urls, 1):
                task = self.process_shop(session, url, idx, len(shop_urls))
                tasks.append(task)

            # Process all shops concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Calculate statistics
            for result in results:
                if isinstance(result, Exception):
                    self.stats['errors'] += 1
                    print(f"[mymarket.az] Exception: {result}")

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
        async with MymarketAzScraperAsync(db_pool, max_concurrent=10) as scraper:
            stats = await scraper.scrape(max_pages=1)

            # Print summary
            print("\n" + "="*50)
            print("MYMARKET.AZ SCRAPING SUMMARY")
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
