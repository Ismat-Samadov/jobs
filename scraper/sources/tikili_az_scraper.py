"""
TIKILI.AZ Scraper - Real Estate Property Listings

Scrapes property listings from tikili.az with:
- AJAX API for paginated property listings
- Individual listing detail pages
- Phone number extraction from listing details
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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class TikiliAzScraper:
    """Scraper for tikili.az real estate property listings"""

    BASE_URL = "https://tikili.az"
    # Search for all apartments for sale (menzil=apartment, satish=sale)
    SEARCH_API_URL = "https://tikili.az/elan-searchajax.php?dil=az&realtor=0&emlak_type=menzil&elan_type=satish&region=no_select&location=no_select&metro=0&oda_sayi=0&min_sahe=0&max_sahe=0&invertar=0&min_price=0&max_price=0&user-type=no_select&searchmod=3&start={start}"

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
            'Referer': 'https://tikili.az/',
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

    async def fetch_listings_page(self, start: int = 0) -> Optional[str]:
        """
        Fetch a page of listings using AJAX API

        Args:
            start: Starting offset (increments by 40 for each page)

        Returns:
            HTML content or None
        """
        try:
            url = self.SEARCH_API_URL.format(start=start)

            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text(encoding='utf-8', errors='ignore')
                    return html
                else:
                    print(f"   ✗ Failed to fetch listings page (HTTP {response.status})")
                    return None

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching listings page at start={start}")
            return None
        except Exception as e:
            print(f"   ✗ Error fetching listings page at start={start}: {e}")
            return None

    def extract_listing_urls(self, html: str) -> List[str]:
        """
        Extract listing URLs from search results page

        Args:
            html: HTML content of search page

        Returns:
            List of listing URLs
        """
        urls = []
        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find all listing links - they are in <a> tags with href like "elan-item.php?elan=83981&dil=az"
            listing_links = soup.find_all('a', href=re.compile(r'elan-item\.php\?elan=\d+'))

            for link in listing_links:
                href = link.get('href')
                if href:
                    # Build full URL
                    full_url = urljoin(self.BASE_URL, href)
                    urls.append(full_url)

            return urls

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

    def extract_listing_data(self, html: str, url: str) -> Optional[Dict]:
        """
        Extract property data and phone number from listing detail page

        Args:
            html: HTML content of listing page
            url: Listing URL

        Returns:
            Dict with listing data or None
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            listing_data = {}

            # Extract listing ID from URL (e.g., elan=84002)
            id_match = re.search(r'elan=(\d+)', url)
            if id_match:
                listing_data['listing_id'] = id_match.group(1)

            # Extract phone number from div with id="item-phone"
            phone_elem = soup.find('div', id='item-phone')
            if phone_elem:
                phone_text = phone_elem.get_text(strip=True)
                # Phone format: "070 596-50-60" or similar
                phone_cleaned = re.sub(r'[^\d]', '', phone_text)
                if len(phone_cleaned) >= 9:
                    listing_data['phone'] = phone_cleaned[-9:]  # Last 9 digits

            # Extract contact person from div with id="elaq-shexs"
            contact_elem = soup.find('div', id='elaq-shexs')
            if contact_elem:
                listing_data['contact_person'] = contact_elem.get_text(strip=True)

            # Extract property parameters from table.elan-params-1
            params_table = soup.find('table', class_='elan-params-1')
            if params_table:
                rows = params_table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True).replace(':', '').strip()
                        value = cells[1].get_text(strip=True)

                        if 'Elan nömrəsi' in key:
                            listing_data['listing_number'] = value
                        elif 'Yerləşdirilib' in key:
                            listing_data['posted_date'] = value
                        elif 'Elan növü' in key:
                            listing_data['building_type'] = value
                        elif 'Sahəsi' in key:
                            area_match = re.search(r'(\d+)', value)
                            if area_match:
                                listing_data['area'] = area_match.group(1)
                        elif 'Təmiri' in key:
                            listing_data['repair_status'] = value
                        elif 'Mərtəbəsi' in key:
                            listing_data['floor'] = value
                        elif 'Otaq sayı' in key:
                            room_match = re.search(r'(\d+)', value)
                            if room_match:
                                listing_data['rooms'] = room_match.group(1)
                        elif 'Binada qaz' in key:
                            listing_data['has_gas'] = value
                        elif 'Sənədi' in key:
                            listing_data['has_deed'] = value
                        elif 'Qiyməti AZN' in key:
                            price_match = re.search(r'([\d\s]+)', value)
                            if price_match:
                                price_str = price_match.group(1).replace(' ', '')
                                listing_data['price'] = price_str

            # Extract location info from the location table
            location_tables = soup.find_all('table', class_='elan-params-1')
            for table in location_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True).replace(':', '').strip()
                        value = cells[1].get_text(strip=True)

                        if 'Rayon' in key:
                            listing_data['region'] = value
                        elif 'Yerləşdiyi ərazi' in key:
                            listing_data['district'] = value
                        elif 'Ünvan' in key:
                            listing_data['address'] = value
                        elif 'Yaxınlıqdakı metro' in key:
                            listing_data['metro'] = value

            # Extract description from "Ümumi məlumat" section
            desc_div = soup.find('div', class_='umumi-melumat')
            if desc_div:
                # Get the <p> tag content
                desc_p = desc_div.find('p')
                if desc_p:
                    listing_data['description'] = desc_p.get_text(strip=True)

            # Extract category from elan-head
            category_link = soup.find('div', class_='elan-head-item-category')
            if category_link:
                category_a = category_link.find('a')
                if category_a:
                    listing_data['category'] = category_a.get_text(strip=True)

            # Extract view count
            view_count_elem = soup.find('span', string=re.compile(r'Baxılıb:'))
            if view_count_elem:
                view_match = re.search(r'(\d+)', view_count_elem.get_text())
                if view_match:
                    listing_data['view_count'] = view_match.group(1)

            listing_data['url'] = url

            return listing_data if listing_data.get('phone') else None

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
                'listing_number': listing_data.get('listing_number'),
                'category': listing_data.get('category'),
                'price': listing_data.get('price'),
                'building_type': listing_data.get('building_type'),
                'area': listing_data.get('area'),
                'rooms': listing_data.get('rooms'),
                'floor': listing_data.get('floor'),
                'repair_status': listing_data.get('repair_status'),
                'has_gas': listing_data.get('has_gas'),
                'has_deed': listing_data.get('has_deed'),
                'description': listing_data.get('description'),
                'region': listing_data.get('region'),
                'district': listing_data.get('district'),
                'address': listing_data.get('address'),
                'metro': listing_data.get('metro'),
                'contact_person': listing_data.get('contact_person'),
                'posted_date': listing_data.get('posted_date'),
                'view_count': listing_data.get('view_count'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'tikili.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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

    async def process_listing(self, url: str) -> Dict:
        """
        Process a single listing - fetch details and save

        Args:
            url: Listing URL

        Returns:
            Processing result dict
        """
        result = {
            'url': url,
            'phone_found': False,
            'phone_saved': False
        }

        try:
            # Fetch listing details
            html = await self.fetch_listing_details(url)
            if not html:
                return result

            # Extract listing data including phone
            listing_data = self.extract_listing_data(html, url)
            if not listing_data or not listing_data.get('phone'):
                return result

            result['phone_found'] = True
            phone = listing_data['phone']

            # Validate phone
            validated_phone = PhoneValidator.validate_phone(phone)
            if not validated_phone:
                self.stats['invalid_phones'] += 1
                return result

            # Save to database
            is_new = self.save_lead(validated_phone, listing_data)

            if is_new:
                self.stats['new_leads'] += 1
                result['phone_saved'] = True
            else:
                self.stats['duplicates'] += 1

            return result

        except Exception as e:
            print(f"   ✗ Error processing listing {url}: {e}")
            self.stats['errors'] += 1
            return result

    async def scrape(self, max_pages: int = 5):
        """
        Main scraping method

        Args:
            max_pages: Maximum number of pages to scrape (each page has ~40 listings)
        """
        print(f"\n{'='*70}")
        print("TIKILI.AZ Scraper - Real Estate Property Listings")
        print(f"{'='*70}\n")

        print(f"🔍 Scraping up to {max_pages} pages...\\n")

        all_listing_urls = []

        # Step 1: Collect all listing URLs from search pages
        # Each page has 40 listings, so start increments by 40
        for page_num in range(max_pages):
            start_offset = page_num * 40
            print(f"   Page {page_num + 1}/{max_pages} (offset={start_offset})...")

            # Fetch search results page
            html = await self.fetch_listings_page(start_offset)
            if not html:
                print(f"   ✗ Failed to fetch page {page_num + 1}, stopping")
                break

            # Extract listing URLs
            urls = self.extract_listing_urls(html)
            if not urls:
                print(f"   No listings found on page {page_num + 1}, stopping")
                break

            print(f"   Found {len(urls)} listings on page {page_num + 1}")
            all_listing_urls.extend(urls)

            # Small delay between pages
            await asyncio.sleep(0.5)

        # Remove duplicates
        all_listing_urls = list(set(all_listing_urls))
        print(f"\n   Total unique listings to process: {len(all_listing_urls)}\n")

        # Step 2: Process each listing
        for idx, url in enumerate(all_listing_urls, 1):
            self.stats['total_listings'] += 1

            # Process listing
            await self.process_listing(url)

            # Small delay between requests
            await asyncio.sleep(0.3)

            # Progress indicator
            if idx % 10 == 0:
                print(f"   Processed {idx}/{len(all_listing_urls)} listings...")

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - TIKILI.AZ")
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
    async with TikiliAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=2)

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
