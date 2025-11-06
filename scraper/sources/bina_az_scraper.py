"""
BINA.AZ Scraper - Real Estate Property Listings

Scrapes property listings from bina.az with:
- GraphQL API for paginated property listings
- Phone number API endpoint for contact information
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
from urllib.parse import urlencode, quote

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class BinaAzScraper:
    """Scraper for bina.az real estate property listings"""

    BASE_URL = "https://bina.az"
    GRAPHQL_URL = "https://bina.az/graphql"
    PHONES_API = "https://bina.az/items/{item_id}/phones"

    # GraphQL query hash for SearchItems
    GRAPHQL_HASH = "872e9c694c34b6674514d48e9dcf1b46241d3d79f365ddf20d138f18e74554c5"

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
        # Headers to mimic real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Content-Type': 'application/json',
            'DNT': '1',
            'Referer': 'https://bina.az/baki/alqi-satqi/menziller',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-requested-with': 'XMLHttpRequest'
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_listings_page(self, cursor: Optional[str] = None, page_size: int = 16) -> Optional[Dict]:
        """
        Fetch a page of listings using GraphQL API

        Args:
            cursor: Pagination cursor (None for first page)
            page_size: Number of items per page

        Returns:
            GraphQL response data or None
        """
        try:
            # Build GraphQL variables
            variables = {
                "first": page_size,
                "filter": {
                    "cityId": "1",  # Baku
                    "categoryId": "1",  # Apartments/Properties
                    "leased": False  # For sale (not rent)
                },
                "sort": "BUMPED_AT_DESC"
            }

            # Add cursor for pagination
            if cursor:
                variables["cursor"] = cursor

            # Build query parameters
            params = {
                "operationName": "SearchItems",
                "variables": json.dumps(variables, separators=(',', ':')),
                "extensions": json.dumps({
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": self.GRAPHQL_HASH
                    }
                }, separators=(',', ':'))
            }

            url = f"{self.GRAPHQL_URL}?{urlencode(params)}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"   ✗ Failed to fetch listings (HTTP {response.status})")
                    return None

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching listings page")
            return None
        except Exception as e:
            print(f"   ✗ Error fetching listings page: {e}")
            return None

    async def fetch_item_phones(self, item_id: str) -> List[str]:
        """
        Fetch phone numbers for a specific item using phones API

        Args:
            item_id: Item/listing ID

        Returns:
            List of phone numbers
        """
        try:
            item_url = f"{self.BASE_URL}/items/{item_id}"

            # Build API URL with query parameters
            params = {
                "source_link": item_url,
                "trigger_button": "main"
            }

            url = self.PHONES_API.format(item_id=item_id)
            url = f"{url}?{urlencode(params)}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # API returns {"phones": ["(055) 518-99-99"]}
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
                    # Silently skip if phone fetch fails (common for listings without visible phones)
                    return []

        except asyncio.TimeoutError:
            return []
        except Exception as e:
            # Silently skip errors
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

            # Prepare full_data JSON with all listing details
            full_data = {
                'item_id': listing_data.get('id'),
                'price': listing_data.get('price'),
                'area': listing_data.get('area'),
                'rooms': listing_data.get('rooms'),
                'floor': listing_data.get('floor'),
                'floors': listing_data.get('floors'),
                'city': listing_data.get('city'),
                'location': listing_data.get('location'),
                'has_mortgage': listing_data.get('hasMortgage'),
                'has_bill_of_sale': listing_data.get('hasBillOfSale'),
                'has_repair': listing_data.get('hasRepair'),
                'company': listing_data.get('company'),
                'photos': listing_data.get('photos', []),
                'vipped': listing_data.get('vipped'),
                'featured': listing_data.get('featured'),
                'is_business': listing_data.get('isBusiness'),
                'updated_at': listing_data.get('updatedAt'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'bina.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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

    async def process_listing(self, item_node: Dict) -> Dict:
        """
        Process a single listing - extract data and fetch phone numbers

        Args:
            item_node: GraphQL item node data

        Returns:
            Processing result dict
        """
        result = {
            'item_id': item_node.get('id'),
            'phones_found': 0,
            'phones_saved': 0
        }

        try:
            item_id = item_node.get('id')
            if not item_id:
                return result

            # Build full listing URL
            path = item_node.get('path', f"/items/{item_id}")
            listing_url = self.BASE_URL + path

            # Extract listing data
            listing_data = {
                'id': item_id,
                'url': listing_url,
                'price': item_node.get('price'),
                'area': item_node.get('area'),
                'rooms': item_node.get('rooms'),
                'floor': item_node.get('floor'),
                'floors': item_node.get('floors'),
                'city': item_node.get('city'),
                'location': item_node.get('location'),
                'hasMortgage': item_node.get('hasMortgage'),
                'hasBillOfSale': item_node.get('hasBillOfSale'),
                'hasRepair': item_node.get('hasRepair'),
                'company': item_node.get('company'),
                'photos': [p.get('large') for p in item_node.get('photos', [])[:4]],  # Save first 4 photos
                'vipped': item_node.get('vipped'),
                'featured': item_node.get('featured'),
                'isBusiness': item_node.get('isBusiness'),
                'updatedAt': item_node.get('updatedAt')
            }

            # Fetch phone numbers
            phones = await self.fetch_item_phones(item_id)
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
            print(f"   ✗ Error processing listing {result['item_id']}: {e}")
            self.stats['errors'] += 1
            return result

    async def scrape(self, max_pages: int = 5, items_per_page: int = 16):
        """
        Main scraping method

        Args:
            max_pages: Maximum number of pages to scrape
            items_per_page: Number of items per page (default: 16)
        """
        print(f"\n{'='*70}")
        print("BINA.AZ Scraper - Real Estate Property Listings")
        print(f"{'='*70}\n")

        cursor = None
        page_count = 0

        print(f"🔍 Scraping up to {max_pages} pages ({items_per_page} listings per page)...\n")

        while page_count < max_pages:
            page_count += 1
            print(f"   Page {page_count}/{max_pages}...")

            # Fetch listings page
            response_data = await self.fetch_listings_page(cursor, items_per_page)

            if not response_data:
                print(f"   ✗ Failed to fetch page {page_count}, stopping")
                break

            # Extract data from GraphQL response
            items_connection = response_data.get('data', {}).get('itemsConnection', {})
            edges = items_connection.get('edges', [])
            page_info = items_connection.get('pageInfo', {})

            if not edges:
                print(f"   No listings found on page {page_count}, stopping")
                break

            print(f"   Found {len(edges)} listings on page {page_count}")

            # Process each listing
            for edge in edges:
                item_node = edge.get('node', {})
                self.stats['total_listings'] += 1

                # Process listing (fetch phones and save)
                await self.process_listing(item_node)

                # Small delay between phone API requests
                await asyncio.sleep(0.2)

            # Check if there's a next page
            has_next_page = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor')

            if not has_next_page or not cursor:
                print(f"   Reached end of listings")
                break

            # Small delay between pages
            await asyncio.sleep(0.5)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - BINA.AZ")
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

    # Run scraper - scrape 3 pages for testing
    async with BinaAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
