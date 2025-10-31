"""
Qarabazar.az scraper - General classifieds website
Extracts phone numbers from various listing categories
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.validator import PhoneValidator
import psycopg2.pool
from dotenv import load_dotenv

class QarabazarAzScraper:
    """Scraper for qarabazar.az classifieds"""

    BASE_URL = "https://qarabazar.az"
    LISTING_URL = f"{BASE_URL}/elanlar"

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

        # Find all listing links - they have the pattern href="/.+-adv\d+.html"
        links = soup.find_all('a', class_='title_synopsis_adv')

        for link in links:
            href = link.get('href')
            if href and href.startswith('/') and 'adv' in href and href.endswith('.html'):
                full_url = f"{self.BASE_URL}{href}"
                urls.append(full_url)

        return urls

    def extract_phone_from_detail(self, html):
        """Extract phone number from listing detail page"""
        soup = BeautifulSoup(html, 'lxml')

        # Phone is in <span itemprop="telephone">
        phone_span = soup.find('span', itemprop='telephone')
        if phone_span:
            phone_text = phone_span.get_text(strip=True)
            return phone_text

        return None

    def extract_listing_data(self, html, url):
        """Extract full listing data from detail page"""
        soup = BeautifulSoup(html, 'lxml')

        data = {
            'source': 'qarabazar.az',
            'listing_url': url,
            'scraped_at': datetime.now().isoformat()
        }

        # Title
        title_elem = soup.find('h1')
        if title_elem:
            data['title'] = title_elem.get_text(strip=True)

        # Price
        price_elem = soup.find('span', itemprop='price')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            data['price'] = price_text

        # Category/Section
        category_elem = soup.find('a', href=lambda x: x and '/elanlar/' in x and x.count('/') >= 3)
        if category_elem:
            data['category'] = category_elem.get_text(strip=True)

        # Location
        location_elem = soup.find('span', itemprop='addressLocality')
        if location_elem:
            data['location'] = location_elem.get_text(strip=True)

        # Description
        desc_elem = soup.find('td', class_='td_text_advert')
        if desc_elem:
            data['description'] = desc_elem.get_text(strip=True)

        # Seller info
        seller_name = soup.find('span', itemprop='name')
        if seller_name:
            data['seller_name'] = seller_name.get_text(strip=True)

        # Listing ID
        listing_id_elem = soup.find('td', class_='history')
        if listing_id_elem and 'Elan №' in listing_id_elem.get_text():
            data['listing_id'] = listing_id_elem.get_text(strip=True)

        # Date posted
        date_elems = soup.find_all('td', class_='history')
        for elem in date_elems:
            text = elem.get_text(strip=True)
            if 'Tarix:' in text:
                data['date_posted'] = text.replace('Tarix:', '').strip()
                break

        # View count
        for elem in date_elems:
            text = elem.get_text(strip=True)
            if 'Baxış sayı' in text:
                data['views'] = text.replace('Baxış sayı:', '').strip()
                break

        # Images
        images = []
        img_links = soup.find_all('a', class_='fancybox-buttons', rel='gallery')
        for img_link in img_links:
            img_url = img_link.get('href')
            if img_url:
                if img_url.startswith('/'):
                    img_url = f"{self.BASE_URL}{img_url}"
                images.append(img_url)

        if images:
            data['images'] = images[:10]  # Limit to 10 images

        # Extract additional parameters from the table
        param_rows = soup.find_all('tr')
        params = {}
        for row in param_rows:
            name_cell = row.find('td', class_='td_name_param')
            value_cell = row.find_next_sibling('td') if name_cell else None

            if name_cell and value_cell:
                param_name = name_cell.get_text(strip=True)
                param_value = value_cell.get_text(strip=True)
                if param_name and param_value:
                    params[param_name] = param_value

        if params:
            data['parameters'] = params

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
                'qarabazar.az',
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
        """Scrape a single detail page for phone number and data"""
        html = await self.fetch_page(session, url)
        if not html:
            self.stats['errors'] += 1
            return

        # Extract phone
        phone_raw = self.extract_phone_from_detail(html)
        if not phone_raw:
            return

        self.stats['extracted_phones'] += 1

        # Validate phone
        validated_phone = PhoneValidator.validate_phone(phone_raw)
        if not validated_phone:
            self.stats['invalid_phones'] += 1
            return

        # Extract full listing data
        full_data = self.extract_listing_data(html, url)

        # Convert to JSON-compatible format
        import json
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
            url = f"{self.LISTING_URL}/"
        else:
            url = f"{self.LISTING_URL}/page{page_num}.html"

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
        print(f"\n🔍 Starting Qarabazar.az scraper (pages: {pages}, concurrency: {concurrency})")

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
        print(f"\n✅ Qarabazar.az scraping completed!")
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
        scraper = QarabazarAzScraper(pool)
        await scraper.scrape(pages=2, concurrency=5)
    finally:
        pool.closeall()


if __name__ == '__main__':
    asyncio.run(main())
