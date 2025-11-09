"""Sources package for various scrapers"""
from .evv_az_scraper import EvvAzScraperAsync
from .villa_az_scraper import VillaAzScraperAsync
from .bul_az_scraper import BulAzScraperAsync
from .turbo_az_scraper import TurboAzScraper, scrape_turbo_az
from .avtopro_az_scraper import AvtoproAzScraperAsync
from .biturbo_az_scraper import BiTurboAzScraperAsync
from .autonet_az_scraper import AutoNetAzScraperAsync
from .bina_az_scraper import BinaAzScraper
from .aratap_az_scraper import AratapAzScraper
from .mashin_al_scraper import MashinAlScraper
from .masinlar_az_scraper import MasinlarAzScraper
from .tezbazar_az_scraper import TezBazarAzScraper
from .tunel_az_scraper import TunelAzScraper
from .tap_az_scraper import TapAzScraper
from .ipoteka_az_scraper import IpotekaAzScraper
from .vipemlak_az_scraper import VipemlakAzScraper
from .yeniemlak_az_scraper import YeniemlakAzScraper
from .unvan_az_scraper import UnvanAzScraper
from .rahatemlak_az_scraper import RahatEmlakAzScraper
from .ucuztap_az_scraper import UcuztapAzScraper
from .birja_in_scraper import BirjaInScraper
from .avtovitrin_com_scraper import AvtovitrinComScraper
from .binalar_az_scraper import BinalarAzScraperAsync
from .binam_az_scraper import BinamAzScraperAsync
from .mymarket_az_scraper import MymarketAzScraperAsync
from .myhome_az_scraper import MyhomeAzScraper

__all__ = ['EvvAzScraperAsync',
           'VillaAzScraperAsync',
           'BulAzScraperAsync',
           'TurboAzScraper',
           'scrape_turbo_az',
           'AvtoproAzScraperAsync',
           'BiTurboAzScraperAsync',
           'AutoNetAzScraperAsync',
           'BinaAzScraper',
           'AratapAzScraper',
           'MashinAlScraper',
           'MasinlarAzScraper',
           'TezBazarAzScraper',
           'TunelAzScraper',
           'TapAzScraper',
           'IpotekaAzScraper',
           'VipemlakAzScraper',
           'YeniemlakAzScraper',
           'UnvanAzScraper',
           'RahatEmlakAzScraper',
           'UcuztapAzScraper',
           'BirjaInScraper',
           'AvtovitrinComScraper',
           'BinalarAzScraperAsync',
           'BinamAzScraperAsync',
           'MymarketAzScraperAsync',
           'MyhomeAzScraper']
