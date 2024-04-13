import os
import sqlalchemy
from dotenv import load_dotenv
import pandas as pd
import requests
from sqlalchemy import create_engine

load_dotenv()

def fetch_vacancies(pages=2):
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
        else:
            print(f"Failed to fetch data from page {page}. Status code: {response.status_code}")

    return pd.DataFrame(all_vacancies)

all_vacancies_df = fetch_vacancies(pages=10)

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
    table_name = 'vacancies'
    all_vacancies_df.to_sql(name=table_name,
                            con = db_engine,
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

