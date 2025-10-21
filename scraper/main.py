"""
Main entry point for running all scrapers
"""
import asyncio
from datetime import datetime
from sources import EvvAzScraperAsync, VillaAzScraperAsync
from scripts.telegram import TelegramNotifier


async def main():
    """Run all configured scrapers"""
    overall_start = datetime.now()
    reports = []

    # EVV.AZ Scraper - scrape all types (Sale, Rent, Daily) - 5 pages each = 15 total
    print("=" * 70)
    print("EVV.AZ Scraper")
    print("=" * 70)
    evv_scraper = EvvAzScraperAsync(max_concurrent=15)

    try:
        evv_stats = await evv_scraper.scrape(all_types=True, pages_per_type=5)
        reports.append({
            'source': 'EVV.AZ',
            'stats': evv_stats,
            'duration': evv_stats.get('duration', 0),
            'start_time': evv_stats.get('start_time', overall_start)
        })
    finally:
        evv_scraper.close()

    # Villa.AZ Scraper - scrape first 5 pages
    # Use lower concurrency (3) to avoid rate limiting
    print("\n" + "=" * 70)
    print("Villa.AZ Scraper")
    print("=" * 70)
    villa_scraper = VillaAzScraperAsync(max_concurrent=3)

    try:
        villa_stats = await villa_scraper.scrape(pages=5)
        reports.append({
            'source': 'Villa.AZ',
            'stats': villa_stats,
            'duration': villa_stats.get('duration', 0),
            'start_time': villa_stats.get('start_time', overall_start)
        })
    finally:
        villa_scraper.close()

    # Calculate overall duration
    overall_end = datetime.now()
    total_duration = (overall_end - overall_start).total_seconds()

    # Send combined Telegram notification
    print("\n" + "=" * 70)
    print("Sending Telegram Notification")
    print("=" * 70)
    notifier = TelegramNotifier()
    if notifier.is_configured():
        success = await notifier.send_multi_source_report(reports, total_duration)
        if success:
            print("✓ Telegram notification sent successfully")
        else:
            print("✗ Failed to send Telegram notification")
    else:
        print("Telegram not configured - skipping notification")
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to enable")

    print("\n" + "=" * 70)
    print(f"All scrapers completed in {total_duration:.2f}s")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
