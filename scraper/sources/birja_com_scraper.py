"""
BIRJA.COM Scraper - Courses and Training Services

Scrapes course listings from birja.com with:
- URL-based pagination
- Direct phone number extraction from detail pages
- Individual listing detail pages
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


class BirjaComScraper:
    """Scraper for birja.com course listings"""

    BASE_URL = "https://birja.com"
    # Category 121/146 = Kurslar (Courses)
    LISTINGS_URL = "https://birja.com/category/az/121/146/0/kurslar"

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

                # Extract title from page title or h1
                title = None
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text(strip=True).split('|')[0].strip()

                # Extract phone number from table
                # Look for phone numbers in <a href="tel:..."> tags
                phone_numbers = []

                # Find all phone links in the page
                phone_links = soup.find_all('a', href=re.compile(r'^tel:'))
                for phone_link in phone_links:
                    phone_text = phone_link.get_text(strip=True)
                    # Clean phone number (remove all non-digits)
                    phone_clean = re.sub(r'[^\d]', '', phone_text)
                    if phone_clean and len(phone_clean) >= 9:  # At least 9 digits
                        phone_numbers.append(phone_clean)

                # Extract price
                price = None
                price_row = soup.find('td', string=re.compile('Qiymət|Price', re.IGNORECASE))
                if price_row and price_row.parent:
                    price_cell = price_row.find_next_sibling('td')
                    if price_cell:
                        price_text = price_cell.get_text(strip=True)
                        # Try to extract numeric price
                        price_match = re.search(r'(\d+)\s*AZN', price_text)
                        if price_match:
                            price = int(price_match.group(1))

                # Extract description
                description = None
                desc_div = soup.find('div', class_='cs_ads_text')
                if desc_div:
                    desc_p = desc_div.find('p')
                    if desc_p:
                        description = desc_p.get_text(strip=True)

                # Extract category
                category = None
                category_row = soup.find('td', string=re.compile('Bölmə|Category', re.IGNORECASE))
                if category_row and category_row.parent:
                    category_cell = category_row.find_next_sibling('td')
                    if category_cell:
                        category_link = category_cell.find('a')
                        if category_link:
                            category = category_link.get_text(strip=True)

                # Extract user/company name
                company = None
                user_row = soup.find('td', string=re.compile('İstifadəçi|User', re.IGNORECASE))
                if user_row and user_row.parent:
                    user_cell = user_row.find_next_sibling('td')
                    if user_cell:
                        company = user_cell.get_text(strip=True)

                # Extract listing ID
                listing_id = None
                id_row = soup.find('td', string=re.compile('Elanın nömrəsi|Ad number', re.IGNORECASE))
                if id_row and id_row.parent:
                    id_cell = id_row.find_next_sibling('td')
                    if id_cell:
                        listing_id = id_cell.get_text(strip=True)

                return {
                    'listing_id': listing_id,
                    'title': title,
                    'price': price,
                    'description': description,
                    'category': category,
                    'company': company,
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
            page_num: Page number (0 = first page, 2 = second page, etc.)

        Returns:
            List of listing URLs
        """
        try:
            # Build URL with pagination
            if page_num == 0:
                url = self.LISTINGS_URL
            else:
                url = f"{self.LISTINGS_URL}/{page_num}"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find all listing cards
                listing_urls = []
                cards = soup.find_all('div', class_='cs_card_col')

                for card in cards:
                    # Find the link to the detail page
                    link = card.find('a', class_='cs_card_img', href=True)
                    if link:
                        href = link['href']
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
                'company': listing_data.get('company'),
                'source_url': listing_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'birja.com', listing_data.get('url'), psycopg2.extras.Json(full_data)))

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
        print("BIRJA.COM Scraper - Courses and Training")
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
        print("Scraping Complete - BIRJA.COM")
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
    async with BirjaComScraper(db_pool) as scraper:
        await scraper.scrape(max_pages=3)  # Test with 3 pages

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
