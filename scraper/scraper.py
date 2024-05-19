# scraper/scraper.py
import urllib3
from bs4 import BeautifulSoup
import pandas as pd
import requests
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class JobScraper:
    def __init__(self):
        self.data = None

    def azercell(self):
        print("Started scraping Azercel")
        url = "https://www.azercell.com/az/about-us/career.html"
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            vacancies_section = soup.find("section", class_="section_vacancies")
            if vacancies_section:
                job_listings = vacancies_section.find_all("a", class_="vacancies__link")
                job_titles = []
                job_links = []
                for job in job_listings:
                    job_title = job.find("h4", class_="vacancies__name").text
                    job_link = job["href"]
                    job_titles.append(job_title)
                    job_links.append(job_link)
                df = pd.DataFrame({
                    'company': 'azercell',
                    "vacancy": job_titles,
                    "apply_link": job_links
                })
                print("Scraping completed Azercell")
                return df
            else:
                print("Vacancies section not found on the page.")
        else:
            print("Failed to retrieve the page. Status code:", response.status_code)

    def pashabank(self):
        print("Scraping Pashabank")
        url = "https://careers.pashabank.az/az/page/vakansiyalar?q=&branch="
        response = requests.get(url)
        vacancy_list = []
        apply_link_list = []
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            job_listings = soup.find_all('div', class_='what-we-do-item')
            for listing in job_listings:
                job_title = listing.find('h3').text
                apply_link = listing.find('a')['href']
                vacancy_list.append(job_title)
                apply_link_list.append(apply_link)
        else:
            print(f"Failed to retrieve the page. Status code: {response.status_code}")
        data = {
            'company': 'pashabank',
            'vacancy': vacancy_list,
            'apply_link': apply_link_list
        }
        df = pd.DataFrame(data)
        df = df.drop_duplicates(subset=['company', 'vacancy', 'apply_link'])
        print("Pashabank Scraping completed")
        return df

    def azerconnect(self):
        print("Started scraping of Azerconnect")
        url = "https://www.azerconnect.az/careers"
        response = requests.get(url, verify=False)
        if response.status_code == 200:
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

            df = pd.DataFrame({'company': 'azerconnect',
                               'vacancy': vacancies,
                               'apply_link': apply_links})
            print("Scraping of Azerconnect completed")
            return df

        else:
            print("Failed to retrieve the web page.")
            return None

    def abb(self):
        print("Scraping starting for ABB")
        base_url = "https://careers.abb-bank.az/api/vacancy/v2/get"
        job_vacancies = []
        page = 0

        while True:
            params = {"page": page}
            response = requests.get(base_url, params=params)

            if response.status_code == 200:
                data = response.json()["data"]

                if not data:
                    break

                for item in data:
                    title = item.get("title")
                    url = item.get("url")
                    job_vacancies.append({"company": "abb", "vacancy": title, "apply_link": url})
                page += 1
            else:
                print(f"Failed to retrieve data for page {page}. Status code: {response.status_code}")
                break

        df = pd.DataFrame(job_vacancies)
        print("ABB scraping completed")
        return df

    def busy_az(self):
        print("Scraping started for busy.az")
        job_vacancies = []
        for page_num in range(1, 5):
            print(f"Scraping page {page_num}")
            url = f'https://busy.az/vacancies?page={page_num}'
            response = requests.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_listings = soup.find_all('a', class_='job-listing')

                for job in job_listings:
                    job_details = job.find('div', class_='job-listing-details')
                    job_title = job_details.find('h3', class_='job-listing-title').text.strip()
                    company_element = job_details.find('i', class_='icon-material-outline-business')
                    company_name = company_element.find_parent('li').text.strip() if company_element else 'N/A'
                    apply_link = job.get('href')
                    job_vacancies.append({ "company": company_name,"vacancy": job_title, "apply_link": apply_link})
            else:
                print(f"Failed to retrieve page {page_num}. Status code: {response.status_code}")

        df = pd.DataFrame(job_vacancies)
        print("Scraping completed for busy.az")
        return df

    def hellojob_az(self):
        print("Started scraping of hellojob.az")
        job_vacancies = []
        base_url = "https://www.hellojob.az"

        for page_number in range(1, 11):
            url = f"{base_url}/vakansiyalar?page={page_number}"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    job_listings = soup.find_all('a', class_='vacancies__item')
                    if not job_listings:
                        print(f"No job listings found on page {page_number}.")
                        continue

                    for job in job_listings:
                        company_name = job.find('p', class_='vacancy_item_company').text.strip()
                        vacancy_title = job.find('h3').text.strip()
                        apply_link = job['href'] if job['href'].startswith('http') else base_url + job['href']

                        job_vacancies.append(
                            {"company": company_name, "vacancy": vacancy_title, "apply_link": apply_link})

                else:
                    print(f"Failed to retrieve page {page_number}. Status code: {response.status_code}")
            except Exception as e:
                print(f"An error occurred while scraping page {page_number}: {e}")
        print("Scraping completed for hellojob.az")
        if job_vacancies:
            return pd.DataFrame(job_vacancies)
        else:
            return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

    def boss_az(self):
        print("Starting to scrape Boss.az...")
        job_vacancies = []
        for page_num in range(1, 21):  # Scrape from page 1 to 20
            url = f"https://boss.az/vacancies?page={page_num}"
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_listings = soup.find_all('div', class_='results-i')
                for job in job_listings:
                    title = job.find('h3', class_='results-i-title').get_text(strip=True)
                    company = job.find('a', class_='results-i-company').get_text(strip=True)
                    link = f"https://boss.az{job.find('a', class_='results-i-link')['href']}"
                    job_vacancies.append({
                        "company": company,
                        "vacancy": title,
                        "apply_link": link
                    })
                print(f"Scraped {len(job_listings)} jobs from page {page_num}")
            else:
                print(f"Failed to retrieve page {page_num}. Status code: {response.status_code}")
        print("Scraping completed boss.az")
        return pd.DataFrame(job_vacancies)
    def ejob_az(self,start_page=1, end_page=20):
        print("Scraping started for ejob.az")
        base_url = "https://ejob.az/is-elanlari"
        all_jobs = []
        for page in range(start_page, end_page + 1):
            url = f"{base_url}/page-{page}/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            response = requests.get(url, headers=headers)
            print(f"URL: {url} - Status Code: {response.status_code}")  # Debugging line
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_tables = soup.find_all('table', class_='background')
                for job in job_tables:
                    title_link = job.find('a', href=True)
                    salary = job.find('div', class_='salary').text if job.find('div',class_='salary') else 'No salary listed'
                    company = job.find('div', class_='company').text if job.find('div', class_='company') else 'No company listed'
                    all_jobs.append({
                        'company': company,
                        'vacancy': title_link.text.strip(),
                        'apply_link': f"https://ejob.az{title_link['href']}"
                    })
            else:
                print(
                    f"Failed to retrieve page: {page} - Response: {response.text[:500]}")
        print("Scraping completed for ejob.az")
        return pd.DataFrame(all_jobs)

    def vakansiya_az(self):
        print("Scraping started for vakansiya.az")
        url = 'https://www.vakansiya.az/az/'
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to retrieve page with status code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        jobs = []

        job_divs = soup.find_all('div', id='js-jobs-wrapper')
        print(f"Found {len(job_divs)} job postings.")

        for job_div in job_divs:
            job = {}
            company = job_div.find_all('div', class_='js-fields')[1].find('a')
            title = job_div.find('a', class_='jobtitle')
            apply_link = title['href'] if title else None

            job['company'] = company.get_text(strip=True) if company else 'N/A'
            job['vacancy'] = title.get_text(strip=True) if title else 'N/A'
            job['apply_link'] = 'https://www.vakansiya.az' + apply_link if apply_link else 'N/A'
            print(f"Job found: {job}")
            jobs.append(job)
        print("Scraping completed for vakansiya.az")
        return pd.DataFrame(jobs)

    def ishelanlari_az(self):
        print("Scraping started for ishelanlari.az")
        url = "https://ishelanlari.az/az/vacancies//0/360/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
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
                print("Scraping completed for ishelanlari.az")
                return pd.DataFrame(vacancies)
            else:
                print(f"Failed to retrieve data, status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Request failed: {e}")

    def bank_of_baku_az(self):
        print("Scraping started for Bank of Baku")
        url = "https://careers.bankofbaku.com/az/vacancies"
        response = requests.get(url, verify=False)  # Disabling SSL verification for the sake of the example
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

                jobs.append({
                    'company': 'Bank of Baku',
                    'vacancy': title,
                    'apply_link': link
                })

        print("Scraping completed for Bank of Baku")
        return pd.DataFrame(jobs)

    def bank_respublika(self):
        print("Scraping started for Bank Respublika")
        url = "https://www.bankrespublika.az/az/career"
        response = requests.get(url, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []

        # Correcting the class to look for job listings
        for job in soup.find_all("div", class_="vacancyItem whiteBox"):
            title_element = job.find("a", class_="title")
            title = title_element.text.strip() if title_element else "No title found"
            link = title_element['href'] if title_element and 'href' in title_element.attrs else "No link available"

            jobs.append({
                "company": 'Bank_Respublika',
                "vacancy": title,
                "apply_link": link
            })
        print("Scraping completed for Bank Respublika")
        return pd.DataFrame(jobs)

    def banker_az(self):
        print("Banker.az")
        base_url = 'https://banker.az/vakansiyalar'
        num_pages = 5

        all_job_titles = []
        all_company_names = []
        all_apply_links = []

        for page in range(1, num_pages + 1):
            url = f"{base_url}/page/{page}/"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            job_listings = soup.find_all('div', class_='list-data')

            job_titles = []
            company_names = []
            apply_links = []

            for job in job_listings:
                # Extract job title and link
                job_info = job.find('div', class_='job-info')
                title_tag = job_info.find('a') if job_info else None
                title = title_tag.text.strip() if title_tag else None
                link = title_tag['href'] if title_tag else None

                # Extract company name from the alt attribute of the img tag within the company logo
                company_logo = job.find('div', class_='company-logo')
                company_img = company_logo.find('img') if company_logo else None
                company = company_img.get('alt') if company_img else None

                # Split the title and company if they are together
                if title and '-' in title:
                    title_parts = title.split(' – ')
                    title = title_parts[0].strip()
                    if len(title_parts) > 1:
                        company = title_parts[1].strip()

                if title and company and link:
                    job_titles.append(title)
                    company_names.append(company)
                    apply_links.append(link)

            all_job_titles.extend(job_titles)
            all_company_names.extend(company_names)
            all_apply_links.extend(apply_links)

        df = pd.DataFrame({
            'company': all_company_names,
            'vacancy': all_job_titles,
            'apply_link': all_apply_links
        })
        print("Banker.az completed")
        return df

    def get_data(self):
        abb_df = self.abb()
        azerconnect_df = self.azerconnect()
        pashabank_df = self.pashabank()
        azercell_df = self.azercell()
        busy_az_df = self.busy_az()
        hellojob_az_df = self.hellojob_az()
        boss_az_df = self.boss_az()
        ejob_az_df = self.ejob_az()
        vakansiya_az_df = self.vakansiya_az()
        ishelanlari_az_df = self.ishelanlari_az()
        bank_of_baku_az_df = self.bank_of_baku_az()
        bank_respublika_df = self.bank_respublika()
        banker_az_df = self.banker_az()


        scrape_date = datetime.now()

        abb_df['scrape_date'] = scrape_date
        azerconnect_df['scrape_date'] = scrape_date
        pashabank_df['scrape_date'] = scrape_date
        azercell_df['scrape_date'] = scrape_date
        busy_az_df['scrape_date'] = scrape_date
        hellojob_az_df['scrape_date'] = scrape_date
        boss_az_df['scrape_date'] = scrape_date
        ejob_az_df['scrape_date'] = scrape_date
        vakansiya_az_df['scrape_date'] = scrape_date
        ishelanlari_az_df['scrape_date'] = scrape_date
        bank_of_baku_az_df['scrape_date'] = scrape_date
        bank_respublika_df['scrape_date'] = scrape_date
        banker_az_df['scrape_date'] = scrape_date
        self.data = pd.concat([pashabank_df,
                               azerconnect_df,
                               azercell_df,
                               abb_df,
                               busy_az_df,
                               hellojob_az_df,
                               boss_az_df,
                               ejob_az_df,
                               vakansiya_az_df,
                               ishelanlari_az_df,
                               bank_of_baku_az_df,
                               bank_respublika_df,
                               banker_az_df],
                              ignore_index=True)
        return self.data
