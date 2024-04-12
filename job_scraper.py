import os
import sqlalchemy
import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, exc
import logging

# Setting up logging configuration
logging.basicConfig(filename='scraper_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VacancyScraper:
    def __init__(self, db_url):
        self.db_url = db_url

    def fetch_vacancies(self, pages=0):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
            'Accept': 'application/json',
            'Referer': 'https://careers.abb-bank.az/vakansiyalar',
            'X-Csrf-Token': 'J4xdXYEeZ5030GVkC33GhjHiFxpwftTEl8llnP1h',
            'X-Requested-With': 'XMLHttpRequest',
            'Dnt': '1'
        }
        all_vacancies = []
        for page in range(1, pages + 1):
            url = f"https://careers.abb-bank.az/api/vacancy/v2/get?page={page}"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                vacancies_on_page = data.get('data', [])
                for vacancy in vacancies_on_page:
                    vacancy['company'] = 'abb'
                all_vacancies.extend(vacancies_on_page)
                logging.info(f"Fetched data from page {page}.")
            else:
                logging.error(f"Failed to fetch data from page {page}. Status code: {response.status_code}")
                # If the response code is not 200, we skip this page and continue to the next one.

        return pd.DataFrame(all_vacancies)

    def save_to_database(self, df, table_name):
        db_engine = None
        try:
            db_engine = create_engine(self.db_url)
            df.to_sql(name=table_name,
                      con=db_engine,
                      index=False,
                      if_exists='append',
                      dtype={"categories": sqlalchemy.types.JSON})
            logging.info("Data saved to the database.")
        except exc.IntegrityError as e:
            if "unique constraint" in str(e):
                logging.warning("Duplicate entry detected. Skipping insertion of duplicate data.")
            else:
                logging.error(f"An error occurred while saving data to the database: {str(e)}")
        except Exception as e:
            logging.error(f"An error occurred while saving data to the database: {str(e)}")
            # Log the error message if an exception occurs during the database operation.
        finally:
            if db_engine:
                db_engine.dispose()
                logging.info("Database connection closed.")


def main():
    load_dotenv()

    # Database connection details
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')

    # Check if all required environment variables are set
    if None in [db_host, db_port, db_user, db_password, db_name]:
        logging.error("One or more required environment variables are not set.")
        return

    # Construct the PostgresSQL connection URL
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    # Initialize VacancyScraper
    scraper = VacancyScraper(db_url)

    # Fetch vacancies
    all_vacancies_df = scraper.fetch_vacancies(pages=5)

    # Save data to the database
    table_name = 'vacancies'
    scraper.save_to_database(all_vacancies_df, table_name)

if __name__ == "__main__":
    main()
