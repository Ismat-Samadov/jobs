"""
AutoNet.AZ API Scraper

Scrapes license plate listings from autonet.az using their public API.
This is much more efficient than HTML scraping.

API Endpoints:
- List items: https://autonet.az/api/license_plates/searchItem/?page={page}
- Get details: https://autonet.az/api/license_plates/get/{id}
"""

import asyncio
import aiohttp
import os
import re
import json
import psycopg2
import psycopg2.extras
from psycopg2 import pool
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from scripts.validator import PhoneValidator

load_dotenv()


class AutoNetAzScraperAsync:
    def __init__(self, max_concurrent: int = 10):
        """
        Initialize the AutoNet.AZ scraper

        Args:
            max_concurrent: Maximum number of concurrent API requests
        """
        self.base_url = "https://autonet.az"
        self.api_url = f"{self.base_url}/api/license_plates"
        self.database_url = os.getenv('DATABASE_URL')
        self.max_concurrent = max_concurrent

        # Initialize database connection pool
        self.db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10, self.database_url
        )

        # Required headers based on the API request
        self.headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Authorization': 'Bearer null',
            'DNT': '1',
            'Origin': 'https://www.autonet.az',
            'Referer': 'https://www.autonet.az/',
            'Sec-CH-UA': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'X-Authorization': '00028c2ddcc1ca6c32bc919dca64c288bf32ff2a',
            'X-Requested-With': 'XMLHttpRequest'
        }

    def close(self):
        """Close database connection pool"""
        if self.db_pool:
            self.db_pool.closeall()

    async def fetch_listings_page(self, session: aiohttp.ClientSession, page: int) -> Optional[Dict]:
        """
        Fetch a page of license plate listings from the API

        Args:
            session: aiohttp session
            page: Page number to fetch

        Returns:
            API response data or None if failed
        """
        url = f"{self.api_url}/searchItem/?page={page}"

        try:
            async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"✗ Failed to fetch page {page}: HTTP {response.status}")
                    return None
        except Exception as e:
            print(f"✗ Error fetching page {page}: {e}")
            return None

    async def fetch_item_details(self, session: aiohttp.ClientSession, item_id: int) -> Optional[Dict]:
        """
        Fetch detailed information for a specific license plate listing

        Args:
            session: aiohttp session
            item_id: ID of the listing

        Returns:
            Item details or None if failed
        """
        url = f"{self.api_url}/get/{item_id}"

        try:
            async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    # API returns a list with one item
                    if data and len(data) > 0:
                        return data[0]
                    return None
                else:
                    print(f"✗ Failed to fetch item {item_id}: HTTP {response.status}")
                    return None
        except Exception as e:
            print(f"✗ Error fetching item {item_id}: {e}")
            return None

    def extract_phone_numbers(self, item: Dict) -> List[str]:
        """
        Extract phone numbers from item data

        Args:
            item: Item data from API

        Returns:
            List of phone numbers
        """
        phones = []

        # Extract phone1 and phone2
        for phone_field in ['phone1', 'phone2']:
            phone = item.get(phone_field)
            if phone:
                # Remove formatting: (050) 323-66-44 -> 0503236644
                cleaned = re.sub(r'[\s\-\(\)]', '', phone)
                if cleaned:
                    phones.append(cleaned)

        return phones

    def format_full_data(self, item: Dict) -> Dict:
        """
        Format item data into full_data structure for database

        Args:
            item: Item data from API

        Returns:
            Formatted data dictionary
        """
        # Format license plate number
        license_plate = f"{item.get('region_number', '')}-{item.get('first_a', '')}{item.get('second_a', '')}-{item.get('number', '')}"

        return {
            "listing_type": "license_plate",
            "title": f"License Plate {license_plate}",
            "price": {
                "amount": item.get('price'),
                "currency": item.get('currency', 'AZN')
            },
            "license_plate": {
                "full_number": license_plate,
                "region_number": item.get('region_number'),
                "first_letter": item.get('first_a'),
                "second_letter": item.get('second_a'),
                "number": item.get('number')
            },
            "seller": {
                "name": item.get('fullname'),
                "phone1": item.get('phone1'),
                "phone2": item.get('phone2')
            },
            "listing_info": {
                "id": item.get('id'),
                "date_posted": item.get('date') or item.get('created_at'),
                "status": item.get('status'),
                "expired": item.get('expired'),
                "region": item.get('region'),
                "city": item.get('cityName', item.get('region'))
            },
            "additional": {
                "kredit": item.get('kredit'),
                "barter": item.get('barter'),
                "information": item.get('information'),
                "position": item.get('position')
            }
        }

    def save_to_database(self, phone_number: str, source_url: str, full_data: Dict) -> bool:
        """
        Save lead to database with phone validation

        Args:
            phone_number: Phone number to save
            source_url: Source URL for the listing
            full_data: Additional data about the listing

        Returns:
            True if saved successfully, False otherwise
        """
        # Validate phone number
        validated_phone = PhoneValidator.validate_phone(phone_number)

        if not validated_phone:
            return False

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Check if record already exists
            cursor.execute("""
                SELECT id FROM leads.leads
                WHERE phone_number = %s AND website = %s
            """, (validated_phone, 'autonet.az'))

            existing = cursor.fetchone()

            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE leads.leads
                    SET source = %s, full_data = %s
                    WHERE phone_number = %s AND website = %s
                """, (source_url, psycopg2.extras.Json(full_data), validated_phone, 'autonet.az'))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO leads.leads (phone_number, website, source, full_data)
                    VALUES (%s, %s, %s, %s)
                """, (validated_phone, 'autonet.az', source_url, psycopg2.extras.Json(full_data)))

            conn.commit()
            cursor.close()
            self.db_pool.putconn(conn)

            return True
        except Exception as e:
            print(f"✗ Database error: {e}")
            if conn:
                conn.rollback()
                self.db_pool.putconn(conn)
            return False

    async def process_listing(self, session: aiohttp.ClientSession, item_id: int, idx: int, total: int) -> Dict[str, int]:
        """
        Process a single listing - fetch details and save to database

        Args:
            session: aiohttp session
            item_id: ID of the listing
            idx: Index for progress tracking
            total: Total number of items

        Returns:
            Dictionary with processing statistics
        """
        result = {'saved': 0, 'duplicates': 0, 'errors': 0}

        # Fetch item details
        item = await self.fetch_item_details(session, item_id)

        if not item:
            result['errors'] += 1
            print(f"✗ [{idx}/{total}] Failed to fetch item {item_id}")
            return result

        # Extract phone numbers
        phones = self.extract_phone_numbers(item)

        if not phones:
            result['errors'] += 1
            print(f"✗ [{idx}/{total}] No phone numbers found for item {item_id}")
            return result

        # Format full data
        source_url = f"https://www.autonet.az/nomreler/{item_id}"
        full_data = self.format_full_data(item)

        # Save each phone number
        saved_count = 0
        for phone in phones:
            if self.save_to_database(phone, source_url, full_data):
                saved_count += 1

        if saved_count > 0:
            result['saved'] = saved_count
            license_plate = full_data['license_plate']['full_number']
            print(f"✓ [{idx}/{total}] Saved {saved_count} phone(s) - {license_plate} - {item.get('price')} {item.get('currency')}")
        else:
            result['duplicates'] = len(phones)

        return result

    async def scrape(self, pages: int = 5) -> Dict[str, int]:
        """
        Main scraping method - fetches listings and processes them

        Args:
            pages: Number of pages to scrape

        Returns:
            Dictionary with scraping statistics
        """
        start_time = datetime.now()
        print(f"\nStarting AutoNet.AZ scraper - {pages} pages")
        print("=" * 70)

        stats = {
            'new_leads': 0,
            'duplicates': 0,
            'errors': 0,
            'duration': 0,
            'start_time': start_time
        }

        async with aiohttp.ClientSession() as session:
            # Step 1: Fetch all listing pages to get IDs
            print(f"\n📋 Fetching listing pages 1-{pages}...")
            all_item_ids = []

            for page in range(1, pages + 1):
                page_data = await self.fetch_listings_page(session, page)

                if page_data and 'data' in page_data:
                    items = page_data['data']
                    item_ids = [item['id'] for item in items]
                    all_item_ids.extend(item_ids)
                    print(f"  ✓ Page {page}: {len(item_ids)} items (Total: {page_data.get('total', 0)})")
                else:
                    print(f"  ✗ Page {page}: Failed to fetch")

            print(f"\n📊 Found {len(all_item_ids)} license plate listings")

            # Step 2: Process items in batches with concurrency control
            print(f"\n🔄 Processing {len(all_item_ids)} items (max {self.max_concurrent} concurrent)...")

            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def process_with_semaphore(item_id: int, idx: int):
                async with semaphore:
                    return await self.process_listing(session, item_id, idx + 1, len(all_item_ids))

            # Process all items concurrently
            tasks = [process_with_semaphore(item_id, idx) for idx, item_id in enumerate(all_item_ids)]
            results = await asyncio.gather(*tasks)

            # Aggregate results
            for result in results:
                stats['new_leads'] += result['saved']
                stats['duplicates'] += result['duplicates']
                stats['errors'] += result['errors']

        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        stats['duration'] = duration

        # Print summary
        print("\n" + "=" * 70)
        print("AutoNet.AZ Scraping Summary:")
        print("=" * 70)
        print(f"  New leads: {stats['new_leads']}")
        print(f"  Duplicates: {stats['duplicates']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Duration: {duration:.2f}s")
        print("=" * 70)

        return stats


if __name__ == "__main__":
    # Test the scraper
    scraper = AutoNetAzScraperAsync(max_concurrent=10)

    try:
        stats = asyncio.run(scraper.scrape(pages=2))
        print(f"\n✅ Test completed: {stats}")
    finally:
        scraper.close()
