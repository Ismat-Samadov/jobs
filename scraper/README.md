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

# 2. Configure environment
cp .env.example .env
# Edit .env and add your DATABASE_URL

# 3. Initialize database
python scripts/init_db.py

# 4. Run scraper
python main.py
```

## Features

- **Async/Await with aiohttp**: Concurrent requests for maximum performance
- **Multi-source support**: Modular design for adding new scrapers
- **Automatic phone extraction**: Extracts phone numbers via API calls
- **Phone validation**: Validates Azerbaijan phone numbers before database insertion
  - Only numeric digits (auto-cleaned)
  - Exactly 9 digits (takes last 9)
  - Valid prefixes: 10, 50, 51, 55, 60, 70, 77, 99
  - 3rd digit cannot be 0 or 1
  - Unique constraint (no duplicates)
- **Telegram notifications**: Automatic reports sent to Telegram channel after each scraping operation
  - Detailed statistics (total, extracted, saved, failed)
  - Performance metrics (duration, speed)
  - Success rate indicators
- **Database storage**: Saves leads to PostgreSQL with duplicate prevention
- **Docker support**: One-command deployment
- **Rate limiting**: Configurable concurrent request limits
- **Error handling**: Robust error handling and retry logic

## Project Structure

```
scraper/
├── sources/
│   ├── __init__.py
│   ├── evv_az_scraper.py    # EVV.AZ scraper
│   └── villa_az_scraper.py  # Villa.AZ scraper
├── scripts/
│   ├── init_db.py            # Database initialization
│   ├── schema.sql            # Database schema
│   ├── validator.py          # Phone number validation
│   └── telegram.py           # Telegram notifications
├── main.py                   # Main entry point
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker compose configuration
├── .env.example              # Environment variables template
└── .env                      # Environment variables (create from .env.example)
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

## Phone Number Validation

All phone numbers are validated before database insertion using `scripts/validator.py`:

### Validation Rules

1. **Extract digits only**: Removes all non-numeric characters
2. **9-digit format**: Takes last 9 digits from the number
3. **Valid prefixes**: First 2 digits must be one of:
   - `10` - Azercell
   - `50` - Azercell
   - `51` - Azercell
   - `55` - Bakcell
   - `60` - Nar Mobile
   - `70` - Nar Mobile
   - `77` - Nar Mobile
   - `99` - Azercell
4. **Third digit validation**: Cannot be `0` or `1`
5. **Uniqueness**: Database constraint ensures no duplicates

### Examples

```python
# Valid numbers
"994505551234"  → "505551234" ✓  # Valid prefix 50, 3rd digit 5
"558688686"     → "558688686" ✓  # Valid prefix 55, 3rd digit 8
"+994 70 555 12 34" → "705551234" ✓  # Valid with formatting

# Invalid numbers
"994500551234"  → Rejected ✗  # 3rd digit is 0
"994405551234"  → Rejected ✗  # Invalid prefix 40
"50555123"      → Rejected ✗  # Only 8 digits
```

**Note**: Invalid phone numbers are silently rejected and not inserted into the database.

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
# Required
DATABASE_URL=postgresql://user:password@host:port/database

# Optional - Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token_here    # Get from @BotFather
TELEGRAM_CHAT_ID=your_chat_id_here        # Get from @userinfobot

# Optional - Docker
PYTHONUNBUFFERED=1                        # For Docker logs
```

## Telegram Notifications Setup

To receive automated reports after each scraping operation:

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the **Bot Token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

**For personal notifications:**
1. Search for `@userinfobot` on Telegram
2. Send `/start`
3. Copy your **Chat ID** (numeric ID)

**For channel notifications:**
1. Add your bot to your channel as an administrator
2. Send a message to your channel
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find your channel's Chat ID in the response (looks like: `-100123456789`)

### 3. Configure Environment Variables

Add to your `.env` file:
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### 4. Test Notification

```bash
python scripts/telegram.py
```

### Notification Format

After each scraping run, you'll receive a detailed report including:
- 📊 **Statistics**: Total listings, phones extracted, new saved, duplicates, failed
- ⏱ **Performance**: Start time, duration, processing speed
- 🎯 **Status**: Success indicator based on extraction rate
- 📍 **By Source**: Individual metrics for each scraper (EVV.AZ, Villa.AZ)

**Example Notification:**
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
- **Default behavior**: Scrapes all 3 types, 5 pages each (15 pages total)

### Villa.AZ (Real Estate)
- Website: https://villa.az
- Type: Real estate listings (villas, land, apartments)
- Location: Azerbaijan
- Extraction: Phone numbers from listing detail pages (supports multiple formats)
- Pagination: Standard page numbers (page=1, 2, 3...)
- **Default behavior**: Scrapes first 5 pages
- **Concurrency**: 3 concurrent requests (optimized to avoid rate limiting)
- **Success rate**: ~80% extraction success

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
