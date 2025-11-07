"""
ARATAP.AZ Scraper - Classifieds Listings

Scrapes classified listings from aratap.az with:
- Pagination-based listing extraction
- Phone number extraction from detail pages
- Multiple categories (real estate, services, jobs, etc.)
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class AratapAzScraper:
    """Scraper for aratap.az classified listings"""

    BASE_URL = "https://aratap.az"

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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,az;q=0.8',
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

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
            url = f"{self.BASE_URL}/page/{page_num}/"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return []

                # Handle encoding
                try:
                    html = await response.text(encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        html = await response.text(encoding='latin-1')
                    except:
                        html = await response.text(errors='ignore')

                soup = BeautifulSoup(html, 'html.parser')

                # Find all listing links in products grid
                listing_urls = []
                products_div = soup.find('div', class_='products')

                if products_div:
                    # Find all product items
                    product_items = products_div.find_all('div', class_='products-i')

                    for item in product_items:
                        # Skip promotion cards
                        if 'promotion-card' in item.get('class', []):
                            continue

                        # Find the product link
                        link = item.find('a', class_='products-link')
                        if link and link.get('href'):
                            href = link['href']

                            # Build full URL
                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('/'):
                                full_url = self.BASE_URL + href
                            else:
                                full_url = self.BASE_URL + '/' + href

                            # Only add actual listing URLs (contain .html)
                            if '.html' in full_url and full_url not in listing_urls:
                                listing_urls.append(full_url)

                return listing_urls

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching page {page_num}")
            return []
        except Exception as e:
            print(f"   ✗ Error fetching page {page_num}: {e}")
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

                # Handle encoding
                try:
                    html = await response.text(encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        html = await response.text(encoding='latin-1')
                    except:
                        html = await response.text(errors='ignore')

                soup = BeautifulSoup(html, 'html.parser')

                # Extract listing ID from URL
                listing_id = None
                id_match = re.search(r'/(\d+)-', listing_url)
                if id_match:
                    listing_id = id_match.group(1)

                # Extract title
                title = None
                title_elem = soup.find('div', class_='products-name')
                if title_elem:
                    title = title_elem.get_text(strip=True)

                # Extract price
                price = None
                price_elem = soup.find('div', class_='product-price')
                if price_elem:
                    price_val = price_elem.find('span', class_='price-val')
                    price_cur = price_elem.find('span', class_='price-cur')
                    if price_val and price_cur:
                        price = f"{price_val.get_text(strip=True)} {price_cur.get_text(strip=True)}"

                # Extract city/location
                location = None
                city_elem = soup.find('span', class_='product-properties__i-value')
                if city_elem:
                    city_link = city_elem.find('a')
                    if city_link:
                        location = city_link.get_text(strip=True)

                # Extract description
                description = None
                desc_elem = soup.find('div', class_='product-description__content')
                if desc_elem:
                    desc_text = desc_elem.find('div', style='white-space: pre-wrap;')
                    if desc_text:
                        description = desc_text.get_text(strip=True)

                # Extract phone numbers
                phone_numbers = []

                # Method 1: From show-phones div
                show_phones_div = soup.find('div', class_='show-phones')
                if show_phones_div:
                    phone_spans = show_phones_div.find_all('span')
                    for span in phone_spans:
                        phone_text = span.get_text(strip=True)
                        # Extract phone number pattern
                        phone_match = re.search(r'\(?\d{3}\)?\s*\d{3}[-\s]?\d{2}[-\s]?\d{2}', phone_text)
                        if phone_match:
                            phone_numbers.append(phone_match.group())

                # Method 2: Search in product-phones section
                product_phones = soup.find('div', class_='product-phones')
                if product_phones:
                    # Find all text that looks like phone numbers
                    phone_text = product_phones.get_text()
                    phones = re.findall(r'\(?\d{3}\)?\s*\d{3}[-\s]?\d{2}[-\s]?\d{2}', phone_text)
                    phone_numbers.extend(phones)

                # Method 3: Look for phone numbers in any link or text
                all_text = soup.get_text()
                additional_phones = re.findall(r'\(?\d{3}\)?\s*\d{3}[-\s]?\d{2}[-\s]?\d{2}', all_text)
                phone_numbers.extend(additional_phones)

                # Clean and deduplicate phone numbers
                cleaned_phones = []
                for phone in phone_numbers:
                    # Remove all non-digit characters
                    digits_only = re.sub(r'\D', '', phone)
                    if digits_only and digits_only not in cleaned_phones:
                        cleaned_phones.append(digits_only)

                return {
                    'listing_id': listing_id,
                    'title': title,
                    'price': price,
                    'location': location,
                    'description': description,
                    'phone_numbers': cleaned_phones,
                    'url': listing_url
                }

        except asyncio.TimeoutError:
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

            # Prepare full_data JSON
            full_data = {
                'listing_id': listing_data.get('listing_id'),
                'title': listing_data.get('title'),
                'price': listing_data.get('price'),
                'location': listing_data.get('location'),
                'description': listing_data.get('description'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'aratap.az', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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
        print("ARATAP.AZ Scraper - Classifieds")
        print(f"{'='*70}\n")

        all_listing_urls = []

        # Scrape listing URLs from pagination pages
        print(f"📋 Scraping listing URLs from {max_pages} pages...")
        for page_num in range(1, max_pages + 1):
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
        print("Scraping Complete - ARATAP.AZ")
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
    async with AratapAzScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)  # Test with 3 pages

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
