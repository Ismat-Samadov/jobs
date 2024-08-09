from fastapi import FastAPI, Depends, Query
from database import connect_to_postgres, close_connection
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta

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
    query = """
    SELECT distinct * 
    FROM public.jobs_jobpost 
    WHERE is_scraped = TRUE 
    AND company ILIKE $1 
    AND posted_at >= NOW() - INTERVAL '30 days'
    ORDER BY posted_at DESC;
    """
    rows = await db.fetch(query, f"%{company}%")
    await close_connection(db)
    return rows

@app.get("/data/position/")
async def get_data_by_position(position: str = Query(..., description="Position name to search for"), db=Depends(connect_to_postgres)):
    query = """
    SELECT distinct * 
    FROM public.jobs_jobpost 
    WHERE is_scraped = TRUE 
    AND title ILIKE $1 
    AND posted_at >= NOW() - INTERVAL '30 days'
    ORDER BY posted_at DESC;
    """
    rows = await db.fetch(query, f"%{position}%")
    await close_connection(db)
    return rows

@app.get("/data/")
async def get_data(
    company: str = Query(None, description="Company name to search for (partial match)"),
    position: str = Query(None, description="Position name to search for"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of items per page"),
    db=Depends(connect_to_postgres)
):
    base_query = """
    SELECT distinct * 
    FROM public.jobs_jobpost 
    WHERE is_scraped = TRUE 
    AND posted_at >= NOW() - INTERVAL '30 days'
    """

    filters = []
    parameters = []

    if company:
        filters.append("company ILIKE $1")
        parameters.append(f"%{company}%")
    if position:
        filters.append("title ILIKE $2")
        parameters.append(f"%{position}%")
    
    if filters:
        base_query += " AND " + " AND ".join(filters)
    
    base_query += " ORDER BY posted_at DESC OFFSET $3 LIMIT $4;"

    offset = (page - 1) * page_size
    parameters.extend([offset, page_size])

    rows = await db.fetch(base_query, *parameters)
    await close_connection(db)
    return rows
