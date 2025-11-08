"""
YENIEMLAK.AZ Scraper - Real Estate Listings

Scrapes real estate listings from yeniemlak.az with:
- HTML pagination for listing URLs
- Phone number extraction from image URLs
- Detail page parsing for property data
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class YeniemlakAzScraper:
    """Scraper for yeniemlak.az real estate listings"""

    BASE_URL = "https://yeniemlak.az"
    SEARCH_URL = "https://yeniemlak.az/elan/axtar"

    def __init__(self, db_pool: SimpleConnectionPool):
        """Initialize scraper with database connection pool"""
        self.db_pool = db_pool
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            'total_listings': 0,
            'new_leads': 0,
            'duplicates': 0,
            'invalid_phones': 0,
            'errors': 0
        }

    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Referer': 'https://yeniemlak.az/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_listings_page(self, page_num: int) -> Optional[str]:
        """
        Fetch a page of listings

        Args:
            page_num: Page number (starts at 1)

        Returns:
            HTML response string or None
        """
        try:
            params = {
                'emlak': '1',
                'elan_nov': '1',
                'seher[]': '0',
                'metro[]': '0',
                'qiymet': '',
                'qiymet2': '',
                'mertebe': '',
                'mertebe2': '',
                'otaq': '',
                'otaq2': '',
                'sahe_m': '',
                'sahe_m2': '',
                'sahe_s': '',
                'sahe_s2': '',
                'page': page_num
            }

            async with self.session.get(self.SEARCH_URL, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    return html
                else:
                    print(f"   ✗ Failed to fetch page {page_num} (HTTP {response.status})")
                    return None

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching page {page_num}")
            return None
        except Exception as e:
            print(f"   ✗ Error fetching page {page_num}: {e}")
            return None

    def extract_listing_urls(self, html: str) -> List[str]:
        """
        Extract listing URLs from HTML response

        Args:
            html: HTML response string

        Returns:
            List of listing URLs
        """
        listing_urls = []

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find all listing tables with class="list"
            listing_tables = soup.find_all('table', class_='list')

            for table in listing_tables:
                # Find the detail link: <a class="detail" href="/elan/...">
                detail_link = table.find('a', class_='detail', href=True)

                if detail_link:
                    href = detail_link['href']

                    # Build full URL
                    if href.startswith('http'):
                        full_url = href
                    elif href.startswith('/'):
                        full_url = self.BASE_URL + href
                    else:
                        full_url = self.BASE_URL + '/' + href

                    listing_urls.append(full_url)

        except Exception as e:
            print(f"   ✗ Error extracting URLs: {e}")

        return listing_urls

    async def scrape_listing_detail(self, listing_url: str) -> Optional[Dict]:
        """
        Scrape individual listing detail page

        Args:
            listing_url: URL of the listing

        Returns:
            Dict with listing data or None
        """
        try:
            async with self.session.get(listing_url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Extract listing ID from URL (e.g., /elan/...-776906 -> 776906)
                listing_id = None
                id_match = re.search(r'-(\d+)$', listing_url)
                if id_match:
                    listing_id = id_match.group(1)

                # Extract phone numbers from image URLs
                # <img src="/tel-show/0504378170">
                phone_numbers = []
                phone_imgs = soup.find_all('img', src=re.compile(r'/tel-show/'))

                for img in phone_imgs:
                    src = img.get('src', '')
                    # Extract phone from /tel-show/0504378170
                    phone_match = re.search(r'/tel-show/(\d+)', src)
                    if phone_match:
                        phone = phone_match.group(1)
                        phone_numbers.append(phone)

                # Extract title/type
                title = None
                emlak_elem = soup.find('emlak')
                if emlak_elem:
                    title = emlak_elem.get_text(strip=True)

                # Extract price
                price = None
                price_elem = soup.find('price')
                if price_elem:
                    price = price_elem.get_text(strip=True) + ' AZN'

                # Extract location from params
                location = None
                location_params = soup.find_all('div', class_='params')
                if location_params and len(location_params) > 0:
                    location = location_params[0].get_text(strip=True)

                # Extract rooms, area, floor
                rooms = None
                area = None
                floor = None

                params_divs = soup.find_all('div', class_='params')
                for div in params_divs:
                    text = div.get_text(strip=True)
                    if 'otaq' in text:
                        rooms = text
                    elif 'm2' in text:
                        area = text
                    elif 'Mərtəbə' in text:
                        floor = text

                # Extract description
                description = None
                text_div = soup.find('div', class_='text')
                if text_div:
                    description = text_div.get_text(strip=True)

                # Extract agent info
                agent_name = None
                agent_div = soup.find('div', class_='ad')
                if agent_div:
                    agent_name = agent_div.get_text(strip=True)

                return {
                    'listing_id': listing_id,
                    'title': title,
                    'price': price,
                    'location': location,
                    'rooms': rooms,
                    'area': area,
                    'floor': floor,
                    'description': description,
                    'agent_name': agent_name,
                    'phone_numbers': phone_numbers,
                    'url': listing_url
                }

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return None

    def save_lead(self, phone_number: str, listing_data: Dict) -> bool:
        """
        Save lead to database

        Args:
            phone_number: Validated phone number
            listing_data: Listing data dict

        Returns:
            True if new lead saved, False if duplicate
        """
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Check if phone exists globally
            cursor.execute("""
                SELECT id, website FROM leads.leads
                WHERE phone_number = %s
            """, (phone_number,))

            existing = cursor.fetchone()

            if existing:
                # Duplicate - skip
                cursor.close()
                self.db_pool.putconn(conn)
                return False

            # Prepare full_data JSON
            full_data = {
                'listing_id': listing_data.get('listing_id'),
                'title': listing_data.get('title'),
                'price': listing_data.get('price'),
                'location': listing_data.get('location'),
                'rooms': listing_data.get('rooms'),
                'area': listing_data.get('area'),
                'floor': listing_data.get('floor'),
                'description': listing_data.get('description'),
                'agent_name': listing_data.get('agent_name'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'yeniemlak.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)
            return True

        except psycopg2.IntegrityError:
            # Duplicate key
            if conn:
                conn.rollback()
                self.db_pool.putconn(conn)
            return False
        except Exception as e:
            print(f"   ✗ Database error: {e}")
            if conn:
                conn.rollback()
                self.db_pool.putconn(conn)
            self.stats['errors'] += 1
            return False

    async def scrape(self, max_pages: int = 5):
        """
        Main scraping method

        Args:
            max_pages: Maximum number of pages to scrape
        """
        print(f"\n{'='*70}")
        print("YENIEMLAK.AZ Scraper - Real Estate")
        print(f"{'='*70}\n")

        all_listing_urls = []

        # Scrape listing URLs from pagination pages
        print(f"📋 Scraping listing URLs from {max_pages} pages...")
        for page_num in range(1, max_pages + 1):
            html = await self.fetch_listings_page(page_num)

            if not html:
                print(f"   Page {page_num}: No data found, stopping pagination")
                break

            listing_urls = self.extract_listing_urls(html)

            if not listing_urls:
                print(f"   Page {page_num}: No listings found, stopping pagination")
                break

            all_listing_urls.extend(listing_urls)
            print(f"   Page {page_num}/{max_pages}: Found {len(listing_urls)} listings")

            # Small delay between pages
            await asyncio.sleep(0.5)

        # Deduplicate URLs
        all_listing_urls = list(set(all_listing_urls))
        self.stats['total_listings'] = len(all_listing_urls)

        print(f"\n✓ Found {len(all_listing_urls)} unique listings\n")

        # Scrape each listing detail page
        print(f"🔍 Scraping listing details and phone numbers...\n")

        for idx, listing_url in enumerate(all_listing_urls, 1):
            # Progress indicator
            if idx % 10 == 0 or idx == 1:
                print(f"   Progress: {idx}/{len(all_listing_urls)} listings...")

            # Scrape listing detail
            listing_data = await self.scrape_listing_detail(listing_url)

            if not listing_data:
                self.stats['errors'] += 1
                continue

            # Get phone numbers
            phone_numbers = listing_data.get('phone_numbers', [])

            if not phone_numbers:
                # No phone numbers found
                continue

            # Validate and save each phone number
            for phone_number in phone_numbers:
                validated_phone = PhoneValidator.validate_phone(phone_number)

                if not validated_phone:
                    self.stats['invalid_phones'] += 1
                    continue

                # Save to database
                is_new = self.save_lead(validated_phone, listing_data)

                if is_new:
                    self.stats['new_leads'] += 1
                else:
                    self.stats['duplicates'] += 1

            # Small delay between requests
            await asyncio.sleep(0.3)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - YENIEMLAK.AZ")
        print(f"{'='*70}")
        print(f"Total listings:    {self.stats['total_listings']:,}")
        print(f"New leads:         {self.stats['new_leads']:,}")
        print(f"Duplicates:        {self.stats['duplicates']:,}")
        print(f"Invalid phones:    {self.stats['invalid_phones']:,}")
        print(f"Errors:            {self.stats['errors']:,}")
        print(f"{'='*70}\n")


async def main():
    """Test function"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Create database pool
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    # Run scraper
    async with YeniemlakAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)  # Test with 3 pages

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
