"""
ARENDA.AZ Scraper - Real Estate Listings

Scrapes real estate listings from arenda.az with:
- Listing page pagination
- Individual listing detail pages
- Phone number extraction from detail pages
- Multiple property types (apartments, houses, land, etc.)
"""
import asyncio
import aiohttp
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class ArendaAzScraper:
    """Scraper for arenda.az real estate listings"""

    BASE_URL = "https://arenda.az"
    # Page number is in the URL path: /filtirli-axtaris/{page_num}/
    # Example: https://arenda.az/filtirli-axtaris/4/?home_search=1&lang=1&site=1&home_s=1
    LISTINGS_URL_TEMPLATE = "https://arenda.az/filtirli-axtaris/{page}/"

    def __init__(self, db_pool: SimpleConnectionPool, max_concurrent: int = 10):
        """Initialize scraper with database connection pool"""
        self.db_pool = db_pool
        self.max_concurrent = max_concurrent
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def extract_listing_urls_from_page(self, html: str) -> List[str]:
        """
        Extract listing URLs from a listings page

        Args:
            html: HTML content of listings page

        Returns:
            List of listing URLs
        """
        soup = BeautifulSoup(html, 'html.parser')
        listing_urls = []

        # Find all listing items - based on the HTML structure
        # <li class="new_elan_box" id="elan_XXXXXX">
        #   <a href="https://arenda.az/..." title="..." target="_blank">
        listing_items = soup.find_all('li', class_='new_elan_box')

        for item in listing_items:
            # Find the main <a> tag within the listing
            link = item.find('a', href=True)
            if link:
                href = link['href']
                # Make sure URL is absolute
                if href.startswith('http'):
                    listing_urls.append(href)
                elif href.startswith('/'):
                    listing_urls.append(self.BASE_URL + href)
                else:
                    listing_urls.append(self.BASE_URL + '/' + href)

        return listing_urls

    def extract_phone_from_detail_page(self, html: str) -> List[str]:
        """
        Extract phone numbers from listing detail page

        Args:
            html: HTML content of detail page

        Returns:
            List of phone numbers found
        """
        soup = BeautifulSoup(html, 'html.parser')
        phones = []

        # Based on the HTML: <p class="elan_in_tel_box"><a href="https://api.whatsapp.com/send?phone=994552289892" class="elan_in_tel" target="_blank">(055) 228-98-92
        # Phone numbers are in <a> tags with class "elan_in_tel"
        phone_links = soup.find_all('a', class_='elan_in_tel')

        for link in phone_links:
            phone_text = link.get_text(strip=True)
            if phone_text:
                # Clean the phone number (remove formatting)
                cleaned = re.sub(r'\D', '', phone_text)
                if cleaned:
                    phones.append(cleaned)

        # Also check WhatsApp links in case the text is not available
        # href="https://api.whatsapp.com/send?phone=994552289892"
        for link in phone_links:
            href = link.get('href', '')
            if 'phone=' in href:
                match = re.search(r'phone=(\d+)', href)
                if match:
                    phone_num = match.group(1)
                    # Remove country code if present
                    if phone_num.startswith('994'):
                        phone_num = phone_num[3:]
                    if phone_num not in phones:
                        phones.append(phone_num)

        return phones

    def extract_listing_details(self, html: str, listing_url: str) -> Optional[Dict]:
        """
        Extract listing details from detail page

        Args:
            html: HTML content of detail page
            listing_url: URL of the listing

        Returns:
            Dict with listing data
        """
        soup = BeautifulSoup(html, 'html.parser')

        try:
            # Extract title
            title_elem = soup.find('h2', class_='elan_main_title')
            title = title_elem.get_text(strip=True) if title_elem else None

            # Extract price
            price = None
            price_elem = soup.find('div', class_='elan_new_price_box')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract numeric value
                price_match = re.search(r'([\d\s,]+)', price_text)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '').replace(',', '')
                    try:
                        price = int(price_str)
                    except ValueError:
                        pass

            # Extract property type and details from elan_property_list
            property_details = {}
            property_list = soup.find('ul', class_='elan_property_list')
            if property_list:
                items = property_list.find_all('li')
                for idx, item in enumerate(items):
                    text = item.get_text(strip=True)
                    if 'otaq' in text.lower():
                        property_details['rooms'] = text
                    elif 'm²' in text or 'm2' in text:
                        property_details['area'] = text
                    elif 'sot' in text:
                        property_details['land_area'] = text
                    elif 'mərtəbə' in text.lower():
                        property_details['floors'] = text
                    elif idx == 0:
                        property_details['document'] = text

            # Extract location
            location = None
            location_elem = soup.find('span', class_='elan_unvan_txt')
            if location_elem:
                location = location_elem.get_text(strip=True)

            # Extract description
            description = None
            desc_elem = soup.find('div', class_='elan_info_txt')
            if desc_elem:
                description = desc_elem.get_text(strip=True)

            # Extract amenities/features from property_lists
            amenities = []
            amenities_list = soup.find('ul', class_='property_lists')
            if amenities_list:
                items = amenities_list.find_all('li')
                for item in items:
                    text = item.get_text(strip=True)
                    if text:
                        amenities.append(text)

            # Extract listing code
            listing_code = None
            code_pattern = re.search(r'Elanın kodu:\s*(\d+)', html)
            if code_pattern:
                listing_code = code_pattern.group(1)

            # Extract seller info
            seller_name = None
            seller_type = None
            seller_info = soup.find('div', class_='new_elan_user_info')
            if seller_info:
                paragraphs = seller_info.find_all('p')
                if len(paragraphs) > 0:
                    # First paragraph contains name and type
                    seller_text = paragraphs[0].get_text(strip=True)
                    # Format: "Elcan (Vasitəçi)" or "Füzuli (Əmlak sahibi)"
                    match = re.match(r'([^(]+)\(([^)]+)\)', seller_text)
                    if match:
                        seller_name = match.group(1).strip()
                        seller_type = match.group(2).strip()

            return {
                'title': title,
                'price': price,
                'property_details': property_details,
                'location': location,
                'description': description,
                'amenities': amenities,
                'listing_code': listing_code,
                'seller_name': seller_name,
                'seller_type': seller_type,
                'url': listing_url
            }

        except Exception as e:
            print(f"   ✗ Error extracting details from {listing_url}: {e}")
            return None

    async def scrape_listing_detail(self, listing_url: str) -> Optional[Dict]:
        """
        Scrape individual listing detail page

        Args:
            listing_url: URL of the listing

        Returns:
            Dict with listing data and phone numbers
        """
        try:
            async with self.session.get(listing_url) as response:
                if response.status != 200:
                    print(f"   ✗ Failed to fetch {listing_url} (HTTP {response.status})")
                    return None

                # Handle encoding issues - try different encodings
                try:
                    html = await response.text(encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        html = await response.text(encoding='latin-1')
                    except:
                        html = await response.text(errors='ignore')

                # Extract phone numbers
                phone_numbers = self.extract_phone_from_detail_page(html)

                # Extract listing details
                listing_data = self.extract_listing_details(html, listing_url)

                if listing_data:
                    listing_data['phone_numbers'] = phone_numbers
                    return listing_data

                return None

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
            page_num: Page number (starts at 1)

        Returns:
            List of listing URLs
        """
        try:
            # Build pagination URL
            # Page number is in the URL path: /filtirli-axtaris/{page_num}/
            # Example: https://arenda.az/filtirli-axtaris/4/?home_search=1&lang=1&site=1&home_s=1
            url = f"https://arenda.az/filtirli-axtaris/{page_num}/"

            params = {
                'home_search': '1',
                'lang': '1',
                'site': '1',
                'home_s': '1',
                'price_min': '',
                'price_max': '',
                'axtar': '',
                'sahe_min': '',
                'sahe_max': '',
                'mertebe_min': '',
                'mertebe_max': '',
                'y_mertebe_min': '',
                'y_mertebe_max': ''
            }

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    print(f"   ✗ Failed to fetch page {page_num} (HTTP {response.status})")
                    return []

                html = await response.text()
                listing_urls = self.extract_listing_urls_from_page(html)

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
                'title': listing_data.get('title'),
                'price': listing_data.get('price'),
                'property_details': listing_data.get('property_details'),
                'location': listing_data.get('location'),
                'description': listing_data.get('description'),
                'amenities': listing_data.get('amenities'),
                'listing_code': listing_data.get('listing_code'),
                'seller_name': listing_data.get('seller_name'),
                'seller_type': listing_data.get('seller_type'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'arenda.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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

    async def scrape(self, pages: int = 5, concurrency: int = 10):
        """
        Main scraping method

        Args:
            pages: Number of pages to scrape (default: 5)
            concurrency: Number of concurrent requests for detail pages (default: 10)
        """
        print(f"\n{'='*70}")
        print("ARENDA.AZ Scraper - Real Estate Listings")
        print(f"{'='*70}\n")

        all_listing_urls = []

        # Scrape listing URLs from pagination pages
        print(f"📋 Scraping listing URLs from {pages} pages...")
        for page_num in range(1, pages + 1):
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

        # Scrape each listing detail page with concurrency control
        print(f"🔍 Scraping listing details and phone numbers...\n")

        # Process listings in batches
        semaphore = asyncio.Semaphore(concurrency)

        async def scrape_with_semaphore(url, idx):
            async with semaphore:
                if idx % 10 == 0 or idx == 1:
                    print(f"   Progress: {idx}/{len(all_listing_urls)} listings...")

                listing_data = await self.scrape_listing_detail(url)

                if not listing_data:
                    self.stats['errors'] += 1
                    return

                # Process phone numbers
                phone_numbers = listing_data.get('phone_numbers', [])

                if not phone_numbers:
                    # No phone numbers found
                    return

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

        # Create tasks for all listings
        tasks = [
            scrape_with_semaphore(url, idx)
            for idx, url in enumerate(all_listing_urls, 1)
        ]

        # Run all tasks
        await asyncio.gather(*tasks)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - ARENDA.AZ")
        print(f"{'='*70}")
        print(f"Total listings:    {self.stats['total_listings']:,}")
        print(f"New leads:         {self.stats['new_leads']:,}")
        print(f"Duplicates:        {self.stats['duplicates']:,}")
        print(f"Invalid phones:    {self.stats['invalid_phones']:,}")
        print(f"Errors:            {self.stats['errors']:,}")
        print(f"{'='*70}\n")

        return {
            'saved_phones': self.stats['new_leads'],
            'duplicates': self.stats['duplicates'],
            'invalid_phones': self.stats['invalid_phones'],
            'errors': self.stats['errors']
        }


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

    # Run scraper - scrape first 5 pages
    async with ArendaAzScraper(db_pool, max_concurrent=10) as scraper:
        await scraper.scrape(pages=5, concurrency=10)

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
