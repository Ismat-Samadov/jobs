import os
from bs4 import BeautifulSoup
import pandas as pd
import requests
from sqlalchemy import create_engine
from datetime import datetime

class JobScraper:
    def __init__(self):
        self.data = None

    def offer_az(self):
        start_page = 1
        end_page = 10
        try:
            print("Started scraping offer.az")
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

            for page in range(start_page, end_page + 1):
                url = f'https://www.offer.az/is-elanlari/page/{page}/'
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # Ensure the request was successful

                soup = BeautifulSoup(response.content, 'html.parser')

                job_elements = soup.find_all('div', class_='job-card')

                # Debugging: Check the number of job elements found
                print(f"Found {len(job_elements)} job elements on page {page}")

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

                    # Debugging: Print each job element
                    print(f" Company: {company}, Vacancy: {title}, Link: {link}")

            df = pd.DataFrame(vacancies, columns=['company','vacancy','apply_link'])
            print("Scraping completed for offer.az")
            return df
        except Exception as e:
            print(f"Offer.az scraping failed: {e}")
            return pd.DataFrame(columns=['company', 'vacancy', 'apply_link'])

    def get_data(self):
        offer_az_df = self.offer_az()

        scrape_date = datetime.now()

        offer_az_df['scrape_date'] = scrape_date

        self.data = pd.concat([ offer_az_df],
                              ignore_index=True)
        return self.data

    def save_to_excel(self, filename):
        if self.data is not None:
            self.data.to_excel(filename, index=False)
            print(f"Data saved to {filename}")
        else:
            print("No data to save.")

# Example usage
scraper = JobScraper()
data = scraper.get_data()
print(data)
scraper.save_to_excel("job_vacancies.xlsx")
