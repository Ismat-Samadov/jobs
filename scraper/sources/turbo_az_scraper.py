"""
Turbo.az Car Listings Scraper
Extracts car listings from turbo.az with detailed information
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
import json
import re
import os
import sys
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.validator import PhoneValidator

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TurboAzScraper:
    """Scraper for turbo.az car listings"""

    BASE_URL = "https://turbo.az"
    LISTING_URL = "https://turbo.az/autos"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'DNT': '1'
    }

    def __init__(self, max_pages: int = 5):
        """
        Initialize scraper

        Args:
            max_pages: Maximum number of pages to scrape (default: 5)
        """
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.csrf_token = None

        # Initialize database connection pool
        self.database_url = os.getenv('DATABASE_URL')
        if self.database_url:
            self.db_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # minimum connections
                10,  # maximum connections
                self.database_url
            )
        else:
            logger.warning("DATABASE_URL not set - database insertion disabled")
            self.db_pool = None

    def _get_csrf_token(self, html: str) -> Optional[str]:
        """Extract CSRF token from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # Look for csrf token in meta tags
            meta_token = soup.find('meta', {'name': 'csrf-token'})
            if meta_token and meta_token.get('content'):
                return meta_token.get('content')

            # Look in forms
            form = soup.find('form')
            if form:
                token_input = form.find('input', {'name': 'authenticity_token'})
                if token_input and token_input.get('value'):
                    return token_input.get('value')
        except Exception as e:
            logger.warning(f"Could not extract CSRF token: {e}")
        return None

    def get_listing_urls(self) -> List[str]:
        """
        Get all listing URLs from multiple pages

        Returns:
            List of listing URLs
        """
        all_urls = []

        for page_num in range(1, self.max_pages + 1):
            try:
                logger.info(f"Scraping page {page_num}/{self.max_pages}")

                params = {'page': page_num}
                response = self.session.get(self.LISTING_URL, params=params, timeout=15)
                response.raise_for_status()

                # Extract CSRF token from first page
                if page_num == 1 and not self.csrf_token:
                    self.csrf_token = self._get_csrf_token(response.text)
                    if self.csrf_token:
                        logger.info("CSRF token extracted successfully")

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find all product links
                products = soup.find_all('div', class_='products-i')

                for product in products:
                    link = product.find('a', class_='products-i__link')
                    if link and link.get('href'):
                        full_url = self.BASE_URL + link['href']
                        all_urls.append(full_url)

                logger.info(f"Found {len(products)} listings on page {page_num}")

                # Be respectful with rate limiting (1.5s between pages)
                time.sleep(1.5)

            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {e}")
                continue

        logger.info(f"Total listings found: {len(all_urls)}")
        return all_urls

    def _get_phone_numbers(self, listing_url: str) -> List[str]:
        """
        Get phone numbers for a listing via API call

        Args:
            listing_url: URL of the listing

        Returns:
            List of phone numbers
        """
        try:
            # Extract listing ID from URL
            listing_id = listing_url.split('/')[-1]

            # Construct phone API URL
            phone_url = f"{listing_url}/show_phones"

            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': listing_url,
                'User-Agent': self.HEADERS['User-Agent']
            }

            if self.csrf_token:
                headers['X-CSRF-Token'] = self.csrf_token

            params = {
                'trigger_button': 'main',
                'source_link': listing_url
            }

            response = self.session.get(
                phone_url,
                params=params,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                phones = data.get('phones', [])
                # Extract primary phone numbers
                return [phone.get('primary', phone.get('raw', '')) for phone in phones if phone]
            else:
                logger.warning(f"Phone API returned status {response.status_code} for {listing_url}")

        except Exception as e:
            logger.warning(f"Could not fetch phone numbers for {listing_url}: {e}")

        return []

    def _clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return ' '.join(text.strip().split())

    def save_to_database(self, phone_number: str, source_url: str, full_data: Optional[Dict] = None) -> bool:
        """
        Save lead to database with validation and connection pooling

        Args:
            phone_number: Phone number to save
            source_url: URL of the listing
            full_data: Complete listing data as JSON/dict

        Returns:
            True if saved successfully, False otherwise
        """
        if not self.db_pool:
            logger.warning("Database pool not available - skipping save")
            return False

        # Validate phone number before attempting to save
        validated_phone = PhoneValidator.validate_phone(phone_number)

        if not validated_phone:
            logger.debug(f"Phone validation failed: {phone_number}")
            return False

        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            conn = None
            try:
                # Get connection from pool
                conn = self.db_pool.getconn()
                cur = conn.cursor()

                # Insert lead with full_data (ignore duplicates by phone number)
                query = """
                    INSERT INTO leads.leads (phone_number, website, source, full_data)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (phone_number)
                    DO UPDATE SET
                        full_data = EXCLUDED.full_data,
                        source = EXCLUDED.source
                    RETURNING id
                """

                # Convert full_data dict to JSON string
                full_data_json = json.dumps(full_data) if full_data else None

                cur.execute(query, (validated_phone, 'turbo.az', source_url, full_data_json))
                conn.commit()

                result = cur.fetchone()
                cur.close()

                # Return connection to pool
                self.db_pool.putconn(conn)

                return True if result else False

            except Exception as e:
                # Return connection to pool if we got one
                if conn:
                    self.db_pool.putconn(conn)

                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Database error after {max_retries} attempts: {e}")
                    return False

        return False

    def _extract_property(self, soup: BeautifulSoup, label: str) -> Optional[str]:
        """Extract property value by label"""
        try:
            # Find the property item by label
            properties = soup.find_all('div', class_='product-properties__i')
            for prop in properties:
                label_elem = prop.find('label', class_='product-properties__i-name')
                if label_elem and label in label_elem.get_text():
                    value_elem = prop.find('span', class_='product-properties__i-value')
                    if value_elem:
                        return self._clean_text(value_elem.get_text())
        except Exception as e:
            logger.debug(f"Error extracting property '{label}': {e}")
        return None

    def scrape_listing(self, url: str) -> List[Dict]:
        """
        Scrape a single listing and return lead(s)
        Note: Returns a list because one listing can have multiple phone numbers

        Args:
            url: Listing URL

        Returns:
            List of lead dictionaries (one per phone number)
        """
        try:
            logger.info(f"Scraping listing: {url}")

            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract basic info
            title = ""
            title_elem = soup.find('h1', class_='product-title')
            if not title_elem:
                # Try from properties
                make = self._extract_property(soup, 'Marka')
                model = self._extract_property(soup, 'Model')
                if make and model:
                    title = f"{make} {model}"
            else:
                title = self._clean_text(title_elem.get_text())

            # Extract price
            price = ""
            price_elem = soup.find('div', class_='product-price__i--bold')
            if price_elem:
                price = self._clean_text(price_elem.get_text())

            # Extract properties
            city = self._extract_property(soup, 'Şəhər') or ""
            year = self._extract_property(soup, 'Buraxılış ili') or ""
            body_type = self._extract_property(soup, 'Ban növü') or ""
            color = self._extract_property(soup, 'Rəng') or ""
            engine = self._extract_property(soup, 'Mühərrik') or ""
            mileage = self._extract_property(soup, 'Yürüş') or ""
            transmission = self._extract_property(soup, 'Sürətlər qutusu') or ""
            gear = self._extract_property(soup, 'Ötürücü') or ""
            is_new = self._extract_property(soup, 'Yeni') or ""
            seats = self._extract_property(soup, 'Yerlərin sayı') or ""
            owners = self._extract_property(soup, 'Sahiblər') or ""
            condition = self._extract_property(soup, 'Vəziyyəti') or ""
            market = self._extract_property(soup, 'Hansı bazar üçün yığılıb') or ""

            # Extract description
            description = ""
            desc_elem = soup.find('div', class_='product-description__content')
            if desc_elem:
                description = self._clean_text(desc_elem.get_text())

            # Extract features/extras
            features = []
            extras_list = soup.find('ul', class_='product-extras')
            if extras_list:
                feature_items = extras_list.find_all('li', class_='product-extras__i')
                features = [self._clean_text(item.get_text()) for item in feature_items]

            # Extract images
            images = []
            img_elements = soup.find_all('img', alt=re.compile(r'.*'))
            for img in img_elements:
                src = img.get('src', '')
                if 'turbo.azstatic.com/uploads' in src and src not in images:
                    images.append(src)

            # Extract listing ID
            listing_id = ""
            id_elem = soup.find('div', class_='product-actions__id')
            if id_elem:
                id_text = id_elem.get_text()
                match = re.search(r'(\d+)', id_text)
                if match:
                    listing_id = match.group(1)

            # Extract view count
            views = ""
            stats = soup.find('ul', class_='product-statistics')
            if stats:
                view_elem = stats.find('span', string=re.compile(r'Baxışların sayı'))
                if view_elem:
                    views_text = view_elem.get_text()
                    match = re.search(r'(\d+)', views_text)
                    if match:
                        views = match.group(1)

            # Get phone numbers
            phone_numbers = self._get_phone_numbers(url)

            # Build full data object
            full_data = {
                'title': title,
                'price': price,
                'city': city,
                'year': year,
                'body_type': body_type,
                'color': color,
                'engine': engine,
                'mileage': mileage,
                'transmission': transmission,
                'gear': gear,
                'is_new': is_new,
                'seats': seats,
                'owners': owners,
                'condition': condition,
                'market': market,
                'description': description,
                'features': features,
                'images': images[:10],  # Limit to first 10 images
                'listing_id': listing_id,
                'views': views,
                'url': url
            }

            # Create separate lead for each phone number
            leads = []
            if phone_numbers:
                for phone in phone_numbers:
                    # Clean phone number (remove spaces and formatting)
                    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)

                    # Save to database
                    saved = self.save_to_database(clean_phone, url, full_data)

                    lead = {
                        'phone_number': clean_phone,
                        'website': 'turbo.az',
                        'source': url,
                        'full_data': full_data,
                        'saved': saved
                    }
                    leads.append(lead)

                logger.info(f"Extracted {len(phone_numbers)} phone number(s) from {url}")
            else:
                logger.warning(f"No phone numbers found for {url}")

            return leads

        except Exception as e:
            logger.error(f"Error scraping listing {url}: {e}")
            return []

    def scrape_all(self) -> Dict:
        """
        Scrape all listings

        Returns:
            Dictionary with stats and leads
        """
        all_leads = []
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'saved': 0
        }

        # Get all listing URLs
        listing_urls = self.get_listing_urls()

        if not listing_urls:
            logger.warning("No listing URLs found")
            return {'stats': stats, 'leads': all_leads}

        # Scrape each listing
        for i, url in enumerate(listing_urls, 1):
            try:
                logger.info(f"Processing listing {i}/{len(listing_urls)}")

                leads = self.scrape_listing(url)

                # Update stats
                if leads:
                    stats['success'] += 1
                    for lead in leads:
                        stats['total'] += 1
                        if lead.get('saved'):
                            stats['saved'] += 1
                else:
                    stats['failed'] += 1

                all_leads.extend(leads)

                logger.info(f"Total leads collected: {len(all_leads)} | Saved: {stats['saved']}")

                # Rate limiting (reduced to 2s for better performance)
                time.sleep(2)

            except Exception as e:
                logger.error(f"Error processing listing {url}: {e}")
                stats['failed'] += 1
                continue

        logger.info(f"Scraping complete. Total leads: {len(all_leads)} | Saved to DB: {stats['saved']}")
        return {'stats': stats, 'leads': all_leads}

    def close(self):
        """Close database connection pool"""
        if self.db_pool:
            self.db_pool.closeall()
            logger.info("Database connection pool closed")


def scrape_turbo_az(max_pages: int = 5) -> Dict:
    """
    Main function to scrape turbo.az

    Args:
        max_pages: Number of pages to scrape (default: 5)

    Returns:
        Dictionary with stats and leads
    """
    scraper = TurboAzScraper(max_pages=max_pages)
    try:
        result = scraper.scrape_all()
        return result
    finally:
        scraper.close()


if __name__ == "__main__":
    # Test the scraper
    print("Starting turbo.az scraper...")
    result = scrape_turbo_az(max_pages=1)  # Test with 1 page

    stats = result.get('stats', {})
    leads = result.get('leads', [])

    print(f"\nTotal leads scraped: {len(leads)}")
    print(f"Saved to database: {stats.get('saved', 0)}")
    print(f"Success rate: {stats.get('success', 0)}/{stats.get('success', 0) + stats.get('failed', 0)}")

    if leads:
        print("\nSample lead:")
        print(json.dumps(leads[0], indent=2, ensure_ascii=False))
