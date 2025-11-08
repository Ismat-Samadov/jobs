"""
AVTOVITRIN.COM Scraper - Car Listings

Scrapes car listings from avtovitrin.com with:
- Paginated search results (all cars)
- Phone number extraction from listing detail pages
- Comprehensive car listing data extraction
"""
import asyncio
import aiohttp
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class AvtovitrinComScraper:
    """Scraper for avtovitrin.com car listings"""

    BASE_URL = "https://www.avtovitrin.com"
    SEARCH_URL = f"{BASE_URL}/search_result.php?cars=0&modelname=0&min_price=&max_price=&start_year=&end_year=&city=0&cur=1"

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
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_search_page(self, page: int = 1) -> Optional[str]:
        """
        Fetch a search results page

        Args:
            page: Page number (starts at 1)

        Returns:
            HTML content or None
        """
        try:
            # Build search URL - same URL for all pages, content loads dynamically
            url = self.SEARCH_URL

            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"   ✗ Failed to fetch search page {page} (HTTP {response.status})")
                    return None

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching search page {page}")
            return None
        except Exception as e:
            print(f"   ✗ Error fetching search page {page}: {e}")
            return None

    def extract_listing_urls(self, html: str) -> List[str]:
        """
        Extract listing URLs from search results page

        Args:
            html: HTML content of search page

        Returns:
            List of listing URLs
        """
        soup = BeautifulSoup(html, 'lxml')
        urls = []

        # Find all listing links - pattern: /cars/{id}-{brand}-{model}
        listing_links = soup.find_all('a', href=re.compile(r'/cars/\d{7}-'))

        for link in listing_links:
            href = link.get('href')
            if href and '/cars/' in href:
                # Convert relative URL to absolute
                if href.startswith('/'):
                    full_url = self.BASE_URL + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = self.BASE_URL + '/' + href

                # Remove duplicates
                if full_url not in urls:
                    urls.append(full_url)

        return urls

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
                soup = BeautifulSoup(html, 'lxml')

                # Extract listing ID from URL
                listing_id = None
                id_match = re.search(r'/cars/(\d{7})-', listing_url)
                if id_match:
                    listing_id = id_match.group(1)

                # Extract title from car_name1
                title = None
                title_elem = soup.find('div', class_='car_name1')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    # Remove the heart icon at the end
                    title = re.sub(r'\s*$', '', title).strip()

                # Extract price
                price = None
                price_elem = soup.find('td', class_='price_car')
                if not price_elem:
                    price_elem = soup.find('td', class_='price_car1')
                if price_elem:
                    price = price_elem.get_text(strip=True)

                # Extract data from tables
                data = {}
                tables = soup.find_all('table', class_=['table_mobile', 'table'])
                for table in tables:
                    rows = table.find_all('tr', class_='row_style')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) == 2:
                            key = cols[0].get_text(strip=True).replace(':', '')
                            value = cols[1].get_text(strip=True)
                            data[key] = value

                # Extract specific fields
                city = data.get('Şəhər', None)
                brand = data.get('Marka', None)
                model = data.get('Model', None)
                year = data.get('Buraxılış ili', None)
                body_type = data.get('Ban növü', None)
                color = data.get('Rəng', None)
                engine_volume = data.get('Mühərrikin həcmi', None)
                engine_power = data.get('Mühərrikin gücü', None)
                fuel_type = data.get('Yanacaq növü', None)
                mileage = data.get('Yürüş', None)
                transmission = data.get('Sürətlər qutusu', None)
                drivetrain = data.get('Ötürücü', None)
                is_new = data.get('Yeni', None)
                credit = data.get('Kredit', None)
                barter = data.get('Barter mümkündür', None)
                views = data.get('Baxışların sayı', None)
                updated_date = data.get('Yeniləndi', None)

                # Extract contact person
                contact_person = None
                contact_elem = soup.find('td', class_='rowone', colspan='2')
                if contact_elem:
                    contact_text = contact_elem.get_text(strip=True)
                    if contact_text and contact_text not in ['DAHA TEZ SAT']:
                        contact_person = contact_text

                # Extract phone numbers
                phone_numbers = []
                phone_elem = soup.find('td', class_='row_phone_number')
                if phone_elem:
                    phone_text = phone_elem.get_text(strip=True)
                    # Extract phone numbers - format: (0XX) XXX-XX-XX or (0XX)XXX-XX-XX
                    phone_matches = re.findall(r'\(?\d{3}\)?\s*\d{3}[-\s]?\d{2}[-\s]?\d{2}', phone_text)
                    for phone in phone_matches:
                        # Clean phone number
                        digits_only = re.sub(r'\D', '', phone)
                        if digits_only and len(digits_only) >= 9:
                            phone_numbers.append(digits_only)

                # Extract description
                description = None
                desc_elem = soup.find('div', class_='car_extra_text')
                if desc_elem:
                    desc_span = desc_elem.find('span')
                    if desc_span:
                        description = desc_span.get_text(strip=True)

                # Extract extra equipment
                extra_equipment = []
                extra_container = soup.find('div', class_='car_extra_container')
                if extra_container:
                    extra_items = extra_container.find_all('div', class_='row3')
                    for item in extra_items:
                        extra_equipment.append(item.get_text(strip=True))

                # Extract images
                images = []
                # Get all images with class car_photo1_ts
                img_elems = soup.find_all('img', class_='car_photo1_ts')
                for img in img_elems:
                    src = img.get('src')
                    if src:
                        # Convert relative URL to absolute
                        if src.startswith('images/'):
                            images.append(self.BASE_URL + '/' + src)
                        elif src.startswith('http'):
                            images.append(src)

                return {
                    'listing_id': listing_id,
                    'url': listing_url,
                    'title': title,
                    'price': price,
                    'city': city,
                    'brand': brand,
                    'model': model,
                    'year': year,
                    'body_type': body_type,
                    'color': color,
                    'engine_volume': engine_volume,
                    'engine_power': engine_power,
                    'fuel_type': fuel_type,
                    'mileage': mileage,
                    'transmission': transmission,
                    'drivetrain': drivetrain,
                    'is_new': is_new,
                    'credit': credit,
                    'barter': barter,
                    'views': views,
                    'updated_date': updated_date,
                    'contact_person': contact_person,
                    'description': description,
                    'extra_equipment': extra_equipment,
                    'images': images[:10],  # Limit to 10 images
                    'phone_numbers': phone_numbers
                }

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching {listing_url}")
            return None
        except Exception as e:
            print(f"   ✗ Error scraping {listing_url}: {e}")
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
                'city': listing_data.get('city'),
                'brand': listing_data.get('brand'),
                'model': listing_data.get('model'),
                'year': listing_data.get('year'),
                'body_type': listing_data.get('body_type'),
                'color': listing_data.get('color'),
                'engine_volume': listing_data.get('engine_volume'),
                'engine_power': listing_data.get('engine_power'),
                'fuel_type': listing_data.get('fuel_type'),
                'mileage': listing_data.get('mileage'),
                'transmission': listing_data.get('transmission'),
                'drivetrain': listing_data.get('drivetrain'),
                'is_new': listing_data.get('is_new'),
                'credit': listing_data.get('credit'),
                'barter': listing_data.get('barter'),
                'views': listing_data.get('views'),
                'updated_date': listing_data.get('updated_date'),
                'contact_person': listing_data.get('contact_person'),
                'description': listing_data.get('description'),
                'extra_equipment': listing_data.get('extra_equipment'),
                'images': listing_data.get('images'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'avtovitrin.com', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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

    async def process_listing(self, listing_url: str) -> Dict:
        """
        Process a single listing - extract data and phone numbers

        Args:
            listing_url: Listing URL

        Returns:
            Processing result dict
        """
        result = {
            'url': listing_url,
            'phones_found': 0,
            'phones_saved': 0
        }

        try:
            # Scrape listing detail
            listing_data = await self.scrape_listing_detail(listing_url)

            if not listing_data:
                self.stats['errors'] += 1
                return result

            # Check if phone numbers were found
            phone_numbers = listing_data.get('phone_numbers', [])
            result['phones_found'] = len(phone_numbers)

            if not phone_numbers:
                return result

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
                    result['phones_saved'] += 1
                else:
                    self.stats['duplicates'] += 1

            return result

        except Exception as e:
            print(f"   ✗ Error processing listing {listing_url}: {e}")
            self.stats['errors'] += 1
            return result

    async def scrape(self, max_listings: int = 100):
        """
        Main scraping method

        Args:
            max_listings: Maximum number of listings to scrape
        """
        print(f"\n{'='*70}")
        print("AVTOVITRIN.COM Scraper - Car Listings")
        print(f"{'='*70}\n")

        # Scrape listing URLs from search page
        print(f"🔍 Scraping listing URLs (max {max_listings})...\n")

        html = await self.fetch_search_page(1)
        if not html:
            print("   ✗ Failed to fetch search page")
            return

        listing_urls = self.extract_listing_urls(html)

        if not listing_urls:
            print("   No listings found")
            return

        # Limit to max_listings
        listing_urls = listing_urls[:max_listings]
        self.stats['total_listings'] = len(listing_urls)

        print(f"✓ Found {len(listing_urls)} listings\n")

        # Scrape each listing detail page
        print(f"📱 Scraping listing details and phone numbers...\n")

        for idx, listing_url in enumerate(listing_urls, 1):
            # Progress indicator
            if idx % 10 == 0 or idx == 1:
                print(f"   Progress: {idx}/{len(listing_urls)} listings...")

            # Process listing
            await self.process_listing(listing_url)

            # Small delay between requests
            await asyncio.sleep(0.5)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - AVTOVITRIN.COM")
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

    # Run scraper - scrape 50 listings for testing
    async with AvtovitrinComScraper(db_pool) as scraper:
        await scraper.scrape(max_listings=50)

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
