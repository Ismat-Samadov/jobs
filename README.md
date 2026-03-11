# Lead Generator

Full-stack application for scraping and managing leads from 35+ Azerbaijani classifieds websites across real estate, auto, and general marketplaces.

## Project Structure

```
.
├── scraper/              # Python scraper backend
│   ├── sources/          # Website-specific scrapers
│   ├── scripts/          # Utilities (validator, telegram)
│   └── main.py           # Scraper orchestrator
│
├── app/                  # Next.js frontend
│   ├── api/              # API routes
│   ├── dashboard/        # User dashboard
│   ├── admin/            # Admin panel
│   └── login/            # Authentication
│
├── lib/                  # Shared utilities
│   ├── db.ts             # Database connection
│   └── auth.ts           # Authentication helpers
│
└── components/           # React components
```

## Features

### Backend (Python Scraper)
- Automated daily scraping from 35+ Azerbaijani websites
- Covers real estate, auto, and general classifieds categories
- Phone number validation (Azerbaijan mobile numbers)
- Telegram notifications with detailed reports
- PostgreSQL storage with duplicate prevention
- GitHub Actions for automated scheduling

#### Supported Sources

**Real Estate** — arenda.az, bina.az, binalar.az, binam.az, emlak.az, evv.az, ipoteka.az, mulk.az, myhome.az, ofis.az, rahatemlak.az, tikili.az, unvan.az, villa.az, vipemlak.az, yeniemlak.az

**Auto** — aratap.az, autonet.az, avtopro.az, avtovitrin.com, biturbo.az, mashin.al, masinlar.az, turbo.az

**General Marketplaces** — birja.com, birja.in, bul.az, lalafo.az, mymarket.az, qarabazar.az, tap.az, tezbazar.az, ucuztap.az, xidmetler.az

### Frontend (Next.js)
- Admin authentication with NextAuth.js
- User management (CRUD operations)
- Leads dashboard with statistics
- Search and pagination
- Excel export functionality
- Role-based access control (Admin/User)

## Screenshots

### Landing Page
![Landing Page](screens/landing%20page.png)

### Login
![Login Page](screens/login%20page.png)

### Dashboard
![Dashboard](screens/dashboard%20page.png)

### Analytics
![Analytics 1](screens/analytics%20page_1.png)
![Analytics 2](screens/analytics%20page_2.png)

### File Export
![File Page](screens/file%20page.png)

## Quick Start

### 1. Database Setup

```bash
# Initialize leads table
psql $DATABASE_URL -f scraper/init_db.sql

# Initialize users table
psql $DATABASE_URL -f init_users_db.sql
```

### 2. Frontend Development

```bash
# Install dependencies
npm install

# Set up environment
cp .env.example .env.local
# Edit .env.local with your credentials

# Run development server
npm run dev
```

Visit http://localhost:3000

**Default credentials**: `admin` / `admin123`

### 3. Backend (Scraper)

```bash
cd scraper

# Local testing
docker compose up scraper

# Or with Python
python main.py
```

## Environment Variables

### Frontend (.env.local)
```bash
DATABASE_URL=postgresql://...
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=generate-with-openssl-rand-base64-32
```

### Backend (scraper/.env)
```bash
DATABASE_URL=postgresql://...
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel
```

Don't forget to:
1. Initialize users database
2. Set environment variables in Vercel
3. Generate secure NEXTAUTH_SECRET
4. Update NEXTAUTH_URL to production domain

## User Roles

### Admin
- Full access to all features
- Create/update/delete users
- View and export all leads
- Access to admin panel

### User
- View leads dashboard
- Search and filter leads
- Export data to Excel
- No user management access

## API Endpoints

### Authentication
- `POST /api/auth/signin` - Login
- `POST /api/auth/signout` - Logout

### Users (Admin only)
- `GET /api/users` - List all users
- `POST /api/users` - Create user
- `PUT /api/users` - Update user
- `DELETE /api/users?id=X` - Delete user

### Leads
- `GET /api/leads` - Get leads (paginated)
- `GET /api/leads/export` - Export to Excel
- `GET /api/stats` - Dashboard statistics

## Scraper Schedule

GitHub Actions runs scraper:
- Daily at **13:00 UTC** (4:00 PM Azerbaijan Time)
- Manual trigger available via GitHub Actions UI

## Tech Stack

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- NextAuth.js (Authentication)
- XLSX (Excel export)

### Backend
- Python 3.11
- aiohttp (Async HTTP)
- BeautifulSoup + lxml (HTML parsing)
- PostgreSQL (psycopg2)
- Docker

### Infrastructure
- Vercel (Frontend hosting)
- Neon Tech (PostgreSQL)
- GitHub Actions (Automation)
- Telegram Bot (Notifications)

## Database Schema

### leads
```sql
id, phone_number (unique), source_url, scraped_at
```

### users
```sql
id, username (unique), password_hash, role, is_active, created_at, last_login
```

### sessions
```sql
id, user_id, session_token, expires, created_at
```

## GitHub Secrets Required

For automated scraping:
- `DATABASE_URL` - PostgreSQL connection string
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `TELEGRAM_CHAT_ID` - Chat/group ID(s) for notifications

## Development

### Install Dependencies

```bash
# Frontend
npm install

# Backend
cd scraper
pip install -r requirements.txt
```

### Run Tests

```bash
# Test scraper locally
cd scraper
python main.py

# Test Telegram notifications
python scripts/telegram.py
```

### Get Telegram Chat ID

```bash
cd scraper
python scripts/get_chat_id.py
```

## Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL is correct
- Check SSL mode is enabled
- Ensure database accepts connections

### Authentication Not Working
- Verify NEXTAUTH_SECRET is set
- Check NEXTAUTH_URL matches current domain
- Clear browser cookies

### Scraper Failures
- Check phone validation rules
- Verify website structure hasn't changed
- Review GitHub Actions logs

## License

Proprietary - All rights reserved

## Support

For issues and questions, contact the development team.
