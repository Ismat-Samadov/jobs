import requests
from bs4 import BeautifulSoup
import pandas as pd

class JobScraper:
    def jobsearch_az(self, max_pages=2):
        base_url = 'https://www.jobsearch.az/vacancies/page='
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

        all_vacancies = []

        for page in range(1, max_pages + 1):
            url = f"{base_url}{page}"
            print(f"Fetching page {page}: {url}")
            response = requests.get(url, headers=headers)
            print(f"Status Code: {response.status_code}")

            if response.status_code != 200:
                print(f"Failed to fetch page {page}")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            job_elements = soup.select('div.list__item')

            print(f"Found {len(job_elements)} job elements")

            for job_element in job_elements:
                title_tag = job_element.select_one('h3.list__item__title')
                company_tag = job_element.select_one('div.list__item__body a')
                date_tag = job_element.select_one('div.list__item__end li span:nth-of-type(2)')
                link_tag = job_element.select_one('a.list__item__text')

                title = title_tag.text.strip() if title_tag else 'No title'
                company = company_tag.text.strip() if company_tag else 'No company'
                date = date_tag.text.strip() if date_tag else 'No date'
                link = link_tag['href'] if link_tag else 'No link'

                all_vacancies.append([title, company, date, link])

                # Debugging: Print each job element
                print(f"Title: {title}, Company: {company}, Date: {date}, Link: {link}")

        df = pd.DataFrame(all_vacancies, columns=['vacancy', 'company', 'date', 'apply_link'])
        print(df.head())
        df.to_excel('job_vacancies_az.xlsx', index=False)
        print("Data saved to job_vacancies_az.xlsx")

# Create an instance of the scraper and run it
scraper = JobScraper()
scraper.jobsearch_az(max_pages=2)
