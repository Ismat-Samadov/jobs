"""
VIPEMLAK.AZ Scraper - Real Estate Listings

Scrapes real estate listings from vipemlak.az with:
- HTML pagination for listing URLs
- AJAX API for phone number extraction
- Detail page parsing for phone extraction parameters
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
from urllib.parse import urljoin, urlparse, parse_qs

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class VipemlakAzScraper:
    """Scraper for vipemlak.az real estate listings"""

    BASE_URL = "https://vipemlak.az"
    SEARCH_URL = "https://vipemlak.az/"
    AJAX_URL = "https://vipemlak.az/ajax.php"

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
            'Referer': 'https://vipemlak.az/',
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
            page_num: Page number (starts at 0, increments by 4)

        Returns:
            HTML response string or None
        """
        try:
            # Calculate start parameter (appears to increment by 4 per page)
            start = page_num * 4

            params = {
                'catid': '261,262',
                'tip': '0',
                'city': '31',
                'start': start
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

            # Find all listing links in product divs
            # <div class="pranto prodbig"><a href="/listing-url.html">
            listing_divs = soup.find_all('div', class_='pranto')

            for div in listing_divs:
                link = div.find('a', href=True)
                if link:
                    href = link['href']

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

    async def extract_phone_params(self, listing_url: str) -> Optional[Dict]:
        """
        Extract phone extraction parameters from listing detail page

        Args:
            listing_url: URL of the listing

        Returns:
            Dict with extraction params or None
        """
        try:
            async with self.session.get(listing_url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find the telshow div with data attributes
                # <div id="telshow" data-id="765366" data-t="homeobject"
                #      data-h="3cb59c0846e00421f697969a13da8439" data-rf="...">
                telshow_div = soup.find('div', id='telshow')

                if not telshow_div:
                    return None

                # Extract parameters
                data_id = telshow_div.get('data-id')
                data_t = telshow_div.get('data-t', 'homeobject')
                data_h = telshow_div.get('data-h')
                data_rf = telshow_div.get('data-rf', '')

                if not data_id or not data_h:
                    return None

                return {
                    'id': data_id,
                    't': data_t,
                    'h': data_h,
                    'rf': data_rf,
                    'url': listing_url
                }

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return None

    async def fetch_phone_numbers(self, params: Dict) -> List[str]:
        """
        Fetch phone numbers using AJAX API

        Args:
            params: Dict with id, t, h, rf parameters

        Returns:
            List of phone numbers
        """
        try:
            # Build POST payload
            payload = {
                'act': 'telshow',
                'id': params['id'],
                't': params['t'],
                'h': params['h'],
                'rf': params['rf']
            }

            # Update headers for AJAX request
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': params['url']
            }

            async with self.session.post(self.AJAX_URL, data=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # Response: {"ok": 1, "tel": "0703896768,0556896768", "msg": "..."}
                    if data.get('ok') == 1:
                        tel_string = data.get('tel', '')

                        if tel_string:
                            # Split by comma if multiple numbers
                            phone_numbers = [p.strip() for p in tel_string.split(',') if p.strip()]
                            return phone_numbers

                return []

        except asyncio.TimeoutError:
            return []
        except Exception as e:
            return []

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
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'vipemlak.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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
        print("VIPEMLAK.AZ Scraper - Real Estate")
        print(f"{'='*70}\n")

        all_listing_urls = []

        # Scrape listing URLs from pagination pages
        print(f"📋 Scraping listing URLs from {max_pages} pages...")
        for page_num in range(max_pages):
            html = await self.fetch_listings_page(page_num)

            if not html:
                print(f"   Page {page_num + 1}: No data found, stopping pagination")
                break

            listing_urls = self.extract_listing_urls(html)

            if not listing_urls:
                print(f"   Page {page_num + 1}: No listings found, stopping pagination")
                break

            all_listing_urls.extend(listing_urls)
            print(f"   Page {page_num + 1}/{max_pages}: Found {len(listing_urls)} listings")

            # Small delay between pages
            await asyncio.sleep(0.5)

        # Deduplicate URLs
        all_listing_urls = list(set(all_listing_urls))
        self.stats['total_listings'] = len(all_listing_urls)

        print(f"\n✓ Found {len(all_listing_urls)} unique listings\n")

        # Scrape each listing detail page for phone numbers
        print(f"🔍 Extracting phone numbers via AJAX API...\n")

        for idx, listing_url in enumerate(all_listing_urls, 1):
            # Progress indicator
            if idx % 10 == 0 or idx == 1:
                print(f"   Progress: {idx}/{len(all_listing_urls)} listings...")

            # Extract phone extraction parameters
            params = await self.extract_phone_params(listing_url)

            if not params:
                self.stats['errors'] += 1
                continue

            # Fetch phone numbers via AJAX
            phone_numbers = await self.fetch_phone_numbers(params)

            if not phone_numbers:
                # No phone numbers found
                continue

            # Prepare listing data
            listing_data = {
                'listing_id': params.get('id'),
                'url': listing_url
            }

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
        print("Scraping Complete - VIPEMLAK.AZ")
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
    async with VipemlakAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)  # Test with 3 pages

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
