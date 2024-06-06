# scraper/save_db.py
import os
import logging
from sqlalchemy import create_engine, types
from sqlalchemy.exc import SQLAlchemyError
from scraper import JobScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conditional loading of dotenv for local development
if os.environ.get('ENV') == 'development':
    from dotenv import load_dotenv
    load_dotenv()

def main():
    job_scraper = JobScraper()
    data = job_scraper.get_data()

    if data.empty:
        logger.warning("No data scraped to save to the database.")
        return

    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')

    # Build the database URL
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
   
    # Create a database engine
    db_engine = create_engine(db_url)

    try:
        table_name = 'jobs'
        data.to_sql(name=table_name,
                    con=db_engine,
                    index=False,
                    if_exists='append',
                    dtype={"categories": types.JSON},
                    )
        logger.info("Data saved to the database.")
    except SQLAlchemyError as e:
        # Improved error handling: log the exception without stopping the program
        logger.error(f"An error occurred while saving data to the database: {str(e)}")
    finally:
        db_engine.dispose()  # Ensure the connection is closed properly
        logger.info("Database connection closed.")

if __name__ == "__main__":
    main()
