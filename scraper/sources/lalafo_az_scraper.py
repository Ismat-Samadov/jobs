"""
Lalafo.az scraper - General classifieds website
Extracts phone numbers from various listing categories via API
"""

import aiohttp
import asyncio
import sys
import os
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.validator import PhoneValidator
import psycopg2.pool
from dotenv import load_dotenv


class LalafoAzScraper:
    """Scraper for lalafo.az classifieds using their API"""

    BASE_URL = "https://lalafo.az"
    API_URL = f"{BASE_URL}/api/search/v3/feed"

    def __init__(self, pool):
        """Initialize scraper with database connection pool"""
        self.pool = pool
        self.stats = {
            'total_listings': 0,
            'extracted_phones': 0,
            'saved_phones': 0,
            'duplicates': 0,
            'invalid_phones': 0,
            'errors': 0
        }

    async def fetch_api_page(self, session, page, m_next_value=None, timeout=30):
        """Fetch a page from the API with error handling"""
        try:
            # Base parameters
            params = {
                'expand': 'url',
                'page': page,
                'per-page': 20,
                'vip_count': 5,
            }

            # Add pagination cursor if available (for pages after first)
            if m_next_value:
                params['m-name'] = 'last_push_up'
                params['m-next-value'] = m_next_value
                params['sub-empty'] = 1

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
                'Referer': 'https://lalafo.az/',
                'country-id': '13',
                'device': 'pc',
                'language': 'az_AZ',
            }

            async with session.get(self.API_URL, params=params, headers=headers, timeout=timeout, ssl=False) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"  ❌ Failed to fetch page {page}: Status {response.status}")
                    return None
        except Exception as e:
            print(f"  ❌ Error fetching page {page}: {e}")
            return None

    def extract_listing_data(self, item):
        """Extract full listing data from API item"""
        data = {
            'source': 'lalafo.az',
            'listing_id': item.get('id'),
            'listing_url': f"{self.BASE_URL}{item.get('url', '')}",
            'scraped_at': datetime.now().isoformat()
        }

        # Basic info
        data['title'] = item.get('title', '')
        data['description'] = item.get('description', '')
        data['city'] = item.get('city', '')
        data['city_alias'] = item.get('city_alias', '')

        # Price information
        if item.get('price'):
            data['price'] = {
                'amount': item.get('price'),
                'currency': item.get('currency', ''),
                'symbol': item.get('symbol', ''),
                'old_price': item.get('old_price'),
                'is_negotiable': item.get('is_negotiable', False)
            }

        # Location
        if item.get('lat') and item.get('lng'):
            data['location'] = {
                'lat': item.get('lat'),
                'lng': item.get('lng')
            }

        # Stats
        data['stats'] = {
            'views': item.get('views', 0),
            'impressions': item.get('impressions', 0),
            'favorite_count': item.get('favorite_count', 0),
            'callers_count': item.get('callers_count', 0),
            'writers_count': item.get('writers_count', 0)
        }

        # Listing status
        data['status'] = {
            'is_vip': item.get('is_vip', False),
            'is_select': item.get('is_select', False),
            'is_premium': item.get('is_premium', False),
        }

        # Category
        data['category_id'] = item.get('category_id')
        data['ad_label'] = item.get('ad_label')

        # Dates
        if item.get('created_time'):
            data['created_at'] = datetime.fromtimestamp(item.get('created_time')).isoformat()
        if item.get('updated_time'):
            data['updated_at'] = datetime.fromtimestamp(item.get('updated_time')).isoformat()

        # Images
        images = item.get('images', [])
        if images:
            data['images'] = [
                {
                    'id': img.get('id'),
                    'url': img.get('thumbnail_url', img.get('original_url', '')),
                    'is_main': img.get('is_main', False)
                }
                for img in images[:10]  # Limit to 10 images
            ]

        # User/Seller info
        user = item.get('user', {})
        if user:
            data['seller'] = {
                'id': user.get('id'),
                'username': user.get('username', ''),
                'is_pro': user.get('pro', False),
                'response_rate': user.get('response_rate'),
                'response_time': user.get('response_time'),
                'response_info': user.get('response_info', '')
            }
            if user.get('avatar'):
                data['seller']['avatar'] = user.get('avatar')

        # Additional parameters
        if item.get('params'):
            data['parameters'] = item.get('params')

        return data

    async def save_lead(self, phone, url, full_data):
        """Save a lead to the database"""
        try:
            conn = self.pool.getconn()
            cursor = conn.cursor()

            # Insert with ON CONFLICT to handle duplicates
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (phone_number) DO NOTHING
                RETURNING id;
            """, (
                phone,
                'lalafo.az',
                url,
                full_data
            ))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            self.pool.putconn(conn)

            return result is not None  # True if inserted, False if duplicate

        except Exception as e:
            print(f"  ❌ Error saving lead {phone}: {e}")
            self.stats['errors'] += 1
            if 'conn' in locals():
                conn.rollback()
                self.pool.putconn(conn)
            return False

    async def process_listing(self, item):
        """Process a single listing item from API response"""
        self.stats['total_listings'] += 1

        # Extract phone number from mobile field
        phone_raw = item.get('mobile')
        if not phone_raw:
            return

        self.stats['extracted_phones'] += 1

        # Validate phone
        validated_phone = PhoneValidator.validate_phone(phone_raw)
        if not validated_phone:
            self.stats['invalid_phones'] += 1
            return

        # Extract full listing data
        full_data = self.extract_listing_data(item)

        # Convert to JSON string
        full_data_json = json.dumps(full_data, ensure_ascii=False)

        # Build listing URL
        listing_url = f"{self.BASE_URL}{item.get('url', '')}"

        # Save to database
        was_saved = await self.save_lead(validated_phone, listing_url, full_data_json)

        if was_saved:
            self.stats['saved_phones'] += 1
            print(f"    ✓ Saved: {validated_phone} - {full_data.get('title', '')[:50]}")
        else:
            self.stats['duplicates'] += 1

    async def scrape(self, pages=5, concurrency=10):
        """Main scraping function"""
        print(f"\n🔍 Starting Lalafo.az scraper (pages: {pages}, concurrency: {concurrency})")

        # Create aiohttp session
        connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            m_next_value = None

            for page_num in range(1, pages + 1):
                print(f"  📄 Scraping page {page_num}...")

                # Fetch API response
                api_response = await self.fetch_api_page(session, page_num, m_next_value)

                if not api_response:
                    print(f"    ⚠️ Failed to fetch page {page_num}, skipping...")
                    continue

                # Get items from response
                items = api_response.get('items', [])
                if not items:
                    print(f"    ⚠️ No items found on page {page_num}")
                    break

                print(f"    Found {len(items)} listings on page {page_num}")

                # Process all listings on this page
                for item in items:
                    await self.process_listing(item)

                # Extract m_next_value for next page from the _links or last item
                # The m_next_value is the last_push_up value from the last item
                if items:
                    last_item = items[-1]
                    m_next_value = last_item.get('last_push_up')

                # Be polite with rate limiting
                await asyncio.sleep(1)

        # Print final stats
        print(f"\n✅ Lalafo.az scraping completed!")
        print(f"  📊 Stats:")
        print(f"    Total listings: {self.stats['total_listings']}")
        print(f"    Extracted phones: {self.stats['extracted_phones']}")
        print(f"    Saved phones: {self.stats['saved_phones']}")
        print(f"    Duplicates: {self.stats['duplicates']}")
        print(f"    Invalid phones: {self.stats['invalid_phones']}")
        print(f"    Errors: {self.stats['errors']}")

        return self.stats


async def main():
    """Test function"""
    load_dotenv()

    # Create database pool
    pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        scraper = LalafoAzScraper(pool)
        await scraper.scrape(pages=5, concurrency=10)
    finally:
        pool.closeall()


if __name__ == '__main__':
    asyncio.run(main())
