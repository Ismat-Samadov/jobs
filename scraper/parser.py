# scraper/parser.py
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
from datetime import datetime
import time
import pytz
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
    def parse_azercell(self):
        logger.info("Started scraping Azercel")
        url = "https://www.azercell.com/az/about-us/career.html"
        response = self.fetch_url(url)
        if response:
            soup = BeautifulSoup(response.text, "html.parser")
            vacancies_section = soup.find("section", class_="section_vacancies")
            if vacancies_section:
                job_listings = vacancies_section.find_all("a", class_="vacancies__link")
                job_titles = [job.find("h4", class_="vacancies__name").text for job in job_listings]
                job_links = [job["href"] for job in job_listings]
                df = pd.DataFrame({'company': 'azercell', "vacancy": job_titles, "apply_link": job_links})
                logger.info("Scraping completed for Azercel")
                return df
            else:
                logger.warning("Vacancies section not found on the Azercel page.")
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_pashabank(self):
        logger.info("Scraping Pashabank")
        url = "https://careers.pashabank.az/az/page/vakansiyalar?q=&branch="
        response = self.fetch_url(url)
        if response:
            if response.status_code == 503:
                logger.warning("Service unavailable for Pashabank (status code 503). Retrying...")
                response = self.fetch_url(url)
            if response and response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_listings = soup.find_all('div', class_='what-we-do-item')
                vacancy_list = [listing.find('h3').text for listing in job_listings]
                apply_link_list = [listing.find('a')['href'] for listing in job_listings]
                df = pd.DataFrame({'company': 'pashabank', 'vacancy': vacancy_list, 'apply_link': apply_link_list})
                df = df.drop_duplicates(subset=['company', 'vacancy', 'apply_link'])
                logger.info("Pashabank Scraping completed")
                return df
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_azerconnect(self):
        logger.info("Started scraping of Azerconnect")
        url = "https://www.azerconnect.az/careers"
        response = self.fetch_url(url, verify=False)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            job_listings = soup.find_all('div', class_='CollapsibleItem_item__CB3bC')

            vacancies = []
            apply_links = []
            for job in job_listings:
                job_title = job.find('div', class_='CollapsibleItem_toggle__XNu5y').find('span').text.strip()
                vacancies.append(job_title)
                apply_link_tag = job.find('a', class_='Button_button-blue__0wZ4l')
                if apply_link_tag:
                    apply_link = apply_link_tag['href']
                    apply_links.append(apply_link)
                else:
                    apply_links.append("N/A")

            df = pd.DataFrame({'company': 'azerconnect', 'vacancy': vacancies, 'apply_link': apply_links})
            logger.info("Scraping of Azerconnect completed")
            return df
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_abb(self):
        logger.info("Scraping starting for ABB")
        base_url = "https://careers.abb-bank.az/api/vacancy/v2/get"
        job_vacancies = []
        page = 0

        while True:
            params = {"page": page}
            response = self.fetch_url(base_url, params=params)

            if response:
                data = response.json().get("data", [])

                if not data:
                    break

                for item in data:
                    title = item.get("title")
                    url = item.get("url")
                    job_vacancies.append({"company": "ABB", "vacancy": title, "apply_link": url})
                page += 1
            else:
                logger.error(f"Failed to retrieve data for page {page}.")
                break

        df = pd.DataFrame(job_vacancies)
        logger.info("ABB scraping completed")
        return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_busy_az(self):
        logger.info("Scraping started for busy.az")
        job_vacancies = []
        for page_num in range(1, 5):
            logger.info(f"Scraping page {page_num}")
            url = f'https://busy.az/vacancies?page={page_num}'
            response = self.fetch_url(url)

            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_listings = soup.find_all('a', class_='job-listing')

                for job in job_listings:
                    job_details = job.find('div', class_='job-listing-details')
                    job_title = job_details.find('h3', class_='job-listing-title').text.strip()
                    company_element = job_details.find('i', class_='icon-material-outline-business')
                    company_name = company_element.find_parent('li').text.strip() if company_element else 'N/A'
                    apply_link = job.get('href')
                    job_vacancies.append({"company": company_name, "vacancy": job_title, "apply_link": apply_link})
            else:
                logger.error(f"Failed to retrieve page {page_num}.")

        df = pd.DataFrame(job_vacancies)
        logger.info("Scraping completed for busy.az")
        return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_hellojob_az(self):
        logger.info("Started scraping of hellojob.az")
        job_vacancies = []
        base_url = "https://www.hellojob.az"

        for page_number in range(1, 11):
            url = f"{base_url}/vakansiyalar?page={page_number}"
            response = self.fetch_url(url)
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_listings = soup.find_all('a', class_='vacancies__item')
                if not job_listings:
                    logger.info(f"No job listings found on page {page_number}.")
                    continue

                for job in job_listings:
                    company_name = job.find('p', class_='vacancy_item_company').text.strip()
                    vacancy_title = job.find('h3').text.strip()
                    apply_link = job['href'] if job['href'].startswith('http') else base_url + job['href']

                    job_vacancies.append({"company": company_name, "vacancy": vacancy_title, "apply_link": apply_link})
            else:
                logger.warning(f"Failed to retrieve page {page_number}")

        logger.info("Scraping completed for hellojob.az")
        return pd.DataFrame(job_vacancies) if job_vacancies else pd.DataFrame(
            columns=['company', 'vacancy', 'apply_link'])
    def parse_boss_az(self):
        logger.info("Starting to scrape Boss.az...")
        job_vacancies = []
        for page_num in range(1, 21):  # Scrape from page 1 to 20
            url = f"https://boss.az/vacancies?page={page_num}"
            response = self.fetch_url(url)
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_listings = soup.find_all('div', class_='results-i')
                for job in job_listings:
                    title = job.find('h3', class_='results-i-title').get_text(strip=True)
                    company = job.find('a', class_='results-i-company').get_text(strip=True)
                    link = f"https://boss.az{job.find('a', class_='results-i-link')['href']}"
                    job_vacancies.append({"company": company, "vacancy": title, "apply_link": link})
                logger.info(f"Scraped {len(job_listings)} jobs from page {page_num}")
            else:
                logger.warning(f"Failed to retrieve page {page_num}. Status code: {response.status_code}")

        logger.info("Scraping completed for boss.az")
        return pd.DataFrame(job_vacancies) if job_vacancies else pd.DataFrame(
            columns=['company', 'vacancy', 'apply_link'])
    def parse_ejob_az(self):
        start_page = 1
        end_page = 20
        logger.info("Scraping started for ejob.az")
        base_url = "https://ejob.az/is-elanlari"
        all_jobs = []
        for page in range(start_page, end_page + 1):
            url = f"{base_url}/page-{page}/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            response = self.fetch_url(url, headers=headers)
            logger.info(f"URL: {url} - Status Code: {response.status_code}")
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_tables = soup.find_all('table', class_='background')
                for job in job_tables:
                    title_link = job.find('a', href=True)
                    salary = job.find('div', class_='salary').text if job.find('div',
                                                                               class_='salary') else 'No salary listed'
                    company = job.find('div', class_='company').text if job.find('div',
                                                                                 class_='company') else 'No company listed'
                    all_jobs.append({
                        'company': company,
                        'vacancy': title_link.text.strip(),
                        'apply_link': f"https://ejob.az{title_link['href']}"
                    })
            else:
                logger.warning(f"Failed to retrieve page {page}.")

        logger.info("Scraping completed for ejob.az")
        return pd.DataFrame(all_jobs) if all_jobs else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_vakansiya_az(self):
        logger.info("Scraping started for vakansiya.az")
        url = 'https://www.vakansiya.az/az/'
        response = self.fetch_url(url)
        if response:
            soup = BeautifulSoup(response.content, 'html.parser')
            jobs = []
            job_divs = soup.find_all('div', id='js-jobs-wrapper')
            logger.info(f"Found {len(job_divs)} job postings.")

            for job_div in job_divs:
                company = job_div.find_all('div', class_='js-fields')[1].find('a')
                title = job_div.find('a', class_='jobtitle')
                apply_link = title['href'] if title else None

                jobs.append({
                    'company': company.get_text(strip=True) if company else 'N/A',
                    'vacancy': title.get_text(strip=True) if title else 'N/A',
                    'apply_link': f'https://www.vakansiya.az{apply_link}' if apply_link else 'N/A'
                })
                logger.info(f"Job found: {jobs[-1]}")

            logger.info("Scraping completed for vakansiya.az")
            return pd.DataFrame(jobs) if jobs else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
        else:
            logger.error("Failed to retrieve the page.")
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_ishelanlari_az(self):
        logger.info("Scraping started for ishelanlari.az")
        url = "https://ishelanlari.az/az/vacancies//0/360/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = self.fetch_url(url, headers=headers)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            vacancies = []
            for job in soup.find_all("div", class_="card-body"):
                title_element = job.find("h2", class_="font-weight-bold")
                company_element = job.find("a", class_="text-muted")
                details_link_element = job.find("a", class_="position-absolute")

                title = title_element.text.strip() if title_element else "No title provided"
                company = company_element.text.strip() if company_element else "No company provided"
                link = details_link_element["href"] if details_link_element else "No link provided"

                vacancies.append({
                    "company": company,
                    "vacancy": title,
                    "apply_link": "https://ishelanlari.az" + link
                })
            logger.info("Scraping completed for ishelanlari.az")
            return pd.DataFrame(vacancies) if vacancies else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
        else:
            logger.error("Failed to retrieve data for ishelanlari.az.")
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_bank_of_baku_az(self):
        logger.info("Scraping started for Bank of Baku")
        url = "https://careers.bankofbaku.com/az/vacancies"
        response = self.fetch_url(url, verify=False)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            jobs = []
            job_blocks = soup.find_all('div', class_='main-cell mc-50p')

            for job_block in job_blocks:
                link_tag = job_block.find('a')
                if link_tag:
                    link = 'https://careers.bankofbaku.com' + link_tag['href']
                    job_info = job_block.find('div', class_='vacancy-list-block-content')
                    title = job_info.find('div', class_='vacancy-list-block-header').get_text(
                        strip=True) if job_info else 'No title provided'
                    department_label = job_info.find('label', class_='light-red-bg')
                    deadline = department_label.get_text(strip=True) if department_label else 'No deadline listed'
                    department_info = job_info.find_all('label')[0].get_text(strip=True) if len(
                        job_info.find_all('label')) > 0 else 'No department listed'
                    location_info = job_info.find_all('label')[1].get_text(strip=True) if len(
                        job_info.find_all('label')) > 1 else 'No location listed'

                    jobs.append({'company': 'Bank of Baku', 'vacancy': title, 'apply_link': link})

            logger.info("Scraping completed for Bank of Baku")
            return pd.DataFrame(jobs) if jobs else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
        else:
            logger.error("Failed to retrieve data for Bank of Baku.")
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_banker_az(self):
        logger.info("Started scraping Banker.az")
        base_url = 'https://banker.az/vakansiyalar'
        num_pages = 5

        all_job_titles = []
        all_company_names = []
        all_apply_links = []

        for page in range(1, num_pages + 1):
            url = f"{base_url}/page/{page}/"
            response = self.fetch_url(url)
            if response:
                soup = BeautifulSoup(response.content, 'html.parser')
                job_listings = soup.find_all('div', class_='list-data')

                for job in job_listings:
                    job_info = job.find('div', class_='job-info')
                    title_tag = job_info.find('a') if job_info else None
                    title = title_tag.text.strip() if title_tag else None
                    link = title_tag['href'] if title_tag else None

                    company_logo = job.find('div', class_='company-logo')
                    company_img = company_logo.find('img') if company_logo else None
                    company = company_img.get('alt') if company_img else None

                    if title and '-' in title:
                        title_parts = title.split(' – ')
                        title = title_parts[0].strip()
                        if len(title_parts) > 1:
                            company = title_parts[1].strip()

                    if title and company and link:
                        all_job_titles.append(title)
                        all_company_names.append(company)
                        all_apply_links.append(link)
            else:
                logger.warning(f"Failed to retrieve page {page}.")

        df = pd.DataFrame({'company': all_company_names, 'vacancy': all_job_titles, 'apply_link': all_apply_links})
        logger.info("Scraping completed for Banker.az")
        return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_smartjob_az(self):
        logger.info("Started scraping SmartJob.az")
        jobs = []

        for page in range(1, 11):
            url = f"https://smartjob.az/vacancies?page={page}"
            response = self.fetch_url(url)
            if response:
                soup = BeautifulSoup(response.text, "html.parser")
                job_listings = soup.find_all('div', class_='item-click')

                if not job_listings:
                    continue

                for listing in job_listings:
                    title = listing.find('div', class_='brows-job-position').h3.a.text.strip()
                    company = listing.find('span', class_='company-title').a.text.strip()
                    jobs.append({
                        'company': company,
                        'vacancy': title,
                        'apply_link': listing.find('div', class_='brows-job-position').h3.a['href']
                    })
            else:
                logger.warning(f"Failed to retrieve page {page}.")

        logger.info("Scraping completed for SmartJob.az")
        return pd.DataFrame(jobs) if jobs else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_xalqbank(self):
        logger.info("Started scraping Xalqbank")
        url = 'https://www.xalqbank.az/az/ferdi/bank/career'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/',
            'Dnt': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cookie': '_gid=GA1.2.2120774294.1716196109; _ym_uid=1707748848536691364; _ym_d=1716196109; _ym_isad=2; _fbp=fb.1.1716196109680.1185575570; _ym_visorc=w; uslk_umm_1234_s=ewAiAHYAZQByAHMAaQBvAG4AIgA6ACIAMQAiACwAIgBkAGEAdABhACIAOgB7AH0AfQA=; _ga_Z2590XM715=GS1.1.1716196109.1.1.1716196497.60.0.0; _ga=GA1.1.544691763.1716196109'
        }
        response = self.fetch_url(url, headers=headers)
        if response:
            soup = BeautifulSoup(response.content, 'html.parser')

            vacancies = []
            vacancy_items = soup.find_all('a', class_='vacancies__item')

            for item in vacancy_items:
                category = item.find('span', class_='vacancies__category').text.strip()
                title = item.find('h2', class_='vacancies__title').text.strip()
                link = item['href']
                vacancies.append([category, title, link])

            df = pd.DataFrame(vacancies, columns=['company', 'vacancy', 'apply_link'])
            df['company'] = 'xalqbank'
            logger.info("Scraping completed for Xalqbank")
            return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
        else:
            logger.error("Failed to retrieve data for Xalqbank.")
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_offer_az(self):
        logger.info("Started scraping offer.az")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/',
            'Dnt': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        vacancies = []

        for page in range(1, 11):
            url = f'https://www.offer.az/is-elanlari/page/{page}/'
            response = self.fetch_url(url, headers=headers)
            if response:
                soup = BeautifulSoup(response.content, 'html.parser')
                job_elements = soup.find_all('div', class_='job-card')
                logger.info(f"Found {len(job_elements)} job elements on page {page}")

                for job_element in job_elements:
                    title_tag = job_element.find('a', class_='job-card__title')
                    company_tag = job_element.find('p', class_='job-card__meta')
                    location_tag = job_element.find_all('p', class_='job-card__meta')[1]
                    date_tag = job_element.find_all('p', class_='job-card__meta')[1]

                    title = title_tag.text.strip() if title_tag else 'No title'
                    company = company_tag.text.strip() if company_tag else 'No company'
                    location = location_tag.text.strip().split(' - ')[1] if location_tag else 'No location'
                    date = date_tag.text.strip().split(' - ')[0] if date_tag else 'No date'
                    link = title_tag['href'] if title_tag and 'href' in title_tag.attrs else 'No link'

                    vacancies.append([company, title, link])
                    logger.info(f"Company: {company}, Vacancy: {title}, Link: {link}")
            else:
                logger.warning(f"Failed to retrieve page {page}.")

        df = pd.DataFrame(vacancies, columns=['company', 'vacancy', 'apply_link'])
        logger.info("Scraping completed for offer.az")
        return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_isveren_az(self):
        start_page = 1
        end_page = 15
        max_retries = 3
        backoff_factor = 1
        jobs = []
        for page_num in range(start_page, end_page + 1):
            retries = 0
            while retries < max_retries:
                try:
                    logger.info(f"Scraping started for isveren.az page {page_num}")
                    url = f"https://isveren.az/?page={page_num}"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
                    }

                    response = requests.get(url, headers=headers, timeout=10)

                    if response.status_code != 200:
                        logger.error(f"Failed to retrieve page {page_num}. Status code: {response.status_code}")
                        break

                    soup = BeautifulSoup(response.text, 'html.parser')
                    job_cards = soup.find_all('div', class_='job-card')

                    for job_card in job_cards:
                        try:
                            title_element = job_card.find('h5', class_='job-title')
                            company_element = job_card.find('p', class_='job-list')
                            link_element = job_card.find('a', href=True)

                            title = title_element.text.strip() if title_element else "No title provided"
                            company = company_element.text.strip() if company_element else "No company provided"
                            link = link_element['href'] if link_element else "No link provided"

                            jobs.append({
                                'company': company,
                                'vacancy': title,
                                'apply_link': link
                            })
                        except Exception as e:
                            logger.error(f"Error parsing job card on page {page_num}: {e}")

                    break  # Exit the retry loop if the request was successful
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    retries += 1
                    logger.warning(f"Attempt {retries} for page {page_num} failed: {e}")
                    if retries < max_retries:
                        sleep_time = backoff_factor * (2 ** (retries - 1))
                        logger.info(f"Retrying page {page_num} in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"Max retries exceeded for page {page_num}")

        df = pd.DataFrame(jobs)
        logger.info("Scraping completed for isveren.az")
        return df
    def parse_isqur(self):
        start_page = 1
        end_page = 5
        logger.info("Started scraping isqur.com")
        job_vacancies = []
        base_url = "https://isqur.com/is-elanlari/sehife-"

        for page_num in range(start_page, end_page + 1):
            logger.info(f"Scraping page {page_num} for isqur.com")
            url = f"{base_url}{page_num}"
            response = self.fetch_url(url)
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_cards = soup.find_all('div', class_='kart')
                for job in job_cards:
                    title = job.find('div', class_='basliq').text.strip()
                    company = "Unknown"  # The provided HTML does not include a company name
                    link = "https://isqur.com/" + job.find('a')['href']
                    job_vacancies.append({'company': company, 'vacancy': title, 'apply_link': link})
            else:
                logger.error(f"Failed to retrieve page {page_num} for isqur.com")

        logger.info("Scraping completed for isqur.com")
        return pd.DataFrame(job_vacancies) if job_vacancies else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
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
                'apply_link': f"https://jobs.glorri.az/vacancies/mktcotton/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_unibank(self):
        company_name = 'unibank'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_abc_telecom(self):
        company_name = 'abc-telecom'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_expressbank(self):
        company_name = 'expressbank'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_aztelekom(self):
        company_name = 'aztelekom'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_azerimed(self):
        company_name = 'azerimed'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_idda(self):
        company_name = 'idda'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_agagroup(self):
        company_name = 'agagroup'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_azercotton(self):
        company_name = 'azercotton'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_accessbank(self):
        company_name = 'accessbank'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_landauschool(self):
        company_name = 'landauschool'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_atb(self):
        company_name = 'atb'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_azal(self):
        company_name = 'azal'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_bankrespublika(self):
        company_name = 'bankrespublika'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_ateshgah(self):
        company_name = 'ateshgah'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_rabitabank(self):
        company_name = 'rabitabank'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_matanata(self):
        company_name = 'matanata'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_fmg(self):
        company_name = 'fmg'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_pashaproperty(self):
        company_name = 'pashaproperty'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_bakusteel(self):
        company_name = 'bakusteel'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_elitoptimal(self):
        company_name = 'elitoptimal'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_aztexgroup(self):
        company_name = 'aztexgroup'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_embawood(self):
        company_name = 'embawood'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_avromed(self):
        company_name = 'avromed'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_fincaazerbaijan(self):
        company_name = 'fincaazerbaijan'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_autoluxaz(self):
        company_name = 'autolux-az'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_pmdprojects(self):
        company_name = 'pmdprojects'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_itv(self):
        company_name = 'itv'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_zafarbaglari(self):
        company_name = 'zafarbaglari'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_pmdgroup(self):
        company_name = 'pmdgroup'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_agilesolutions(self):
        company_name = 'agilesolutions'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_otomed(self):
        company_name = 'otomed'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_grandagro(self):
        company_name = 'grandagro'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_azrose(self):
        company_name = 'azrose'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_idealkredit(self):
        company_name = 'idealkredit'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_azbadam(self):
        company_name = 'azbadam'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_code(self):
        company_name = 'code'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_agrofoodinvest(self):
        company_name = 'agrofoodinvest'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_urc(self):
        company_name = 'urc'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_agrarco(self):
        company_name = 'agrarco'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_hermese(self):
        company_name = 'hermese'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_ailab(self):
        company_name = 'ailab'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_vipgroup(self):
        company_name = 'vipgroup'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_saluspharma(self):
        company_name = 'saluspharma'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_coolab(self):
        company_name = 'coolab'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_ecologistics(self):
        company_name = 'eco-logistics'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_grandagroinvitro(self):
        company_name = 'grandagroinvitro'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_glorri(self):
        company_name = 'glorri'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_bakuagropark(self):
        company_name = 'bakuagropark'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_agroparkyalama(self):
        company_name = 'agroparkyalama'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_sofcons(self):
        company_name = 'sofcons'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_bakertilly(self):
        company_name = 'bakertilly'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_butafarm(self):
        company_name = 'butafarm'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_deligy(self):
        company_name = 'deligy'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_absheronport(self):
        company_name = 'absheronport'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_bpgconsulting(self):
        company_name = 'bpgconsulting'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_pashadevelopment(self):
        company_name = 'pashadevelopment'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_fbco(self):
        company_name = 'fbco'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_hrcbaku(self):
        company_name = 'hrcbaku'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })

        return pd.DataFrame(jobs_data)
    def parse_alameta(self):
        company_name = 'alameta'
        logger.info(f"Fetching jobs from Glorri.az for {company_name}")
        base_url = f"https://atsapp.glorri.az/job-service/v2/company/{company_name}/jobs"
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
                'company': company_name,
                'vacancy': job['title'],
                'apply_link': f"https://jobs.glorri.az/vacancies/{company_name}/{job['slug']}/apply"
            })
        return pd.DataFrame(jobs_data)

    def parse_kapitalbank(self):
        logger.info("Fetching jobs from Kapital Bank API")
        url = "https://apihr.kapitalbank.az/api/Vacancy/vacancies?Skip=0&Take=150&SortField=id&OrderBy=true"
        response = self.fetch_url(url)

        if response:
            data = response.json().get('data', [])
            if not data:
                logger.warning("No job data found in the API response.")
                return pd.DataFrame(
                    columns=['company', 'vacancy', 'apply_link'])

            jobs_data = []
            for job in data:
                jobs_data.append({
                    'company': 'Kapital Bank',
                    'vacancy': job['header'],
                    'apply_link': f"https://hr.kapitalbank.az/vacancy/{job['id']}"
                })

            logger.info("Job data fetched and parsed successfully from Kapital Bank API")
            return pd.DataFrame(jobs_data)
        else:
            logger.error("Failed to fetch data from Kapital Bank API.")
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

    def parse_jobbox_az(self, start_page=1, end_page=5):
        logger.info(f"Scraping started for jobbox.az from page {start_page} to page {end_page}")
        job_vacancies = []
        for page_num in range(start_page, end_page + 1):
            logger.info(f"Scraping page {page_num}")
            url = f'https://jobbox.az/az/vacancies?page={page_num}'
            response = self.fetch_url(url)

            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_items = soup.find_all('li', class_='item')

                for item in job_items:
                    job = {}

                    link_tag = item.find('a')
                    if link_tag:
                        job['apply_link'] = link_tag['href']
                    else:
                        continue  # Skip if no link found

                    title_ul = item.find('ul', class_='title')
                    if title_ul:
                        title_div = title_ul.find_all('li')
                        job['vacancy'] = title_div[0].text.strip() if len(title_div) > 0 else None
                    else:
                        continue  # Skip if title information is missing

                    address_ul = item.find('ul', class_='address')
                    if address_ul:
                        address_div = address_ul.find_all('li')
                        job['company'] = address_div[0].text.strip() if len(address_div) > 0 else None
                    else:
                        continue  # Skip if address information is missing

                    job_vacancies.append(job)
            else:
                logger.error(f"Failed to retrieve page {page_num}.")

        df = pd.DataFrame(job_vacancies, columns=['company', 'vacancy', 'apply_link'])
        logger.info("Scraping completed for jobbox.az")
        return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_vakansiya_biz(self):
        logger.info("Started scraping Vakansiya.biz")
        base_url = "https://api.vakansiya.biz/api/v1/vacancies/search"
        headers = {'Content-Type': 'application/json'}
        page = 1
        all_jobs = []

        while True:
            response = requests.get(f"{base_url}?page={page}&country_id=108&city_id=0&industry_id=0&job_type_id=0&work_type_id=0&gender=-1&education_id=0&experience_id=0&min_salary=0&max_salary=0&title=", headers=headers)

            if response.status_code != 200:
                logger.error(f"Failed to fetch page {page}: {response.status_code}")
                break

            data = response.json()
            jobs = data.get('data', [])
            all_jobs.extend(jobs)

            if not data.get('next_page_url'):
                break

            page += 1

        job_listings = [{
            'company': job['company_name'],
            'vacancy': job['title'],
            'apply_link': f"https://vakansiya.biz/az/vakansiyalar/{job['id']}/{job['slug']}"
        } for job in all_jobs]

        df = pd.DataFrame(job_listings)
        logger.info("Scraping completed for Vakansiya.biz")
        return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

    def parse_its_gov(self):
        start_page=1
        end_page=20
        logger.info(f"Scraping its.gov.az from page {start_page} to page {end_page}")
        base_url = "https://its.gov.az/page/vakansiyalar?page="
        all_vacancies = []

        for page in range(start_page, end_page + 1):
            url = f"{base_url}{page}"
            logger.info(f"Fetching page {page}")
            response = self.fetch_url(url)
            if response:
                soup = BeautifulSoup(response.text, "html.parser")
                events = soup.find_all('div', class_='event')
                if not events:
                    logger.info(f"No job listings found on page {page}")
                    break

                for event in events:
                    title_tag = event.find('a', class_='event__link')
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        link = title_tag['href']
                        deadline_tag = event.find('span', class_='event__time')
                        deadline = deadline_tag.get_text(strip=True) if deadline_tag else 'N/A'
                        all_vacancies.append({'company': 'Icbari tibbi sigorta', 'vacancy': title, 'apply_link': link})
            else:
                logger.warning(f"Failed to retrieve page {page}")

        return pd.DataFrame(all_vacancies)
    
    def parse_career_ady_az(self):
        logger.info("Started scraping career.ady.az")
        print("------------------------------------")
        print("------------------------------------")
        print("------------------------------------")
        print("------------------------------------")
        print("------------------------------------")

        url = "https://career.ady.az/"
        response = self.fetch_url(url)
        if response:
            soup = BeautifulSoup(response.content, "html.parser")
            job_listings = []

            table = soup.find("table", {"id": "tbl_vacation"})
            if table:
                rows = table.find_all("tr", class_="job-listing")

                for row in rows:
                    job_title = row.find("td", class_="job-title-sec").find("a").text.strip()
                    company = row.find("td", class_="job-title-sec").find("span").text.strip()
                    location = row.find("td", class_="job-lctn").text.strip()
                    end_date = row.find("td", class_="job-enddate").text.strip()
                    job_url = row.find("a", class_="job-is")["href"]

                    job_listings.append({
                        "company": "ADY-Azərbaycan Dəmir Yolları",
                        "vacancy": job_title,
                        "apply_link": "https://career.ady.az"+job_url
                    })

                df = pd.DataFrame(job_listings)
                logger.info("Scraping completed for career.ady.az")
                return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
        logger.warning("Failed to scrape career.ady.az")
        print("------------------------------------")
        print("------------------------------------")
        print("------------------------------------")
        print("------------------------------------")
        print("------------------------------------")

        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])


    def parse_is_elanlari_iilkin(self):
        logger.info("Started scraping is-elanlari.iilkin.com")
        base_url = 'http://is-elanlari.iilkin.com/vakansiyalar/'
        job_listings = []

        # Function to scrape a single page
        def scrape_page(content):
            soup = BeautifulSoup(content, 'html.parser')
            main_content = soup.find('main', id='main', class_='site-main')
            if main_content:
                articles = main_content.find_all('article')
                for job in articles:
                    title_element = job.find('a', class_='home-title-links')
                    company_element = job.find('p', class_='vacan-company-name')
                    link_element = job.find('a', class_='home-title-links')

                    job_listings.append({
                        "vacancy": title_element.text.strip() if title_element else 'N/A',
                        "company": company_element.text.strip() if company_element else 'N/A',
                        "apply_link": link_element['href'] if link_element else 'N/A'
                    })
            else:
                logger.warning("Main content not found")

        for page_num in range(1, 4):
            url = base_url if page_num == 1 else f'{base_url}{page_num}'
            logger.info(f'Scraping page {page_num}...')
            response = self.fetch_url(url)
            if response:
                scrape_page(response.content)
        
        if job_listings:
            df = pd.DataFrame(job_listings)
            logger.info("Scraping completed for is-elanlari.iilkin.com")
            return df
        else:
            logger.warning("No job listings found")
            return pd.DataFrame(columns=['vacancy', 'company', 'apply_link'])


    def parse_djinni_co(self):
        pages=15
        logger.info(f"Started scraping djinni.co for first {pages} pages")

        login_url = 'https://djinni.co/login?from=frontpage_main'
        base_jobs_url = 'https://djinni.co/jobs/'

        credentials = {
            'email': self.email,
            'password': self.password
        }

        session = requests.Session()
        login_page = session.get(login_url)
        soup = BeautifulSoup(login_page.text, 'html.parser')

        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_token:
            credentials['csrfmiddlewaretoken'] = csrf_token['value']
        else:
            logger.error("CSRF token not found.")
            return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

        headers = {
            'Referer': login_url
        }

        response = session.post(login_url, data=credentials, headers=headers)
        if 'logout' in response.text:
            logger.info("Login successful for djinni.co")
        else:
            logger.error("Login failed for djinni.co")
            return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

        jobs = []

        def scrape_jobs_page(page_url):
            response = session.get(page_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            job_items = soup.find_all('li', class_='list-jobs__item')
            for job_item in job_items:
                job = {}
                job['company'] = job_item.find('a', class_='mr-2').text.strip()
                job['vacancy'] = job_item.find('a', class_='h3 job-list-item__link').text.strip()
                job['apply_link'] = 'https://djinni.co' + job_item.find('a', class_='h3 job-list-item__link')['href']
                jobs.append(job)

        for page in range(1, pages + 1):
            logger.info(f"Scraping page {page} for djinni.co")
            page_url = f"{base_jobs_url}?page={page}"
            scrape_jobs_page(page_url)

        df = pd.DataFrame(jobs, columns=['company', 'vacancy', 'apply_link'])
        logger.info("Scraping completed for djinni.co")

        if df.empty:
            logger.warning("No jobs found during scraping.")
            return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

        for job in df.to_dict('records'):
            logger.info(f"Title: {job['vacancy']}")
            logger.info(f"Company: {job['company']}")
            logger.info(f"Detailed Info Link: {job['apply_link']}")
            logger.info("="*40)

        return df if not df.empty else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

  
    def parse_talhunt_az(self):
        logger.info("Started scraping Talhunt.az")
        base_url = "https://api.talhunt.az/jobs/Vacancy/All"
        offset = 0
        limit = 10
        params = {
            'offset': offset,
            'limit': limit,
            'lang': 'az',
            'search': ''
        }
        job_vacancies = []

        while True:
            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching data from {base_url} with params {params}: {e}")
                break

            items = data.get('items', [])
            
            if not items:
                break

            for job in items:
                tenant = job.get('tenant', 'N/A')
                vacancy_url = job.get('vacancyUrl', '')
                apply_link = f"https://jobs.talhunt.az/{tenant}/{vacancy_url}"
                job_vacancies.append({
                    'company': job.get('companyName', 'N/A'),
                    'vacancy': job.get('title', 'N/A'),
                    'apply_link': apply_link
                })
            
            if data.get('totalPage', 0) <= params['offset'] // limit + 1:
                break
            
            params['offset'] += limit

        df = pd.DataFrame(job_vacancies)
        logger.info("Scraping completed for Talhunt.az")

        return df

    def parse_tabib_vacancies(self):
        logger.info("Started scraping TABIB vacancies")
        url = "https://tabib.gov.az/_next/data/VVczvdjPBoUR2khOC7cCO/az/vetendashlar-ucun/vakansiyalar.json"
        response = self.fetch_url(url)

        if response:
            data = response.json()
            vacancies = data.get("pageProps", {}).get("vacancies", [])
            if vacancies:
                vacancy_list = []
                for vacancy in vacancies:
                    vacancy_info = {
                        "company": "TABIB",
                        "vacancy": vacancy["title"],
                        "apply_link": f"https://tabib.gov.az/vetendashlar-ucun/vakansiyalar/{vacancy['id']}"
                    }
                    vacancy_list.append(vacancy_info)
                df = pd.DataFrame(vacancy_list)
                logger.info("Scraping completed for TABIB")
                return df
            else:
                logger.warning("No vacancies found in the API response.")
        return pd.DataFrame(columns=["company", "vacancy", "apply_link"])

 
    def parse_projobs_vacancies(self):
        """Fetch and parse job vacancies from Projobs API."""
        data = []
        base_url = "https://core.projobs.az/v1/vacancies"
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Connection': 'keep-alive',
            'Dnt': '1',
            'Host': 'core.projobs.az',
            'Origin': 'https://projobs.az',
            'Referer': 'https://projobs.az/',
            'Sec-Ch-Ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        }
        max_pages=10
        for page in range(1, max_pages + 1):
            url = f"{base_url}?page={page}"
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                vacancies = response.json().get("data", [])
                for vacancy in vacancies:
                    vacancy_info = {
                        "company": vacancy["companyName"],
                        "vacancy": vacancy["name"],
                        "apply_link": f"https://projobs.az/jobdetails/{vacancy['id']}"
                    }
                    data.append(vacancy_info)
                logger.info(f"Scraped page {page} successfully.")
            except requests.RequestException as e:
                logger.error(f"Request to {url} failed: {e}")
                continue

        if data:
            df = pd.DataFrame(data)
            logger.info("Scraping completed for Projobs")
            return df
        else:
            logger.warning("No vacancies found in the API response.")
            return pd.DataFrame(columns=["company", "vacancy", "apply_link"])

    def parse_azergold(self):
        logger.info("Started scraping AzerGold")
        url = "https://careers.azergold.az/"
        response = self.fetch_url(url, verify=False)  # Added verify=False to handle SSL issues
        if response:
            soup = BeautifulSoup(response.text, "html.parser")
            logger.info("Page fetched successfully")

            # Locate the table containing the job listings
            table = soup.find("table", class_="table-vacancy")
            if table:
                logger.info("Vacancies section found")
                job_rows = table.find("tbody").find_all("tr")

                job_titles = []
                job_links = []

                for row in job_rows:
                    title_cell = row.find("td")
                    if title_cell:
                        title_link = title_cell.find("a")
                        if title_link:
                            job_titles.append(title_link.text.strip())
                            job_links.append(title_link["href"])

                df = pd.DataFrame({'company': 'AzerGold', "vacancy": job_titles, "apply_link": job_links})
                logger.info("Scraping completed for AzerGold")
                return df
            else:
                logger.warning("Vacancies section not found on the AzerGold page.")
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def parse_konsis(self):
        logger.info("Started scraping Konsis")
        url = "https://konsis.az/karyera-vakansiya/"
        response = self.fetch_url(url, verify=False)  # Added verify=False to handle SSL issues
        if response:
            soup = BeautifulSoup(response.text, "html.parser")
            logger.info("Page fetched successfully")

            # Locate the articles containing the job listings
            articles = soup.find_all("div", class_="grid-item")
            if articles:
                logger.info("Vacancies section found")
                job_titles = []
                job_companies = []
                job_locations = []
                job_types = []
                job_descriptions = []
                job_links = []

                for article in articles:
                    meta = article.find("div", class_="item--meta")
                    if meta:
                        job_title = meta.find("h3", class_="item--title").text.strip()
                        features = meta.find_all("li")
                        job_company = features[0].text.strip()
                        job_location = features[1].text.strip()
                        job_type = features[2].text.strip()
                        job_description = article.find("div", class_="item-desc").text.strip()
                        job_link = article.find("a", class_="btn btn-secondary", href=True)["href"]

                        job_titles.append(job_title)
                        job_companies.append(job_company)
                        job_locations.append(job_location)
                        job_types.append(job_type)
                        job_descriptions.append(job_description)
                        job_links.append("https://konsis.az" + job_link)

                df = pd.DataFrame({
                    'company': job_companies,
                    'vacancy': job_titles,
                    'apply_link': job_links
                })
                logger.info("Scraping completed for Konsis")
                return df
            else:
                logger.warning("Vacancies section not found on the Konsis page.")
        return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

    def parse_baku_electronics(self):
        logger.info("Started scraping Baku Electronics")
        base_url = "https://careers.bakuelectronics.az/az/vacancies/?p="
        all_job_titles = []
        all_job_categories = []
        all_job_locations = []
        all_job_deadlines = []
        all_job_links = []

        for page in range(1, 3):  
            url = f"{base_url}{page}"
            response = self.fetch_url(url, verify=False)
            if response:
                soup = BeautifulSoup(response.text, "html.parser")
                logger.info(f"Page {page} fetched successfully")

                # Locate the blocks containing the job listings
                vacancy_blocks = soup.find_all("div", class_="vacancy-list-block")
                if vacancy_blocks:
                    logger.info("Vacancies section found")
                    for block in vacancy_blocks:
                        header = block.find("div", class_="vacancy-list-block-header")
                        info = block.find("div", class_="vacancy-list-block-info")
                        deadline = block.find("div", class_="vacancy-list-block-note")
                        link_tag = block.find_parent("a", href=True)
                        link = link_tag["href"] if link_tag else None

                        job_title = header.text.strip() if header else None
                        category_location = info.find_all("label") if info else []
                        job_category = category_location[0].text.strip() if len(category_location) > 0 else None
                        job_location = category_location[1].text.strip() if len(category_location) > 1 else None
                        job_deadline = deadline.text.strip() if deadline else None
                        job_link = "https://careers.bakuelectronics.az" + link if link else None

                        if None in [job_title, job_category, job_location, job_deadline, job_link]:
                            logger.warning(f"Missing elements in block: title={job_title}, category={job_category}, location={job_location}, deadline={job_deadline}, link={job_link}")
                            continue

                        all_job_titles.append(job_title)
                        all_job_categories.append(job_category)
                        all_job_locations.append(job_location)
                        all_job_deadlines.append(job_deadline)
                        all_job_links.append(job_link)
                else:
                    logger.warning(f"Vacancies section not found on page {page}.")
            else:
                logger.warning(f"Failed to fetch page {page}.")

        df = pd.DataFrame({
            'company': 'Baku Electronics',
            'vacancy': all_job_titles,
            'apply_link': all_job_links
        })
        logger.info("Scraping completed for Baku Electronics")
        return df
    def parse_asco(self):
        logger.info("Started scraping ASCO")
        base_url = "https://www.asco.az/az/pages/6/65?page="
        all_job_numbers = []
        all_job_titles = []
        all_job_deadlines = []
        all_job_links = []

        for page in range(1, 4):  
            url = f"{base_url}{page}"
            response = self.fetch_url(url, verify=False)
            if response:
                soup = BeautifulSoup(response.text, "html.parser")
                logger.info(f"Page {page} fetched successfully")

                # Locate the blocks containing the job listings
                table = soup.find("table", class_="default")
                if table:
                    rows = table.find_all("tr")[1:]  # Skip header row
                    for row in rows:
                        cols = row.find_all("td")
                        job_number = cols[0].text.strip() if cols[0] else None
                        job_title = cols[1].text.strip() if cols[1] else None
                        job_deadline = cols[2].text.strip() if cols[2] else None
                        job_link_tag = cols[3].find("a", href=True)
                        job_link = job_link_tag["href"] if job_link_tag else None

                        if None in [job_number, job_title, job_deadline, job_link]:
                            logger.warning(f"Missing elements in row: number={job_number}, title={job_title}, deadline={job_deadline}, link={job_link}")
                            continue

                        all_job_numbers.append(job_number)
                        all_job_titles.append(job_title)
                        all_job_deadlines.append(job_deadline)
                        all_job_links.append(job_link)
                else:
                    logger.warning(f"Job listings table not found on page {page}.")
            else:
                logger.warning(f"Failed to fetch page {page}.")

        df = pd.DataFrame({
            'company': 'ASCO',
            'vacancy': all_job_titles,
            'apply_link': all_job_links
        })
        logger.info("Scraping completed for ASCO")
        return df
    def parse_cbar(self):
        logger.info("Started scraping CBAR")
        url = "https://www.cbar.az/hr/f?p=100:106"
        response = self.fetch_url(url, verify=False)
        if response:
            soup = BeautifulSoup(response.text, "html.parser")
            logger.info("Page fetched successfully")

            all_job_numbers = []
            all_job_titles = []
            all_job_start_dates = []
            all_job_end_dates = []
            all_job_links = []

            # Locate the blocks containing the job listings
            table = soup.find("table", class_="a-IRR-table")
            if table:
                rows = table.find_all("tr")[1:]  # Skip header row
                for row in rows:
                    cols = row.find_all("td")
                    job_number = cols[0].text.strip() if cols[0] else None
                    job_title = cols[1].text.strip() if cols[1] else None
                    job_start_date = cols[2].text.strip() if cols[2] else None
                    job_end_date = cols[3].text.strip() if cols[3] else None
                    job_link_tag = cols[1].find("a", href=True)
                    job_link = job_link_tag["href"] if job_link_tag else None

                    if job_link and 'javascript:' in job_link:
                        match = re.search(r"P50_VACANCY_ID,P50_POSITION_ID:([^,]+),([^&]+)", job_link)
                        if match:
                            job_vacancy_id = match.group(1)
                            job_position_id = match.group(2)
                            job_link = f"https://www.cbar.az/hr/f?p=100:50::::50:P50_VACANCY_ID,P50_POSITION_ID:{job_vacancy_id},{job_position_id}"

                    if None in [job_number, job_title, job_start_date, job_end_date, job_link]:
                        logger.warning(f"Missing elements in row: number={job_number}, title={job_title}, start_date={job_start_date}, end_date={job_end_date}, link={job_link}")
                        continue

                    all_job_numbers.append(job_number)
                    all_job_titles.append(job_title)
                    all_job_start_dates.append(job_start_date)
                    all_job_end_dates.append(job_end_date)
                    all_job_links.append(job_link)
            else:
                logger.warning("Job listings table not found on the page.")

            df = pd.DataFrame({
                'company': 'CBAR',
                'vacancy': all_job_titles,
                'apply_link': 'https://www.cbar.az/hr/f?p=100:106'
            })
            logger.info("Scraping completed for CBAR")
            return df
        else:
            logger.error("Failed to fetch the page.")
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

        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'vacancies__item')))

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
                continue

        driver.quit()

        df = pd.DataFrame(jobs)
        logger.info("Scraping completed for classic.jobsearch.az")
        return df
    def get_data(self):
        methods = [
            self.parse_azercell,
            self.parse_pashabank,
            self.parse_azerconnect,
            self.parse_abb,
            self.parse_busy_az,
            self.parse_hellojob_az,
            self.parse_boss_az,
            self.parse_ejob_az,
            self.parse_vakansiya_az,
            self.parse_ishelanlari_az,
            self.parse_bank_of_baku_az,
            self.parse_banker_az,
            self.parse_smartjob_az,
            self.parse_xalqbank,
            self.parse_offer_az,
            self.parse_isveren_az,
            self.parse_isqur,
            self.parse_mktcotton,
            self.parse_unibank,
            self.parse_abc_telecom,
            self.parse_expressbank,
            self.parse_aztelekom,
            self.parse_azerimed,
            self.parse_idda,
            self.parse_agagroup,
            self.parse_azercotton,
            self.parse_accessbank,
            self.parse_landauschool,
            self.parse_atb,
            self.parse_azal,
            self.parse_bankrespublika,
            self.parse_ateshgah,
            self.parse_rabitabank,
            self.parse_matanata,
            self.parse_fmg,
            self.parse_pashaproperty,
            self.parse_bakusteel,
            self.parse_elitoptimal,
            self.parse_aztexgroup,
            self.parse_embawood,
            self.parse_avromed,
            self.parse_fincaazerbaijan,
            self.parse_autoluxaz,
            self.parse_pmdprojects,
            self.parse_itv,
            self.parse_zafarbaglari,
            self.parse_pmdgroup,
            self.parse_agilesolutions,
            self.parse_otomed,
            self.parse_grandagro,
            self.parse_azrose,
            self.parse_idealkredit,
            self.parse_azbadam,
            self.parse_code,
            self.parse_agrofoodinvest,
            self.parse_urc,
            self.parse_agrarco,
            self.parse_hermese,
            self.parse_ailab,
            self.parse_vipgroup,
            self.parse_saluspharma,
            self.parse_coolab,
            self.parse_ecologistics,
            self.parse_grandagroinvitro,
            self.parse_glorri,
            self.parse_bakuagropark,
            self.parse_agroparkyalama,
            self.parse_sofcons,
            self.parse_bakertilly,
            self.parse_butafarm,
            self.parse_deligy,
            self.parse_absheronport,
            self.parse_bpgconsulting,
            self.parse_pashadevelopment,
            self.parse_fbco,
            self.parse_hrcbaku,
            self.parse_alameta,
            self.parse_kapitalbank,
            self.parse_jobbox_az,
            self.parse_vakansiya_biz,
            self.parse_its_gov,
            self.parse_career_ady_az,
            self.parse_is_elanlari_iilkin,
            self.parse_djinni_co,
            self.parse_talhunt_az,
            self.parse_tabib_vacancies,
            self.parse_projobs_vacancies,
            self.parse_azergold,
            self.parse_konsis,
            self.parse_baku_electronics,
            self.parse_asco,
            self.parse_cbar,
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

    # Print data before saving
    logger.info(f"Data to be saved: {data}")

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
