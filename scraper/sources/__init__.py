"""Sources package for various scrapers"""
from .evv_az_scraper import EvvAzScraperAsync
from .villa_az_scraper import VillaAzScraperAsync
from .bul_az_scraper import BulAzScraperAsync
from .turbo_az_scraper import TurboAzScraper, scrape_turbo_az
from .avtopro_az_scraper import AvtoproAzScraperAsync

__all__ = ['EvvAzScraperAsync',
           'VillaAzScraperAsync',
           'BulAzScraperAsync',
           'TurboAzScraper',
           'scrape_turbo_az',
           'AvtoproAzScraperAsync']
