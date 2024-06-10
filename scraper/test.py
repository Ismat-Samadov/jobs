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
    # Other methods

    def parse_djinni_co(self, email, password, pages=3):
        """
        Function to parse job listings from djinni.co.

        :param email: Email address for login
        :param password: Password for login
        :param pages: Number of pages to scrape (default is 3)
        :return: DataFrame containing job details
        """

        logger.info(f"Started scraping djinni.co for first {pages} pages")

        # Define the login URL and the base URL for the jobs page
        login_url = 'https://djinni.co/login?from=frontpage_main'
        base_jobs_url = 'https://djinni.co/jobs/'

        # Define your login credentials
        credentials = {
            'email': email,
            'password': password
        }

        # Start a session
        session = requests.Session()

        # Get the login page to fetch any necessary CSRF tokens or cookies
        login_page = session.get(login_url)
        soup = BeautifulSoup(login_page.text, 'html.parser')

        # Check if a CSRF token is required and extract it
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_token:
            credentials['csrfmiddlewaretoken'] = csrf_token['value']

        # Perform the login
        response = session.post(login_url, data=credentials)

        # Check if login was successful
        if response.url == login_url:
            logger.error("Login failed for djinni.co")
            return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
        else:
            logger.info("Login successful for djinni.co")

            jobs = []

            # Function to scrape a single page
            def scrape_jobs_page(page_url):
                response = session.get(page_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                job_items = soup.find_all('li', class_='list-jobs__item')
                for job_item in job_items:
                    job = {}
                    job['id'] = job_item.get('id')
                    job['title'] = job_item.find('a', class_='h3 job-list-item__link').text.strip()
                    job['company'] = job_item.find('a', class_='mr-2').text.strip()
                    job['location'] = job_item.find('span', class_='location-text').text.strip()
                    job['experience'] = job_item.find('span', class_='nobr').text.strip()
                    job['description'] = job_item.find('div', class_='js-truncated-text').text.strip()
                    jobs.append(job)

            # Scrape the specified number of pages
            for page in range(1, pages + 1):
                logger.info(f"Scraping page {page} for djinni.co")
                page_url = f"{base_jobs_url}?page={page}"
                scrape_jobs_page(page_url)

            df = pd.DataFrame(jobs, columns=['id', 'title', 'company', 'location', 'experience', 'description'])
            logger.info("Scraping completed for djinni.co")
            return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

    # Other methods

# Example usage
if __name__ == "__main__":
    scraper = JobScraper()
    email = 'ismetsemedov@gmail.com'
    password = 'I19941994i'
    djinni_jobs = scraper.parse_djinni_co(email, password)

    # Print the extracted job details
    for job in djinni_jobs.to_dict('records'):
        print(f"Job ID: {job['id']}")
        print(f"Title: {job['title']}")
        print(f"Company: {job['company']}")
        print(f"Location: {job['location']}")
        print(f"Experience: {job['experience']}")
        print(f"Description: {job['description']}")
        print("="*40)
