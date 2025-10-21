"""
Fetch and inspect the actual HTML structure of a Villa.AZ listing page
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def inspect_villa_listing():
    """Fetch and print the HTML structure of a real Villa.AZ listing"""

    # Use the listing URL provided by the user
    url = "https://villa.az/villa-siena-baku-buzovna-villas-42106"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')

                # Save HTML to file for inspection
                with open('villa_listing_sample.html', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())

                print("HTML saved to villa_listing_sample.html")
                print("\n" + "="*70)
                print("KEY ELEMENTS FOUND:")
                print("="*70)

                # Find and print key elements
                print("\n1. TITLE/HEADING tags:")
                for h1 in soup.find_all('h1'):
                    print(f"  <h1>: {h1.get_text(strip=True)[:100]}")
                for h2 in soup.find_all('h2')[:3]:
                    print(f"  <h2>: {h2.get_text(strip=True)[:100]}")

                print("\n2. PRICE elements (looking for 'AZN' or 'manat'):")
                price_candidates = soup.find_all(string=lambda text: text and ('AZN' in str(text) or 'manat' in str(text).lower()))
                for i, candidate in enumerate(price_candidates[:5]):
                    parent = candidate.parent
                    print(f"  {i+1}. {parent.name}.{parent.get('class', [])}: {candidate.strip()[:80]}")

                print("\n3. PROPERTY DETAILS (looking for structured data):")
                # Look for common property detail patterns
                for label in ['Ölkə', 'Şəhər', 'Kateqoriya', 'Sahə', 'Otaq', 'Mərtəbə', 'sənəd']:
                    elements = soup.find_all(string=re.compile(label, re.IGNORECASE))
                    for elem in elements[:2]:
                        parent = elem.parent
                        print(f"  Found '{label}': {parent.name}.{parent.get('class', [])} - {elem.strip()[:60]}")

                print("\n4. DESCRIPTION text blocks:")
                # Look for long text blocks
                for p in soup.find_all('p'):
                    text = p.get_text(strip=True)
                    if len(text) > 200:
                        print(f"  <p>: {text[:150]}...")
                        break

                print("\n5. PHONE NUMBER elements:")
                phone_links = soup.find_all('a', href=re.compile(r'tel:'))
                for i, link in enumerate(phone_links[:3]):
                    print(f"  {i+1}. href={link.get('href')}, text={link.get_text(strip=True)}, class={link.get('class', [])}")

                print("\n6. IMAGE elements:")
                images = soup.find_all('img')[:10]
                for i, img in enumerate(images):
                    print(f"  {i+1}. src={img.get('src', '')[:60]}, class={img.get('class', [])}")

                print("\n" + "="*70)
                print("Check 'villa_listing_sample.html' for full HTML structure")
                print("="*70)
            else:
                print(f"Failed to fetch listing page: HTTP {response.status}")

if __name__ == "__main__":
    import re
    asyncio.run(inspect_villa_listing())
