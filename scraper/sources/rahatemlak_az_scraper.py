"""
RAHATEMLAK.AZ Scraper - Real Estate Property Listings

Scrapes property listings from rahatemlak.az with:
- Paginated search results for apartments (property_type=8)
- AJAX API for phone number extraction
- Comprehensive property data extraction
"""
import asyncio
import aiohttp
import re
import json
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


class RahatEmlakAzScraper:
    """Scraper for rahatemlak.az real estate property listings"""

    BASE_URL = "https://rahatemlak.az"
    SEARCH_URL = f"{BASE_URL}/search-property"
    PHONE_API = f"{BASE_URL}/ajax/property/view-phone"

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
            # Don't include Accept-Encoding to let aiohttp handle it automatically
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
        # auto_decompress=True by default in aiohttp
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
            # Build search URL for apartments in Baku (city=6), for sale (ad_type=1)
            params = {
                'ad_type': '1',  # For sale
                'property_type': '8',  # Apartments
                'city': '6',  # Baku
                'page': page
            }

            url = self.SEARCH_URL
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    # aiohttp automatically decompresses gzip/deflate/br
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
        soup = BeautifulSoup(html, 'html.parser')
        urls = []

        # Find all property cards - they are in <a> tags with href starting with "https://rahatemlak.az/elan/"
        property_cards = soup.find_all('a', href=re.compile(r'https://rahatemlak\.az/elan/\d+'))

        for card in property_cards:
            href = card.get('href')
            if href and href not in urls:
                # Extract clean URL (remove any query parameters)
                clean_url = href.split('?')[0] if '?' in href else href
                if clean_url not in urls:
                    urls.append(clean_url)

        return urls

    async def fetch_phone_number(self, property_id: str, referer: str, csrf_token: Optional[str] = None) -> Optional[str]:
        """
        Fetch phone number via AJAX API

        Args:
            property_id: Property ID
            referer: Referer URL
            csrf_token: CSRF token extracted from page

        Returns:
            Phone number or None
        """
        try:
            # Update headers for AJAX request
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': referer,
                'Origin': self.BASE_URL
            }

            # Add CSRF token to headers
            if csrf_token:
                headers['X-CSRF-TOKEN'] = csrf_token

            payload = {
                'id': property_id
            }

            async with self.session.post(
                self.PHONE_API,
                data=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # API returns {"status":true,"phone":"(055) 369-65-05","phone_full":"+994553696505"}
                    if data.get('status') and data.get('phone_full'):
                        # Extract digits only from phone_full
                        phone_full = data['phone_full']
                        digits_only = re.sub(r'\D', '', phone_full)
                        return digits_only

                    return None
                else:
                    # Silently skip if phone fetch fails
                    return None

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            # Silently skip errors
            return None

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

                # aiohttp automatically decompresses gzip/deflate/br
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Extract property ID from URL
                property_id_match = re.search(r'/elan/(\d+)', listing_url)
                if not property_id_match:
                    return None

                property_id = property_id_match.group(1)

                # Extract title (h1)
                title = None
                title_elem = soup.find('h1')
                if title_elem:
                    title = title_elem.get_text(strip=True)

                # Extract price
                price = None
                price_elem = soup.find('div', class_='price-value')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # Extract numeric value
                    price_match = re.search(r'([\d,]+)\s*AZN', price_text)
                    if price_match:
                        price = price_match.group(1).replace(',', '')

                # Extract price per m²
                price_per_sqm = None
                price_part_elem = soup.find('div', class_='price-part')
                if price_part_elem:
                    price_part_text = price_part_elem.get_text(strip=True)
                    # Extract "1 m² ~ 2,200 AZN"
                    price_sqm_match = re.search(r'1 m² ~ ([\d,]+)', price_part_text)
                    if price_sqm_match:
                        price_per_sqm = price_sqm_match.group(1).replace(',', '')

                # Extract overview details
                property_type = None
                floor = None
                rooms = None
                area = None
                document = None

                overview_boxes = soup.find_all('div', class_='overview-box')
                for box in overview_boxes:
                    title_elem = box.find('div', class_='overview-box-content-title')
                    text_elem = box.find('div', class_='overview-box-content-text')

                    if title_elem and text_elem:
                        title_text = title_elem.get_text(strip=True)
                        value_text = text_elem.get_text(strip=True)

                        if 'Əmlak növü' in title_text:
                            property_type = value_text
                        elif 'Mərtəbə' in title_text:
                            floor = value_text
                        elif 'Otaq' in title_text:
                            rooms = value_text
                        elif 'Sahə' in title_text:
                            area = value_text
                        elif 'Çıxarış' in title_text:
                            document = value_text

                # Extract description
                description = None
                desc_elem = soup.find('div', class_='text-box')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)

                # Extract location details
                city = None
                district = None
                address = None

                location_boxes = soup.find_all('div', class_='location-box')
                for box in location_boxes:
                    title_elem = box.find('div', class_='location-box-title')
                    text_elem = box.find('div', class_='location-box-text')

                    if title_elem and text_elem:
                        title_text = title_elem.get_text(strip=True)
                        value_text = text_elem.get_text(strip=True)

                        if 'Şəhər' in title_text:
                            city = value_text
                        elif 'Rayon' in title_text:
                            district = value_text
                        elif 'Ünvan' in title_text:
                            address = value_text

                # Extract features (document, mortgage, repair status)
                features = []
                feature_spans = soup.find_all('span', class_=re.compile(r'bg-(document|mortgage|repair)'))
                for span in feature_spans:
                    feature_info = span.get('data-info')
                    if feature_info:
                        features.append(feature_info)

                # Extract images
                images = []
                image_links = soup.find_all('a', {'data-fslightbox': 'gallery'})
                for link in image_links:
                    href = link.get('href')
                    if href and '/images/property/' in href:
                        images.append(href)

                # Extract view count and listing number
                view_count = None
                listing_number = None

                detail_lists = soup.find_all('div', class_='detail-list')
                for detail in detail_lists:
                    title_elem = detail.find('div', class_='detail-list-title')
                    text_elem = detail.find('div', class_='detail-list-text')

                    if title_elem and text_elem:
                        title_text = title_elem.get_text(strip=True)
                        value_text = text_elem.get_text(strip=True)

                        if 'Elan nömrəsi' in title_text:
                            listing_number = value_text
                        elif 'Baxış sayı' in title_text:
                            # Extract number from "851 dəfə baxılıb"
                            view_match = re.search(r'(\d+)', value_text)
                            if view_match:
                                view_count = view_match.group(1)

                # Extract author info
                author_name = None
                author_type = None

                author_elem = soup.find('div', class_='author-content-name')
                if author_elem:
                    author_name = author_elem.get_text(strip=True)

                author_type_elem = soup.find('div', class_='author-content-type')
                if author_type_elem:
                    author_type = author_type_elem.get_text(strip=True)

                # Extract agency info (if available)
                agency_name = None
                agency_elem = soup.find('div', class_='card-agency-name')
                if agency_elem:
                    h6 = agency_elem.find('h6')
                    if h6:
                        agency_name = h6.get_text(strip=True)

                # Extract CSRF token from meta tag
                csrf_token = None
                csrf_meta = soup.find('meta', attrs={'name': 'csrf-token'})
                if csrf_meta:
                    csrf_token = csrf_meta.get('content')

                # Fetch phone number via AJAX
                phone_number = await self.fetch_phone_number(property_id, listing_url, csrf_token)

                return {
                    'property_id': property_id,
                    'url': listing_url,
                    'title': title,
                    'price': price,
                    'price_per_sqm': price_per_sqm,
                    'property_type': property_type,
                    'floor': floor,
                    'rooms': rooms,
                    'area': area,
                    'document': document,
                    'description': description,
                    'city': city,
                    'district': district,
                    'address': address,
                    'features': features,
                    'images': images[:10],  # Limit to 10 images
                    'view_count': view_count,
                    'listing_number': listing_number,
                    'author_name': author_name,
                    'author_type': author_type,
                    'agency_name': agency_name,
                    'phone_number': phone_number
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
                'property_id': listing_data.get('property_id'),
                'title': listing_data.get('title'),
                'price': listing_data.get('price'),
                'price_per_sqm': listing_data.get('price_per_sqm'),
                'property_type': listing_data.get('property_type'),
                'floor': listing_data.get('floor'),
                'rooms': listing_data.get('rooms'),
                'area': listing_data.get('area'),
                'document': listing_data.get('document'),
                'description': listing_data.get('description'),
                'city': listing_data.get('city'),
                'district': listing_data.get('district'),
                'address': listing_data.get('address'),
                'features': listing_data.get('features'),
                'images': listing_data.get('images'),
                'view_count': listing_data.get('view_count'),
                'listing_number': listing_data.get('listing_number'),
                'author_name': listing_data.get('author_name'),
                'author_type': listing_data.get('author_type'),
                'agency_name': listing_data.get('agency_name'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'rahatemlak.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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
        Process a single listing - extract data and fetch phone number

        Args:
            listing_url: Listing URL

        Returns:
            Processing result dict
        """
        result = {
            'url': listing_url,
            'phone_found': False,
            'phone_saved': False
        }

        try:
            # Scrape listing detail
            listing_data = await self.scrape_listing_detail(listing_url)

            if not listing_data:
                self.stats['errors'] += 1
                return result

            # Check if phone number was found
            phone_number = listing_data.get('phone_number')
            if not phone_number:
                return result

            result['phone_found'] = True

            # Validate phone
            validated_phone = PhoneValidator.validate_phone(phone_number)

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
        print("RAHATEMLAK.AZ Scraper - Real Estate Property Listings")
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
        print("Scraping Complete - RAHATEMLAK.AZ")
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
    async with RahatEmlakAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
