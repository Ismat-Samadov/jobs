"""
UCUZTAP.AZ Scraper - Classified Ads Listings

Scrapes classified ads from ucuztap.az with:
- Paginated search results (all categories)
- Phone number extraction from listing detail pages
- Comprehensive ad data extraction
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


class UcuztapAzScraper:
    """Scraper for ucuztap.az classified ads listings"""

    BASE_URL = "https://ucuztap.az"
    SEARCH_URL = f"{BASE_URL}/"

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
            # Build search URL - homepage shows all latest listings
            if page == 1:
                url = self.SEARCH_URL
            else:
                url = f"{self.SEARCH_URL}?page={page}"

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

        # Find all listing cards - they are in <a> tags with href="/elan/{id}-{slug}/"
        # Inside <section class="thumbnail i-product">
        listing_links = soup.find_all('a', href=re.compile(r'/elan/\d+-'))

        for link in listing_links:
            href = link.get('href')
            if href and '/elan/' in href:
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

                # Extract listing ID from URL or page
                listing_id = None
                id_match = re.search(r'/elan/(\d+)-', listing_url)
                if id_match:
                    listing_id = id_match.group(1)
                else:
                    # Try to find it in the page
                    id_div = soup.find('div', class_='txt-right')
                    if id_div:
                        id_text = id_div.get_text(strip=True)
                        id_match = re.search(r'#(\d+)', id_text)
                        if id_match:
                            listing_id = id_match.group(1)

                # Extract title (h1)
                title = None
                title_elem = soup.find('h1')
                if title_elem:
                    title = title_elem.get_text(strip=True)

                # Extract category
                category = None
                category_link = soup.find('a', class_='txt-underline')
                if category_link:
                    category = category_link.get_text(strip=True)

                # Extract price
                price = None
                price_btn = soup.find('button', class_='btn-price')
                if price_btn:
                    price_text = price_btn.get_text(strip=True)
                    # Extract numeric value
                    price_match = re.search(r'([\d\s,]+)', price_text)
                    if price_match:
                        price = price_match.group(1).replace(' ', '').replace(',', '')
                    elif 'Razılaşma' in price_text:
                        price = 'Razılaşma ilə'

                # Extract description
                description = None
                desc_elem = soup.find('h2', class_='fs-15')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)

                # Extract location
                location = None
                location_span = soup.find('span', string=re.compile(r'Bakı|Sumqayıt|Gəncə'))
                if location_span:
                    location_text = location_span.get_text(strip=True)
                    location_match = re.search(r'(Bakı|Sumqayıt|Gəncə)', location_text)
                    if location_match:
                        location = location_match.group(1)

                # Extract view count
                view_count = None
                view_span = soup.find('span', string=re.compile(r'dəfə'))
                if view_span:
                    view_text = view_span.get_text(strip=True)
                    view_match = re.search(r'(\d+)\s*dəfə', view_text)
                    if view_match:
                        view_count = view_match.group(1)

                # Extract time posted
                time_posted = None
                time_span = soup.find('span', class_='i-profile-statsBorder')
                if time_span:
                    time_posted = time_span.get_text(strip=True)

                # Extract shop/user name
                shop_name = None
                shop_h3 = soup.find('h3', class_='m-t-1')
                if shop_h3:
                    shop_name = shop_h3.get_text(strip=True)

                # Extract images
                images = []
                image_links = soup.find_all('a', {'data-carousel': 'carousel'})
                for link in image_links:
                    href = link.get('href')
                    if href and '/a/' in href:
                        images.append(href)

                # Extract phone numbers - they are in <strong> tags with format (0XX) XXX XX XX
                phone_numbers = []
                phone_strongs = soup.find_all('strong', class_='fs-20')
                for strong in phone_strongs:
                    phone_text = strong.get_text(strip=True)
                    # Look for phone pattern (0XX) XXX XX XX or similar
                    phone_matches = re.findall(r'\(?\d{3}\)?\s*\d{3}\s*\d{2}\s*\d{2}', phone_text)
                    for phone in phone_matches:
                        # Clean phone number
                        digits_only = re.sub(r'\D', '', phone)
                        if digits_only and len(digits_only) >= 9:
                            phone_numbers.append(digits_only)

                return {
                    'listing_id': listing_id,
                    'url': listing_url,
                    'title': title,
                    'category': category,
                    'price': price,
                    'description': description,
                    'location': location,
                    'view_count': view_count,
                    'time_posted': time_posted,
                    'shop_name': shop_name,
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
                'category': listing_data.get('category'),
                'price': listing_data.get('price'),
                'description': listing_data.get('description'),
                'location': listing_data.get('location'),
                'view_count': listing_data.get('view_count'),
                'time_posted': listing_data.get('time_posted'),
                'shop_name': listing_data.get('shop_name'),
                'images': listing_data.get('images'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'ucuztap.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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

    async def scrape(self, max_pages: int = 5):
        """
        Main scraping method

        Args:
            max_pages: Maximum number of pages to scrape
        """
        print(f"\n{'='*70}")
        print("UCUZTAP.AZ Scraper - Classified Ads Listings")
        print(f"{'='*70}\n")

        all_listing_urls = []

        # Scrape listing URLs from search pages
        print(f"🔍 Scraping listing URLs from {max_pages} pages...\n")

        for page in range(1, max_pages + 1):
            print(f"   Page {page}/{max_pages}...")

            html = await self.fetch_search_page(page)
            if not html:
                print(f"   ✗ Failed to fetch page {page}, stopping")
                break

            listing_urls = self.extract_listing_urls(html)

            if not listing_urls:
                print(f"   No listings found on page {page}, stopping")
                break

            all_listing_urls.extend(listing_urls)
            print(f"   Found {len(listing_urls)} listings on page {page}")

            # Small delay between pages
            await asyncio.sleep(0.5)

        # Deduplicate URLs
        all_listing_urls = list(set(all_listing_urls))
        self.stats['total_listings'] = len(all_listing_urls)

        print(f"\n✓ Found {len(all_listing_urls)} unique listings\n")

        # Scrape each listing detail page
        print(f"📱 Scraping listing details and phone numbers...\n")

        for idx, listing_url in enumerate(all_listing_urls, 1):
            # Progress indicator
            if idx % 10 == 0 or idx == 1:
                print(f"   Progress: {idx}/{len(all_listing_urls)} listings...")

            # Process listing
            await self.process_listing(listing_url)

            # Small delay between requests
            await asyncio.sleep(0.3)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - UCUZTAP.AZ")
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
    async with UcuztapAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
