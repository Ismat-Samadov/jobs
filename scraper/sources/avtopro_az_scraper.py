"""
Avtopro.az scraper - Car registration number plates marketplace
"""
import asyncio
import aiohttp
from typing import Dict, List
from datetime import datetime
import json
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.validator import PhoneValidator

load_dotenv()


class AvtoproAzScraperAsync:
    """Async scraper for avtopro.az registration number plates"""

    def __init__(self, max_concurrent: int = 5):
        self.base_url = "https://api.avtopro.az/api/register_numbers"
        self.website_url = "https://avtopro.az"
        self.database_url = os.getenv('DATABASE_URL')
        self.max_concurrent = max_concurrent

        # Initialize database connection pool
        self.db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, self.database_url)

        # Anti-blocking headers (removed zstd encoding as aiohttp doesn't support it)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Origin': 'https://avtopro.az',
            'Referer': 'https://avtopro.az/',
            'DNT': '1',
            'Sec-CH-UA': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }

    async def fetch_page(self, session: aiohttp.ClientSession, page_number: int) -> Dict:
        """Fetch a single page from the API"""
        params = {
            'paginate': 30,
            'number': '',
            'page': page_number
        }

        try:
            async with session.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    # Let aiohttp handle JSON decoding automatically
                    data = await response.json()

                    if data.get('success') and data.get('data'):
                        return data['data']
                else:
                    print(f"Failed to fetch page {page_number} (HTTP {response.status})")

        except Exception as e:
            print(f"Error fetching page {page_number}: {e}")

        return None

    def save_to_database(self, phone_number: str, source_url: str, full_data: Dict = None) -> bool:
        """Save lead to database with validation"""
        # Validate phone number
        validated_phone = PhoneValidator.validate_phone(phone_number)

        if not validated_phone:
            return False

        conn = None
        try:
            conn = self.db_pool.getconn()
            cur = conn.cursor()

            query = """
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (phone_number)
                DO UPDATE SET
                    full_data = EXCLUDED.full_data,
                    source = EXCLUDED.source
                RETURNING id
            """

            full_data_json = json.dumps(full_data, ensure_ascii=False) if full_data else None
            cur.execute(query, (validated_phone, 'avtopro.az', source_url, full_data_json))
            conn.commit()

            result = cur.fetchone()
            cur.close()
            self.db_pool.putconn(conn)

            return True if result else False

        except Exception as e:
            if conn:
                self.db_pool.putconn(conn)
            print(f"Database error: {e}")
            return False

    async def process_listing(self, listing: Dict) -> Dict:
        """Process a single listing"""
        result = {
            'id': listing.get('id'),
            'success': False,
            'saved': False
        }

        # Get phone number
        phone = listing.get('author_phone', '').strip()
        if not phone:
            return result

        # Build full_data structure
        full_data = {
            'listing_type': 'registration_number',
            'listing_id': listing.get('id', ''),
            'region_number_id': listing.get('region_number_id', ''),
            'first_letter': listing.get('first_letter', ''),
            'second_letter': listing.get('second_letter', ''),
            'number': listing.get('number', ''),
            'full_number': f"{listing.get('region_number_id', '')}-{listing.get('first_letter', '')}{listing.get('second_letter', '')}-{listing.get('number', '')}",
            'price': listing.get('price', ''),
            'currency': listing.get('currency', ''),
            'city_id': listing.get('city_id', ''),
            'views': listing.get('views', ''),
            'author_name': listing.get('author_name', ''),
            'author_phone': listing.get('author_phone', ''),
            'description': listing.get('description', ''),
            'status': listing.get('status', ''),
            'created_at': listing.get('created_at', ''),
            'updated_at': listing.get('updated_at', ''),
            'region': listing.get('region', {}),
            'city': listing.get('city', {})
        }

        # Construct source URL
        source_url = f"{self.website_url}/register-numbers/{listing.get('id', '')}"

        result['success'] = True

        # Save to database
        if self.save_to_database(phone, source_url, full_data):
            result['saved'] = True

        return result

    async def scrape_page(self, session: aiohttp.ClientSession, page_number: int) -> Dict[str, int]:
        """Scrape a single page"""
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'saved': 0
        }

        # Fetch page data
        page_data = await self.fetch_page(session, page_number)

        if not page_data or 'data' not in page_data:
            return stats

        listings = page_data['data']
        stats['total'] = len(listings)

        # Process all listings
        tasks = [self.process_listing(listing) for listing in listings]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate statistics
        for result in results:
            if isinstance(result, Exception):
                stats['failed'] += 1
            elif isinstance(result, dict):
                if result['success']:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1

                if result.get('saved'):
                    stats['saved'] += 1

        return stats

    async def scrape(self, **kwargs) -> Dict[str, int]:
        """
        Main scraping method

        Kwargs:
            pages (int): Number of pages to scrape (default: 5)
        """
        start_time = datetime.now()
        print(f"Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        pages = kwargs.get('pages', 5)

        total_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'saved': 0
        }

        # Create aiohttp session
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Scrape all pages
            for page in range(1, pages + 1):
                print(f"Scraping page {page}/{pages}...")

                stats = await self.scrape_page(session, page)

                total_stats['total'] += stats['total']
                total_stats['success'] += stats['success']
                total_stats['failed'] += stats['failed']
                total_stats['saved'] += stats['saved']

                print(f"  Page {page}: Found {stats['total']} listings, Saved {stats['saved']}")

                # Rate limiting - wait 1 second between pages
                if page < pages:
                    await asyncio.sleep(1)

        # Print summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\nCompleted in {duration:.2f}s | Found: {total_stats['total']} | Saved: {total_stats['saved']} | Failed: {total_stats['failed']}")

        # Add timing info for main.py
        total_stats['duration'] = duration
        total_stats['start_time'] = start_time

        return total_stats

    def close(self):
        """Close database connection pool"""
        if self.db_pool:
            self.db_pool.closeall()


async def main():
    """Main function to run the scraper standalone"""
    scraper = AvtoproAzScraperAsync(max_concurrent=5)

    try:
        stats = await scraper.scrape(pages=5)

        print("\n" + "="*50)
        print("SCRAPING SUMMARY")
        print("="*50)
        print(f"Total listings found: {stats['total']}")
        print(f"Successfully extracted: {stats['success']}")
        print(f"Failed to extract: {stats['failed']}")
        print(f"Saved to database: {stats['saved']}")
        print(f"Time taken: {stats['duration']:.2f} seconds")
        print("="*50)
    finally:
        scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
