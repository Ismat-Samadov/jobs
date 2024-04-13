# models.py
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

Base = declarative_base()

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



class VacancyInResponse(BaseModel):
    id: int
    title: str
    description: str
    term: str
    type: str
    begin_date: str
    end_date: str
    status: str
    created_at: str
    updated_at: str
    url: str
    categories: str
    company: str
