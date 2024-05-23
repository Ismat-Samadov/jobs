import urllib3
from bs4 import BeautifulSoup
import pandas as pd
import requests
from datetime import datetime
import logging
import concurrent.futures

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

    def parse_ejob_az(self, start_page=1, end_page=20):
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

    def parse_bank_respublika(self):
        logger.info("Scraping started for Bank Respublika")
        url = "https://www.bankrespublika.az/az/career"
        response = self.fetch_url(url, verify=False)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            jobs = []

            for job in soup.find_all("div", class_="vacancyItem whiteBox"):
                title_element = job.find("a", class_="title")
                title = title_element.text.strip() if title_element else "No title found"
                link = title_element['href'] if title_element and 'href' in title_element.attrs else "No link available"

                jobs.append({"company": 'Bank_Respublika', "vacancy": title, "apply_link": link})

            logger.info("Scraping completed for Bank Respublika")
            return pd.DataFrame(jobs) if jobs else pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
        else:
            logger.error("Failed to retrieve data for Bank Respublika.")
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
            self.parse_bank_respublika,
            self.parse_banker_az,
            self.parse_smartjob_az,
            self.parse_xalqbank,
            self.parse_offer_az
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


# Usage
if __name__ == "__main__":
    scraper = JobScraper()
    job_data = scraper.get_data()
    print(job_data)
