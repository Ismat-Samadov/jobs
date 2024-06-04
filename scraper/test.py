import urllib3
from bs4 import BeautifulSoup
import pandas as pd
import requests
from datetime import datetime
import logging
import concurrent.futures
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_vakansiya_biz():
    logger.info("Started scraping vakansiya.biz")
    base_url = "https://api.vakansiya.biz/api/v1/vacancies/search"
    job_vacancies = []

    for page_num in range(1, 11):
        params = {
            "page": page_num,
            "country_id": 108,
            "city_id": 0,
            "industry_id": 0,
            "job_type_id": 0,
            "work_type_id": 0,
            "gender": -1,
            "education_id": 0,
            "experience_id": 0,
            "min_salary": 0,
            "max_salary": 0,
            "title": ""
        }
        response = fetch_url(base_url, params=params)
        if response:
            page_data = response.json().get('data', {}).get('items', [])
            if not page_data:
                break

            for item in page_data:
                job_vacancies.append({
                    'company': item.get('company_name', 'N/A'),
                    'vacancy': item.get('title', 'N/A'),
                    'apply_link': item.get('url', 'N/A')
                })
        else:
            logger.error(f"Failed to retrieve page {page_num} for vakansiya.biz")

    logger.info("Scraping completed for vakansiya.biz")
    return pd.DataFrame(job_vacancies) if job_vacancies else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])


print(parse_vakansiya_biz())