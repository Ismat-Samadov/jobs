"""
MYHOME.AZ Scraper - Real Estate Property Listings

Scrapes property listings from myhome.az with:
- REST API for paginated property listings
- Phone number extraction from user_id
- Comprehensive property data extraction
"""
import asyncio
import aiohttp
import re
import json
from typing import List, Dict, Optional
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import sys
import os
from urllib.parse import urlencode

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class MyhomeAzScraper:
    """Scraper for myhome.az real estate property listings"""

    BASE_URL = "https://myhome.az"
    API_URL = "https://myhome.az/api/v1/announcement/list"
    PHONE_API_URL = "https://api.myhome.az/api/announcement/phone/{announcement_id}"

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
        # Headers to mimic real browser for main API
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Referer': 'https://myhome.az/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'authorization': 'Bearer undefined',
            'access-control-allow-origin': '*'
        }

        # Headers for phone API (same-site CORS)
        self.phone_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Origin': 'https://myhome.az',
            'Referer': 'https://myhome.az/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site'
        }

        self.session = aiohttp.ClientSession(timeout=timeout, headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_listings_page(self, page: int = 1) -> Optional[Dict]:
        """
        Fetch a page of listings using REST API

        Args:
            page: Page number (starts from 1)

        Returns:
            API response data or None
        """
        try:
            # Build API URL with page parameter
            url = f"{self.API_URL}?page={page}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"   ✗ Failed to fetch listings (HTTP {response.status})")
                    return None

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching listings page {page}")
            return None
        except Exception as e:
            print(f"   ✗ Error fetching listings page {page}: {e}")
            return None

    async def fetch_announcement_phone(self, announcement_id: int) -> Optional[str]:
        """
        Fetch phone number for a specific announcement using phone API

        Args:
            announcement_id: Announcement ID

        Returns:
            Phone number or None
        """
        try:
            url = self.PHONE_API_URL.format(announcement_id=announcement_id)

            # Use phone_headers for same-site CORS
            async with self.session.get(url, headers=self.phone_headers) as response:
                if response.status == 200:
                    # API returns plain text phone number like: +994773467301
                    phone_text = await response.text()

                    # Clean the phone number
                    if phone_text:
                        # Remove + and country code prefix
                        cleaned = re.sub(r'\D', '', phone_text)
                        if len(cleaned) >= 9:
                            return cleaned[-9:]  # Get last 9 digits (Azerbaijan format)
                    return None
                else:
                    # Silently skip if phone fetch fails
                    return None

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            # Silently skip errors
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

            # Prepare full_data JSON with all listing details
            full_data = {
                'announcement_id': listing_data.get('id'),
                'title': listing_data.get('title'),
                'price': listing_data.get('price'),
                'area': listing_data.get('area'),
                'room_count': listing_data.get('room_count'),
                'floor': listing_data.get('floor'),
                'floor_count': listing_data.get('floor_count'),
                'house_area': listing_data.get('house_area'),
                'address': listing_data.get('address'),
                'city': listing_data.get('city'),
                'region': listing_data.get('region'),
                'village': listing_data.get('village'),
                'formatted_date': listing_data.get('formatted_date'),
                'is_vip': listing_data.get('is_vip'),
                'is_premium': listing_data.get('is_premium'),
                'rental_type': listing_data.get('rental_type'),
                'credit_possible': listing_data.get('credit_possible'),
                'in_credit': listing_data.get('in_credit'),
                'document_id': listing_data.get('document_id'),
                'is_repaired': listing_data.get('is_repaired'),
                'metro_stations': listing_data.get('metro_stations', []),
                'main_image': listing_data.get('main_image_thumb'),
                'source_url': listing_data.get('url'),
                'user_id': listing_data.get('user_id')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'myhome.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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

    async def process_listing(self, item: Dict) -> Dict:
        """
        Process a single listing - extract data and fetch phone numbers

        Args:
            item: Announcement item data

        Returns:
            Processing result dict
        """
        result = {
            'announcement_id': item.get('id'),
            'phones_found': 0,
            'phones_saved': 0
        }

        try:
            announcement_id = item.get('id')
            if not announcement_id:
                return result

            # Build full listing URL
            listing_url = f"{self.BASE_URL}/announcement/{announcement_id}"

            # Extract address info
            address_data = item.get('address', {})
            city_name = address_data.get('city', {}).get('name') if address_data.get('city') else None
            region_name = address_data.get('region', {}).get('name') if address_data.get('region') else None
            village_name = address_data.get('village', {}).get('name') if address_data.get('village') else None

            # Extract listing data
            listing_data = {
                'id': announcement_id,
                'url': listing_url,
                'title': item.get('title'),
                'price': item.get('price'),
                'area': item.get('area'),
                'room_count': item.get('room_count'),
                'floor': item.get('floor'),
                'floor_count': item.get('floor_count'),
                'house_area': item.get('house_area'),
                'description': item.get('description'),
                'address': address_data.get('address'),
                'city': city_name,
                'region': region_name,
                'village': village_name,
                'formatted_date': item.get('formatted_date'),
                'is_vip': item.get('is_vip'),
                'is_premium': item.get('is_premium'),
                'rental_type': item.get('rental_type'),
                'credit_possible': item.get('credit_possible'),
                'in_credit': item.get('in_credit'),
                'document_id': item.get('document_id'),
                'is_repaired': item.get('is_repaired'),
                'metro_stations': [station.get('name') for station in item.get('metro_stations', [])],
                'main_image_thumb': item.get('main_image_thumb'),
                'user_id': item.get('user_id')
            }

            # Fetch phone number from API
            phones = []
            phone = await self.fetch_announcement_phone(announcement_id)
            if phone:
                phones.append(phone)

            result['phones_found'] = len(phones)

            if not phones:
                return result

            # Validate and save each phone number
            for phone in phones:
                validated_phone = PhoneValidator.validate_phone(phone)

                if not validated_phone:
                    self.stats['invalid_phones'] += 1
                    continue

                # Save to database
                is_new = self.save_lead(validated_phone, listing_data)

                if is_new:
                    self.stats['new_leads'] += 1
                    result['phones_saved'] += 1
                else:
                    self.stats['duplicates'] += 1

            return result

        except Exception as e:
            print(f"   ✗ Error processing listing {result['announcement_id']}: {e}")
            self.stats['errors'] += 1
            return result

    async def scrape(self, max_pages: int = 5):
        """
        Main scraping method

        Args:
            max_pages: Maximum number of pages to scrape
        """
        print(f"\n{'='*70}")
        print("MYHOME.AZ Scraper - Real Estate Property Listings")
        print(f"{'='*70}\n")

        print(f"🔍 Scraping up to {max_pages} pages...\n")

        for page_num in range(1, max_pages + 1):
            print(f"   Page {page_num}/{max_pages}...")

            # Fetch listings page
            response_data = await self.fetch_listings_page(page_num)

            if not response_data:
                print(f"   ✗ Failed to fetch page {page_num}, stopping")
                break

            # Extract data from API response
            listings = response_data.get('data', [])
            meta = response_data.get('meta', {})

            if not listings:
                print(f"   No listings found on page {page_num}, stopping")
                break

            print(f"   Found {len(listings)} listings on page {page_num}")

            # Process each listing
            for item in listings:
                self.stats['total_listings'] += 1

                # Process listing (extract phones and save)
                await self.process_listing(item)

                # Small delay between processing
                await asyncio.sleep(0.3)

            # Check if there's a next page
            current_page = meta.get('current_page', page_num)
            last_page = meta.get('last_page', page_num)

            if current_page >= last_page:
                print(f"   Reached end of listings (page {current_page}/{last_page})")
                break

            # Small delay between pages
            await asyncio.sleep(0.5)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - MYHOME.AZ")
        print(f"{'='*70}")
        print(f"Total listings:    {self.stats['total_listings']:,}")
        print(f"New leads:         {self.stats['new_leads']:,}")
        print(f"Duplicates:        {self.stats['duplicates']:,}")
        print(f"Invalid phones:    {self.stats['invalid_phones']:,}")
        print(f"Errors:            {self.stats['errors']:,}")
        print(f"{'='*70}\n")

        return self.stats


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

    # Run scraper - scrape 3 pages for testing
    async with MyhomeAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
