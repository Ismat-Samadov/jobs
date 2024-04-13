import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Text
import os
from dotenv import load_dotenv
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

# Define SQLAlchemy engine
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')

# Check if all required environment variables are provided
if None in [DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]:
    raise EnvironmentError("One or more required environment variables are missing.")

# Construct the PostgreSQL connection URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
logging.debug(f"Database URL: {DATABASE_URL}")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Add a print statement or logging message to indicate successful database connection
logging.debug("Connecting to the database...")

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Add a print statement or logging message to indicate successful session creation
logging.debug("Database session created successfully.")

# Define base class for declarative models
Base = declarative_base()

# Define SQLAlchemy model for "vacancies" table
class Vacancy(Base):
    __tablename__ = "vacancies"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    term = Column(String)
    type = Column(String)
    begin_date = Column(String)
    end_date = Column(String)
    status = Column(String)
    created_at = Column(String)
    updated_at = Column(String)
    url = Column(String)
    categories = Column(String)
    company = Column(String)

    def __repr__(self):
        return f"<Vacancy(id={self.id}, title={self.title})>"

# Dependency to get the database session
def get_db():
    logging.debug("Getting database session...")
    db = SessionLocal()
    try:
        yield db
    finally:
        logging.debug("Closing database session...")
        db.close()

app = FastAPI()


# CRUD operations
def get_vacancies(db: Session, skip: int = 0, limit: int = 10):
    logging.debug("Fetching vacancies from the database...")
    return db.query(Vacancy).offset(skip).limit(limit).all()

def get_vacancy(db: Session, vacancy_id: int):
    logging.debug(f"Fetching vacancy with ID: {vacancy_id} from the database...")
    return db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()

def create_vacancy(db: Session, vacancy: Vacancy):
    logging.debug("Creating new vacancy in the database...")
    db.add(vacancy)
    db.commit()
    db.refresh(vacancy)
    logging.debug(f"Vacancy created successfully. ID: {vacancy.id}")
    return vacancy

def update_vacancy(db: Session, vacancy_id: int, updated_vacancy: Vacancy):
    logging.debug(f"Updating vacancy with ID: {vacancy_id} in the database...")
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if vacancy:
        for attr, value in updated_vacancy.dict().items():
            setattr(vacancy, attr, value)
        db.commit()
        db.refresh(vacancy)
        logging.debug(f"Vacancy with ID: {vacancy_id} updated successfully.")
    else:
        logging.debug(f"Vacancy with ID: {vacancy_id} not found.")
    return vacancy

def delete_vacancy(db: Session, vacancy_id: int):
    logging.debug(f"Deleting vacancy with ID: {vacancy_id} from the database...")
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if vacancy:
        db.delete(vacancy)
        db.commit()
        logging.debug(f"Vacancy with ID: {vacancy_id} deleted successfully.")
        return {"message": "Vacancy deleted successfully"}
    else:
        logging.debug(f"Vacancy with ID: {vacancy_id} not found.")
        raise HTTPException(status_code=404, detail="Vacancy not found")

# API endpoints
@app.get("/vacancies/", response_model=Optional[List[Vacancy]])
async def read_vacancies(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    logging.debug(f"Received request to read vacancies with skip={skip} and limit={limit}.")
    return get_vacancies(db, skip=skip, limit=limit)

@app.get("/vacancies/{vacancy_id}", response_model=Vacancy)
async def read_vacancy(vacancy_id: int, db: Session = Depends(get_db)):
    logging.debug(f"Received request to read vacancy with ID: {vacancy_id}.")
    vacancy = get_vacancy(db, vacancy_id)
    if vacancy is None:
        logging.debug(f"Vacancy with ID: {vacancy_id} not found.")
        raise HTTPException(status_code=404, detail="Vacancy not found")
    else:
        logging.debug(f"Vacancy with ID: {vacancy_id} found.")
    return vacancy

@app.post("/vacancies/", response_model=Vacancy)
async def create_vacancy(vacancy: Vacancy, db: Session = Depends(get_db)):
    logging.debug("Received request to create a new vacancy.")
    return create_vacancy(db, vacancy)

@app.put("/vacancies/{vacancy_id}", response_model=Vacancy)
async def update_vacancy(vacancy_id: int, updated_vacancy: Vacancy, db: Session = Depends(get_db)):
    logging.debug(f"Received request to update vacancy with ID: {vacancy_id}.")
    return update_vacancy(db, vacancy_id, updated_vacancy)

@app.delete("/vacancies/{vacancy_id}")
async def delete_vacancy(vacancy_id: int, db: Session = Depends(get_db)):
    logging.debug(f"Received request to delete vacancy with ID: {vacancy_id}.")
    return delete_vacancy(db, vacancy_id)


# Run the FastAPI application
if __name__ == "__main__":
    import uvicorn
    logging.debug("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
