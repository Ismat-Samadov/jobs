import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_hellojob_az():
    job_vacancies = []

    for page_number in range(1, 11):  
        url = f"https://www.hellojob.az/vakansiyalar?page={page_number}"
        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            job_listings = soup.find_all('a', class_='vacancies__item')

            for job in job_listings:
                company_name = job.find('p', class_='vacancy_item_company').text.strip()
                vacancy_title = job.find('h3').text.strip()
                apply_link = "https://www.hellojob.az" + job['href']

                job_vacancies.append({"company": company_name, "vacancy": vacancy_title, "apply_link": apply_link})

        else:
            print(f"Failed to retrieve page {page_number}. Status code:", response.status_code)

    return pd.DataFrame(job_vacancies)


