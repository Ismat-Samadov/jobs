# app/api.py
from fastapi import FastAPI, Depends, Query
from database import connect_to_postgres, close_connection
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()


# CORS settings to allow only the specified origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jobapi.netlify.app",
        "https://ismat-samadov.github.io"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.head("/")
async def head_root():
    """
    Handler for HEAD requests at the root URL ("/").
    """
    return {"message": "This is a HEAD request."}

@app.get("/")
async def read_root():
    """
    Handler for GET requests at the root URL ("/").
    """
    return {"message": "Welcome to your FastAPI application!"}
@app.get("/")
async def read_root():
    return {"message": "Welcome to your JobAPI "}

@app.get("/data/")
async def get_data(db=Depends(connect_to_postgres)):
    query = "SELECT * FROM vacancy_table;"
    rows = await db.fetch(query)
    await close_connection(db)
    return rows


@app.get("/data/company/{company}")
async def get_data_by_company(company: str, db=Depends(connect_to_postgres)):
    query = "SELECT * FROM vacancy_table WHERE company = $1;"
    rows = await db.fetch(query, company)
    await close_connection(db)
    return rows
@app.get("/data/position/")
async def get_data_by_position(position: str = Query(..., description="Position name to search for"), db=Depends(connect_to_postgres)):
    query = "SELECT * FROM vacancy_table WHERE vacancy ILIKE $1;"
    rows = await db.fetch(query, f"%{position}%")
    await close_connection(db)
    return rows
@app.post("/data/")
async def create_data(data: dict, db=Depends(connect_to_postgres)):
    query = "INSERT INTO vacancies (title, description) VALUES ($1, $2) RETURNING *;"
    values = (data.get("title"), data.get("description"))
    row = await db.fetchrow(query, *values)
    await close_connection(db)
    return row
