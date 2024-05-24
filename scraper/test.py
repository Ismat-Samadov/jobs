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

class JobScraper:
    def __init__(self):
        self.data = None

    def fetch_url(self, url, headers=None, params=None, verify=True):
        try:
            response = requests.get(url, headers=headers, params=params, verify=verify)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Request to {url} failed: {e}")
            return None

    def parse_mktcotton(self):
        logger.info("Fetching jobs from Glorri.az for MKT Cotton")
        base_url = "https://atsapp.glorri.az/job-service/v2/company/mktcotton/jobs"
        all_jobs = []
        offset = 0
        limit = 18

        while True:
            params = {'offset': offset, 'limit': limit}
            response = self.fetch_url(base_url, params=params)
            if response:
                data = response.json()
                entities = data.get('entities', [])

                if not entities:
                    break

                all_jobs.extend(entities)
                offset += limit
                logger.info(f"Fetched {len(entities)} jobs, total so far: {len(all_jobs)}")
            else:
                logger.error("Failed to retrieve jobs data.")
                break

        logger.info(f"Total jobs fetched: {len(all_jobs)}")

        jobs_data = []
        for job in all_jobs:
            jobs_data.append({
                'company': job['company']['name'] if 'company' in job else 'MKT Cotton',
                'vacancy': job['title'],
                'location': job['location'],
                'apply_link': f"https://jobs.glorri.az/vacancies/mktcotton/{job['slug']}/apply",
                'view_count': job.get('viewCount', 'N/A')
            })

        return pd.DataFrame(jobs_data)

    def get_data(self):
        methods = [
            self.parse_mktcotton  # Added the new parser to the methods list
        ]

        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_method = {executor.submit(method): method for method in methods}
            for future in concurrent.futures.as_completed(future_to_method):
                method = future_to_method[future]
                try:
                    result = future.result()
                    if not result.empty:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error executing {method.__name__}: {e}")

        if results:
            self.data = pd.concat(results, ignore_index=True)
            self.data['scrape_date'] = datetime.now()
        else:
            self.data = pd.DataFrame(columns=['company', 'vacancy', 'apply_link', 'scrape_date'])

        return self.data


def main():
    scraper = JobScraper()

    # Fetch data using all the parsers including the new MKT Cotton parser
    data = scraper.get_data()
    excel_file = 'scraped_jobs.xlsx'
    data.to_excel(excel_file, index=False)
    # Print the first few rows of the resulting dataframe
    print(data.head())

if __name__ == "__main__":
    main()
