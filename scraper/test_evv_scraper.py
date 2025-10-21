"""
Test script to verify the EVV.AZ scraper with full_data extraction
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sources.evv_az_scraper import EvvAzScraperAsync
from datetime import datetime


async def test_scraper():
    """Test the scraper with just 1 page"""
    print("=" * 70)
    print("Testing EVV.AZ Scraper with full_data extraction")
    print("=" * 70)

    scraper = EvvAzScraperAsync(max_concurrent=5)

    try:
        # Scrape just the first page of sale listings (should have ~24 listings)
        stats = await scraper.scrape(listing_type=1, page=1)

        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print(f"Total listings found: {stats['total']}")
        print(f"Successfully extracted: {stats['success']}")
        print(f"Failed to extract: {stats['failed']}")
        print(f"Saved to database: {stats['saved']}")
        print(f"Time taken: {stats.get('duration', 0):.2f} seconds")
        print("=" * 70)

        if stats['saved'] > 0:
            print("\n✓ Scraper test PASSED - At least one lead was saved with full_data")
            print("\nYou can now check your database to see the full_data JSON:")
            print("  SELECT phone_number, website, full_data FROM leads.leads ORDER BY created_at DESC LIMIT 1;")
        else:
            print("\n✗ Scraper test FAILED - No leads were saved")

    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()


if __name__ == "__main__":
    asyncio.run(test_scraper())
