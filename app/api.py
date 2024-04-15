# app/api.py
from fastapi import FastAPI, Depends
from database import connect_to_postgres, close_connection
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()


# CORS settings to allow only the specified origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ismat-samadov.github.io/job_api/"],
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
    return {"message": "Welcome to your FastAPI application!"}

@app.get("/data/")
async def get_data(db=Depends(connect_to_postgres)):
    query = "SELECT * FROM vacancy_table;"
    rows = await db.fetch(query)
    await close_connection(db)
    return rows

@app.get("/data/id/{id}")
async def get_data_by_id(id: int, db=Depends(connect_to_postgres)):
    query = "SELECT * FROM vacancy_table WHERE id = $1;"
    row = await db.fetchrow(query, id)
    await close_connection(db)
    return row

@app.get("/data/company/{company}")
async def get_data_by_company(company: str, db=Depends(connect_to_postgres)):
    query = "SELECT * FROM vacancy_table WHERE company = $1;"
    rows = await db.fetch(query, company)
    await close_connection(db)
    return rows
@app.post("/data/")
async def create_data(data: dict, db=Depends(connect_to_postgres)):
    query = "INSERT INTO vacancies (title, description) VALUES ($1, $2) RETURNING *;"
    values = (data.get("title"), data.get("description"))
    row = await db.fetchrow(query, *values)
    await close_connection(db)
    return row

@app.put("/data/{id}")
async def update_data(id: int, data: dict, db=Depends(connect_to_postgres)):
    query = "UPDATE vacancy_table SET column1 = $1, column2 = $2 WHERE id = $3 RETURNING *;"
    values = (data.get("column1"), data.get("column2"), id)
    row = await db.fetchrow(query, *values)
    await close_connection(db)
    return row

@app.delete("/data/{id}")
async def delete_data(id: int, db=Depends(connect_to_postgres)):
    query = "DELETE FROM vacancy_table WHERE id = $1 RETURNING *;"
    row = await db.fetchrow(query, id)
    await close_connection(db)
    return row