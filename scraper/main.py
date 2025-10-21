"""
Main entry point for running all scrapers
"""
import asyncio
from sources import EvvAzScraperAsync, VillaAzScraperAsync


async def main():
    """Run all configured scrapers"""
    # EVV.AZ Scraper - scrape all types (Sale, Rent, Daily) - 5 pages each = 15 total
    evv_scraper = EvvAzScraperAsync(max_concurrent=15)

    try:
        await evv_scraper.scrape(all_types=True, pages_per_type=5)
    finally:
        evv_scraper.close()

    # Villa.AZ Scraper - scrape first 5 pages
    # Use lower concurrency (3) to avoid rate limiting
    villa_scraper = VillaAzScraperAsync(max_concurrent=3)

    try:
        await villa_scraper.scrape(pages=5)
    finally:
        villa_scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
