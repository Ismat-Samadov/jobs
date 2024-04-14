#scraper/scraper.py
import urllib3
from bs4 import BeautifulSoup
import os
import sqlalchemy
from dotenv import load_dotenv
import pandas as pd
import requests
from sqlalchemy import create_engine
load_dotenv()
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
            responsibilities = []
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


    def get_data(self):
        abb_df = self.scrape_abb()
        azerconnect_df = self.scrape_azerconnect()
        pashabank_df = self.scrape_pashabank()
        azercell_df = self.scrape_azercell()
        self.data = pd.concat([pashabank_df,
                               azerconnect_df,
                               azercell_df,
                               abb_df],
                              ignore_index=True)


if __name__ == "__main__":
    job_scraper = JobScraper()
    job_scraper.get_data()

    # Database connection details
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')

    # Construct the PostgreSQL connection URL
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    # Establish connection to PostgreSQL database
    db_engine = create_engine(db_url)

    try:
        # Save data to the database
        table_name = 'vacancy_table'
        job_scraper.data.to_sql(name=table_name,
                                con=db_engine,
                                index=False,
                                if_exists='append',
                                dtype={"categories": sqlalchemy.types.JSON},
                                )

        print("Data saved to the database.")
    except Exception as e:
        print(f"An error occurred while saving data to the database: {str(e)}")
    finally:
        # Close the database connection
        db_engine.dispose()
        print("Database connection closed.")
