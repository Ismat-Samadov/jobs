# api/api.py
from fastapi import FastAPI, Depends, Query
from database import connect_to_postgres, close_connection
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query

app = FastAPI()

# CORS settings to allow only the specified origin
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["https://capit.netlify.app","https://vacancy.streamlit.app/"],
    allow_origins=["*"],
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
    return {"message": "Welcome to your JobAPI"}

@app.get("/data/company/{company}")
async def get_data_by_company(company: str, db=Depends(connect_to_postgres)):
    query = "SELECT distinct * FROM jobs WHERE scrape_date = (select max(scrape_date) from jobs ) and  company ILIKE $1 ORDER BY scrape_date DESC;"
    rows = await db.fetch(query, f"%{company}%")
    await close_connection(db)
    return rows

@app.get("/data/position/")
async def get_data_by_position(position: str = Query(..., description="Position name to search for"), db=Depends(connect_to_postgres)):
    query = "SELECT distinct * FROM jobs WHERE scrape_date = (select max(scrape_date) from jobs ) and vacancy ILIKE $1 ORDER BY scrape_date DESC;"
    rows = await db.fetch(query, f"%{position}%")
    await close_connection(db)
    return rows


# @app.get("/data/")
# async def get_data(
#     company: str = Query(None, description="Company name to search for (partial match)"),
#     position: str = Query(None, description="Position name to search for"),
#     page: int = Query(1, description="Page number"),
#     page_size: int = Query(10, description="Number of items per page"),
#     db=Depends(connect_to_postgres)
# ):
#     if company is None and position is None:
#         # If neither company nor position is provided, return all data
#         query = "SELECT distinct * FROM jobs where scrape_date = (select max(scrape_date) from jobs ) ORDER BY scrape_date DESC OFFSET $1 LIMIT $2;"
#         offset = (page - 1) * page_size
#         rows = await db.fetch(query, offset, page_size)
#     elif company is not None and position is not None:
#         # If both company and position are provided, search by both
#         query = "SELECT distinct * FROM jobs WHERE scrape_date = (select max(scrape_date) from jobs ) and company ILIKE $1 AND vacancy ILIKE $2 ORDER BY scrape_date DESC OFFSET $3 LIMIT $4;"
#         offset = (page - 1) * page_size
#         rows = await db.fetch(query, f"%{company}%", f"%{position}%", offset, page_size)
#     elif company is not None:
#         # If only company is provided, search by company with LIKE
#         query = "SELECT distinct * FROM jobs WHERE scrape_date = (select max(scrape_date) from jobs ) and company ILIKE $1 ORDER BY scrape_date DESC OFFSET $2 LIMIT $3;"
#         offset = (page - 1) * page_size
#         rows = await db.fetch(query, f"%{company}%", offset, page_size)
#     else:
#         # If only position is provided, search by position
#         query = "SELECT distinct * FROM jobs WHERE scrape_date = (select max(scrape_date) from jobs ) and vacancy ILIKE $1 ORDER BY scrape_date DESC OFFSET $2 LIMIT $3;"
#         offset = (page - 1) * page_size
#         rows = await db.fetch(query, f"%{position}%", offset, page_size)
#     await close_connection(db)
#     return rows

@app.get("/data/")
async def get_data(
    company: str = Query(None, description="Company name to search for (partial match)"),
    position: str = Query("data,analyst,analitik,scientist,reporter,hesabat,sql,power bi,python", description="Position name to search for (default: multiple data-related terms)"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of items per page"),
    db=Depends(connect_to_postgres)
):
    query = "SELECT DISTINCT * FROM jobs WHERE scrape_date = (SELECT MAX(scrape_date) FROM jobs)"
    filters = []
    params = []
    offset = (page - 1) * page_size

    if company:
        filters.append("company ILIKE $1")
        params.append(f"%{company}%")
    if position:
        position_terms = position.split(',')
        filters.append(" OR ".join([f"vacancy ILIKE ${i+2}" for i in range(len(position_terms))]))
        params.extend([f"%{term}%" for term in position_terms])

    if filters:
        query += " AND " + " AND ".join(filters)

    query += " ORDER BY scrape_date DESC OFFSET $3 LIMIT $4;"
    params.extend([offset, page_size])

    rows = await db.fetch(query, *params)
    await close_connection(db)
    return rows
