import urllib3
from bs4 import BeautifulSoup
import pandas as pd
import requests
from datetime import datetime
import concurrent.futures
import time
from dotenv import load_dotenv
import os
import logging
from sqlalchemy import create_engine, types
from sqlalchemy.exc import SQLAlchemyError
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class JobScraper:
    def __init__(self):
        self.data = None
        self.email = None
        self.password = None
        self.load_credentials()

    def load_credentials(self):
        load_dotenv()
        self.email = os.getenv('EMAIL')
        self.password = os.getenv('PASSWORD')
        if not self.email or not self.password:
            logger.error("Email or password not set in environment variables.")

    def fetch_url(self, url, headers=None, params=None, verify=True):
        try:
            response = requests.get(url, headers=headers, params=params, verify=verify)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Request to {url} failed: {e}")
            return None

    def parse_classic_jobsearch_az(self):
        logger.info("Started scraping classic.jobsearch.az")

        chrome_options = Options()
        chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://classic.jobsearch.az/vacancies?date=&salary=&ads=&job_type=&location=&seniority=&ordering=&q=")

        def scroll_page(driver, max_scrolls):
            scroll_pause_time = 5  # Adjust to allow time for loading
            scrolls = 0
            last_height = driver.execute_script("return document.body.scrollHeight")

            while scrolls < max_scrolls:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                time.sleep(scroll_pause_time)

                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break  # Exit loop if no more content is loaded
                last_height = new_height
                scrolls += 1

        # Scroll 30 times to ensure more jobs are loaded
        scroll_page(driver, 30)

        try:
            WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'vacancies__item')))
        except Exception as e:
            logger.error("Error waiting for vacancies__item elements: %s", e)
            driver.save_screenshot('error_screenshot.png')
            driver.quit()
            return pd.DataFrame()

        jobs = []
        elements = driver.find_elements(By.CLASS_NAME, 'vacancies__item')
        seen_titles = set()

        for index, element in enumerate(elements):
            try:
                title_element = element.find_element(By.CSS_SELECTOR, 'h2.vacancies__title > a')
                company_element = element.find_element(By.CSS_SELECTOR, 'a.vacancies__provided > span')
                link = title_element.get_attribute('href')
                title = title_element.text.strip()

                if title not in seen_titles:
                    job = {
                        'company': company_element.text.strip(),
                        'vacancy': title,
                        'apply_link': link
                    }
                    jobs.append(job)
                    seen_titles.add(title)
            except Exception as e:
                logger.error(f"Error processing element {index}: {e}")
                driver.save_screenshot(f'error_element_{index}.png')
                continue

        driver.quit()

        df = pd.DataFrame(jobs)
        logger.info("Scraping completed for classic.jobsearch.az")
        return df

    def get_data(self):
        methods = [
            self.parse_classic_jobsearch_az
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
    # Conditional loading of dotenv for local development
    if os.environ.get('ENV') == 'development':
        load_dotenv()

    job_scraper = JobScraper()
    data = job_scraper.get_data()

    if data.empty:
        logger.warning("No data scraped to save to the database.")
        return

    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')

    # Build the database URL
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    # Create a database engine
    db_engine = create_engine(db_url)

    try:
        table_name = 'jobs'
        data.to_sql(name=table_name,
                    con=db_engine,
                    index=False,
                    if_exists='append',
                    dtype={"categories": types.JSON},
                    )
        logger.info("Data saved to the database.")
    except SQLAlchemyError as e:
        # Improved error handling: log the exception without stopping the program
        logger.error(f"An error occurred while saving data to the database: {str(e)}")
    finally:
        db_engine.dispose()  # Ensure the connection is closed properly
        logger.info("Database connection closed.")

if __name__ == "__main__":
    main()
