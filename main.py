# main.py
import logging
from fastapi import FastAPI, Depends, HTTPException
from typing import List, Optional, Dict
from pydantic import BaseModel  # Import BaseModel

from sqlalchemy.orm import Session
from database import create_session
from models import VacancyInResponse, Vacancy

app = FastAPI()

# Dependency to get the database session
def get_db():
    logging.debug("Getting database session...")
    db = create_session()
    try:
        yield db
    finally:
        logging.debug("Closing database session...")
        db.close()



# Update vacancy CRUD operations to use Pydantic model
def get_vacancy(db: Session, vacancy_id: int) -> Vacancy:
    logging.debug(f"Fetching vacancy with ID: {vacancy_id} from the database...")
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        logging.debug(f"Vacancy with ID: {vacancy_id} not found.")
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy

def create_vacancy(db: Session, vacancy: Vacancy) -> Vacancy:
    logging.debug("Creating new vacancy in the database...")
    db.add(vacancy)
    db.commit()
    db.refresh(vacancy)
    logging.debug(f"Vacancy created successfully. ID: {vacancy.id}")
    return vacancy

def update_vacancy(db: Session, vacancy_id: int, updated_vacancy: Vacancy) -> Vacancy:
    logging.debug(f"Updating vacancy with ID: {vacancy_id} in the database...")
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        logging.debug(f"Vacancy with ID: {vacancy_id} not found.")
        raise HTTPException(status_code=404, detail="Vacancy not found")
    for attr, value in updated_vacancy.dict().items():
        setattr(vacancy, attr, value)
    db.commit()
    db.refresh(vacancy)
    logging.debug(f"Vacancy with ID: {vacancy_id} updated successfully.")
    return vacancy

def delete_vacancy(db: Session, vacancy_id: int) -> Dict[str, str]:
    logging.debug(f"Deleting vacancy with ID: {vacancy_id} from the database...")
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        logging.debug(f"Vacancy with ID: {vacancy_id} not found.")
        raise HTTPException(status_code=404, detail="Vacancy not found")
    db.delete(vacancy)
    db.commit()
    logging.debug(f"Vacancy with ID: {vacancy_id} deleted successfully.")
    return {"message": "Vacancy deleted successfully"}

# API endpoints

# Update other routes to use Pydantic model
@app.get("/vacancies/{vacancy_id}", response_model=VacancyInResponse)
async def read_vacancy(vacancy_id: int, db: Session = Depends(get_db)) -> VacancyInResponse:
    logging.debug(f"Received request to read vacancy with ID: {vacancy_id}.")
    return get_vacancy(db, vacancy_id)

@app.post("/vacancies/", response_model=VacancyInResponse)
async def create_vacancy(vacancy: Vacancy, db: Session = Depends(get_db)) -> VacancyInResponse:
    logging.debug("Received request to create a new vacancy.")
    return create_vacancy(db, vacancy)

@app.put("/vacancies/{vacancy_id}", response_model=VacancyInResponse)
async def update_vacancy(vacancy_id: int, updated_vacancy: Vacancy, db: Session = Depends(get_db)) -> VacancyInResponse:
    logging.debug(f"Received request to update vacancy with ID: {vacancy_id}.")
    return update_vacancy(db, vacancy_id, updated_vacancy)

@app.delete("/vacancies/{vacancy_id}")
async def delete_vacancy(vacancy_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    logging.debug(f"Received request to delete vacancy with ID: {vacancy_id}.")
    return delete_vacancy(db, vacancy_id)


# Run the FastAPI application
if __name__ == "__main__":
    import uvicorn
    logging.debug("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
