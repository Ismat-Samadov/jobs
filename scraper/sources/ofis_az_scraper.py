"""
OFIS.AZ Scraper - Real Estate Property Listings

Scrapes property listings from ofis.az with:
- POST API for paginated property listings
- Individual listing detail pages
- AJAX API for phone number extraction
- Comprehensive property data extraction
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Optional
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import sys
import os
from urllib.parse import urljoin
import hashlib

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class OfisAzScraper:
    """Scraper for ofis.az real estate property listings"""

    BASE_URL = "https://ofis.az"
    LIST_API_URL = "https://ofis.az/homelist/?start={page}"
    PHONE_API_URL = "https://ofis.az/ajax.php"

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
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Referer': 'https://ofis.az/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_listings_page(self, page: int = 0) -> Optional[str]:
        """
        Fetch a page of listings using POST API

        Args:
            page: Page number (starts from 0)

        Returns:
            HTML content or None
        """
        try:
            url = self.LIST_API_URL.format(page=page)

            # Use POST with empty body
            async with self.session.post(url, data='') as response:
                if response.status == 200:
                    html = await response.text(encoding='utf-8', errors='ignore')
                    return html
                else:
                    print(f"   ✗ Failed to fetch listings page (HTTP {response.status})")
                    return None

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching listings page {page}")
            return None
        except Exception as e:
            print(f"   ✗ Error fetching listings page {page}: {e}")
            return None

    def extract_listing_urls(self, html: str) -> List[Dict]:
        """
        Extract listing URLs and IDs from search results page

        Args:
            html: HTML content of search page

        Returns:
            List of dicts with listing URLs and IDs
        """
        listings = []
        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find all listing divs with class "nobj prod"
            listing_divs = soup.find_all('div', class_='nobj prod')

            for div in listing_divs:
                # Find the link to the listing
                link = div.find('a', href=re.compile(r'-\d+\.html$'))
                if link:
                    href = link.get('href')
                    if href:
                        # Build full URL
                        full_url = urljoin(self.BASE_URL, href)

                        # Extract listing ID from URL (e.g., /kupcali-4-otaq-yeni-gunesli-q-199831.html -> 199831)
                        id_match = re.search(r'-(\d+)\.html$', href)
                        if id_match:
                            listing_id = id_match.group(1)
                            listings.append({
                                'url': full_url,
                                'listing_id': listing_id
                            })

            return listings

        except Exception as e:
            print(f"   ✗ Error extracting listing URLs: {e}")
            return []

    async def fetch_listing_details(self, url: str) -> Optional[str]:
        """
        Fetch individual listing detail page

        Args:
            url: Listing detail URL

        Returns:
            HTML content or None
        """
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text(encoding='utf-8', errors='ignore')
                    return html
                else:
                    return None

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return None

    async def fetch_phone_numbers(self, listing_id: str, listing_hash: str) -> List[str]:
        """
        Fetch phone numbers using AJAX API

        Args:
            listing_id: Listing ID
            listing_hash: Hash parameter from the listing page

        Returns:
            List of phone numbers
        """
        try:
            # Prepare POST data
            data = {
                'act': 'telshow',
                'id': listing_id,
                't': 'product',
                'h': listing_hash,
                'rf': ''
            }

            async with self.session.post(self.PHONE_API_URL, data=data) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get('ok') == 1 and result.get('tel'):
                        # Phone numbers are comma-separated like "0555399993,0505399993"
                        phone_str = result['tel']
                        phones = [p.strip() for p in phone_str.split(',')]

                        # Clean phones (remove non-digits and get last 9 digits)
                        cleaned_phones = []
                        for phone in phones:
                            cleaned = re.sub(r'[^\d]', '', phone)
                            if len(cleaned) >= 9:
                                cleaned_phones.append(cleaned[-9:])

                        return cleaned_phones

                    return []
                else:
                    return []

        except Exception as e:
            return []

    def extract_listing_data(self, html: str, url: str, listing_id: str) -> Optional[Dict]:
        """
        Extract property data from listing detail page

        Args:
            html: HTML content of listing page
            url: Listing URL
            listing_id: Listing ID

        Returns:
            Dict with listing data or None
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            listing_data = {}

            listing_data['listing_id'] = listing_id
            listing_data['url'] = url

            # Extract hash for phone API from div#telshow
            telshow_div = soup.find('div', id='telshow')
            if telshow_div:
                listing_data['hash'] = telshow_div.get('data-h', '')
            else:
                # Try to find it in the page
                return None

            # Extract title from h1
            title_elem = soup.find('h1')
            if title_elem:
                listing_data['title'] = title_elem.get_text(strip=True)

            # Extract listing code
            code_elem = soup.find('span', class_='open_idshow')
            if code_elem:
                code_text = code_elem.get_text()
                code_match = re.search(r'(\d+)', code_text)
                if code_match:
                    listing_data['listing_code'] = code_match.group(1)

            # Extract data from the info section (div with class "openhalf")
            info_div = soup.find('div', class_='openhalf')
            if info_div:
                # Find all <p> tags with property info
                p_tags = info_div.find_all('p')

                for p in p_tags:
                    text = p.get_text(strip=True)
                    b_tag = p.find('b')

                    if b_tag:
                        key = b_tag.get_text(strip=True)

                        # Extract category
                        if 'Kateqoriya' in key:
                            links = p.find_all('a')
                            if links:
                                listing_data['category'] = links[0].get_text(strip=True)
                                if len(links) > 1:
                                    listing_data['listing_type'] = links[1].get_text(strip=True)

                        # Extract city
                        elif 'Şəhər' in key:
                            value = text.replace(key, '').strip()
                            listing_data['city'] = value

                        # Extract region and district
                        elif 'xrayonsp' in str(p):
                            spans = p.find_all('span', class_='xrayonsp')
                            if len(spans) > 0:
                                listing_data['region'] = spans[0].get_text(strip=True)
                            if len(spans) > 1:
                                listing_data['district'] = spans[1].get_text(strip=True)

                        # Extract rooms
                        elif 'Otaq Sayı' in key:
                            value = text.replace(key, '').strip()
                            room_match = re.search(r'(\d+)', value)
                            if room_match:
                                listing_data['rooms'] = room_match.group(1)

                        # Extract area
                        elif 'Sahə' in key:
                            value = text.replace(key, '').strip()
                            area_match = re.search(r'(\d+)', value)
                            if area_match:
                                listing_data['area'] = area_match.group(1)

                        # Extract address
                        elif 'Ünvan' in key:
                            value = text.replace(key, '').strip()
                            listing_data['address'] = value

                        # Extract price
                        elif 'Qiymət' in key:
                            price_span = p.find('span', class_='pricecolor')
                            if price_span:
                                price_text = price_span.get_text(strip=True)
                                price_match = re.search(r'([\d\s]+)', price_text)
                                if price_match:
                                    listing_data['price'] = price_match.group(1).replace(' ', '')

                            # Check for rental price
                            if '/ Ay' in text:
                                listing_data['rental_type'] = 'monthly'

            # Extract description from full text
            desc_p = soup.find('p', class_='fullteshow')
            if desc_p:
                listing_data['description'] = desc_p.get_text(strip=True)

            # Extract contact info
            contact_div = soup.find('div', class_='infocontact')
            if contact_div:
                # Extract user name
                user_link = contact_div.find('a', href=re.compile(r'/user/'))
                if user_link:
                    listing_data['contact_person'] = user_link.get_text(strip=True).replace('(Bütün Elanları)', '').strip()

            # Extract posting date
            date_span = soup.find('span', class_='viewsbb')
            if date_span:
                date_text = date_span.get_text()
                date_match = re.search(r'Tarix:\s*(.+)', date_text)
                if date_match:
                    listing_data['posted_date'] = date_match.group(1).strip()

            return listing_data

        except Exception as e:
            print(f"   ✗ Error extracting listing data: {e}")
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
                'listing_id': listing_data.get('listing_id'),
                'listing_code': listing_data.get('listing_code'),
                'title': listing_data.get('title'),
                'category': listing_data.get('category'),
                'listing_type': listing_data.get('listing_type'),
                'price': listing_data.get('price'),
                'rental_type': listing_data.get('rental_type'),
                'area': listing_data.get('area'),
                'rooms': listing_data.get('rooms'),
                'city': listing_data.get('city'),
                'region': listing_data.get('region'),
                'district': listing_data.get('district'),
                'address': listing_data.get('address'),
                'description': listing_data.get('description'),
                'contact_person': listing_data.get('contact_person'),
                'posted_date': listing_data.get('posted_date'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'ofis.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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

    async def process_listing(self, listing_info: Dict) -> Dict:
        """
        Process a single listing - fetch details and phone numbers

        Args:
            listing_info: Dict with 'url' and 'listing_id'

        Returns:
            Processing result dict
        """
        result = {
            'url': listing_info['url'],
            'phones_found': 0,
            'phones_saved': 0
        }

        try:
            # Fetch listing details
            html = await self.fetch_listing_details(listing_info['url'])
            if not html:
                return result

            # Extract listing data
            listing_data = self.extract_listing_data(html, listing_info['url'], listing_info['listing_id'])
            if not listing_data or not listing_data.get('hash'):
                return result

            # Fetch phone numbers using AJAX API
            phones = await self.fetch_phone_numbers(listing_data['listing_id'], listing_data['hash'])

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
            print(f"   ✗ Error processing listing {listing_info['url']}: {e}")
            self.stats['errors'] += 1
            return result

    async def scrape(self, max_pages: int = 5):
        """
        Main scraping method

        Args:
            max_pages: Maximum number of pages to scrape
        """
        print(f"\n{'='*70}")
        print("OFIS.AZ Scraper - Real Estate Property Listings")
        print(f"{'='*70}\n")

        print(f"🔍 Scraping up to {max_pages} pages...\n")

        all_listings = []

        # Step 1: Collect all listing URLs from search pages
        for page_num in range(max_pages):
            print(f"   Page {page_num + 1}/{max_pages}...")

            # Fetch search results page
            html = await self.fetch_listings_page(page_num)
            if not html:
                print(f"   ✗ Failed to fetch page {page_num + 1}, stopping")
                break

            # Extract listing info
            listings = self.extract_listing_urls(html)
            if not listings:
                print(f"   No listings found on page {page_num + 1}, stopping")
                break

            print(f"   Found {len(listings)} listings on page {page_num + 1}")
            all_listings.extend(listings)

            # Small delay between pages
            await asyncio.sleep(0.5)

        # Remove duplicates by listing_id
        seen_ids = set()
        unique_listings = []
        for listing in all_listings:
            if listing['listing_id'] not in seen_ids:
                seen_ids.add(listing['listing_id'])
                unique_listings.append(listing)

        print(f"\n   Total unique listings to process: {len(unique_listings)}\n")

        # Step 2: Process each listing
        for idx, listing_info in enumerate(unique_listings, 1):
            self.stats['total_listings'] += 1

            # Process listing
            await self.process_listing(listing_info)

            # Small delay between requests
            await asyncio.sleep(0.3)

            # Progress indicator
            if idx % 10 == 0:
                print(f"   Processed {idx}/{len(unique_listings)} listings...")

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - OFIS.AZ")
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

    # Run scraper - scrape 2 pages for testing
    async with OfisAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=2)

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
