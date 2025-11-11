#!/usr/bin/env python3
"""
Import CSV files from data directory into leads.leads table

Features:
- Handles multiple phone numbers per row (splits by semicolon, comma, newline)
- Validates each phone number using PhoneValidator
- Creates separate database row for each valid phone number
- Stores all CSV data in full_data JSONB column
- Handles duplicates gracefully (UNIQUE constraint on phone_number)
- Comprehensive logging and statistics
"""

import os
import sys
import csv
import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Add parent directory to path for validator import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.scripts.validator import PhoneValidator

# Load environment variables
load_dotenv()

class CSVImporter:
    """Import CSV files from data directory into leads table"""

    # CSV file configurations - map each file to its structure
    CSV_CONFIGS = {
        'avtotemir_masters.csv': {
            'website': 'avtotemir.az',
            'phone_column': 'phone_numbers',  # Multiple phones separated by ;
            'url_column': 'url',
            'multi_phone_separator': ';',  # Separator for multiple phones
            'columns_to_store': [
                'id', 'name', 'position', 'car_brands', 'location',
                'rating', 'votes', 'experience', 'views', 'added_date',
                'address', 'services', 'note', 'images'
            ]
        },
        'insaat_listings.csv': {
            'website': 'insaat.az',
            'phone_column': 'phone',
            'url_column': 'url',
            'multi_phone_separator': None,  # Single phone
            'columns_to_store': [
                'listing_id', 'title', 'category', 'subcategory', 'price',
                'price_azn', 'description', 'contact_name', 'contact_type',
                'location', 'date', 'images'
            ]
        },
        'temirci_listings.csv': {
            'website': 'temirci.az',
            'phone_column': 'phone',
            'url_column': 'listing_url',
            'multi_phone_separator': None,  # Single phone
            'columns_to_store': [
                'ad_id', 'category', 'title', 'city', 'price', 'description',
                'views', 'date_posted', 'image_url', 'scraped_at'
            ]
        },
        'ustalar_masters.csv': {
            'website': 'ustalar.az',
            'phone_column': 'phone',
            'url_column': 'url',
            'multi_phone_separator': None,  # Single phone
            'columns_to_store': [
                'listing_id', 'title', 'category', 'subcategory', 'price',
                'contact_name', 'location', 'date', 'description', 'images'
            ]
        },
        'ustasi_listings.csv': {
            'website': 'ustasi.az',
            'phone_column': 'phone',
            'url_column': 'url',
            'multi_phone_separator': None,  # Single phone
            'columns_to_store': [
                'listing_id', 'title', 'categories', 'price', 'user_name',
                'user_id', 'location', 'date', 'description'
            ]
        }
    }

    def __init__(self, db_connection_string: str):
        """Initialize importer with database connection"""
        self.db_conn = psycopg2.connect(db_connection_string)
        self.stats = {
            'total_rows': 0,
            'total_phones_found': 0,
            'valid_phones': 0,
            'invalid_phones': 0,
            'new_leads': 0,
            'duplicates': 0,
            'errors': 0
        }
        self.file_stats = {}

    def extract_phone_numbers(self, phone_field: str, separator: Optional[str] = None) -> List[str]:
        """
        Extract and clean phone numbers from a field

        Handles:
        - Multiple phones separated by semicolon, comma, or newline
        - Phone numbers with various formatting (spaces, dashes, parens)
        - Country codes (+994, 994)

        Args:
            phone_field: Raw phone field from CSV
            separator: Separator for multiple phones (;, comma, etc.)

        Returns:
            List of cleaned phone number strings
        """
        if not phone_field or phone_field.strip() == '':
            return []

        # Replace common separators with semicolon for consistent splitting
        phone_field = phone_field.replace('\n', ';').replace(',', ';')

        # Split by separator if specified, otherwise treat as single phone
        if separator:
            raw_phones = phone_field.split(separator)
        else:
            raw_phones = [phone_field]

        # Clean each phone number
        cleaned_phones = []
        for phone in raw_phones:
            phone = phone.strip()
            if phone:
                cleaned_phones.append(phone)

        return cleaned_phones

    def save_lead(self, phone_number: str, website: str, source_url: str,
                  full_data: Dict) -> Tuple[bool, str]:
        """
        Save a lead to the database

        Args:
            phone_number: Validated 9-digit phone number
            website: Source website name
            source_url: Source URL
            full_data: Dict with all CSV data

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            cursor = self.db_conn.cursor()

            # Check if phone already exists
            cursor.execute("""
                SELECT id, website FROM leads.leads
                WHERE phone_number = %s
            """, (phone_number,))

            existing = cursor.fetchone()

            if existing:
                cursor.close()
                return (False, f"Duplicate - already exists from {existing[1]}")

            # Insert new lead
            cursor.execute("""
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
            """, (phone_number, website, source_url, psycopg2.extras.Json(full_data)))

            self.db_conn.commit()
            cursor.close()
            return (True, "Inserted successfully")

        except psycopg2.IntegrityError as e:
            self.db_conn.rollback()
            return (False, f"Duplicate - integrity error")
        except Exception as e:
            self.db_conn.rollback()
            return (False, f"Error: {str(e)}")

    def process_csv_file(self, file_path: str, config: Dict) -> Dict:
        """
        Process a single CSV file and import all valid leads

        Args:
            file_path: Path to CSV file
            config: Configuration dict for this CSV file

        Returns:
            Statistics dict for this file
        """
        filename = os.path.basename(file_path)
        print(f"\n{'='*80}")
        print(f"Processing: {filename}")
        print(f"{'='*80}")

        file_stats = {
            'rows_processed': 0,
            'phones_found': 0,
            'valid_phones': 0,
            'invalid_phones': 0,
            'new_leads': 0,
            'duplicates': 0,
            'errors': 0,
            'invalid_phone_examples': []
        }

        website = config['website']
        phone_column = config['phone_column']
        url_column = config['url_column']
        separator = config.get('multi_phone_separator')
        columns_to_store = config['columns_to_store']

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                    file_stats['rows_processed'] += 1

                    # Extract source URL
                    source_url = row.get(url_column, '').strip()
                    if not source_url:
                        source_url = f"{website}/listing/{row_num}"

                    # Extract phone number(s) from the phone column
                    phone_field = row.get(phone_column, '')
                    raw_phones = self.extract_phone_numbers(phone_field, separator)

                    if not raw_phones:
                        continue  # Skip rows with no phone numbers

                    file_stats['phones_found'] += len(raw_phones)

                    # Process each phone number
                    for raw_phone in raw_phones:
                        # Validate phone number
                        validated_phone = PhoneValidator.validate_phone(raw_phone)

                        if not validated_phone:
                            file_stats['invalid_phones'] += 1
                            # Store first 5 invalid examples for reporting
                            if len(file_stats['invalid_phone_examples']) < 5:
                                file_stats['invalid_phone_examples'].append(raw_phone)
                            continue

                        file_stats['valid_phones'] += 1

                        # Build full_data dict with all relevant columns
                        full_data = {
                            'source_website': website,
                            'imported_at': datetime.now().isoformat(),
                            'raw_phone': raw_phone,
                            'validated_phone': validated_phone
                        }

                        # Add all columns from config
                        for col in columns_to_store:
                            if col in row:
                                full_data[col] = row[col]

                        # Save to database
                        success, message = self.save_lead(
                            validated_phone,
                            website,
                            source_url,
                            full_data
                        )

                        if success:
                            file_stats['new_leads'] += 1
                        elif 'Duplicate' in message:
                            file_stats['duplicates'] += 1
                        else:
                            file_stats['errors'] += 1

                    # Progress indicator every 100 rows
                    if file_stats['rows_processed'] % 100 == 0:
                        print(f"  Processed {file_stats['rows_processed']} rows... "
                              f"({file_stats['new_leads']} new leads, "
                              f"{file_stats['duplicates']} duplicates)")

        except Exception as e:
            print(f"  ✗ Error processing file: {e}")
            file_stats['errors'] += 1

        # Print file statistics
        print(f"\n{'='*80}")
        print(f"File: {filename} - COMPLETED")
        print(f"{'='*80}")
        print(f"  Rows processed:     {file_stats['rows_processed']:,}")
        print(f"  Phones found:       {file_stats['phones_found']:,}")
        print(f"  Valid phones:       {file_stats['valid_phones']:,}")
        print(f"  Invalid phones:     {file_stats['invalid_phones']:,}")
        print(f"  New leads inserted: {file_stats['new_leads']:,}")
        print(f"  Duplicates skipped: {file_stats['duplicates']:,}")
        print(f"  Errors:             {file_stats['errors']:,}")

        if file_stats['invalid_phone_examples']:
            print(f"\n  Invalid phone examples:")
            for example in file_stats['invalid_phone_examples']:
                print(f"    - {example}")

        return file_stats

    def import_all_csv_files(self, data_directory: str):
        """
        Import all CSV files from the data directory

        Args:
            data_directory: Path to directory containing CSV files
        """
        print(f"\n{'='*80}")
        print(f"CSV IMPORT TOOL - Lead Generator")
        print(f"{'='*80}")
        print(f"Data directory: {data_directory}")
        print(f"Files to process: {len(self.CSV_CONFIGS)}")
        print(f"{'='*80}\n")

        # Process each configured CSV file
        for filename, config in self.CSV_CONFIGS.items():
            file_path = os.path.join(data_directory, filename)

            if not os.path.exists(file_path):
                print(f"⚠ Warning: File not found: {filename}")
                continue

            file_stats = self.process_csv_file(file_path, config)
            self.file_stats[filename] = file_stats

            # Update global stats
            self.stats['total_rows'] += file_stats['rows_processed']
            self.stats['total_phones_found'] += file_stats['phones_found']
            self.stats['valid_phones'] += file_stats['valid_phones']
            self.stats['invalid_phones'] += file_stats['invalid_phones']
            self.stats['new_leads'] += file_stats['new_leads']
            self.stats['duplicates'] += file_stats['duplicates']
            self.stats['errors'] += file_stats['errors']

        # Print final summary
        self.print_final_summary()

    def print_final_summary(self):
        """Print final import statistics"""
        print(f"\n{'='*80}")
        print(f"FINAL IMPORT SUMMARY")
        print(f"{'='*80}")
        print(f"Total CSV rows:           {self.stats['total_rows']:,}")
        print(f"Total phones found:       {self.stats['total_phones_found']:,}")
        print(f"Valid phones:             {self.stats['valid_phones']:,}")
        print(f"Invalid phones:           {self.stats['invalid_phones']:,}")
        print(f"New leads inserted:       {self.stats['new_leads']:,}")
        print(f"Duplicates skipped:       {self.stats['duplicates']:,}")
        print(f"Errors:                   {self.stats['errors']:,}")
        print(f"{'='*80}")

        # Calculate success rate
        if self.stats['total_phones_found'] > 0:
            valid_rate = (self.stats['valid_phones'] / self.stats['total_phones_found']) * 100
            insert_rate = (self.stats['new_leads'] / self.stats['valid_phones']) * 100 if self.stats['valid_phones'] > 0 else 0
            print(f"\nSuccess Rates:")
            print(f"  Phone validation:  {valid_rate:.1f}%")
            print(f"  Insertion rate:    {insert_rate:.1f}%")

        print(f"\n{'='*80}\n")

    def close(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()


def main():
    """Main function"""
    # Get database connection string from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Get data directory path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(project_dir, 'data')

    if not os.path.exists(data_dir):
        print(f"Error: Data directory not found: {data_dir}")
        sys.exit(1)

    # Create importer and run
    importer = CSVImporter(db_url)

    try:
        importer.import_all_csv_files(data_dir)
    except KeyboardInterrupt:
        print("\n\nImport interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        importer.close()


if __name__ == "__main__":
    main()
