"""
CSV Import Script - Import leads from CSV files into the database
"""
import csv
import os
import sys
import json
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.validator import PhoneValidator

# Load environment variables
load_dotenv()


class CSVImporter:
    """Import CSV data into the leads database"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL not set in environment")

        # Initialize connection pool
        self.db_pool = psycopg2.pool.SimpleConnectionPool(
            1,  # minimum connections
            10,  # maximum connections
            self.database_url
        )

    def save_to_database(self, phone_number: str, website: str, source_url: str, full_data: dict) -> bool:
        """
        Save lead to database with validation

        Args:
            phone_number: Phone number to save
            website: Website source (e.g., 'kurslar.az')
            source_url: URL of the listing
            full_data: Complete listing data as dict

        Returns:
            True if saved successfully, False otherwise
        """
        # Validate phone number
        validated_phone = PhoneValidator.validate_phone(phone_number)

        if not validated_phone:
            return False

        max_retries = 3
        retry_delay = 0.5

        for attempt in range(max_retries):
            conn = None
            try:
                # Get connection from pool
                conn = self.db_pool.getconn()
                cur = conn.cursor()

                # Insert lead with full_data (ignore duplicates by phone number)
                query = """
                    INSERT INTO leads.leads (phone_number, website, source, full_data)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (phone_number)
                    DO UPDATE SET
                        full_data = EXCLUDED.full_data,
                        source = EXCLUDED.source,
                        website = EXCLUDED.website
                    RETURNING id
                """

                # Convert full_data dict to JSON string
                full_data_json = json.dumps(full_data, ensure_ascii=False)

                cur.execute(query, (validated_phone, website, source_url, full_data_json))
                conn.commit()

                result = cur.fetchone()
                cur.close()

                # Return connection to pool
                self.db_pool.putconn(conn)

                return True if result else False

            except Exception as e:
                # Return connection to pool if we got one
                if conn:
                    self.db_pool.putconn(conn)

                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"Database error after {max_retries} attempts: {e}")
                    return False

        return False

    def import_kurslar_csv(self, csv_path: str) -> dict:
        """
        Import kurslar.az CSV file

        CSV columns: ajax_hash, ajax_id, ajax_type, categories, date, description,
                     image_url, listing_id, location, phone_numbers, price, title,
                     url, user_name, user_url
        """
        print(f"\n{'='*70}")
        print(f"Importing KURSLAR.AZ data from: {csv_path}")
        print(f"{'='*70}")

        stats = {
            'total': 0,
            'valid_phones': 0,
            'invalid_phones': 0,
            'saved': 0,
            'duplicates': 0
        }

        start_time = datetime.now()

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                stats['total'] += 1

                # Extract phone number
                phone = row.get('phone_numbers', '').strip()

                if not phone:
                    stats['invalid_phones'] += 1
                    continue

                # Build full_data object
                full_data = {
                    'listing_type': 'course',
                    'listing_id': row.get('listing_id', ''),
                    'title': row.get('title', ''),
                    'description': row.get('description', ''),
                    'categories': row.get('categories', ''),
                    'location': row.get('location', ''),
                    'price': row.get('price', ''),
                    'date': row.get('date', ''),
                    'image_url': row.get('image_url', ''),
                    'user_name': row.get('user_name', ''),
                    'user_url': row.get('user_url', ''),
                    'ajax_type': row.get('ajax_type', ''),
                }

                # Get source URL
                source_url = row.get('url', '')

                # Save to database
                if self.save_to_database(phone, 'kurslar.az', source_url, full_data):
                    stats['saved'] += 1
                    stats['valid_phones'] += 1
                else:
                    # Check if it was invalid or duplicate
                    if PhoneValidator.validate_phone(phone):
                        stats['duplicates'] += 1
                        stats['valid_phones'] += 1
                    else:
                        stats['invalid_phones'] += 1

                # Progress update every 100 rows
                if stats['total'] % 100 == 0:
                    print(f"Processed: {stats['total']} | Saved: {stats['saved']} | Duplicates: {stats['duplicates']}")

        duration = (datetime.now() - start_time).total_seconds()

        print(f"\n{'='*70}")
        print(f"KURSLAR.AZ Import Complete in {duration:.2f}s")
        print(f"{'='*70}")
        print(f"Total rows: {stats['total']}")
        print(f"Valid phones: {stats['valid_phones']}")
        print(f"Invalid phones: {stats['invalid_phones']}")
        print(f"Saved to DB: {stats['saved']}")
        print(f"Duplicates: {stats['duplicates']}")
        print(f"{'='*70}")

        return stats

    def import_tutors_csv(self, csv_path: str) -> dict:
        """
        Import repetitor.az CSV file

        CSV columns: id, url, name, phone, rating, age, experience, city,
                     teaching_language, teaching_format, subject_category, subject_name,
                     reviews_count, description, subject_taught, price_teacher_location,
                     price_student_location, price_online, education_year,
                     education_institution, education_specialty
        """
        print(f"\n{'='*70}")
        print(f"Importing REPETITOR.AZ data from: {csv_path}")
        print(f"{'='*70}")

        stats = {
            'total': 0,
            'valid_phones': 0,
            'invalid_phones': 0,
            'saved': 0,
            'duplicates': 0
        }

        start_time = datetime.now()

        with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig to handle BOM
            reader = csv.DictReader(f)

            for row in reader:
                stats['total'] += 1

                # Extract phone number
                phone = row.get('phone', '').strip()

                if not phone:
                    stats['invalid_phones'] += 1
                    continue

                # Build full_data object
                full_data = {
                    'listing_type': 'tutor',
                    'tutor_id': row.get('id', ''),
                    'name': row.get('name', ''),
                    'description': row.get('description', ''),
                    'subject_taught': row.get('subject_taught', ''),
                    'city': row.get('city', ''),
                    'rating': row.get('rating', ''),
                    'age': row.get('age', ''),
                    'experience': row.get('experience', ''),
                    'teaching_language': row.get('teaching_language', ''),
                    'teaching_format': row.get('teaching_format', ''),
                    'subject_category': row.get('subject_category', ''),
                    'subject_name': row.get('subject_name', ''),
                    'reviews_count': row.get('reviews_count', ''),
                    'price_teacher_location': row.get('price_teacher_location', ''),
                    'price_student_location': row.get('price_student_location', ''),
                    'price_online': row.get('price_online', ''),
                    'education_year': row.get('education_year', ''),
                    'education_institution': row.get('education_institution', ''),
                    'education_specialty': row.get('education_specialty', ''),
                }

                # Get source URL
                source_url = row.get('url', '')

                # Save to database
                if self.save_to_database(phone, 'repetitor.az', source_url, full_data):
                    stats['saved'] += 1
                    stats['valid_phones'] += 1
                else:
                    # Check if it was invalid or duplicate
                    if PhoneValidator.validate_phone(phone):
                        stats['duplicates'] += 1
                        stats['valid_phones'] += 1
                    else:
                        stats['invalid_phones'] += 1

                # Progress update every 500 rows
                if stats['total'] % 500 == 0:
                    print(f"Processed: {stats['total']} | Saved: {stats['saved']} | Duplicates: {stats['duplicates']}")

        duration = (datetime.now() - start_time).total_seconds()

        print(f"\n{'='*70}")
        print(f"REPETITOR.AZ Import Complete in {duration:.2f}s")
        print(f"{'='*70}")
        print(f"Total rows: {stats['total']}")
        print(f"Valid phones: {stats['valid_phones']}")
        print(f"Invalid phones: {stats['invalid_phones']}")
        print(f"Saved to DB: {stats['saved']}")
        print(f"Duplicates: {stats['duplicates']}")
        print(f"{'='*70}")

        return stats

    def close(self):
        """Close database connection pool"""
        if self.db_pool:
            self.db_pool.closeall()
            print("\nDatabase connection pool closed")


def main():
    """Main import function"""
    # CSV file paths
    kurslar_csv = '/Users/ismatsamadov/lead_generator/scraper/.backup_removed_files/phone/2025/kurslar_data.csv'
    tutors_csv = '/Users/ismatsamadov/lead_generator/scraper/.backup_removed_files/phone/2025/tutors_data.csv'

    # Check if files exist
    if not os.path.exists(kurslar_csv):
        print(f"Error: {kurslar_csv} not found")
        return

    if not os.path.exists(tutors_csv):
        print(f"Error: {tutors_csv} not found")
        return

    # Initialize importer
    importer = CSVImporter()

    try:
        # Import both CSV files
        kurslar_stats = importer.import_kurslar_csv(kurslar_csv)
        tutors_stats = importer.import_tutors_csv(tutors_csv)

        # Overall summary
        print(f"\n{'='*70}")
        print("OVERALL IMPORT SUMMARY")
        print(f"{'='*70}")
        print(f"Total rows processed: {kurslar_stats['total'] + tutors_stats['total']}")
        print(f"Total saved to DB: {kurslar_stats['saved'] + tutors_stats['saved']}")
        print(f"Total duplicates: {kurslar_stats['duplicates'] + tutors_stats['duplicates']}")
        print(f"Total invalid phones: {kurslar_stats['invalid_phones'] + tutors_stats['invalid_phones']}")
        print(f"{'='*70}")

    finally:
        importer.close()


if __name__ == "__main__":
    main()
