"""
MULK.AZ Scraper - Real Estate Property Listings

Scrapes property listings from mulk.az with:
- Pagination support for listing pages
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


class MulkAzScraper:
    """Scraper for mulk.az real estate property listings"""

    BASE_URL = "https://mulk.az"
    SEARCH_URL = "https://mulk.az/search.php?category=&lease=false&pricemin=&pricemax=&rooms=&areamin=&areamax=&bolge_id=1&rayon_id=&qesebe_id=&metro_id=&get={page}"

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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_listing_page(self, page: int = 1) -> Optional[str]:
        """
        Fetch a page of listings

        Args:
            page: Page number (starts from 1)

        Returns:
            HTML content or None
        """
        try:
            url = self.SEARCH_URL.format(page=page)

            async with self.session.get(url) as response:
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

            # Find all listing links - they are in <a> tags with class "xeberler2"
            listing_links = soup.find_all('a', class_='xeberler2')

            for link in listing_links:
                href = link.get('href')
                if href and href.endswith('.mulk'):
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

            # Extract title (category and price)
            title_elem = soup.find('strong', class_='primary')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                listing_data['title'] = title_text

                # Extract price from title
                price_match = re.search(r'(\d[\d\s,]*)\s*AZN', title_text)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '').replace(',', '')
                    listing_data['price'] = price_str

            # Extract details from table
            desc_table = soup.find('table', id='desc')
            if desc_table:
                rows = desc_table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)

                        if 'Category' in key or 'Kateqoriya' in key:
                            listing_data['category'] = value
                        elif 'Mərtəbə' in key:
                            listing_data['floor'] = value
                        elif 'Sahə' in key:
                            area_match = re.search(r'(\d+)', value)
                            if area_match:
                                listing_data['area'] = area_match.group(1)
                        elif 'Otaq' in key:
                            room_match = re.search(r'(\d+)', value)
                            if room_match:
                                listing_data['rooms'] = room_match.group(1)
                        elif 'Cup' in key or 'Kupça' in key:
                            listing_data['has_deed'] = value

            # Extract description
            content_div = soup.find('div', class_='col-md-4')
            if content_div:
                # Find description text (before the table)
                desc_text = []
                for elem in content_div.children:
                    if hasattr(elem, 'name'):
                        if elem.name == 'br':
                            continue
                        elif elem.name == 'table':
                            break
                    else:
                        text = str(elem).strip()
                        if text and text not in ['Ümumi məlumat', 'Yerləşdiyi yer', 'Əlaqədar şəxs']:
                            desc_text.append(text)

                if desc_text:
                    listing_data['description'] = ' '.join(desc_text)

            # Extract location
            location_badges = soup.find_all('b', class_='badge')
            if location_badges:
                locations = [badge.get_text(strip=True) for badge in location_badges if badge.get_text(strip=True)]
                if locations:
                    listing_data['region'] = locations[0] if len(locations) > 0 else None
                    listing_data['district'] = locations[1] if len(locations) > 1 else None

            # Extract address
            addr_elem = content_div.find_all(text=True) if content_div else []
            for i, text in enumerate(addr_elem):
                if 'Yerləşdiyi yer' in text:
                    # The address is usually after the badges
                    for j in range(i+1, len(addr_elem)):
                        addr_text = str(addr_elem[j]).strip()
                        if addr_text and addr_text not in ['', 'Əlaqədar şəxs'] and '<' not in addr_text:
                            listing_data['address'] = addr_text
                            break
                    break

            # Extract phone number
            phone_elem = soup.find('i', class_='fa-phone')
            if phone_elem:
                # Phone is in the text after the icon
                parent = phone_elem.parent
                if parent:
                    phone_text = parent.get_text()
                    # Extract phone pattern like (055) 233-07-00
                    phone_matches = re.findall(r'\((\d{3})\)\s*(\d{3})-?(\d{2})-?(\d{2})', phone_text)
                    if phone_matches:
                        # Combine digits
                        phone = ''.join(phone_matches[0])
                        listing_data['phone'] = phone

            # Extract listing ID from URL
            id_match = re.search(r'/(\d+)\.mulk', url)
            if id_match:
                listing_data['listing_id'] = id_match.group(1)

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
                'title': listing_data.get('title'),
                'price': listing_data.get('price'),
                'category': listing_data.get('category'),
                'area': listing_data.get('area'),
                'rooms': listing_data.get('rooms'),
                'floor': listing_data.get('floor'),
                'has_deed': listing_data.get('has_deed'),
                'description': listing_data.get('description'),
                'region': listing_data.get('region'),
                'district': listing_data.get('district'),
                'address': listing_data.get('address'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'mulk.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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
            max_pages: Maximum number of pages to scrape
        """
        print(f"\n{'='*70}")
        print("MULK.AZ Scraper - Real Estate Property Listings")
        print(f"{'='*70}\n")

        print(f"🔍 Scraping up to {max_pages} pages...\n")

        all_listing_urls = []

        # Step 1: Collect all listing URLs from search pages
        for page_num in range(1, max_pages + 1):
            print(f"   Page {page_num}/{max_pages}...")

            # Fetch search results page
            html = await self.fetch_listing_page(page_num)
            if not html:
                print(f"   ✗ Failed to fetch page {page_num}, stopping")
                break

            # Extract listing URLs
            urls = self.extract_listing_urls(html)
            if not urls:
                print(f"   No listings found on page {page_num}, stopping")
                break

            print(f"   Found {len(urls)} listings on page {page_num}")
            all_listing_urls.extend(urls)

            # Small delay between pages
            await asyncio.sleep(0.5)

        print(f"\n   Total listings to process: {len(all_listing_urls)}\n")

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
        print("Scraping Complete - MULK.AZ")
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
    async with MulkAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=2)

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
