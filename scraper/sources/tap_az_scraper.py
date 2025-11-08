"""
TAP.AZ Scraper - Classifieds Listings

Scrapes classified listings from tap.az with:
- JSON API for paginated listings
- Phone number API endpoint for contact extraction
- HTML parsing for detail page data
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


class TapAzScraper:
    """Scraper for tap.az classified listings"""

    BASE_URL = "https://tap.az"
    SECTIONS_URL = "https://tap.az/sections"
    PHONES_API = "https://tap.az/ads/{ad_id}/phones"

    def __init__(self, db_pool: SimpleConnectionPool):
        """Initialize scraper with database connection pool"""
        self.db_pool = db_pool
        self.session: Optional[aiohttp.ClientSession] = None
        self.csrf_token: Optional[str] = None
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
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Referer': 'https://tap.az/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

        # Get CSRF token from main page
        await self._fetch_csrf_token()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _fetch_csrf_token(self):
        """Fetch CSRF token from main page"""
        try:
            async with self.session.get(self.BASE_URL) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Find CSRF token in meta tag
                    csrf_meta = soup.find('meta', {'name': 'csrf-token'})
                    if csrf_meta:
                        self.csrf_token = csrf_meta.get('content')
        except Exception as e:
            print(f"   ✗ Error fetching CSRF token: {e}")

    async def fetch_listings_page(self, page_num: int) -> Optional[Dict]:
        """
        Fetch a page of listings from API

        Args:
            page_num: Page number (starts at 1)

        Returns:
            API response dict or None
        """
        try:
            params = {'page': page_num}

            async with self.session.get(self.SECTIONS_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"   ✗ Failed to fetch page {page_num} (HTTP {response.status})")
                    return None

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching page {page_num}")
            return None
        except Exception as e:
            print(f"   ✗ Error fetching page {page_num}: {e}")
            return None

    async def fetch_ad_phones(self, ad_id: int) -> List[str]:
        """
        Fetch phone numbers for a specific ad

        Args:
            ad_id: Advertisement ID

        Returns:
            List of phone numbers
        """
        try:
            url = self.PHONES_API.format(ad_id=ad_id)

            # Add CSRF token to headers if available
            headers = {}
            if self.csrf_token:
                headers['X-CSRF-Token'] = self.csrf_token

            async with self.session.post(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # API returns {"phones": ["(051) 207-44-44"]}
                    phones = data.get('phones', [])

                    # Clean phone numbers (remove formatting)
                    cleaned_phones = []
                    for phone in phones:
                        # Remove all non-digit characters
                        digits_only = re.sub(r'\D', '', phone)
                        if digits_only:
                            cleaned_phones.append(digits_only)

                    return cleaned_phones
                else:
                    # Silently skip if phone fetch fails
                    return []

        except asyncio.TimeoutError:
            return []
        except Exception as e:
            return []

    async def fetch_ad_details(self, ad_url: str) -> Optional[Dict]:
        """
        Fetch advertisement detail page

        Args:
            ad_url: URL of the ad

        Returns:
            Dict with ad data or None
        """
        try:
            async with self.session.get(ad_url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Extract title
                title = None
                title_elem = soup.find('div', class_='product-properties__i-name')
                if title_elem:
                    # Try to get from product name
                    name_elem = soup.find('div', class_='products-name')
                    if name_elem:
                        title = name_elem.get_text(strip=True)

                # Extract price
                price = None
                price_elem = soup.find('span', class_='price-val')
                if price_elem:
                    price_val = price_elem.get_text(strip=True)
                    cur_elem = soup.find('span', class_='price-cur')
                    if cur_elem:
                        price = f"{price_val} {cur_elem.get_text(strip=True)}"

                # Extract city/location
                location = None
                city_elem = soup.find('label', string='Şəhir')
                if city_elem and city_elem.parent:
                    location_span = city_elem.parent.find('span', class_='product-properties__i-value')
                    if location_span:
                        location = location_span.get_text(strip=True)

                # Extract category
                category = None
                cat_elem = soup.find('label', string='Malın növü')
                if cat_elem and cat_elem.parent:
                    cat_link = cat_elem.parent.find('a')
                    if cat_link:
                        category = cat_link.get_text(strip=True)

                # Extract description
                description = None
                desc_elem = soup.find('div', class_='product-description__content')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)

                # Extract shop info if available
                shop_name = None
                shop_elem = soup.find('span', class_='product-shop__owner-name')
                if shop_elem:
                    shop_name = shop_elem.get_text(strip=True)

                return {
                    'title': title,
                    'price': price,
                    'location': location,
                    'category': category,
                    'description': description,
                    'shop_name': shop_name,
                    'url': ad_url
                }

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return None

    def save_lead(self, phone_number: str, ad_data: Dict) -> bool:
        """
        Save lead to database

        Args:
            phone_number: Validated phone number
            ad_data: Advertisement data dict

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
                'ad_id': ad_data.get('ad_id'),
                'title': ad_data.get('title'),
                'price': ad_data.get('price'),
                'location': ad_data.get('location'),
                'category': ad_data.get('category'),
                'description': ad_data.get('description'),
                'shop_name': ad_data.get('shop_name'),
                'source_url': ad_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'tap.az', ad_data.get('url'), psycopg2.extras.Json(full_data)))

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
        print("TAP.AZ Scraper - Classifieds")
        print(f"{'='*70}\n")

        all_ad_ids = []

        # Fetch ad IDs from pagination pages
        print(f"📋 Fetching ad listings from {max_pages} pages...")
        for page_num in range(1, max_pages + 1):
            response = await self.fetch_listings_page(page_num)

            if not response:
                print(f"   Page {page_num}: No data found, stopping pagination")
                break

            # Extract ad IDs from home_product_ids array
            ad_ids = response.get('home_product_ids', [])

            if not ad_ids:
                print(f"   Page {page_num}: No ads found, stopping pagination")
                break

            all_ad_ids.extend(ad_ids)
            print(f"   Page {page_num}/{max_pages}: Found {len(ad_ids)} ads")

            # Small delay between pages
            await asyncio.sleep(0.5)

        self.stats['total_listings'] = len(all_ad_ids)
        print(f"\n✓ Found {len(all_ad_ids)} ad listings\n")

        # Fetch details for each ad
        print(f"🔍 Fetching ad details and phone numbers...\n")

        for idx, ad_id in enumerate(all_ad_ids, 1):
            # Progress indicator
            if idx % 10 == 0 or idx == 1:
                print(f"   Progress: {idx}/{len(all_ad_ids)} ads...")

            # Build ad URL
            # We'll need to fetch the detail page to get category/slug, so we'll use a generic pattern
            # Format: /elanlar/{category}/{slug}/{ad_id}
            # Since we only have ID from API, we'll construct a direct URL
            ad_url = f"{self.BASE_URL}/elanlar/elektronika/plansetler/{ad_id}"

            # Try to fetch detail page first to get actual URL
            # The detail page will have the correct URL structure
            try:
                # First, try to fetch phones directly
                phones = await self.fetch_ad_phones(ad_id)

                if not phones:
                    # No phone numbers found
                    continue

                # Fetch ad details (we need this for additional info)
                ad_data = await self.fetch_ad_details(ad_url)

                if not ad_data:
                    # Create minimal data structure
                    ad_data = {
                        'ad_id': ad_id,
                        'url': ad_url
                    }
                else:
                    ad_data['ad_id'] = ad_id

                # Validate and save each phone number
                for phone in phones:
                    validated_phone = PhoneValidator.validate_phone(phone)

                    if not validated_phone:
                        self.stats['invalid_phones'] += 1
                        continue

                    # Save to database
                    is_new = self.save_lead(validated_phone, ad_data)

                    if is_new:
                        self.stats['new_leads'] += 1
                    else:
                        self.stats['duplicates'] += 1

            except Exception as e:
                self.stats['errors'] += 1
                continue

            # Small delay between requests
            await asyncio.sleep(0.3)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - TAP.AZ")
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
    async with TapAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)  # Test with 3 pages

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
