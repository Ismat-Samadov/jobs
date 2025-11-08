"""
Main entry point for running all scrapers
"""
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from sources import EvvAzScraperAsync, VillaAzScraperAsync, BulAzScraperAsync, scrape_turbo_az, BiTurboAzScraperAsync, AutoNetAzScraperAsync
from sources.xidmetler_az_scraper import XidmetlerAzScraper
from sources.birja_com_scraper import BirjaComScraper
from sources.qarabazar_az_scraper import QarabazarAzScraper
from sources.emlak_az_scraper import EmlakAzScraper
from sources.lalafo_az_scraper import LalafoAzScraper
from sources.bina_az_scraper import BinaAzScraper
from sources.arenda_az_scraper import ArendaAzScraper
from sources.aratap_az_scraper import AratapAzScraper
from sources.mashin_al_scraper import MashinAlScraper
from sources.masinlar_az_scraper import MasinlarAzScraper
from sources.tezbazar_az_scraper import TezBazarAzScraper
from sources.tunel_az_scraper import TunelAzScraper
from scripts.telegram import TelegramNotifier
import os
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()


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

    # Bul.AZ Scraper - scrape first 5 pages
    print("\n" + "=" * 70)
    print("Bul.AZ Scraper")
    print("=" * 70)
    bul_scraper = BulAzScraperAsync(max_concurrent=10)

    try:
        bul_stats = await bul_scraper.scrape(pages=5)
        reports.append({
            'source': 'Bul.AZ',
            'stats': bul_stats,
            'duration': bul_stats.get('duration', 0),
            'start_time': bul_stats.get('start_time', overall_start)
        })
    finally:
        bul_scraper.close()

    # Turbo.AZ Scraper - scrape first 5 pages (runs in thread executor)
    print("\n" + "=" * 70)
    print("Turbo.AZ Scraper")
    print("=" * 70)
    turbo_start = datetime.now()

    try:
        # Run synchronous scraper in thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, scrape_turbo_az, 5)

        turbo_end = datetime.now()
        turbo_duration = (turbo_end - turbo_start).total_seconds()

        stats = result.get('stats', {})
        leads = result.get('leads', [])

        turbo_stats = {
            'new_leads': stats.get('saved', 0),
            'duplicates': stats.get('total', 0) - stats.get('saved', 0),
            'errors': stats.get('failed', 0),
            'duration': turbo_duration,
            'start_time': turbo_start,
            'leads': leads
        }

        reports.append({
            'source': 'Turbo.AZ',
            'stats': turbo_stats,
            'duration': turbo_duration,
            'start_time': turbo_start
        })

        print(f"✓ Turbo.AZ scraping completed: {stats.get('total', 0)} leads ({stats.get('saved', 0)} saved) in {turbo_duration:.2f}s")
    except Exception as e:
        print(f"✗ Turbo.AZ scraping failed: {e}")

    # BiTurbo.AZ Scraper - scrape first 5 pages
    print("\n" + "=" * 70)
    print("BiTurbo.AZ Scraper")
    print("=" * 70)
    biturbo_scraper = BiTurboAzScraperAsync(max_concurrent=10)

    try:
        biturbo_stats = await biturbo_scraper.scrape(pages=5)
        reports.append({
            'source': 'BiTurbo.AZ',
            'stats': biturbo_stats,
            'duration': biturbo_stats.get('duration', 0),
            'start_time': biturbo_stats.get('start_time', overall_start)
        })
    finally:
        biturbo_scraper.close()

    # AutoNet.AZ Scraper - scrape first 5 pages (license plates)
    print("\n" + "=" * 70)
    print("AutoNet.AZ Scraper (License Plates)")
    print("=" * 70)
    autonet_scraper = AutoNetAzScraperAsync(max_concurrent=10)

    try:
        autonet_stats = await autonet_scraper.scrape(pages=5)
        reports.append({
            'source': 'AutoNet.AZ',
            'stats': autonet_stats,
            'duration': autonet_stats.get('duration', 0),
            'start_time': autonet_stats.get('start_time', overall_start)
        })
    finally:
        autonet_scraper.close()

    # XiDMETLER.AZ Scraper - scrape courses/training listings
    print("\n" + "=" * 70)
    print("XiDMETLER.AZ Scraper (Courses & Training)")
    print("=" * 70)
    xidmetler_start = datetime.now()

    # Create database pool for XidmetlerAz scraper
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with XidmetlerAzScraper(db_pool) as xidmetler_scraper:
            await xidmetler_scraper.scrape(max_pages=5)

            xidmetler_end = datetime.now()
            xidmetler_duration = (xidmetler_end - xidmetler_start).total_seconds()

            xidmetler_stats = {
                'new_leads': xidmetler_scraper.stats['new_leads'],
                'duplicates': xidmetler_scraper.stats['duplicates'],
                'errors': xidmetler_scraper.stats['errors'],
                'invalid_phones': xidmetler_scraper.stats['invalid_phones'],
                'duration': xidmetler_duration,
                'start_time': xidmetler_start
            }

            reports.append({
                'source': 'XiDMETLER.AZ',
                'stats': xidmetler_stats,
                'duration': xidmetler_duration,
                'start_time': xidmetler_start
            })
    except Exception as e:
        print(f"✗ XiDMETLER.AZ scraping failed: {e}")
    finally:
        db_pool.closeall()

    # BIRJA.COM Scraper - scrape courses/training listings
    print("\n" + "=" * 70)
    print("BIRJA.COM Scraper (Courses & Training)")
    print("=" * 70)
    birja_start = datetime.now()

    # Create database pool for BirjaCom scraper
    db_pool2 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with BirjaComScraper(db_pool2) as birja_scraper:
            await birja_scraper.scrape(max_pages=5)

            birja_end = datetime.now()
            birja_duration = (birja_end - birja_start).total_seconds()

            birja_stats = {
                'new_leads': birja_scraper.stats['new_leads'],
                'duplicates': birja_scraper.stats['duplicates'],
                'errors': birja_scraper.stats['errors'],
                'invalid_phones': birja_scraper.stats['invalid_phones'],
                'duration': birja_duration,
                'start_time': birja_start
            }

            reports.append({
                'source': 'BIRJA.COM',
                'stats': birja_stats,
                'duration': birja_duration,
                'start_time': birja_start
            })
    except Exception as e:
        print(f"✗ BIRJA.COM scraping failed: {e}")
    finally:
        db_pool2.closeall()

    # QARABAZAR.AZ Scraper - scrape classifieds listings
    print("\n" + "=" * 70)
    print("QARABAZAR.AZ Scraper (Classifieds)")
    print("=" * 70)
    qarabazar_start = datetime.now()

    # Create database pool for QarabazarAz scraper
    db_pool3 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        qarabazar_scraper = QarabazarAzScraper(db_pool3)
        qarabazar_stats_raw = await qarabazar_scraper.scrape(pages=5, concurrency=10)

        qarabazar_end = datetime.now()
        qarabazar_duration = (qarabazar_end - qarabazar_start).total_seconds()

        qarabazar_stats = {
            'new_leads': qarabazar_stats_raw['saved_phones'],
            'duplicates': qarabazar_stats_raw['duplicates'],
            'errors': qarabazar_stats_raw['errors'],
            'invalid_phones': qarabazar_stats_raw['invalid_phones'],
            'duration': qarabazar_duration,
            'start_time': qarabazar_start
        }

        reports.append({
            'source': 'QARABAZAR.AZ',
            'stats': qarabazar_stats,
            'duration': qarabazar_duration,
            'start_time': qarabazar_start
        })
    except Exception as e:
        print(f"✗ QARABAZAR.AZ scraping failed: {e}")
    finally:
        db_pool3.closeall()

    # EMLAK.AZ Scraper - scrape real estate listings
    print("\n" + "=" * 70)
    print("EMLAK.AZ Scraper (Real Estate)")
    print("=" * 70)
    emlak_start = datetime.now()

    # Create database pool for EmlakAz scraper
    db_pool4 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        emlak_scraper = EmlakAzScraper(db_pool4)
        emlak_stats_raw = await emlak_scraper.scrape(pages=5, concurrency=10)

        emlak_end = datetime.now()
        emlak_duration = (emlak_end - emlak_start).total_seconds()

        emlak_stats = {
            'new_leads': emlak_stats_raw['saved_phones'],
            'duplicates': emlak_stats_raw['duplicates'],
            'errors': emlak_stats_raw['errors'],
            'invalid_phones': emlak_stats_raw['invalid_phones'],
            'duration': emlak_duration,
            'start_time': emlak_start
        }

        reports.append({
            'source': 'EMLAK.AZ',
            'stats': emlak_stats,
            'duration': emlak_duration,
            'start_time': emlak_start
        })
    except Exception as e:
        print(f"✗ EMLAK.AZ scraping failed: {e}")
    finally:
        db_pool4.closeall()

    # LALAFO.AZ Scraper - scrape classifieds listings
    print("\n" + "=" * 70)
    print("LALAFO.AZ Scraper (Classifieds)")
    print("=" * 70)
    lalafo_start = datetime.now()

    # Create database pool for LalafoAz scraper
    db_pool5 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        lalafo_scraper = LalafoAzScraper(db_pool5)
        lalafo_stats_raw = await lalafo_scraper.scrape(pages=5, concurrency=10)

        lalafo_end = datetime.now()
        lalafo_duration = (lalafo_end - lalafo_start).total_seconds()

        lalafo_stats = {
            'new_leads': lalafo_stats_raw['saved_phones'],
            'duplicates': lalafo_stats_raw['duplicates'],
            'errors': lalafo_stats_raw['errors'],
            'invalid_phones': lalafo_stats_raw['invalid_phones'],
            'duration': lalafo_duration,
            'start_time': lalafo_start
        }

        reports.append({
            'source': 'LALAFO.AZ',
            'stats': lalafo_stats,
            'duration': lalafo_duration,
            'start_time': lalafo_start
        })
    except Exception as e:
        print(f"✗ LALAFO.AZ scraping failed: {e}")
    finally:
        db_pool5.closeall()

    # BINA.AZ Scraper - scrape real estate agencies
    print("\n" + "=" * 70)
    print("BINA.AZ Scraper (Real Estate Agencies)")
    print("=" * 70)
    bina_start = datetime.now()

    # Create database pool for BinaAz scraper
    db_pool6 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with BinaAzScraper(db_pool6) as bina_scraper:
            await bina_scraper.scrape()  # All agencies on first page

            bina_end = datetime.now()
            bina_duration = (bina_end - bina_start).total_seconds()

            bina_stats = {
                'new_leads': bina_scraper.stats['new_leads'],
                'duplicates': bina_scraper.stats['duplicates'],
                'errors': bina_scraper.stats['errors'],
                'invalid_phones': bina_scraper.stats['invalid_phones'],
                'duration': bina_duration,
                'start_time': bina_start
            }

            reports.append({
                'source': 'BINA.AZ',
                'stats': bina_stats,
                'duration': bina_duration,
                'start_time': bina_start
            })
    except Exception as e:
        print(f"✗ BINA.AZ scraping failed: {e}")
    finally:
        db_pool6.closeall()

    # ARENDA.AZ Scraper - scrape real estate listings
    print("\n" + "=" * 70)
    print("ARENDA.AZ Scraper (Real Estate)")
    print("=" * 70)
    arenda_start = datetime.now()

    # Create database pool for ArendaAz scraper
    db_pool7 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with ArendaAzScraper(db_pool7, max_concurrent=10) as arenda_scraper:
            arenda_stats_raw = await arenda_scraper.scrape(pages=5, concurrency=10)

            arenda_end = datetime.now()
            arenda_duration = (arenda_end - arenda_start).total_seconds()

            arenda_stats = {
                'new_leads': arenda_stats_raw['saved_phones'],
                'duplicates': arenda_stats_raw['duplicates'],
                'errors': arenda_stats_raw['errors'],
                'invalid_phones': arenda_stats_raw['invalid_phones'],
                'duration': arenda_duration,
                'start_time': arenda_start
            }

            reports.append({
                'source': 'ARENDA.AZ',
                'stats': arenda_stats,
                'duration': arenda_duration,
                'start_time': arenda_start
            })
    except Exception as e:
        print(f"✗ ARENDA.AZ scraping failed: {e}")
    finally:
        db_pool7.closeall()

    # ARATAP.AZ Scraper - scrape classifieds listings
    print("\n" + "=" * 70)
    print("ARATAP.AZ Scraper (Classifieds)")
    print("=" * 70)
    aratap_start = datetime.now()

    # Create database pool for AratapAz scraper
    db_pool8 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with AratapAzScraper(db_pool8) as aratap_scraper:
            await aratap_scraper.scrape(max_pages=5)

            aratap_end = datetime.now()
            aratap_duration = (aratap_end - aratap_start).total_seconds()

            aratap_stats = {
                'new_leads': aratap_scraper.stats['new_leads'],
                'duplicates': aratap_scraper.stats['duplicates'],
                'errors': aratap_scraper.stats['errors'],
                'invalid_phones': aratap_scraper.stats['invalid_phones'],
                'duration': aratap_duration,
                'start_time': aratap_start
            }

            reports.append({
                'source': 'ARATAP.AZ',
                'stats': aratap_stats,
                'duration': aratap_duration,
                'start_time': aratap_start
            })
    except Exception as e:
        print(f"✗ ARATAP.AZ scraping failed: {e}")
    finally:
        db_pool8.closeall()

    # MASHIN.AL Scraper - scrape car listings
    print("\n" + "=" * 70)
    print("MASHIN.AL Scraper (Cars)")
    print("=" * 70)
    mashin_start = datetime.now()

    # Create database pool for MashinAl scraper
    db_pool9 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with MashinAlScraper(db_pool9) as mashin_scraper:
            await mashin_scraper.scrape(max_pages=5)

            mashin_end = datetime.now()
            mashin_duration = (mashin_end - mashin_start).total_seconds()

            mashin_stats = {
                'new_leads': mashin_scraper.stats['new_leads'],
                'duplicates': mashin_scraper.stats['duplicates'],
                'errors': mashin_scraper.stats['errors'],
                'invalid_phones': mashin_scraper.stats['invalid_phones'],
                'duration': mashin_duration,
                'start_time': mashin_start
            }

            reports.append({
                'source': 'MASHIN.AL',
                'stats': mashin_stats,
                'duration': mashin_duration,
                'start_time': mashin_start
            })
    except Exception as e:
        print(f"✗ MASHIN.AL scraping failed: {e}")
    finally:
        db_pool9.closeall()

    # MASINLAR.AZ Scraper - scrape car rental/sales listings
    print("\n" + "=" * 70)
    print("MASINLAR.AZ Scraper (Car Rental & Sales)")
    print("=" * 70)
    masinlar_start = datetime.now()

    # Create database pool for MasinlarAz scraper
    db_pool10 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with MasinlarAzScraper(db_pool10) as masinlar_scraper:
            await masinlar_scraper.scrape(max_pages=5)

            masinlar_end = datetime.now()
            masinlar_duration = (masinlar_end - masinlar_start).total_seconds()

            masinlar_stats = {
                'new_leads': masinlar_scraper.stats['new_leads'],
                'duplicates': masinlar_scraper.stats['duplicates'],
                'errors': masinlar_scraper.stats['errors'],
                'invalid_phones': masinlar_scraper.stats['invalid_phones'],
                'duration': masinlar_duration,
                'start_time': masinlar_start
            }

            reports.append({
                'source': 'MASINLAR.AZ',
                'stats': masinlar_stats,
                'duration': masinlar_duration,
                'start_time': masinlar_start
            })
    except Exception as e:
        print(f"✗ MASINLAR.AZ scraping failed: {e}")
    finally:
        db_pool10.closeall()

    # TEZBAZAR.AZ Scraper - scrape classifieds listings
    print("\n" + "=" * 70)
    print("TEZBAZAR.AZ Scraper (Classifieds)")
    print("=" * 70)
    tezbazar_start = datetime.now()

    # Create database pool for TezBazarAz scraper
    db_pool11 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with TezBazarAzScraper(db_pool11) as tezbazar_scraper:
            await tezbazar_scraper.scrape(max_pages=5)

            tezbazar_end = datetime.now()
            tezbazar_duration = (tezbazar_end - tezbazar_start).total_seconds()

            tezbazar_stats = {
                'new_leads': tezbazar_scraper.stats['new_leads'],
                'duplicates': tezbazar_scraper.stats['duplicates'],
                'errors': tezbazar_scraper.stats['errors'],
                'invalid_phones': tezbazar_scraper.stats['invalid_phones'],
                'duration': tezbazar_duration,
                'start_time': tezbazar_start
            }

            reports.append({
                'source': 'TEZBAZAR.AZ',
                'stats': tezbazar_stats,
                'duration': tezbazar_duration,
                'start_time': tezbazar_start
            })
    except Exception as e:
        print(f"✗ TEZBAZAR.AZ scraping failed: {e}")
    finally:
        db_pool11.closeall()

    # TUNEL.AZ Scraper - scrape car listings
    print("\n" + "=" * 70)
    print("TUNEL.AZ Scraper (Cars)")
    print("=" * 70)
    tunel_start = datetime.now()

    # Create database pool for TunelAz scraper
    db_pool12 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with TunelAzScraper(db_pool12) as tunel_scraper:
            await tunel_scraper.scrape(max_pages=5)

            tunel_end = datetime.now()
            tunel_duration = (tunel_end - tunel_start).total_seconds()

            tunel_stats = {
                'new_leads': tunel_scraper.stats['new_leads'],
                'duplicates': tunel_scraper.stats['duplicates'],
                'errors': tunel_scraper.stats['errors'],
                'invalid_phones': tunel_scraper.stats['invalid_phones'],
                'duration': tunel_duration,
                'start_time': tunel_start
            }

            reports.append({
                'source': 'TUNEL.AZ',
                'stats': tunel_stats,
                'duration': tunel_duration,
                'start_time': tunel_start
            })
    except Exception as e:
        print(f"✗ TUNEL.AZ scraping failed: {e}")
    finally:
        db_pool12.closeall()

    # Calculate overall duration
    overall_end = datetime.now()
    total_duration = (overall_end - overall_start).total_seconds()

    # Send combined Telegram notification
    print("\n" + "=" * 70)
    print("Sending Telegram Notification")
    print("=" * 70)

    # Create database pool for Telegram notifier (to query actual stats)
    telegram_db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 5,
        os.getenv('DATABASE_URL')
    )

    try:
        notifier = TelegramNotifier(db_pool=telegram_db_pool)
        if notifier.is_configured():
            success = await notifier.send_multi_source_report(reports, total_duration)
            if success:
                print("✓ Telegram notification sent successfully")
            else:
                print("✗ Failed to send Telegram notification")
        else:
            print("Telegram not configured - skipping notification")
            print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to enable")
    finally:
        telegram_db_pool.closeall()

    print("\n" + "=" * 70)
    print(f"All scrapers completed in {total_duration:.2f}s")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
