#!/usr/bin/env python3
"""
Script to import kurslar.az CSV data into leads.leads table
Transforms CSV format to match database schema
"""

import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
from validator import PhoneValidator

# Load environment variables from .env or .env.local
try:
    from dotenv import load_dotenv
    # Try to load from parent directory's .env.local
    env_path = Path(__file__).parent.parent.parent / '.env.local'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try scraper's .env
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, rely on environment variables

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Error: DATABASE_URL environment variable not set")
    print("   Please set DATABASE_URL or create .env.local file")
    sys.exit(1)

# CSV file path
CSV_FILE = '/Users/ismatsamadov/lead_generator/scraper/.backup_removed_files/phone/2025/kurslar_data.csv'

# Website source
WEBSITE = 'kurslar.az'


def extract_phone_numbers(phone_str):
    """
    Extract and validate phone numbers from comma-separated string
    Returns list of valid phone numbers
    """
    if not phone_str or phone_str.strip() == '':
        return []

    # Split by comma and clean
    phones = [p.strip() for p in phone_str.split(',')]
    valid_phones = []

    for phone in phones:
        if phone:
            validated = PhoneValidator.validate_phone(phone)
            if validated:
                valid_phones.append(validated)

    return valid_phones


def transform_row_to_lead(row):
    """
    Transform CSV row to database lead format
    Returns list of tuples: (phone_number, website, source, full_data)
    """
    leads = []

    # Extract phone numbers
    phone_numbers = extract_phone_numbers(row.get('phone_numbers', ''))

    if not phone_numbers:
        return []

    # Source URL
    source_url = row.get('url', '').strip()
    if not source_url:
        source_url = f"https://kurslar.az/kurslar/{row.get('listing_id', 'unknown')}.html"

    # Build full_data JSON
    full_data = {
        'listing_id': row.get('listing_id', ''),
        'ajax_id': row.get('ajax_id', ''),
        'title': row.get('title', '').strip(),
        'description': row.get('description', '').strip(),
        'category': row.get('categories', '').strip(),
        'price': row.get('price', '').strip(),
        'location': row.get('location', '').strip(),
        'date_posted': row.get('date', '').strip(),
        'image_url': row.get('image_url', '').strip(),
        'url': source_url,
        'user_name': row.get('user_name', '').strip(),
        'user_url': row.get('user_url', '').strip(),
        'ajax_type': row.get('ajax_type', '').strip(),
        'ajax_hash': row.get('ajax_hash', '').strip(),
        'source_type': 'courses',
        'scraped_at': datetime.now().isoformat()
    }

    # Remove empty fields
    full_data = {k: v for k, v in full_data.items() if v}

    # Create one lead entry per phone number
    for phone in phone_numbers:
        leads.append((
            phone,
            WEBSITE,
            source_url,
            json.dumps(full_data, ensure_ascii=False)
        ))

    return leads


def import_csv_to_database():
    """
    Main function to import CSV data into PostgreSQL
    """
    print(f"🔄 Starting import from {CSV_FILE}")
    print(f"📊 Target database: {WEBSITE}\n")

    stats = {
        'total_rows': 0,
        'total_phones': 0,
        'valid_phones': 0,
        'invalid_phones': 0,
        'inserted': 0,
        'duplicates': 0,
        'errors': 0
    }

    # Read and process CSV
    leads_to_insert = []

    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                stats['total_rows'] += 1

                # Extract phone count
                phone_str = row.get('phone_numbers', '')
                if phone_str:
                    phone_count = len([p for p in phone_str.split(',') if p.strip()])
                    stats['total_phones'] += phone_count

                # Transform row to leads
                leads = transform_row_to_lead(row)
                stats['valid_phones'] += len(leads)
                stats['invalid_phones'] += phone_count - len(leads) if phone_str else 0

                leads_to_insert.extend(leads)

                # Progress update every 100 rows
                if stats['total_rows'] % 100 == 0:
                    print(f"  Processed {stats['total_rows']} rows, extracted {len(leads_to_insert)} valid leads...")

    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    print(f"\n✅ CSV processing complete!")
    print(f"   Total rows: {stats['total_rows']}")
    print(f"   Total phones found: {stats['total_phones']}")
    print(f"   Valid phones: {stats['valid_phones']}")
    print(f"   Invalid phones: {stats['invalid_phones']}")
    print(f"   Leads ready to insert: {len(leads_to_insert)}\n")

    if not leads_to_insert:
        print("⚠️  No valid leads to insert!")
        return

    # Insert into database
    print(f"🔄 Inserting into database...\n")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Batch insert with ON CONFLICT handling
        insert_query = """
            INSERT INTO leads.leads (phone_number, website, source, full_data, created_at)
            VALUES %s
            ON CONFLICT (phone_number) DO NOTHING
        """

        # Prepare data with created_at timestamp
        insert_data = [
            (phone, website, source, full_data, datetime.now())
            for phone, website, source, full_data in leads_to_insert
        ]

        # Execute batch insert
        execute_values(cursor, insert_query, insert_data)

        # Get number of rows actually inserted
        stats['inserted'] = cursor.rowcount
        stats['duplicates'] = len(leads_to_insert) - stats['inserted']

        conn.commit()

        print(f"✅ Database insertion complete!")
        print(f"   Inserted: {stats['inserted']}")
        print(f"   Duplicates skipped: {stats['duplicates']}\n")

        # Get current totals from database
        cursor.execute("SELECT COUNT(*) FROM leads.leads WHERE website = %s", (WEBSITE,))
        total_kurslar = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM leads.leads")
        total_all = cursor.fetchone()[0]

        print(f"📊 Database Statistics:")
        print(f"   Total {WEBSITE} leads: {total_kurslar}")
        print(f"   Total all leads: {total_all}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Database error: {e}")
        stats['errors'] += 1
        if conn:
            conn.rollback()

    # Final summary
    print(f"\n{'='*60}")
    print(f"IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"CSV Rows Processed:     {stats['total_rows']}")
    print(f"Phone Numbers Found:    {stats['total_phones']}")
    print(f"Valid Phone Numbers:    {stats['valid_phones']}")
    print(f"Invalid Phone Numbers:  {stats['invalid_phones']}")
    print(f"Leads Inserted:         {stats['inserted']}")
    print(f"Duplicates Skipped:     {stats['duplicates']}")
    print(f"Errors:                 {stats['errors']}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    import_csv_to_database()
