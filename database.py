import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
logging.basicConfig(level=logging.DEBUG)

def create_session():
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT')
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_NAME = os.environ.get('DB_NAME')

    if None in [DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]:
        raise EnvironmentError("One or more required environment variables are missing.")

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    logging.debug(f"Database URL: {DATABASE_URL}")

    engine = create_engine(DATABASE_URL)

    logging.debug("Connecting to the database...")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logging.debug("Database session created successfully.")

    return SessionLocal()
