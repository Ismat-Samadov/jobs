"""
Fetch and inspect the actual HTML structure of an EVV.AZ listing page
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def inspect_evv_listing():
    """Fetch and print the HTML structure of a real EVV.AZ listing"""

    # Use a real listing URL
    url = "https://www.evv.az/dasinmaz-emlak-satis?type=1"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }

    async with aiohttp.ClientSession() as session:
        # First, get the listing page to find a listing URL
        async with session.get(url, headers=headers) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'lxml')

            # Find first listing link
            listing_link = soup.find('a', class_='img_link')
            if listing_link:
                listing_url = 'https://www.evv.az' + listing_link.get('href')
                print(f"Inspecting: {listing_url}\n")

                # Fetch the individual listing page
                async with session.get(listing_url, headers=headers) as listing_response:
                    if listing_response.status == 200:
                        listing_html = await listing_response.text()
                        listing_soup = BeautifulSoup(listing_html, 'lxml')

                        # Save HTML to file for inspection
                        with open('listing_sample.html', 'w', encoding='utf-8') as f:
                            f.write(listing_soup.prettify())

                        print("HTML saved to listing_sample.html")
                        print("\n" + "="*70)
                        print("KEY ELEMENTS FOUND:")
                        print("="*70)

                        # Find and print key elements
                        print("\n1. TITLE/HEADING tags:")
                        for h1 in listing_soup.find_all('h1'):
                            print(f"  <h1>: {h1.get_text(strip=True)[:100]}")

                        print("\n2. PRICE elements (looking for 'AZN' or numbers):")
                        price_candidates = listing_soup.find_all(string=lambda text: 'AZN' in str(text) or 'azn' in str(text))
                        for i, candidate in enumerate(price_candidates[:5]):
                            parent = candidate.parent
                            print(f"  {i+1}. {parent.name}.{parent.get('class', [])}: {candidate.strip()[:80]}")

                        print("\n3. TABLE elements (property details):")
                        tables = listing_soup.find_all('table')
                        for i, table in enumerate(tables[:3]):
                            print(f"  Table {i+1} classes: {table.get('class', [])}")
                            rows = table.find_all('tr')[:3]
                            for row in rows:
                                cells = row.find_all(['td', 'th'])
                                if cells:
                                    print(f"    Row: {' | '.join([c.get_text(strip=True)[:30] for c in cells])}")

                        print("\n4. DESCRIPTION/TEXT blocks:")
                        # Look for divs with substantial text
                        for div in listing_soup.find_all('div'):
                            text = div.get_text(strip=True)
                            if len(text) > 100 and len(text) < 500:
                                classes = div.get('class', [])
                                print(f"  div.{classes}: {text[:100]}...")
                                break

                        print("\n5. IMAGE elements:")
                        images = listing_soup.find_all('img')[:5]
                        for i, img in enumerate(images):
                            print(f"  {i+1}. src={img.get('src', '')[:60]}, class={img.get('class', [])}")

                        print("\n" + "="*70)
                        print("Check 'listing_sample.html' for full HTML structure")
                        print("="*70)
                    else:
                        print(f"Failed to fetch listing page: HTTP {listing_response.status}")
            else:
                print("No listing link found on main page")

if __name__ == "__main__":
    asyncio.run(inspect_evv_listing())
