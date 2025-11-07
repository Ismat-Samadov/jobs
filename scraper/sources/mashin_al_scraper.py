"""
MASHIN.AL Scraper - Car Listings

Scrapes car listings from mashin.al using their API:
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


class MashinAlScraper:
    """Scraper for mashin.al car listings using API"""

    BASE_URL = "https://mashin.al"
    API_URL = "https://v2.mashin.al/api/v2/car"

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
            'Origin': 'https://mashin.al',
            'Referer': 'https://mashin.al/',
            'locale': 'az',
            'breakpointm': 'true',
            'ptk': 'E0AF1DB4-E797-4796-9150-3DECEA5CF26A',
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
            url = f"{self.API_URL}?page={page_num}"

            # Payload for POST request
            payload = {
                "sort_by": "created_at",
                "sort_order": "desc",
                "additional_brands": {"0": {}, "1": {}, "2": {}, "3": {}, "4": {}},
                "exclude_additional_brands": {"0": {}, "1": {}, "2": {}, "3": {}, "4": {}},
                "all_options": {},
                "announce_type": 0,
                "currency": 1
            }

            async with self.session.post(url, json=payload) as response:
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

    async def fetch_car_details(self, car_id: int) -> Optional[Dict]:
        """
        Fetch individual car details including phone number

        Args:
            car_id: Car listing ID

        Returns:
            Car details dict or None
        """
        try:
            url = f"{self.API_URL}/{car_id}"

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

    def save_lead(self, phone_number: str, car_data: Dict) -> bool:
        """
        Save lead to database

        Args:
            phone_number: Validated phone number
            car_data: Car data dict

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
                'car_id': car_data.get('id'),
                'id_unique': car_data.get('id_unique'),
                'brand': car_data.get('brand'),
                'model': car_data.get('model'),
                'year': car_data.get('year'),
                'price': car_data.get('price'),
                'mileage': car_data.get('mileage'),
                'region': car_data.get('region', {}).get('name'),
                'car_number': car_data.get('car_number'),
                'comment': car_data.get('comment'),
                'source_url': f"{self.BASE_URL}/masinlar/{car_data.get('id')}"
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'mashin.al', full_data['source_url'], psycopg2.extras.Json(full_data)))

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
        print("MASHIN.AL Scraper - Car Listings")
        print(f"{'='*70}\n")

        all_car_ids = []

        # Fetch car IDs from pagination pages
        print(f"📋 Fetching car listings from {max_pages} pages...")
        for page_num in range(1, max_pages + 1):
            response = await self.fetch_listings_page(page_num)

            if not response or 'data' not in response:
                print(f"   Page {page_num}: No data found, stopping pagination")
                break

            cars = response['data']
            if not cars:
                print(f"   Page {page_num}: No cars found, stopping pagination")
                break

            # Extract car IDs
            page_car_ids = [car['id'] for car in cars if 'id' in car]
            all_car_ids.extend(page_car_ids)

            meta = response.get('meta', {})
            total_pages = meta.get('total_pages', 0)

            print(f"   Page {page_num}/{max_pages}: Found {len(page_car_ids)} cars (Total available: {meta.get('total', 0)} cars)")

            # Small delay between pages
            await asyncio.sleep(0.5)

        self.stats['total_listings'] = len(all_car_ids)
        print(f"\n✓ Found {len(all_car_ids)} car listings\n")

        # Fetch details for each car
        print(f"🔍 Fetching car details and phone numbers...\n")

        for idx, car_id in enumerate(all_car_ids, 1):
            # Progress indicator
            if idx % 10 == 0 or idx == 1:
                print(f"   Progress: {idx}/{len(all_car_ids)} cars...")

            # Fetch car details
            car_data = await self.fetch_car_details(car_id)

            if not car_data:
                self.stats['errors'] += 1
                continue

            # Extract phone number from user data
            user = car_data.get('user', {})
            phone = user.get('phone')

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
            is_new = self.save_lead(validated_phone, car_data)

            if is_new:
                self.stats['new_leads'] += 1
            else:
                self.stats['duplicates'] += 1

            # Small delay between requests
            await asyncio.sleep(0.2)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - MASHIN.AL")
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
    async with MashinAlScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)  # Test with 3 pages

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
