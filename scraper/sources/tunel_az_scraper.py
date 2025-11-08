"""
TUNEL.AZ Scraper - Car Listings

Scrapes car listings from tunel.az using their API:
- API-based listing pagination
- Individual car detail API for phone numbers
- JSON response parsing
"""
import asyncio
import aiohttp
import json
from typing import List, Dict, Optional
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class TunelAzScraper:
    """Scraper for tunel.az car listings using API"""

    BASE_URL = "https://tunel.az"
    API_BASE = "https://api.tunel.az/api"
    ANNOUNCEMENTS_URL = f"{API_BASE}/announcements"

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
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Origin': 'https://tunel.az',
            'Referer': 'https://tunel.az/',
            'x-device-id': '8C8637DB-99D1-44EB-BC4D-34B3D25C0F3B',
            'x-browser': 'Chrome',
            'x-device-type': 'web',
            'x-os': 'Mac OS',
            'x-timezone': 'Asia/Baku',
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_listings_page(self, page_num: int) -> Optional[Dict]:
        """
        Fetch a page of car listings from API

        Args:
            page_num: Page number (starts at 1)

        Returns:
            API response dict or None
        """
        try:
            params = {
                'page': page_num,
                'limit': 24,
                'announcement_type': 'sale',
                'excluded_extra_types': 'masters'
            }

            async with self.session.get(self.ANNOUNCEMENTS_URL, params=params) as response:
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

    async def fetch_announcement_details(self, slug: str) -> Optional[Dict]:
        """
        Fetch individual announcement details including phone number

        Args:
            slug: Announcement slug

        Returns:
            Announcement details dict or None
        """
        try:
            url = f"{self.ANNOUNCEMENTS_URL}/{slug}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    # Silently skip failed requests (some listings may be removed)
                    return None

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return None

    def save_lead(self, phone_number: str, announcement_data: Dict) -> bool:
        """
        Save lead to database

        Args:
            phone_number: Validated phone number
            announcement_data: Announcement data dict

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

            # Extract data from nested structure
            data = announcement_data.get('data', {})

            # Prepare full_data JSON
            full_data = {
                'announcement_id': data.get('id'),
                'slug': data.get('slug'),
                'title': data.get('title'),
                'price': data.get('price'),
                'currency': data.get('currency'),
                'year': data.get('year'),
                'mileage': data.get('mileage'),
                'brand': data.get('brand', {}).get('name'),
                'model': data.get('model', {}).get('name'),
                'region': data.get('region', {}).get('name'),
                'city': data.get('city', {}).get('name'),
                'description': data.get('description'),
                'source_url': f"{self.BASE_URL}/announcement/{data.get('slug')}"
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'tunel.az', full_data['source_url'], psycopg2.extras.Json(full_data)))

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
        print("TUNEL.AZ Scraper - Car Listings")
        print(f"{'='*70}\n")

        all_slugs = []

        # Fetch announcement slugs from pagination pages
        print(f"📋 Fetching car listings from {max_pages} pages...")
        for page_num in range(1, max_pages + 1):
            response = await self.fetch_listings_page(page_num)

            if not response or 'data' not in response:
                print(f"   Page {page_num}: No data found, stopping pagination")
                break

            items = response.get('data', {}).get('items', [])
            if not items:
                print(f"   Page {page_num}: No announcements found, stopping pagination")
                break

            # Extract slugs
            page_slugs = [item['slug'] for item in items if 'slug' in item]
            all_slugs.extend(page_slugs)

            total = response.get('data', {}).get('total', 0)
            print(f"   Page {page_num}/{max_pages}: Found {len(page_slugs)} announcements (Total available: {total})")

            # Small delay between pages
            await asyncio.sleep(0.5)

        self.stats['total_listings'] = len(all_slugs)
        print(f"\n✓ Found {len(all_slugs)} car announcements\n")

        # Fetch details for each announcement
        print(f"🔍 Fetching announcement details and phone numbers...\n")

        for idx, slug in enumerate(all_slugs, 1):
            # Progress indicator
            if idx % 10 == 0 or idx == 1:
                print(f"   Progress: {idx}/{len(all_slugs)} announcements...")

            # Fetch announcement details
            announcement_data = await self.fetch_announcement_details(slug)

            if not announcement_data:
                self.stats['errors'] += 1
                continue

            # Extract phone number from publishment data
            data = announcement_data.get('data', {})
            publishment = data.get('publishment', {})
            phone = publishment.get('phone')

            if not phone:
                # No phone number found
                continue

            # Convert phone to string
            phone_str = str(phone)

            # Validate phone number
            validated_phone = PhoneValidator.validate_phone(phone_str)

            if not validated_phone:
                self.stats['invalid_phones'] += 1
                continue

            # Save to database
            is_new = self.save_lead(validated_phone, announcement_data)

            if is_new:
                self.stats['new_leads'] += 1
            else:
                self.stats['duplicates'] += 1

            # Small delay between requests
            await asyncio.sleep(0.2)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - TUNEL.AZ")
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
    async with TunelAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)  # Test with 3 pages

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
