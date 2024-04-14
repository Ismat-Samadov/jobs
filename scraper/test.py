import requests
from bs4 import BeautifulSoup
import pandas as pd


def scrape_access():
    url = "https://www.accessbank.az/az/our-bank/vacancies/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        job_titles = []
        job_links = []
        vacancies = soup.select('.gmb_embed_job_box > a')
        for vacancy in vacancies:
            job_titles.append(vacancy.text.strip())
            job_links.append(vacancy['href'])
        data = {
            'company': 'Access Bank',
            'vacancy': job_titles,
            'apply_link': job_links,
        }
        df = pd.DataFrame(data)
        return df

df = scrape_access()
print(df['vacancy'])
df.to_excel("accessbank_job_vacancies.xlsx", index=False)
