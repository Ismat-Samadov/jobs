# Lead Generator - Multi-Source Web Scraper

High-performance async web scraper for extracting real estate listings and phone numbers from multiple sources.

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and run
docker-compose up --build

# Initialize database (first time only)
docker-compose --profile init run init-db

# Run scraper
docker-compose up scraper
```

### Option 2: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment (.env file)
DATABASE_URL=postgresql://user:password@host:port/database

# 3. Initialize database
python scripts/init_db.py

# 4. Run scraper
python main.py
```

## Features

- **Async/Await with aiohttp**: Concurrent requests for maximum performance
- **Multi-source support**: Modular design for adding new scrapers
- **Automatic phone extraction**: Extracts phone numbers via API calls
- **Database storage**: Saves leads to PostgreSQL with duplicate prevention
- **Docker support**: One-command deployment
- **Rate limiting**: Configurable concurrent request limits
- **Error handling**: Robust error handling and retry logic

## Project Structure

```
scraper/
├── sources/
│   ├── __init__.py
│   └── evv_az_scraper.py    # EVV.AZ scraper
├── scripts/
│   ├── init_db.py            # Database initialization
│   └── schema.sql            # Database schema
├── main.py                   # Main entry point
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker compose configuration
└── .env                      # Environment variables
```


## Database Schema

Universal `leads` table for all sources:

```sql
CREATE TABLE leads.leads (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    website VARCHAR(255) NOT NULL,
    source VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Data Format

Extracted data includes:
- **phone_number**: Last 9 digits (e.g., "506271539")
- **website**: Source website (e.g., "evv.az")
- **source**: Full listing URL

## Adding New Scrapers

1. Create new scraper file in `sources/` directory:
```python
# sources/new_site_scraper.py
class NewSiteScraperAsync:
    async def scrape_from_url(self, url: str) -> Dict[str, int]:
        # Implementation
        pass

    def save_to_database(self, phone_number: str, source_url: str) -> bool:
        # Implementation
        pass
```

2. Update `sources/__init__.py`:
```python
from .evv_az_scraper import EvvAzScraperAsync
from .new_site_scraper import NewSiteScraperAsync

__all__ = ['EvvAzScraperAsync', 'NewSiteScraperAsync']
```

3. Update `main.py` to include new source in choices and add run function

4. Update `docker-compose.yml` if needed

## Performance

- Concurrent requests: 10 (configurable)
- Average speed: ~20-30 listings per minute
- Automatic rate limiting to avoid blocking
- Docker deployment for scalability

## Environment Variables

```bash
DATABASE_URL=postgresql://user:password@host:port/database  # Required
PYTHONUNBUFFERED=1                                          # For Docker logs
```

## GitHub Actions Automation

The scraper can run automatically via GitHub Actions:

- **Schedule**: Daily at 13:00 UTC
- **Manual trigger**: Available via workflow_dispatch

### Setup GitHub Secrets

1. Go to your GitHub repository → Settings → Secrets and variables → Actions
2. Add the following secret:
   - `DATABASE_URL`: Your PostgreSQL connection string

### Workflow File

Located at `../.github/workflows/scraper.yml` (in repository root) - automatically runs the scraper daily.

## Current Sources

### EVV.AZ (Real Estate)
- Website: https://www.evv.az
- Type: Real estate listings
- Location: Azerbaijan
- Extraction: Phone numbers via API
- Pagination: 24 items per page (page=0, 24, 48, 72...)
- Listing Types:
  - Type 1: Sale listings
  - Type 2: Rent listings
  - Type 3: Daily rent listings
- **Default behavior**: `--all-types` scrapes all 3 types, 3 pages each (9 pages total)

## Error Handling

- Automatic retry on network errors
- Duplicate detection (unique phone numbers only)
- Graceful handling of missing phone numbers
- Detailed logging for debugging

## Troubleshooting

### Database Connection Issues
- Check your `DATABASE_URL` in `.env`
- Make sure PostgreSQL is accessible
- Run `python scripts/init_db.py` to initialize schema

### Scraper Not Finding Listings
- Check if website structure has changed
- Verify URL is correct
- Check network connectivity

### Docker Issues
- Make sure Docker is running
- Try `docker-compose down` then `docker-compose up --build`
- Check logs with `docker-compose logs`

## Notes

- The scraper respects websites' structure and API endpoints
- Phone numbers are extracted via official API endpoints
- Each phone number is saved only once (unique constraint)
- All scrapers use async/await for optimal performance
- Your leads are saved to `leads.leads` table with columns: `phone_number`, `website`, `source`
