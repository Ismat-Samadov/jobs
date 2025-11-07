"""
MASINLAR.AZ Scraper - Car Rental and Sales Listings

Scrapes car listings from masinlar.az with:
- POST-based pagination to /homelist/?start={page}
- HTML response parsing for listing URLs
- AJAX endpoint for phone number extraction
- Detail page scraping for full listing data
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


class MasinlarAzScraper:
    """Scraper for masinlar.az car rental and sales listings"""

    BASE_URL = "https://masinlar.az"
    HOMELIST_URL = "https://masinlar.az/homelist/"
    AJAX_URL = "https://masinlar.az/ajax.php"

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
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Origin': 'https://masinlar.az',
            'Referer': 'https://masinlar.az/',
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_listings_page(self, page_num: int) -> Optional[str]:
        """
        Fetch a page of listings using POST request

        Args:
            page_num: Page number (starts at 0 for first page, then 4, 8, 12...)

        Returns:
            HTML response string or None
        """
        try:
            # Calculate start parameter (page 1 = 0, page 2 = 4, page 3 = 8, etc.)
            start = page_num * 4 if page_num > 0 else 0
            url = f"{self.HOMELIST_URL}?start={start}"

            # POST request with empty body
            async with self.session.post(url) as response:
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

            # Find all product divs
            prod_divs = soup.find_all('div', class_='nobj')

            for div in prod_divs:
                # Find the link inside holderimg div
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

    async def fetch_phone_via_ajax(self, listing_id: str, hash_val: str, referer: str) -> Optional[str]:
        """
        Fetch phone number via AJAX endpoint

        Args:
            listing_id: Listing ID
            hash_val: Security hash from detail page
            referer: Referer URL path

        Returns:
            Phone number or None
        """
        try:
            payload = {
                'act': 'telshow',
                'id': listing_id,
                't': 'product',
                'h': hash_val,
                'rf': referer
            }

            async with self.session.post(self.AJAX_URL, data=payload) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get('ok') == 1 and 'tel' in data:
                        phone = data['tel']
                        # Clean phone number
                        digits_only = re.sub(r'\D', '', phone)
                        return digits_only

                return None

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return None

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

                # Extract listing ID from URL (e.g., /kia-cerato-2016-il-17470.html -> 17470)
                listing_id = None
                id_match = re.search(r'-(\d+)\.html$', listing_url)
                if id_match:
                    listing_id = id_match.group(1)

                # Extract title
                title = None
                title_elem = soup.find('h1')
                if title_elem:
                    title = title_elem.get_text(strip=True)

                # Extract category
                category = None
                cat_link = soup.find('div', id='openhalf')
                if cat_link:
                    cat_elem = cat_link.find('a', title=True)
                    if cat_elem:
                        category = cat_elem.get_text(strip=True)

                # Extract price
                price = None
                price_elem = soup.find('span', class_='pricecolor')
                if price_elem:
                    price = price_elem.get_text(strip=True)

                # Extract description
                description = None
                desc_elem = soup.find('p', class_='infop100')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)

                # Extract location
                location = None
                location_elem = soup.find('span', class_='glyphicon-map-marker')
                if location_elem and location_elem.parent:
                    location_text = location_elem.parent.get_text(strip=True)
                    # Remove icon text
                    location = location_text.replace('', '').strip()

                # Extract phone data attributes
                tel_div = soup.find('div', {'id': 'telshow'})

                phone_number = None
                if tel_div:
                    item_id = tel_div.get('data-id')
                    hash_val = tel_div.get('data-h')

                    if item_id and hash_val:
                        # Extract referer from URL path
                        referer = listing_url.replace(self.BASE_URL + '/', '')

                        # Fetch phone via AJAX
                        phone_number = await self.fetch_phone_via_ajax(item_id, hash_val, referer)

                return {
                    'listing_id': listing_id,
                    'title': title,
                    'category': category,
                    'price': price,
                    'location': location,
                    'description': description,
                    'phone_number': phone_number,
                    'url': listing_url
                }

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"   ✗ Error scraping {listing_url}: {e}")
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
                'category': listing_data.get('category'),
                'price': listing_data.get('price'),
                'location': listing_data.get('location'),
                'description': listing_data.get('description'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'masinlar.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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
        print("MASINLAR.AZ Scraper - Car Rental & Sales")
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
            print(f"   Page {page_num + 1}: Found {len(listing_urls)} listings")

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

            # Get phone number
            phone_number = listing_data.get('phone_number')

            if not phone_number:
                # No phone number found
                continue

            # Validate phone number
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
        print("Scraping Complete - MASINLAR.AZ")
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
    async with MasinlarAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)  # Test with 3 pages

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
