import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime


class JobScraper:
    def __init__(self):
        self.data = None

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
        boss_az_df = self.scrape_boss_az()
        scrape_date = datetime.now()
        boss_az_df['scrape_date'] = scrape_date
        self.data = boss_az_df
        return self.data


# Usage example:
scraper = JobScraper()
data = scraper.get_data()
print(data)
