# Scraper Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Scraper Implementations](#scraper-implementations)
6. [Database Schema](#database-schema)
7. [Performance Characteristics](#performance-characteristics)
8. [Deployment Options](#deployment-options)
9. [Error Handling & Resilience](#error-handling--resilience)
10. [Extension Guide](#extension-guide)

---

## Overview

### Purpose
Multi-source asynchronous web scraper designed to extract business contact information (phone numbers) from various Azerbaijan-based classifieds and real estate platforms, validate them, and store in PostgreSQL database.

### Key Features
- **Async/Concurrent Processing**: Uses `asyncio` and `aiohttp` for high-performance concurrent scraping
- **Multi-Source Support**: Modular design supporting 5+ different websites
- **Phone Validation**: Strict validation based on Azerbaijan phone number standards
- **Intelligent Deduplication**: Database-level unique constraints prevent duplicate leads
- **Rich Data Extraction**: Beyond phone numbers - extracts property details, seller info, images, etc.
- **Telegram Notifications**: Real-time progress reports sent to Telegram
- **Docker Support**: Containerized deployment with Docker Compose
- **Connection Pooling**: Efficient database connection management with psycopg2 pools

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                          │
│                      (main.py)                               │
│  - Coordinates all scrapers                                  │
│  - Manages execution flow                                    │
│  - Aggregates statistics                                     │
│  - Sends notifications                                       │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐       ┌───────────────┐
│  ASYNC POOL   │       │  SYNC POOL    │
│               │       │               │
│ ┌───────────┐ │       │ ┌───────────┐ │
│ │EVV.AZ     │ │       │ │Turbo.AZ   │ │
│ │(API-based)│ │       │ │(scraping) │ │
│ └───────────┘ │       │ └───────────┘ │
│               │       │               │
│ ┌───────────┐ │       └───────────────┘
│ │Villa.AZ   │ │
│ │(scraping) │ │
│ └───────────┘ │
│               │
│ ┌───────────┐ │
│ │Bul.AZ     │ │
│ │(scraping) │ │
│ └───────────┘ │
│               │
│ ┌───────────┐ │
│ │Avtopro.AZ │ │
│ │(scraping) │ │
│ └───────────┘ │
└───────┬───────┘
        │
        ▼
┌───────────────────────┐
│   SHARED SERVICES     │
├───────────────────────┤
│ • PhoneValidator      │
│ • Database Pool       │
│ • TelegramNotifier    │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│   PostgreSQL DB       │
│   (leads.leads)       │
└───────────────────────┘
```

### Technology Stack

#### Core Technologies
- **Python 3.10+**: Main programming language
- **asyncio**: Asynchronous I/O framework
- **aiohttp**: Async HTTP client for web requests
- **BeautifulSoup4**: HTML parsing
- **lxml**: Fast XML/HTML parser
- **PostgreSQL**: Relational database
- **psycopg2**: PostgreSQL adapter with connection pooling
- **Docker**: Containerization

#### Dependencies
```
aiohttp==3.9.1          # Async HTTP client
beautifulsoup4==4.12.3  # HTML parsing
lxml==5.1.0             # Fast parser
psycopg2-binary==2.9.9  # PostgreSQL adapter
python-dotenv==1.0.0    # Environment variables
aiofiles==23.2.1        # Async file I/O
requests==2.31.0        # Sync HTTP (for Turbo.AZ)
```

---

## Core Components

### 1. Main Orchestrator (`main.py`)

**Purpose**: Coordinates execution of all scrapers and aggregates results

**Key Responsibilities**:
- Initialize scrapers with appropriate concurrency limits
- Execute scrapers sequentially (to avoid rate limiting)
- Aggregate statistics from all sources
- Send combined Telegram notification
- Measure overall performance

**Execution Flow**:
```python
1. Start EVV.AZ scraper (async)
   - Type 1 (Sale): 5 pages
   - Type 2 (Rent): 5 pages
   - Type 3 (Daily): 5 pages
   - Concurrency: 15 simultaneous requests

2. Start Villa.AZ scraper (async)
   - 5 pages
   - Concurrency: 3 (rate limiting)

3. Start Bul.AZ scraper (async)
   - 5 pages
   - Concurrency: 10

4. Start Turbo.AZ scraper (sync in thread pool)
   - 5 pages
   - Sequential processing

5. Aggregate statistics

6. Send Telegram notification
```

### 2. Phone Validator (`scripts/validator.py`)

**Purpose**: Validate Azerbaijan phone numbers before database insertion

**Validation Rules**:
```python
class PhoneValidator:
    VALID_PREFIXES = ['10', '50', '51', '55', '60', '70', '77', '99']
    INVALID_THIRD_DIGITS = ['0', '1']

    def validate_phone(phone_number: str) -> Optional[str]:
        # 1. Extract only digits: re.sub(r'\D', '', phone_raw)
        # 2. Take last 9 digits: cleaned[-9:]
        # 3. Validate length == 9
        # 4. Check prefix in VALID_PREFIXES
        # 5. Verify 3rd digit not in INVALID_THIRD_DIGITS
        # 6. Return validated phone or None
```

**Examples**:
| Input | Valid? | Output | Reason |
|-------|--------|--------|--------|
| `994505551234` | ✓ | `505551234` | Valid prefix 50, 3rd digit 5 |
| `+994 55 868 86 86` | ✓ | `558688686` | Valid with formatting |
| `994500551234` | ✗ | `None` | 3rd digit is 0 |
| `994405551234` | ✗ | `None` | Invalid prefix 40 |
| `50555123` | ✗ | `None` | Only 8 digits |

### 3. Database Connection Pool

**Implementation**: `psycopg2.pool.SimpleConnectionPool`

**Configuration**:
```python
self.db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,   # Minimum idle connections
    maxconn=10,  # Maximum total connections
    dsn=DATABASE_URL
)
```

**Usage Pattern**:
```python
# Get connection from pool
conn = self.db_pool.getconn()
try:
    # Use connection
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
finally:
    # Always return to pool
    self.db_pool.putconn(conn)
```

**Benefits**:
- Reuses connections (avoiding connection overhead)
- Thread-safe for async operations
- Automatic connection management
- Configurable pool size

### 4. Telegram Notifier (`scripts/telegram.py`)

**Purpose**: Send scraping reports to Telegram channels/chats

**Features**:
- **Multi-recipient support**: Comma-separated chat IDs
- **Formatted reports**: HTML formatting with emojis
- **Performance metrics**: Duration, speed, success rate
- **Multi-source aggregation**: Combined reports

**Message Format**:
```
✅ Multi-Source Scraping Report

📊 Overall Statistics
━━━━━━━━━━━━━━━━━━
📋 Total Listings: 480
📱 Phones Extracted: 420 (87.5%)
💾 New Saved: 156 (37.1%)
🔄 Duplicates/Invalid: 264
❌ Failed: 60

📍 By Source
━━━━━━━━━━━━━━━━━━
✅ EVV.AZ: 360/360 (100.0%) | Saved: 132
⚠️ Villa.AZ: 60/120 (50.0%) | Saved: 24

⏱ Performance
━━━━━━━━━━━━━━━━━━
⏳ Total Duration: 125.45s
⚡ Overall Speed: 3.8 listings/sec

🎯 Status: Excellent
```

---

## Data Flow

### Complete Scraping Flow

```
1. DISCOVERY PHASE
   ┌──────────────────────────────────────┐
   │ Scraper fetches listing page HTML    │
   │ Example: https://evv.az/page=1       │
   └──────────────┬───────────────────────┘
                  ▼
   ┌──────────────────────────────────────┐
   │ Extract listing URLs from page       │
   │ BeautifulSoup parses HTML            │
   │ Finds: [listing1_url, listing2_url...] │
   └──────────────┬───────────────────────┘
                  ▼

2. EXTRACTION PHASE (Parallel for each listing)
   ┌──────────────────────────────────────┐
   │ Fetch listing detail page            │
   │ OR call phone API endpoint           │
   └──────────────┬───────────────────────┘
                  ▼
   ┌──────────────────────────────────────┐
   │ Extract data:                        │
   │ • Phone number(s)                    │
   │ • Title, price, location             │
   │ • Property details                   │
   │ • Seller information                 │
   │ • Images                             │
   │ • Description                        │
   └──────────────┬───────────────────────┘
                  ▼

3. VALIDATION PHASE
   ┌──────────────────────────────────────┐
   │ PhoneValidator.validate_phone()      │
   │ • Strip non-digits                   │
   │ • Check length (9 digits)            │
   │ • Validate prefix                    │
   │ • Check 3rd digit                    │
   └──────────────┬───────────────────────┘
                  ▼
         Valid?  / \  Invalid
                /   \
               ✓     ✗
               │     │
               │     └─→ Skip (return False)
               ▼

4. DATABASE PHASE
   ┌──────────────────────────────────────┐
   │ Get connection from pool             │
   └──────────────┬───────────────────────┘
                  ▼
   ┌──────────────────────────────────────┐
   │ INSERT INTO leads.leads              │
   │ ON CONFLICT (phone_number)           │
   │ DO UPDATE SET full_data=...          │
   └──────────────┬───────────────────────┘
                  ▼
   ┌──────────────────────────────────────┐
   │ Return connection to pool            │
   │ Update statistics (saved/duplicate)  │
   └──────────────────────────────────────┘

5. REPORTING PHASE
   ┌──────────────────────────────────────┐
   │ Aggregate stats from all scrapers    │
   │ Format Telegram message              │
   │ Send notification                    │
   └──────────────────────────────────────┘
```

---

## Scraper Implementations

### 1. EVV.AZ Scraper (`evv_az_scraper.py`)

**Type**: Real Estate Listings (Apartments, Houses)

**Approach**: API-based phone extraction

**Architecture**:
```
Class: EvvAzScraperAsync

Key Methods:
├── scrape(all_types=True, pages_per_type=5)
│   └── Main entry point, orchestrates scraping
│
├── build_urls(listing_type, start_page, end_page)
│   └── Generates URLs for pagination
│
├── scrape_from_url(url)
│   └── Fetches and processes single page
│
├── extract_listing_urls(html_content)
│   └── Parses HTML to find listing links
│
├── process_listing(session, listing, idx, total)
│   ├── get_phone_number() -> API call
│   └── fetch_listing_details() -> Full data extraction
│
└── save_to_database(phone, source_url, full_data)
    └── Validates and inserts to DB
```

**URL Structure**:
```
Base: https://www.evv.az/dasinmaz-emlak-satis?type={1,2,3}
Types:
  1 = Sale listings
  2 = Rent listings
  3 = Daily rent listings

Pagination: &page={0, 24, 48, 72...}  (24 items per page)
```

**Phone Extraction**:
```
POST https://www.evv.az/evvaz/get_phone
Headers:
  - X-Requested-With: XMLHttpRequest
  - Content-Type: application/x-www-form-urlencoded
  - Referer: {listing_url}
Body:
  - id: {listing_id}

Response:
  HTML with <a href="tel:+994XXXXXXXXX">
```

**Full Data Extraction** (`fetch_listing_details()`):
```javascript
{
  "listing_type": "real_estate",
  "title": "3 otaqlı mənzil...",
  "price": {
    "amount": 98000,
    "currency": "AZN",
    "price_per_sqm": 1531
  },
  "property_details": {
    "city": "Bakı",
    "property_type": "Yeni tikili",
    "location": "Nəsimi r., Metro Elmlar Akademiyası",
    "document": "Çıxarış",
    "floor": "6/9",
    "area": "64 m²",
    "rooms": 3,
    "mortgage": "Var",
    "repair": "Təmirli"
  },
  "description": "Full description text...",
  "seller": {
    "name": "Seller Name",
    "type": "Rieltor"
  },
  "listing_info": {
    "ad_id": "51945"
  },
  "images": ["url1", "url2", "url3"],
  "price_comparison": {}
}
```

**Concurrency**: 15 simultaneous requests (high capacity)

**Performance**:
- ~100% extraction success rate (API-based)
- ~24 listings per page
- ~360 listings per full run (15 pages)

---

### 2. Villa.AZ Scraper (`villa_az_scraper.py`)

**Type**: Real Estate Listings (Villas, Land, Apartments)

**Approach**: HTML scraping from detail pages

**Architecture**:
```
Class: VillaAzScraperAsync

Key Methods:
├── scrape(pages=5)
│   └── Main entry point
│
├── build_urls(start_page, end_page)
│   └── Generates paginated URLs
│
├── extract_listing_urls(html_content)
│   └── Finds listing links: <div class="ads"> -> <a>
│
├── process_listing(session, listing, idx, total)
│   ├── get_phone_numbers() -> Extract from detail page
│   └── fetch_listing_details() -> Full data extraction
│
└── save_to_database(phone, source_url, full_data)
```

**URL Structure**:
```
Search: https://villa.az/search?page={1,2,3...}
Listing: https://villa.az/elanlar/{slug}
```

**Phone Extraction**:
```
Parse detail page HTML:
  <a href="tel:+994XXXXXXXXX">
  <a href="tel:(+994) XX XXX XX XX">

Regex: re.compile(r'tel:.*\+994')
Extract all digits, remove 994 prefix, take last 9 digits
```

**Full Data Extraction**:
```javascript
{
  "listing_type": "real_estate",
  "title": "Villa satılır...",
  "price": {
    "amount": 850000,
    "currency": "AZN"
  },
  "property_details": {
    "country": "Azərbaycan",
    "city": "Bakı",
    "category": "Villa",
    "area_sqm": "500",
    "area_sot": "10",
    "rooms": "6",
    "floor": "2",
    "document": "Çıxarış"
  },
  "address": "Mərdəkan qəsəbəsi, Dəniz kənarı",
  "description": "Full description...",
  "seller": {
    "name": "Owner Name",
    "type": "Sahibindən"
  },
  "listing_info": {
    "ad_id": "123456",
    "date_posted": "10.01.2025",
    "views": 256
  },
  "features": ["Hovuz", "Qaraj", "Təmirli"],
  "images": ["url1", "url2", "url3"]
}
```

**Concurrency**: 3 simultaneous requests (lower to avoid rate limiting)

**Performance**:
- ~80% extraction success rate (some listings hide phones)
- ~24 listings per page
- ~120 listings per full run (5 pages)

---

### 3. Bul.AZ Scraper (`bul_az_scraper.py`)

**Type**: Classifieds (Various categories)

**Approach**: Similar to Villa.AZ (HTML scraping)

**Concurrency**: 10 simultaneous requests

**URL Structure**:
```
Search: https://bul.az/elanlar?page={1,2,3...}
```

---

### 4. Turbo.AZ Scraper (`turbo_az_scraper.py`)

**Type**: Car Listings

**Approach**: Synchronous scraping with CSRF token handling

**Architecture**:
```
Class: TurboAzScraper (Synchronous)

Key Methods:
├── scrape_all()
│   └── Main orchestrator
│
├── get_listing_urls()
│   └── Scrapes multiple pages for URLs
│
├── scrape_listing(url)
│   ├── _get_phone_numbers() -> API call with CSRF
│   └── Extract full car details
│
└── save_to_database(phone, source_url, full_data)

Function: scrape_turbo_az(max_pages)
  └── Wrapper function for async integration
```

**CSRF Token Handling**:
```python
# Extract from first page
csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']

# Include in phone API request
headers['X-CSRF-Token'] = csrf_token
```

**Phone API**:
```
GET {listing_url}/show_phones
Headers:
  - X-CSRF-Token: {token}
  - X-Requested-With: XMLHttpRequest
  - Referer: {listing_url}
Params:
  - trigger_button: main
  - source_link: {listing_url}

Response JSON:
{
  "phones": [
    {"primary": "0505551234", "raw": "+994505551234"}
  ]
}
```

**Full Data Extraction**:
```javascript
{
  "title": "Mercedes-Benz E 200",
  "price": "45 000 AZN",
  "city": "Bakı",
  "year": "2020",
  "body_type": "Sedan",
  "color": "Qara",
  "engine": "2.0 L",
  "mileage": "85 000 km",
  "transmission": "Avtomat",
  "gear": "Arxa",
  "is_new": "Xeyr",
  "seats": "5",
  "owners": "1",
  "condition": "Yaxşı vəziyyətdə",
  "market": "Avropa",
  "description": "Full description...",
  "features": ["Lyuk", "Dəri salon", "ABS"],
  "images": ["url1", "url2", ...],
  "listing_id": "7654321",
  "views": "1234",
  "url": "https://turbo.az/autos/7654321"
}
```

**Execution**: Runs in ThreadPoolExecutor (sync code in async context)

**Performance**:
- ~20 listings per page
- 2-second delay between listings (rate limiting)
- ~100 listings per full run (5 pages)

---

### 5. Avtopro.AZ Scraper (`avtopro_az_scraper.py`)

**Type**: Auto parts and services

**Approach**: Async HTML scraping

**Concurrency**: 10 simultaneous requests

---

## Database Schema

### Table: `leads.leads`

```sql
CREATE SCHEMA IF NOT EXISTS leads;

CREATE TABLE leads.leads (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL UNIQUE,  -- 9-digit validated number
    website VARCHAR(255) NOT NULL,              -- Source website (e.g., "evv.az")
    source VARCHAR(500) NOT NULL,               -- Full listing URL
    full_data JSONB,                            -- Complete listing data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE UNIQUE INDEX idx_phone_number ON leads.leads(phone_number);
CREATE INDEX idx_website ON leads.leads(website);
CREATE INDEX idx_created_at ON leads.leads(created_at);
CREATE INDEX idx_full_data_gin ON leads.leads USING GIN (full_data);
```

### Data Insertion Strategy

**UPSERT Pattern** (ON CONFLICT):
```sql
INSERT INTO leads.leads (phone_number, website, source, full_data)
VALUES (%s, %s, %s, %s)
ON CONFLICT (phone_number)
DO UPDATE SET
    full_data = EXCLUDED.full_data,
    source = EXCLUDED.source,
    updated_at = CURRENT_TIMESTAMP
RETURNING id;
```

**Benefits**:
- **Automatic deduplication**: Phone number is unique key
- **Data freshness**: Updates full_data if phone exists
- **Idempotent**: Can re-run scraper without creating duplicates
- **Statistics tracking**: RETURNING clause indicates new vs updated

### JSONB Full Data Structure

**Advantages of JSONB**:
- Flexible schema (different sources have different fields)
- Queryable with GIN indexes
- Supports JSON path queries
- Compressed storage

**Example Queries**:
```sql
-- Find all listings in Bakı
SELECT * FROM leads.leads
WHERE full_data->>'city' = 'Bakı';

-- Find apartments with 3+ rooms
SELECT * FROM leads.leads
WHERE (full_data->'property_details'->>'rooms')::int >= 3;

-- Find cars by year
SELECT * FROM leads.leads
WHERE website = 'turbo.az'
  AND (full_data->>'year')::int >= 2020;

-- Search in description
SELECT * FROM leads.leads
WHERE full_data->>'description' ILIKE '%təmirli%';
```

---

## Performance Characteristics

### Scraping Speed

| Source | Pages | Listings/Page | Total Listings | Concurrency | Avg Duration | Speed |
|--------|-------|---------------|----------------|-------------|--------------|-------|
| EVV.AZ | 15 | ~24 | ~360 | 15 | ~45s | 8 listings/s |
| Villa.AZ | 5 | ~24 | ~120 | 3 | ~60s | 2 listings/s |
| Bul.AZ | 5 | ~20 | ~100 | 10 | ~30s | 3.3 listings/s |
| Turbo.AZ | 5 | ~20 | ~100 | 1 (sync) | ~200s | 0.5 listings/s |
| **Total** | **30** | - | **~680** | - | **~335s** | **2 listings/s** |

### Success Rates

| Source | Extraction Rate | Save Rate | Notes |
|--------|----------------|-----------|-------|
| EVV.AZ | ~95-100% | ~40% | High extraction (API), moderate save (duplicates) |
| Villa.AZ | ~60-80% | ~35% | Some listings hide phones |
| Bul.AZ | ~70-85% | ~30% | Varies by category |
| Turbo.AZ | ~80-90% | ~25% | CSRF required, high duplicates |

### Resource Usage

**Memory**:
- Base process: ~50 MB
- Per concurrent request: ~2 MB
- Total peak: ~150-200 MB

**Database Connections**:
- Pool size: 1-10 connections
- Typical usage: 3-5 active connections
- Connection reuse: 95%+

**Network**:
- Requests per second: ~5-15 (varies by concurrency)
- Average request size: 50-200 KB
- Total bandwidth: ~50-100 MB per full scrape

---

## Deployment Options

### Option 1: Docker Compose (Recommended)

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  scraper:
    build: .
    env_file:
      - .env
    depends_on:
      - db
    command: python main.py

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: leads_db
      POSTGRES_USER: scraper
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  init-db:
    build: .
    env_file:
      - .env
    depends_on:
      - db
    command: python scripts/init_db.py
    profiles:
      - init

volumes:
  postgres_data:
```

**Commands**:
```bash
# Initialize database (first time)
docker-compose --profile init run init-db

# Run scraper
docker-compose up scraper

# View logs
docker-compose logs -f scraper
```

### Option 2: Local Python Environment

**Setup**:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL

# Initialize database
python scripts/init_db.py

# Run scraper
python main.py
```

### Option 3: GitHub Actions (Scheduled)

**Workflow** (`.github/workflows/scraper.yml`):
```yaml
name: Run Scraper

on:
  schedule:
    - cron: '0 13 * * *'  # Daily at 13:00 UTC
  workflow_dispatch:  # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          cd scraper
          pip install -r requirements.txt

      - name: Run scraper
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          cd scraper
          python main.py
```

**Setup**:
1. Add GitHub secrets: `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
2. Commit workflow file
3. Scraper runs automatically daily

---

## Error Handling & Resilience

### 1. Network Errors

**Strategy**: Retry with exponential backoff

```python
# In scraper methods
try:
    async with session.get(url, timeout=15) as response:
        if response.status == 200:
            return await response.text()
except aiohttp.ClientError as e:
    logger.error(f"Network error: {e}")
    # Continue to next listing (don't crash entire scrape)
    return None
```

**Timeouts**:
- Page fetch: 10-15 seconds
- API calls: 10 seconds
- Session timeout: 30 seconds

### 2. Database Errors

**Strategy**: Connection pool + retry logic

```python
max_retries = 3
retry_delay = 1  # seconds

for attempt in range(max_retries):
    conn = None
    try:
        conn = self.db_pool.getconn()
        # ... database operation ...
        self.db_pool.putconn(conn)
        return True
    except Exception as e:
        if conn:
            self.db_pool.putconn(conn)
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
        else:
            logger.error(f"DB error after {max_retries} attempts: {e}")
            return False
```

**Handled Scenarios**:
- Connection timeout
- Unique constraint violations (duplicates)
- Transaction deadlocks
- Pool exhaustion

### 3. Validation Errors

**Strategy**: Silent rejection (log and continue)

```python
validated_phone = PhoneValidator.validate_phone(phone_number)
if not validated_phone:
    # Don't crash - just skip invalid phone
    return False
```

**Invalid Phone Handling**:
- Logged at debug level
- Not inserted to database
- Stats show as "failed" or "invalid"
- Doesn't block other listings

### 4. Rate Limiting

**Strategy**: Respectful delays + lower concurrency

```python
# Villa.AZ: Lower concurrency to avoid blocks
villa_scraper = VillaAzScraperAsync(max_concurrent=3)

# Turbo.AZ: Delay between requests
time.sleep(2)  # 2 seconds between listings
```

**Detection**:
- HTTP 429 (Too Many Requests)
- HTTP 403 (Forbidden)
- Connection refused

**Response**:
- Reduce concurrency
- Increase delays
- Rotate user agents (future enhancement)

### 5. HTML Structure Changes

**Strategy**: Defensive parsing + fallbacks

```python
# Try multiple selectors
title = soup.find('h1', class_='prop_title')
if not title:
    title = soup.find('h1')  # Fallback
if not title:
    title = soup.find('title')  # Last resort
```

**Monitoring**:
- Track extraction success rates in Telegram reports
- Alert if success rate drops below threshold
- Manual inspection triggered

---

## Extension Guide

### Adding a New Scraper

**Step 1**: Create scraper file in `sources/`

```python
# sources/newsite_az_scraper.py

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import os
import sys
from typing import List, Dict, Optional
from datetime import datetime
import time
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.validator import PhoneValidator

load_dotenv()


class NewSiteAzScraperAsync:
    def __init__(self, max_concurrent: int = 10):
        self.base_url = "https://newsite.az"
        self.database_url = os.getenv('DATABASE_URL')
        self.max_concurrent = max_concurrent

        # Initialize connection pool
        self.db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10, self.database_url
        )

        self.headers = {
            'User-Agent': 'Mozilla/5.0 ...',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    async def scrape(self, pages: int = 3) -> Dict[str, int]:
        """Main entry point"""
        start_time = datetime.now()
        print(f"Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Scraping logic here
        stats = await self.scrape_multiple_pages(pages)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        stats['duration'] = duration
        stats['start_time'] = start_time

        return stats

    async def scrape_multiple_pages(self, pages: int):
        # Implementation
        pass

    def save_to_database(self, phone_number: str, source_url: str, full_data: Optional[Dict] = None) -> bool:
        """Standard save method"""
        validated_phone = PhoneValidator.validate_phone(phone_number)
        if not validated_phone:
            return False

        conn = None
        try:
            conn = self.db_pool.getconn()
            cur = conn.cursor()

            query = """
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (phone_number)
                DO UPDATE SET full_data = EXCLUDED.full_data, source = EXCLUDED.source
                RETURNING id
            """

            cur.execute(query, (validated_phone, 'newsite.az', source_url, json.dumps(full_data)))
            conn.commit()

            result = cur.fetchone()
            cur.close()
            self.db_pool.putconn(conn)

            return True if result else False
        except Exception as e:
            if conn:
                self.db_pool.putconn(conn)
            return False

    def close(self):
        """Close database pool"""
        if self.db_pool:
            self.db_pool.closeall()
```

**Step 2**: Update `sources/__init__.py`

```python
from .evv_az_scraper import EvvAzScraperAsync
from .villa_az_scraper import VillaAzScraperAsync
from .bul_az_scraper import BulAzScraperAsync
from .turbo_az_scraper import TurboAzScraper, scrape_turbo_az
from .avtopro_az_scraper import AvtoproAzScraperAsync
from .newsite_az_scraper import NewSiteAzScraperAsync  # NEW

__all__ = [
    'EvvAzScraperAsync',
    'VillaAzScraperAsync',
    'BulAzScraperAsync',
    'TurboAzScraper',
    'scrape_turbo_az',
    'AvtoproAzScraperAsync',
    'NewSiteAzScraperAsync'  # NEW
]
```

**Step 3**: Integrate in `main.py`

```python
from sources import EvvAzScraperAsync, VillaAzScraperAsync, BulAzScraperAsync, scrape_turbo_az, NewSiteAzScraperAsync

async def main():
    overall_start = datetime.now()
    reports = []

    # ... existing scrapers ...

    # NEW SCRAPER
    print("\n" + "=" * 70)
    print("NewSite.AZ Scraper")
    print("=" * 70)
    newsite_scraper = NewSiteAzScraperAsync(max_concurrent=10)

    try:
        newsite_stats = await newsite_scraper.scrape(pages=5)
        reports.append({
            'source': 'NewSite.AZ',
            'stats': newsite_stats,
            'duration': newsite_stats.get('duration', 0),
            'start_time': newsite_stats.get('start_time', overall_start)
        })
    finally:
        newsite_scraper.close()

    # ... rest of main ...
```

**Step 4**: Test

```bash
# Test single scraper
cd scraper
python sources/newsite_az_scraper.py

# Test integration
python main.py
```

### Best Practices for New Scrapers

1. **Always use PhoneValidator**: Ensure data quality
2. **Implement connection pooling**: Reuse DB connections
3. **Add proper error handling**: Don't crash on single failures
4. **Extract full_data**: Capture as much context as possible
5. **Respect rate limits**: Use appropriate concurrency and delays
6. **Return standardized stats**: `{'total', 'success', 'failed', 'saved', 'duration', 'start_time'}`
7. **Close resources**: Implement `close()` method for cleanup

---

## Monitoring & Observability

### Telegram Notifications

**Real-time monitoring** via Telegram:
- Scraping start/end times
- Success/failure rates per source
- Number of new leads saved
- Performance metrics (speed, duration)
- Error alerts (low extraction rate)

### Logs

**Logging levels**:
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Normal operation message")
logger.warning("Non-critical issue")
logger.error("Critical error")
logger.debug("Detailed debugging info")
```

**Log outputs**:
- Console (stdout)
- Docker logs (docker-compose logs)
- GitHub Actions logs

### Database Analytics

**Query examples**:
```sql
-- Leads by source
SELECT website, COUNT(*) as count
FROM leads.leads
GROUP BY website
ORDER BY count DESC;

-- Daily lead growth
SELECT DATE(created_at) as date, COUNT(*) as new_leads
FROM leads.leads
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date;

-- Deduplication effectiveness
SELECT
    COUNT(*) as total_inserts,
    COUNT(DISTINCT phone_number) as unique_phones,
    COUNT(*) - COUNT(DISTINCT phone_number) as duplicates
FROM leads.leads;
```

---

## Security Considerations

### Environment Variables

**Sensitive data** (never commit):
- `DATABASE_URL`: PostgreSQL connection string
- `TELEGRAM_BOT_TOKEN`: Bot API token
- `TELEGRAM_CHAT_ID`: Chat/channel IDs

**Storage**:
- Local: `.env` file (in `.gitignore`)
- Docker: Environment variables or secrets
- GitHub: Repository secrets

### Database Security

1. **Use least-privilege user**:
```sql
CREATE USER scraper_user WITH PASSWORD 'strong_password';
GRANT SELECT, INSERT, UPDATE ON leads.leads TO scraper_user;
GRANT USAGE, SELECT ON SEQUENCE leads.leads_id_seq TO scraper_user;
```

2. **SSL connections** (production):
```
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

3. **Connection limits**:
```python
# Limit pool size to avoid exhaustion
maxconn=10  # Don't set too high
```

### Web Scraping Ethics

1. **Respect robots.txt**: Check site policies
2. **Rate limiting**: Don't overload servers
3. **User-Agent**: Identify yourself properly
4. **Public data only**: Only scrape publicly visible data
5. **Terms of Service**: Review and comply with ToS

---

## Troubleshooting

### Common Issues

**Issue**: Database connection errors
```
psycopg2.OperationalError: could not connect to server
```
**Solution**:
- Verify `DATABASE_URL` is correct
- Check database is running
- Ensure network connectivity
- Run `scripts/init_db.py` to initialize schema

---

**Issue**: Low extraction success rate
```
Villa.AZ: 30/120 (25.0%) | Saved: 8
```
**Solution**:
- Website structure may have changed
- Check scraper selectors (BeautifulSoup find calls)
- Verify network connectivity
- Increase timeout values

---

**Issue**: Telegram notifications not sending
```
Telegram not configured - skipping notification
```
**Solution**:
- Set `TELEGRAM_BOT_TOKEN` in `.env`
- Set `TELEGRAM_CHAT_ID` in `.env`
- Test with `python scripts/telegram.py`
- Verify bot has permission to send to chat

---

**Issue**: Too many database connections
```
psycopg2.pool.PoolError: connection pool exhausted
```
**Solution**:
- Reduce `max_concurrent` in scrapers
- Increase `maxconn` in connection pool
- Ensure connections are properly returned (`putconn`)

---

**Issue**: Rate limiting / IP blocked
```
HTTP 429 Too Many Requests
```
**Solution**:
- Reduce `max_concurrent`
- Increase delays between requests
- Implement rotating proxies (future)
- Wait before retrying (cooldown period)

---

## Future Enhancements

### Planned Features

1. **Proxy Rotation**:
   - Rotate IP addresses to avoid rate limiting
   - Use proxy pools (Bright Data, Oxylabs)

2. **Email Extraction**:
   - Extend validation for email addresses
   - Store in separate field or in full_data

3. **Image Download**:
   - Download and store images to R2/S3
   - Create thumbnails
   - OCR for text extraction

4. **Incremental Scraping**:
   - Only scrape new listings (not re-scrape entire site)
   - Track last scrape timestamp
   - Delta updates

5. **Machine Learning**:
   - Lead scoring (predict conversion likelihood)
   - Price prediction models
   - Duplicate detection beyond phone numbers

6. **API Endpoints**:
   - REST API for triggering scrapers
   - Real-time scraping status
   - Lead search and filtering

7. **Advanced Monitoring**:
   - Prometheus metrics
   - Grafana dashboards
   - Alerting (PagerDuty, Slack)

---

## Conclusion

This scraper architecture provides a robust, scalable foundation for multi-source lead generation. Key strengths:

- **Modularity**: Easy to add new sources
- **Performance**: Async/concurrent processing
- **Reliability**: Error handling, retries, connection pooling
- **Data Quality**: Phone validation, deduplication
- **Observability**: Telegram notifications, logging
- **Deployment Flexibility**: Docker, local, GitHub Actions

The system is production-ready and has successfully scraped thousands of leads from Azerbaijan's major classifieds platforms.

---

*Document Version: 1.0*
*Last Updated: January 2025*
*Author: Lead Generator Team*
