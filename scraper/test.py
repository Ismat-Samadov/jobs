import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class JobScraper:
    def __init__(self):
        self.data = None

    def xalqbank(self):
        print("Started scraping Xalqbank")
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
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Ensure the request was successful

        soup = BeautifulSoup(response.content, 'html.parser')

        vacancies = []
        vacancy_items = soup.find_all('a', class_='vacancies__item')

        for item in vacancy_items:
            category = item.find('span', class_='vacancies__category').text.strip()
            title = item.find('h2', class_='vacancies__title').text.strip()
            location = item.find('span', class_='vacancies__location').text.strip()
            link = item['href']
            vacancies.append([category, title, location, link])

        df = pd.DataFrame(vacancies, columns=['company', 'vacancy', 'location', 'apply_link'])
        df['company'] = 'xalqbank'
        print("Scraping completed for Xalqbank")
        return df

    def get_data(self):
        xalqbank_df = self.xalqbank()

        scrape_date = datetime.now()

        xalqbank_df['scrape_date'] = scrape_date

        self.data = pd.concat([xalqbank_df],
                              ignore_index=True)
        return self.data

