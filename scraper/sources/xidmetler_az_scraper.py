"""
XiDMETLER.AZ Scraper - Courses and Training Services

Scrapes course listings from xidmetler.az with:
- URL-based pagination
- AJAX phone number extraction
- Individual listing detail pages
"""
import asyncio
import aiohttp
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class XidmetlerAzScraper:
    """Scraper for xidmetler.az course listings"""

    BASE_URL = "https://xidmetler.az"
    LISTINGS_URL = "https://xidmetler.az/kurslar/"
    AJAX_URL = "https://xidmetler.az/ajax.php"

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
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def extract_listing_id_and_hash(self, html_content: str, listing_url: str) -> Optional[Tuple[str, str]]:
        """
        Extract listing ID and hash from listing detail page

        Args:
            html_content: HTML content of detail page
            listing_url: URL of the listing

        Returns:
            Tuple of (listing_id, hash) or None
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find the phone reveal button with data attributes
            tel_div = soup.find('div', {'id': 'telshow'})

            if tel_div:
                listing_id = tel_div.get('data-id')
                hash_val = tel_div.get('data-h')

                if listing_id and hash_val:
                    return (listing_id, hash_val)

            # Fallback: extract ID from URL
            id_match = re.search(r'-(\d+)\.html$', listing_url)
            if id_match:
                return (id_match.group(1), None)

            return None

        except Exception as e:
            print(f"   ✗ Error extracting listing ID: {e}")
            return None

    async def fetch_phone_numbers_ajax(self, listing_id: str, hash_val: str, referer: str) -> List[str]:
        """
        Fetch phone numbers via AJAX endpoint

        Args:
            listing_id: Listing ID
            hash_val: Security hash
            referer: Referer page

        Returns:
            List of phone numbers
        """
        try:
            payload = {
                'act': 'telshow',
                'id': listing_id,
                't': 'product',
                'h': hash_val,
                'rf': referer
            }

            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Referer': f"{self.BASE_URL}/{referer}"
            }

            async with self.session.post(self.AJAX_URL, data=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract phone numbers from "tel" field
                    if data.get('ok') == 1 and 'tel' in data:
                        phones_str = data['tel']
                        # Split by comma
                        phones = [p.strip() for p in phones_str.split(',') if p.strip()]
                        return phones

                return []

        except asyncio.TimeoutError:
            print(f"   ✗ AJAX timeout for listing {listing_id}")
            return []
        except Exception as e:
            print(f"   ✗ AJAX error for listing {listing_id}: {e}")
            return []

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

                # Extract listing ID and hash
                id_hash = self.extract_listing_id_and_hash(html, listing_url)
                if not id_hash:
                    print(f"   ✗ Could not extract listing ID from {listing_url}")
                    return None

                listing_id, hash_val = id_hash

                # Extract title
                title_elem = soup.find('h1')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Course"

                # Extract price
                price = None
                price_elem = soup.find('span', class_='pricecolor')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price_match = re.search(r'(\d+)', price_text)
                    if price_match:
                        price = int(price_match.group(1))

                # Extract description
                description = None
                desc_elem = soup.find('p', class_='infop100')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)

                # Extract category
                category = None
                breadcrumb = soup.find('div', class_='breadcrumb2')
                if breadcrumb:
                    links = breadcrumb.find_all('a')
                    if len(links) >= 2:
                        category = links[-1].get_text(strip=True)

                # Extract location
                location = None
                info_contact = soup.find('div', class_='infocontact')
                if info_contact:
                    location_elem = info_contact.find('span', class_='glyphicon-map-marker')
                    if location_elem and location_elem.parent:
                        location = location_elem.parent.get_text(strip=True).replace('📍', '').strip()

                # Fetch phone numbers via AJAX if we have hash
                phone_numbers = []
                if hash_val:
                    # Extract referer from URL (e.g., "kurslar/?start=2")
                    referer = listing_url.replace(self.BASE_URL + '/', '')
                    phone_numbers = await self.fetch_phone_numbers_ajax(listing_id, hash_val, referer)

                return {
                    'listing_id': listing_id,
                    'title': title,
                    'price': price,
                    'description': description,
                    'category': category,
                    'location': location,
                    'phone_numbers': phone_numbers,
                    'url': listing_url
                }

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching {listing_url}")
            return None
        except Exception as e:
            print(f"   ✗ Error scraping {listing_url}: {e}")
            return None

    async def scrape_listings_page(self, page_num: int) -> List[str]:
        """
        Scrape listing URLs from a pagination page

        Args:
            page_num: Page number (starts at 0 for first page)

        Returns:
            List of listing URLs
        """
        try:
            # Build URL with pagination
            if page_num == 0:
                url = self.LISTINGS_URL
            else:
                url = f"{self.LISTINGS_URL}?start={page_num}"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find all listing links in the product grid
                listing_urls = []
                prod_wrap = soup.find('div', {'id': 'prodwrap', 'class': 'prodwrap'})

                if prod_wrap:
                    # Find all <a> tags with href to detail pages
                    for link in prod_wrap.find_all('a', href=True):
                        href = link['href']
                        # Filter for actual listing URLs (contain .html and exclude images)
                        if '.html' in href and not href.startswith('/uploads/'):
                            # Build full URL
                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('/'):
                                full_url = self.BASE_URL + href
                            else:
                                full_url = self.BASE_URL + '/' + href

                            # Deduplicate
                            if full_url not in listing_urls:
                                listing_urls.append(full_url)

                return listing_urls

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching page {page_num}")
            return []
        except Exception as e:
            print(f"   ✗ Error fetching page {page_num}: {e}")
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
                'title': listing_data.get('title'),
                'price': listing_data.get('price'),
                'description': listing_data.get('description'),
                'category': listing_data.get('category'),
                'location': listing_data.get('location'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'xidmetler.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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
        print("XiDMETLER.AZ Scraper - Courses and Training")
        print(f"{'='*70}\n")

        all_listing_urls = []

        # Scrape listing URLs from pagination pages
        print(f"📋 Scraping listing URLs from {max_pages} pages...")
        for page_num in range(max_pages):
            listing_urls = await self.scrape_listings_page(page_num)

            if not listing_urls:
                print(f"   Page {page_num}: No listings found, stopping pagination")
                break

            all_listing_urls.extend(listing_urls)
            print(f"   Page {page_num}: Found {len(listing_urls)} listings")

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

            # Process phone numbers
            phone_numbers = listing_data.get('phone_numbers', [])

            if not phone_numbers:
                # No phone numbers found
                continue

            # Validate and save each phone number
            for phone in phone_numbers:
                validated_phone = PhoneValidator.validate_phone(phone)

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
        print("Scraping Complete - XiDMETLER.AZ")
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
    async with XidmetlerAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)  # Test with 3 pages

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
