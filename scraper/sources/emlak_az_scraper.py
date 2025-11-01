"""
Emlak.az scraper - Real estate classifieds website
Extracts phone numbers from property listings
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import sys
import os
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.validator import PhoneValidator
import psycopg2.pool
from dotenv import load_dotenv

class EmlakAzScraper:
    """Scraper for emlak.az real estate listings"""

    BASE_URL = "https://emlak.az"
    # Satılır (Sale) listings
    LISTING_URL = f"{BASE_URL}/elanlar/?ann_type=3&announce_type=18880&sort_type=0"

    def __init__(self, pool):
        """Initialize scraper with database connection pool"""
        self.pool = pool
        self.stats = {
            'total_listings': 0,
            'extracted_phones': 0,
            'saved_phones': 0,
            'duplicates': 0,
            'invalid_phones': 0,
            'errors': 0
        }

    async def fetch_page(self, session, url, timeout=30):
        """Fetch a page with error handling"""
        try:
            async with session.get(url, timeout=timeout, ssl=False) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"  ❌ Failed to fetch {url}: Status {response.status}")
                    return None
        except Exception as e:
            print(f"  ❌ Error fetching {url}: {e}")
            return None

    def extract_listing_urls(self, html):
        """Extract all listing URLs from a listings page"""
        soup = BeautifulSoup(html, 'lxml')
        urls = []

        # Find all listing links in ticket divs
        tickets = soup.find_all('div', class_='ticket')

        for ticket in tickets:
            link = ticket.find('a', href=True)
            if link:
                href = link.get('href')
                if href and href.startswith('/') and '.html' in href:
                    # Build full URL
                    full_url = f"{self.BASE_URL}{href}"
                    urls.append(full_url)

        return urls

    def extract_phones_from_detail(self, html):
        """Extract phone numbers from listing detail page"""
        soup = BeautifulSoup(html, 'lxml')
        phones = []

        # Phone numbers are in <p class="phone">
        phone_elem = soup.find('p', class_='phone')
        if phone_elem:
            phone_text = phone_elem.get_text(strip=True)
            # Split by comma as there can be multiple phones
            phone_parts = phone_text.split(',')
            for part in phone_parts:
                cleaned = part.strip()
                if cleaned:
                    phones.append(cleaned)

        return phones

    def extract_listing_data(self, html, url):
        """Extract full listing data from detail page"""
        soup = BeautifulSoup(html, 'lxml')

        data = {
            'source': 'emlak.az',
            'listing_url': url,
            'scraped_at': datetime.now().isoformat()
        }

        # Title
        title_elem = soup.find('h1', class_='title')
        if title_elem:
            data['title'] = title_elem.get_text(strip=True)

        # Price (in AZN)
        price_div = soup.find('div', class_='price')
        if price_div:
            price_span = price_div.find('span', class_='m')
            if price_span:
                price_text = price_span.get_text(strip=True).replace(' ', '')
                data['price'] = price_text + ' AZN'

        # Listing code
        code_elem = soup.find('b')
        if code_elem and code_elem.parent and 'Elanın kodu:' in code_elem.parent.get_text():
            data['listing_code'] = code_elem.get_text(strip=True)

        # View count
        views_elem = soup.find('span', class_='views-count')
        if views_elem:
            views_text = views_elem.get_text(strip=True)
            data['views'] = views_text

        # Date
        date_elem = soup.find('span', class_='date')
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            data['date_posted'] = date_text

        # Description
        desc_div = soup.find('div', class_='desc')
        if desc_div:
            desc_p = desc_div.find('p')
            if desc_p:
                data['description'] = desc_p.get_text(strip=True)

        # Technical characteristics
        tech_dl = soup.find('dl', class_='technical-characteristics')
        if tech_dl:
            params = {}
            dds = tech_dl.find_all('dd')
            for dd in dds:
                label_span = dd.find('span', class_='label')
                if label_span:
                    label = label_span.get_text(strip=True)
                    # Get the value (everything after the label)
                    value = dd.get_text(strip=True).replace(label, '').strip()
                    if label and value:
                        params[label] = value

            if params:
                data['technical_details'] = params

        # Seller info
        seller_elem = soup.find('p', class_='name-seller')
        if seller_elem:
            seller_text = seller_elem.get_text(strip=True)
            data['seller_name'] = seller_text

        # Address/Location
        map_address = soup.find('div', class_='map-address')
        if map_address:
            h4 = map_address.find('h4')
            if h4:
                address = h4.get_text(strip=True).replace('Ünvan:', '').strip()
                data['address'] = address

        return data

    async def save_lead(self, phone, url, full_data):
        """Save a lead to the database"""
        try:
            conn = self.pool.getconn()
            cursor = conn.cursor()

            # Insert with ON CONFLICT to handle duplicates
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (phone_number) DO NOTHING
                RETURNING id;
            """, (
                phone,
                'emlak.az',
                url,
                full_data
            ))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            self.pool.putconn(conn)

            return result is not None  # True if inserted, False if duplicate

        except Exception as e:
            print(f"  ❌ Error saving lead {phone}: {e}")
            self.stats['errors'] += 1
            if 'conn' in locals():
                conn.rollback()
                self.pool.putconn(conn)
            return False

    async def scrape_detail_page(self, session, url):
        """Scrape a single detail page for phone numbers and data"""
        html = await self.fetch_page(session, url)
        if not html:
            self.stats['errors'] += 1
            return

        # Extract phones
        phones_raw = self.extract_phones_from_detail(html)
        if not phones_raw:
            return

        # Extract full listing data
        full_data = self.extract_listing_data(html, url)

        # Process each phone number
        for phone_raw in phones_raw:
            self.stats['extracted_phones'] += 1

            # Validate phone
            validated_phone = PhoneValidator.validate_phone(phone_raw)
            if not validated_phone:
                self.stats['invalid_phones'] += 1
                continue

            # Convert to JSON-compatible format
            full_data_json = json.dumps(full_data, ensure_ascii=False)

            # Save to database
            was_saved = await self.save_lead(validated_phone, url, full_data_json)

            if was_saved:
                self.stats['saved_phones'] += 1
            else:
                self.stats['duplicates'] += 1

    async def scrape_listings_page(self, session, page_num):
        """Scrape a single listings page"""
        if page_num == 1:
            url = f"{self.LISTING_URL}&page=1"
        else:
            url = f"{self.LISTING_URL}&page={page_num}"

        print(f"  📄 Scraping page {page_num}: {url}")

        html = await self.fetch_page(session, url)
        if not html:
            return []

        # Extract listing URLs
        listing_urls = self.extract_listing_urls(html)
        self.stats['total_listings'] += len(listing_urls)

        print(f"    Found {len(listing_urls)} listings on page {page_num}")

        return listing_urls

    async def scrape(self, pages=5, concurrency=10):
        """Main scraping function"""
        print(f"\n🔍 Starting Emlak.az scraper (pages: {pages}, concurrency: {concurrency})")

        # Create aiohttp session
        connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Step 1: Scrape all listing pages to get URLs
            all_listing_urls = []

            for page_num in range(1, pages + 1):
                listing_urls = await self.scrape_listings_page(session, page_num)
                all_listing_urls.extend(listing_urls)
                await asyncio.sleep(0.5)  # Be polite

            print(f"\n  📋 Total listings found: {len(all_listing_urls)}")

            # Step 2: Scrape all detail pages with concurrency control
            print(f"  🔎 Scraping detail pages...")

            semaphore = asyncio.Semaphore(concurrency)

            async def scrape_with_semaphore(url):
                async with semaphore:
                    await self.scrape_detail_page(session, url)
                    await asyncio.sleep(0.3)  # Rate limiting

            # Process all detail pages
            tasks = [scrape_with_semaphore(url) for url in all_listing_urls]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Print final stats
        print(f"\n✅ Emlak.az scraping completed!")
        print(f"  📊 Stats:")
        print(f"    Total listings: {self.stats['total_listings']}")
        print(f"    Extracted phones: {self.stats['extracted_phones']}")
        print(f"    Saved phones: {self.stats['saved_phones']}")
        print(f"    Duplicates: {self.stats['duplicates']}")
        print(f"    Invalid phones: {self.stats['invalid_phones']}")
        print(f"    Errors: {self.stats['errors']}")

        return self.stats


async def main():
    """Test function"""
    load_dotenv()

    # Create database pool
    pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        scraper = EmlakAzScraper(pool)
        await scraper.scrape(pages=2, concurrency=5)
    finally:
        pool.closeall()


if __name__ == '__main__':
    asyncio.run(main())
