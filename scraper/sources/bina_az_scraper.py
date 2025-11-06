"""
BINA.AZ Scraper - Real Estate Agencies

Scrapes agency listings from bina.az with:
- Agency listing page pagination
- API endpoint for phone numbers
- Agency profile information
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
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.validator import PhoneValidator


class BinaAzScraper:
    """Scraper for bina.az real estate agencies"""

    BASE_URL = "https://bina.az"
    AGENCIES_URL = "https://bina.az/agentlikler"
    PHONES_API = "https://bina.az/agentlikler/{slug}/phones?react=true"

    def __init__(self, db_pool: SimpleConnectionPool):
        """Initialize scraper with database connection pool"""
        self.db_pool = db_pool
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            'total_agencies': 0,
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
            'Accept': 'application/json',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'DNT': '1',
            'Referer': self.AGENCIES_URL,
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def extract_agency_slug(self, href: str) -> Optional[str]:
        """
        Extract agency slug from href URL

        Args:
            href: Agency href like "/agentlikler/jetset-real-estate"

        Returns:
            Slug like "jetset-real-estate" or None
        """
        match = re.search(r'/agentlikler/([^/]+)$', href)
        if match:
            return match.group(1)
        return None

    async def fetch_agency_phones(self, slug: str) -> List[str]:
        """
        Fetch phone numbers from API endpoint

        Args:
            slug: Agency slug (e.g., "jetset-real-estate")

        Returns:
            List of phone numbers
        """
        try:
            url = self.PHONES_API.format(slug=slug)

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # API returns {"phones": ["(070) 731-00-31", "(050) 460-86-12"]}
                    phones = data.get('phones', [])

                    # Clean phone numbers (remove formatting)
                    cleaned_phones = []
                    for phone in phones:
                        # Remove all non-digit characters
                        digits_only = re.sub(r'\D', '', phone)
                        if digits_only:
                            cleaned_phones.append(digits_only)

                    return cleaned_phones
                else:
                    print(f"   ✗ Failed to fetch phones for {slug} (HTTP {response.status})")
                    return []

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching phones for {slug}")
            return []
        except Exception as e:
            print(f"   ✗ Error fetching phones for {slug}: {e}")
            return []

    async def scrape_agency_detail(self, agency_card_html: BeautifulSoup) -> Optional[Dict]:
        """
        Scrape agency detail from card HTML and fetch phones from API

        Args:
            agency_card_html: BeautifulSoup object of agency card

        Returns:
            Dict with agency data or None
        """
        try:
            # Extract href
            href = agency_card_html.get('href')
            if not href:
                return None

            # Extract slug from href
            slug = self.extract_agency_slug(href)
            if not slug:
                print(f"   ✗ Could not extract slug from {href}")
                return None

            agency_url = self.BASE_URL + href

            # Extract agency title
            title_elem = agency_card_html.find('h2', {'data-cy': 'agency-title'})
            title = title_elem.get_text(strip=True) if title_elem else slug

            # Extract offer count
            count_elem = agency_card_html.find('span', {'data-cy': 'agency-count'})
            offer_count = None
            if count_elem:
                count_text = count_elem.get('title', '')
                count_match = re.search(r'(\d+)', count_text)
                if count_match:
                    offer_count = int(count_match.group(1))

            # Extract description
            desc_elem = agency_card_html.find('span', {'data-cy': 'agency-desc'})
            description = desc_elem.get_text(strip=True) if desc_elem else None

            # Extract logo
            logo_elem = agency_card_html.find('img', {'data-cy': 'agency-logo'})
            logo_url = logo_elem.get('src') if logo_elem else None

            # Fetch phone numbers from API
            phone_numbers = await self.fetch_agency_phones(slug)

            return {
                'slug': slug,
                'title': title,
                'offer_count': offer_count,
                'description': description,
                'logo_url': logo_url,
                'phone_numbers': phone_numbers,
                'url': agency_url
            }

        except Exception as e:
            print(f"   ✗ Error scraping agency card: {e}")
            return None

    async def scrape_agencies_page(self, page_num: int) -> List[BeautifulSoup]:
        """
        Scrape agency cards from a pagination page

        Args:
            page_num: Page number (1 = first page)

        Returns:
            List of agency card BeautifulSoup objects
        """
        try:
            # Build URL with pagination
            if page_num == 1:
                url = self.AGENCIES_URL
            else:
                url = f"{self.AGENCIES_URL}?page={page_num}"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find all agency cards
                agency_cards = soup.find_all('a', {'data-cy': 'agency'})

                return agency_cards

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout fetching page {page_num}")
            return []
        except Exception as e:
            print(f"   ✗ Error fetching page {page_num}: {e}")
            return []

    def save_lead(self, phone_number: str, agency_data: Dict) -> bool:
        """
        Save lead to database

        Args:
            phone_number: Validated phone number
            agency_data: Agency data dict

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
                'slug': agency_data.get('slug'),
                'title': agency_data.get('title'),
                'offer_count': agency_data.get('offer_count'),
                'description': agency_data.get('description'),
                'logo_url': agency_data.get('logo_url'),
                'source_url': agency_data.get('url')
            }

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, 'bina.az', agency_data.get('url'), psycopg2.extras.Json(full_data)))

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

    async def scrape(self, max_pages: int = 1):
        """
        Main scraping method

        Args:
            max_pages: Maximum number of pages to scrape (default: 1 since all agencies are on first page)
        """
        print(f"\n{'='*70}")
        print("BINA.AZ Scraper - Real Estate Agencies")
        print(f"{'='*70}\n")

        all_agency_cards = []

        # Scrape agency cards from listing page
        print(f"📋 Scraping agency listings...")

        # Note: bina.az loads all agencies on first page, so we only need page 1
        agency_cards = await self.scrape_agencies_page(1)

        if not agency_cards:
            print(f"   No agencies found")
            return

        # Deduplicate by href
        seen_hrefs = set()
        unique_cards = []
        for card in agency_cards:
            href = card.get('href')
            if href and href not in seen_hrefs:
                seen_hrefs.add(href)
                unique_cards.append(card)

        all_agency_cards = unique_cards
        self.stats['total_agencies'] = len(all_agency_cards)

        print(f"✓ Found {len(all_agency_cards)} unique agencies\n")

        # Scrape each agency detail and fetch phones
        print(f"🔍 Fetching phone numbers from API...\n")

        for idx, agency_card in enumerate(all_agency_cards, 1):
            # Progress indicator
            if idx % 10 == 0 or idx == 1:
                print(f"   Progress: {idx}/{len(all_agency_cards)} agencies...")

            # Extract agency data from card and fetch phones
            agency_data = await self.scrape_agency_detail(agency_card)

            if not agency_data:
                self.stats['errors'] += 1
                continue

            # Process phone numbers
            phone_numbers = agency_data.get('phone_numbers', [])

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
                is_new = self.save_lead(validated_phone, agency_data)

                if is_new:
                    self.stats['new_leads'] += 1
                else:
                    self.stats['duplicates'] += 1

            # Small delay between API requests
            await asyncio.sleep(0.3)

        # Print final stats
        print(f"\n{'='*70}")
        print("Scraping Complete - BINA.AZ")
        print(f"{'='*70}")
        print(f"Total agencies:    {self.stats['total_agencies']:,}")
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

    # Run scraper (only needs 1 page since all agencies are on first page)
    async with BinaAzScraper(db_pool) as scraper:
        await scraper.scrape()

    db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(main())
