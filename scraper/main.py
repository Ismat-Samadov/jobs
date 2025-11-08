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
from sources.tap_az_scraper import TapAzScraper
from sources.ipoteka_az_scraper import IpotekaAzScraper
from sources.vipemlak_az_scraper import VipemlakAzScraper
from sources.yeniemlak_az_scraper import YeniemlakAzScraper
from sources.unvan_az_scraper import UnvanAzScraper
from sources.rahatemlak_az_scraper import RahatEmlakAzScraper
from sources.ucuztap_az_scraper import UcuztapAzScraper
from sources.birja_in_scraper import BirjaInScraper
from sources.avtovitrin_com_scraper import AvtovitrinComScraper
from sources.binalar_az_scraper import BinalarAzScraperAsync
from sources.binam_az_scraper import BinamAzScraperAsync
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

    # BINA.AZ Scraper - scrape real estate property listings
    print("\n" + "=" * 70)
    print("BINA.AZ Scraper (Real Estate Properties)")
    print("=" * 70)
    bina_start = datetime.now()

    # Create database pool for BinaAz scraper
    db_pool6 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with BinaAzScraper(db_pool6) as bina_scraper:
            await bina_scraper.scrape(max_pages=5)

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

    # TAP.AZ Scraper - scrape classifieds listings
    print("\n" + "=" * 70)
    print("TAP.AZ Scraper (Classifieds)")
    print("=" * 70)
    tap_start = datetime.now()

    # Create database pool for TapAz scraper
    db_pool13 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with TapAzScraper(db_pool13) as tap_scraper:
            await tap_scraper.scrape(max_pages=5)

            tap_end = datetime.now()
            tap_duration = (tap_end - tap_start).total_seconds()

            tap_stats = {
                'new_leads': tap_scraper.stats['new_leads'],
                'duplicates': tap_scraper.stats['duplicates'],
                'errors': tap_scraper.stats['errors'],
                'invalid_phones': tap_scraper.stats['invalid_phones'],
                'duration': tap_duration,
                'start_time': tap_start
            }

            reports.append({
                'source': 'TAP.AZ',
                'stats': tap_stats,
                'duration': tap_duration,
                'start_time': tap_start
            })
    except Exception as e:
        print(f"✗ TAP.AZ scraping failed: {e}")
    finally:
        db_pool13.closeall()

    # IPOTEKA.AZ Scraper - scrape real estate listings
    print("\n" + "=" * 70)
    print("IPOTEKA.AZ Scraper (Real Estate)")
    print("=" * 70)
    ipoteka_start = datetime.now()

    # Create database pool for IpotekaAz scraper
    db_pool14 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with IpotekaAzScraper(db_pool14) as ipoteka_scraper:
            await ipoteka_scraper.scrape(max_pages=5)

            ipoteka_end = datetime.now()
            ipoteka_duration = (ipoteka_end - ipoteka_start).total_seconds()

            ipoteka_stats = {
                'new_leads': ipoteka_scraper.stats['new_leads'],
                'duplicates': ipoteka_scraper.stats['duplicates'],
                'errors': ipoteka_scraper.stats['errors'],
                'invalid_phones': ipoteka_scraper.stats['invalid_phones'],
                'duration': ipoteka_duration,
                'start_time': ipoteka_start
            }

            reports.append({
                'source': 'IPOTEKA.AZ',
                'stats': ipoteka_stats,
                'duration': ipoteka_duration,
                'start_time': ipoteka_start
            })
    except Exception as e:
        print(f"✗ IPOTEKA.AZ scraping failed: {e}")
    finally:
        db_pool14.closeall()

    # VIPEMLAK.AZ Scraper - scrape real estate listings
    print("\n" + "=" * 70)
    print("VIPEMLAK.AZ Scraper (Real Estate)")
    print("=" * 70)
    vipemlak_start = datetime.now()

    # Create database pool for VipemlakAz scraper
    db_pool15 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with VipemlakAzScraper(db_pool15) as vipemlak_scraper:
            await vipemlak_scraper.scrape(max_pages=5)

            vipemlak_end = datetime.now()
            vipemlak_duration = (vipemlak_end - vipemlak_start).total_seconds()

            vipemlak_stats = {
                'new_leads': vipemlak_scraper.stats['new_leads'],
                'duplicates': vipemlak_scraper.stats['duplicates'],
                'errors': vipemlak_scraper.stats['errors'],
                'invalid_phones': vipemlak_scraper.stats['invalid_phones'],
                'duration': vipemlak_duration,
                'start_time': vipemlak_start
            }

            reports.append({
                'source': 'VIPEMLAK.AZ',
                'stats': vipemlak_stats,
                'duration': vipemlak_duration,
                'start_time': vipemlak_start
            })
    except Exception as e:
        print(f"✗ VIPEMLAK.AZ scraping failed: {e}")
    finally:
        db_pool15.closeall()

    # YENIEMLAK.AZ Scraper - scrape real estate listings
    print("\n" + "=" * 70)
    print("YENIEMLAK.AZ Scraper (Real Estate)")
    print("=" * 70)
    yeniemlak_start = datetime.now()

    # Create database pool for YeniemlakAz scraper
    db_pool16 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with YeniemlakAzScraper(db_pool16) as yeniemlak_scraper:
            await yeniemlak_scraper.scrape(max_pages=5)

            yeniemlak_end = datetime.now()
            yeniemlak_duration = (yeniemlak_end - yeniemlak_start).total_seconds()

            yeniemlak_stats = {
                'new_leads': yeniemlak_scraper.stats['new_leads'],
                'duplicates': yeniemlak_scraper.stats['duplicates'],
                'errors': yeniemlak_scraper.stats['errors'],
                'invalid_phones': yeniemlak_scraper.stats['invalid_phones'],
                'duration': yeniemlak_duration,
                'start_time': yeniemlak_start
            }

            reports.append({
                'source': 'YENIEMLAK.AZ',
                'stats': yeniemlak_stats,
                'duration': yeniemlak_duration,
                'start_time': yeniemlak_start
            })
    except Exception as e:
        print(f"✗ YENIEMLAK.AZ scraping failed: {e}")
    finally:
        db_pool16.closeall()

    # UNVAN.AZ Scraper - scrape classifieds listings
    print("\n" + "=" * 70)
    print("UNVAN.AZ Scraper (Classifieds)")
    print("=" * 70)
    unvan_start = datetime.now()

    # Create database pool for UnvanAz scraper
    db_pool17 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with UnvanAzScraper(db_pool17) as unvan_scraper:
            await unvan_scraper.scrape(max_pages=5)

            unvan_end = datetime.now()
            unvan_duration = (unvan_end - unvan_start).total_seconds()

            unvan_stats = {
                'new_leads': unvan_scraper.stats['new_leads'],
                'duplicates': unvan_scraper.stats['duplicates'],
                'errors': unvan_scraper.stats['errors'],
                'invalid_phones': unvan_scraper.stats['invalid_phones'],
                'duration': unvan_duration,
                'start_time': unvan_start
            }

            reports.append({
                'source': 'UNVAN.AZ',
                'stats': unvan_stats,
                'duration': unvan_duration,
                'start_time': unvan_start
            })
    except Exception as e:
        print(f"✗ UNVAN.AZ scraping failed: {e}")
    finally:
        db_pool17.closeall()

    # RAHATEMLAK.AZ Scraper - scrape real estate listings
    print("\n" + "=" * 70)
    print("RAHATEMLAK.AZ Scraper (Real Estate)")
    print("=" * 70)
    rahatemlak_start = datetime.now()

    # Create database pool for RahatEmlakAz scraper
    db_pool18 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with RahatEmlakAzScraper(db_pool18) as rahatemlak_scraper:
            await rahatemlak_scraper.scrape(max_pages=5)

            rahatemlak_end = datetime.now()
            rahatemlak_duration = (rahatemlak_end - rahatemlak_start).total_seconds()

            rahatemlak_stats = {
                'new_leads': rahatemlak_scraper.stats['new_leads'],
                'duplicates': rahatemlak_scraper.stats['duplicates'],
                'errors': rahatemlak_scraper.stats['errors'],
                'invalid_phones': rahatemlak_scraper.stats['invalid_phones'],
                'duration': rahatemlak_duration,
                'start_time': rahatemlak_start
            }

            reports.append({
                'source': 'RAHATEMLAK.AZ',
                'stats': rahatemlak_stats,
                'duration': rahatemlak_duration,
                'start_time': rahatemlak_start
            })
    except Exception as e:
        print(f"✗ RAHATEMLAK.AZ scraping failed: {e}")
    finally:
        db_pool18.closeall()

    # UCUZTAP.AZ Scraper - scrape classifieds listings
    print("\n" + "=" * 70)
    print("UCUZTAP.AZ Scraper (Classifieds)")
    print("=" * 70)
    ucuztap_start = datetime.now()

    # Create database pool for UcuztapAz scraper
    db_pool19 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with UcuztapAzScraper(db_pool19) as ucuztap_scraper:
            await ucuztap_scraper.scrape(max_pages=5)

            ucuztap_end = datetime.now()
            ucuztap_duration = (ucuztap_end - ucuztap_start).total_seconds()

            ucuztap_stats = {
                'new_leads': ucuztap_scraper.stats['new_leads'],
                'duplicates': ucuztap_scraper.stats['duplicates'],
                'errors': ucuztap_scraper.stats['errors'],
                'invalid_phones': ucuztap_scraper.stats['invalid_phones'],
                'duration': ucuztap_duration,
                'start_time': ucuztap_start
            }

            reports.append({
                'source': 'UCUZTAP.AZ',
                'stats': ucuztap_stats,
                'duration': ucuztap_duration,
                'start_time': ucuztap_start
            })
    except Exception as e:
        print(f"✗ UCUZTAP.AZ scraping failed: {e}")
    finally:
        db_pool19.closeall()

    # BIRJA-IN.AZ Scraper - scrape training and course listings
    print("\n" + "=" * 70)
    print("BIRJA-IN.AZ Scraper (Training & Courses)")
    print("=" * 70)
    birja_in_start = datetime.now()

    # Create database pool for BirjaIn scraper
    db_pool20 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with BirjaInScraper(db_pool20) as birja_in_scraper:
            await birja_in_scraper.scrape(max_pages=5)

            birja_in_end = datetime.now()
            birja_in_duration = (birja_in_end - birja_in_start).total_seconds()

            birja_in_stats = {
                'new_leads': birja_in_scraper.stats['new_leads'],
                'duplicates': birja_in_scraper.stats['duplicates'],
                'errors': birja_in_scraper.stats['errors'],
                'invalid_phones': birja_in_scraper.stats['invalid_phones'],
                'duration': birja_in_duration,
                'start_time': birja_in_start
            }

            reports.append({
                'source': 'BIRJA-IN.AZ',
                'stats': birja_in_stats,
                'duration': birja_in_duration,
                'start_time': birja_in_start
            })
    except Exception as e:
        print(f"✗ BIRJA-IN.AZ scraping failed: {e}")
    finally:
        db_pool20.closeall()

    # AVTOVITRIN.COM Scraper - scrape car listings
    print("\n" + "=" * 70)
    print("AVTOVITRIN.COM Scraper (Cars)")
    print("=" * 70)
    avtovitrin_start = datetime.now()

    # Create database pool for AvtovitrinCom scraper
    db_pool21 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with AvtovitrinComScraper(db_pool21) as avtovitrin_scraper:
            await avtovitrin_scraper.scrape(max_pages=5)

            avtovitrin_end = datetime.now()
            avtovitrin_duration = (avtovitrin_end - avtovitrin_start).total_seconds()

            avtovitrin_stats = {
                'new_leads': avtovitrin_scraper.stats['new_leads'],
                'duplicates': avtovitrin_scraper.stats['duplicates'],
                'errors': avtovitrin_scraper.stats['errors'],
                'invalid_phones': avtovitrin_scraper.stats['invalid_phones'],
                'duration': avtovitrin_duration,
                'start_time': avtovitrin_start
            }

            reports.append({
                'source': 'AVTOVITRIN.COM',
                'stats': avtovitrin_stats,
                'duration': avtovitrin_duration,
                'start_time': avtovitrin_start
            })
    except Exception as e:
        print(f"✗ AVTOVITRIN.COM scraping failed: {e}")
    finally:
        db_pool21.closeall()

    # BINALAR.AZ Scraper - scrape real estate listings
    print("\n" + "=" * 70)
    print("BINALAR.AZ Scraper (Real Estate)")
    print("=" * 70)
    binalar_start = datetime.now()

    # Create database pool for BinalarAz scraper
    db_pool22 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with BinalarAzScraperAsync(db_pool22) as binalar_scraper:
            await binalar_scraper.scrape(max_pages=5)

            binalar_end = datetime.now()
            binalar_duration = (binalar_end - binalar_start).total_seconds()

            binalar_stats = {
                'new_leads': binalar_scraper.stats['new_leads'],
                'duplicates': binalar_scraper.stats['duplicates'],
                'errors': binalar_scraper.stats['errors'],
                'invalid_phones': binalar_scraper.stats['invalid_phones'],
                'duration': binalar_duration,
                'start_time': binalar_start
            }

            reports.append({
                'source': 'BINALAR.AZ',
                'stats': binalar_stats,
                'duration': binalar_duration,
                'start_time': binalar_start
            })
    except Exception as e:
        print(f"✗ BINALAR.AZ scraping failed: {e}")
    finally:
        db_pool22.closeall()

    # BINAM.AZ Scraper - scrape real estate listings
    print("\n" + "=" * 70)
    print("BINAM.AZ Scraper (Real Estate)")
    print("=" * 70)
    binam_start = datetime.now()

    # Create database pool for BinamAz scraper
    db_pool23 = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        os.getenv('DATABASE_URL')
    )

    try:
        async with BinamAzScraperAsync(db_pool23) as binam_scraper:
            await binam_scraper.scrape(max_pages=5)

            binam_end = datetime.now()
            binam_duration = (binam_end - binam_start).total_seconds()

            binam_stats = {
                'new_leads': binam_scraper.stats['new_leads'],
                'duplicates': binam_scraper.stats['duplicates'],
                'errors': binam_scraper.stats['errors'],
                'invalid_phones': binam_scraper.stats['invalid_phones'],
                'duration': binam_duration,
                'start_time': binam_start
            }

            reports.append({
                'source': 'BINAM.AZ',
                'stats': binam_stats,
                'duration': binam_duration,
                'start_time': binam_start
            })
    except Exception as e:
        print(f"✗ BINAM.AZ scraping failed: {e}")
    finally:
        db_pool23.closeall()

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
