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

    def scrape_azercell(self):
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
                return df
            else:
                print("Vacancies section not found on the page.")
        else:
            print("Failed to retrieve the page. Status code:", response.status_code)

    def scrape_pashabank(self):
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
        return df

    def scrape_azerconnect(self):
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
            return df

        else:
            print("Failed to retrieve the web page.")
            return None

    def scrape_abb(self):
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
        return df

    def scrape_busy_az(self):
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
        return df

    def scrape_hellojob_az(self):
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

        if job_vacancies:
            return pd.DataFrame(job_vacancies)
        else:
            return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])
    def scrape_boss_az(self):
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

        return pd.DataFrame(job_vacancies)


    def get_data(self):
        abb_df = self.scrape_abb()
        azerconnect_df = self.scrape_azerconnect()
        pashabank_df = self.scrape_pashabank()
        azercell_df = self.scrape_azercell()
        busy_az_df = self.scrape_busy_az()
        hellojob_az_df = self.scrape_hellojob_az()
        boss_az_df = self.scrape_boss_az()




        scrape_date = datetime.now()

        abb_df['scrape_date'] = scrape_date
        azerconnect_df['scrape_date'] = scrape_date
        pashabank_df['scrape_date'] = scrape_date
        azercell_df['scrape_date'] = scrape_date
        busy_az_df['scrape_date'] = scrape_date
        hellojob_az_df['scrape_date'] = scrape_date
        boss_az_df['scrape_date'] = scrape_date



        self.data = pd.concat([pashabank_df,
                               azerconnect_df,
                               azercell_df,
                               abb_df,
                               busy_az_df,
                               hellojob_az_df,
                               boss_az_df],
                              ignore_index=True)
        return self.data
