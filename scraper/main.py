"""
Main entry point for running all scrapers
"""
import asyncio
from sources import EvvAzScraperAsync, VillaAzScraperAsync


async def main():
    """Run all configured scrapers"""
    # EVV.AZ Scraper - scrape all types (Sale, Rent, Daily)
    evv_scraper = EvvAzScraperAsync(max_concurrent=15)

    try:
        await evv_scraper.scrape(all_types=True)
    finally:
        evv_scraper.close()

    # Villa.AZ Scraper - scrape first 3 pages
    villa_scraper = VillaAzScraperAsync(max_concurrent=15)

    try:
        await villa_scraper.scrape(pages=3)
    finally:
        villa_scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
