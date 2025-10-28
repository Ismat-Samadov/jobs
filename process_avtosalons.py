#!/usr/bin/env python3
"""
Process avtosalons.csv file:
1. Parse CSV data
2. Validate phone numbers using validator.py
3. Deduplicate phone numbers
4. Format data for database insertion
5. Insert into PostgreSQL database
"""

import csv
import sys
import os
import json
from typing import List, Dict, Set
import psycopg2
from psycopg2.extras import execute_batch, Json
from datetime import datetime

# Add the scraper/scripts directory to path to import validator
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper', 'scripts'))
from validator import PhoneValidator


class AvtosalonProcessor:
    def __init__(self, db_url: str):
        """Initialize processor with database connection"""
        self.db_url = db_url
        self.conn = None
        self.validator = PhoneValidator()

    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            print("✓ Connected to database")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            sys.exit(1)

    def close_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")

    def parse_csv(self, filepath: str) -> List[Dict]:
        """Parse CSV file and extract data"""
        records = []

        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader, start=2):
                    records.append({
                        'name': row['Name'].strip(),
                        'url': row['URL'].strip(),
                        'logo': row['Logo'].strip(),
                        'description': row['Description'].strip(),
                        'contact': row['Contact'].strip(),
                        'ads_count': int(row['Ads Count']) if row['Ads Count'].strip() else 0,
                        'line_number': idx
                    })

            print(f"✓ Parsed {len(records)} records from CSV")
            return records

        except Exception as e:
            print(f"✗ Error parsing CSV: {e}")
            sys.exit(1)

    def extract_and_validate_phones(self, contact_field: str, record_name: str) -> List[str]:
        """
        Extract multiple phone numbers from contact field and validate each

        Args:
            contact_field: Raw contact string (e.g., "(050) 578-07-07, (077) 223-63-63")
            record_name: Name of the avtosalon for logging

        Returns:
            List of validated 9-digit phone numbers
        """
        # Split by comma to get individual phone numbers
        phone_candidates = contact_field.split(',')

        validated_phones = []
        for phone_raw in phone_candidates:
            phone_raw = phone_raw.strip()
            if not phone_raw:
                continue

            validated = self.validator.validate_phone(phone_raw)
            if validated:
                validated_phones.append(validated)
            else:
                print(f"  ⚠ Invalid phone in '{record_name}': {phone_raw}")

        return validated_phones

    def process_records(self, records: List[Dict]) -> tuple:
        """
        Process all records:
        1. Extract and validate phone numbers
        2. Deduplicate
        3. Format for database insertion

        Returns:
            Tuple of (leads_data, stats)
        """
        all_phones: Set[str] = set()
        leads_data = []
        stats = {
            'total_records': len(records),
            'total_phones_extracted': 0,
            'valid_phones': 0,
            'invalid_phones': 0,
            'duplicate_phones': 0,
            'unique_phones': 0
        }

        print("\nProcessing records...")
        print("=" * 80)

        for record in records:
            name = record['name']
            contact = record['contact']

            # Extract and validate phones
            validated_phones = self.extract_and_validate_phones(contact, name)

            stats['total_phones_extracted'] += len(contact.split(','))
            stats['valid_phones'] += len(validated_phones)
            stats['invalid_phones'] += (len(contact.split(',')) - len(validated_phones))

            # Check for duplicates and create lead entries
            for phone in validated_phones:
                if phone in all_phones:
                    stats['duplicate_phones'] += 1
                    print(f"  ⚠ Duplicate phone {phone} in '{name}'")
                else:
                    all_phones.add(phone)
                    leads_data.append({
                        'phone': phone,
                        'name': name,
                        'url': record['url'],
                        'logo': record['logo'],
                        'description': record['description'],
                        'ads_count': record['ads_count']
                    })

        stats['unique_phones'] = len(all_phones)

        print("=" * 80)
        print(f"\n📊 Processing Statistics:")
        print(f"  Total records: {stats['total_records']}")
        print(f"  Total phones extracted: {stats['total_phones_extracted']}")
        print(f"  Valid phones: {stats['valid_phones']}")
        print(f"  Invalid phones: {stats['invalid_phones']}")
        print(f"  Duplicate phones: {stats['duplicate_phones']}")
        print(f"  Unique phones (to insert): {stats['unique_phones']}")

        return leads_data, stats

    def insert_to_database(self, leads_data: List[Dict], source: str = 'avtosalons_csv'):
        """
        Insert validated and deduplicated leads into database

        Args:
            leads_data: List of lead dictionaries
            source: Source identifier for the leads
        """
        if not leads_data:
            print("\n⚠ No data to insert")
            return

        try:
            cursor = self.conn.cursor()

            # Prepare insert query with ON CONFLICT DO NOTHING for deduplication
            insert_query = """
                INSERT INTO leads.leads (
                    phone_number,
                    website,
                    source,
                    full_data,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (phone_number) DO NOTHING
                RETURNING id
            """

            # Prepare data for batch insert
            now = datetime.now()
            insert_data = [
                (
                    lead['phone'],
                    f"https://turbo.az{lead['url']}" if lead['url'].startswith('/') else lead['url'],
                    source,
                    Json({
                        'name': lead['name'],
                        'url': lead['url'],
                        'logo': lead['logo'],
                        'description': lead['description'],
                        'ads_count': lead['ads_count']
                    }),
                    now
                )
                for lead in leads_data
            ]

            print(f"\n📥 Inserting {len(insert_data)} leads into database...")

            # Execute batch insert
            inserted_count = 0
            for data in insert_data:
                cursor.execute(insert_query, data)
                if cursor.fetchone():
                    inserted_count += 1

            self.conn.commit()

            print(f"✓ Successfully inserted {inserted_count} new leads")
            print(f"  {len(insert_data) - inserted_count} leads already existed (duplicates skipped)")

            cursor.close()

        except Exception as e:
            self.conn.rollback()
            print(f"✗ Error inserting to database: {e}")
            raise

    def run(self, csv_filepath: str):
        """Main execution flow"""
        print("\n" + "=" * 80)
        print("🚀 Avtosalons CSV Processor")
        print("=" * 80)

        # Connect to database
        self.connect_db()

        try:
            # Parse CSV
            records = self.parse_csv(csv_filepath)

            # Process and validate
            leads_data, stats = self.process_records(records)

            # Insert to database
            self.insert_to_database(leads_data)

            print("\n" + "=" * 80)
            print("✅ Processing completed successfully!")
            print("=" * 80 + "\n")

        finally:
            self.close_db()


def main():
    """Main entry point"""
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("✗ Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    # CSV file path
    csv_file = os.path.join(os.path.dirname(__file__), 'avtosalons.csv')

    if not os.path.exists(csv_file):
        print(f"✗ Error: CSV file not found at {csv_file}")
        sys.exit(1)

    # Create processor and run
    processor = AvtosalonProcessor(db_url)
    processor.run(csv_file)


if __name__ == "__main__":
    main()
