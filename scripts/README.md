# Scripts

This directory contains one-time setup and utility scripts for the Lead Generator application.

## Database Setup Scripts

### `init_users_db.sql`
SQL script to initialize the users database schema and create the admin user.

**Usage:**
```bash
psql -U postgres -d leads_db -f scripts/init_users_db.sql
```

### `init_users.ts`
TypeScript script to initialize users in the database.

**Usage:**
```bash
npx ts-node scripts/init_users.ts
```

## Utility Scripts

### `check_full_data.js`
Script to check and verify the full_data column in the leads table.

**Usage:**
```bash
node scripts/check_full_data.js
```

## Notes

- These scripts are typically run once during setup or for maintenance tasks
- Make sure database credentials are properly configured in `.env.local` before running database scripts
- Backup your database before running any modification scripts
