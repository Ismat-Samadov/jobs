import os
import sqlalchemy
from dotenv import load_dotenv
from sqlalchemy import create_engine
from scraper import JobScraper

load_dotenv()

if __name__ == "__main__":
    job_scraper = JobScraper()
    job_scraper.get_data()

    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')

    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    db_engine = create_engine(db_url)

    try:
        table_name = 'jobs'
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
        db_engine.dispose()
        print("Database connection closed.")
