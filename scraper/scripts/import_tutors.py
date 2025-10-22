"""
Import tutors data from CSV into the leads database
"""
import os
import csv
import json
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv('.env.local')
load_dotenv('../.env.local')

DATABASE_URL = os.getenv('DATABASE_URL')

# Determine the correct path to the CSV file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, '.backup_removed_files/phone/2025/tutors_data.csv')

def clean_phone_number(phone):
    """
    Clean and validate Azerbaijan phone numbers
    Returns 9-digit format or None if invalid
    """
    if not phone:
        return None

    # Remove all non-numeric characters
    phone = re.sub(r'\D', '', phone)

    # Take last 9 digits
    if len(phone) >= 9:
        phone = phone[-9:]
    else:
        return None

    # Validate Azerbaijan phone number format
    # Valid operator prefixes: 10, 50, 51, 55, 60, 70, 77, 99
    valid_prefixes = ['10', '50', '51', '55', '60', '70', '77', '99']
    prefix = phone[:2]

    if prefix not in valid_prefixes:
        return None

    # Third digit cannot be 0 or 1
    if phone[2] in ['0', '1']:
        return None

    return phone


def import_tutors_data():
    """Import tutors data from CSV into leads table"""

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    total_rows = 0
    valid_phones = 0
    invalid_phones = 0
    duplicate_phones = 0
    inserted = 0

    try:
        with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            # Prepare batch insert
            batch_data = []

            for row in reader:
                total_rows += 1

                # Clean phone number
                phone = clean_phone_number(row.get('phone', ''))

                if not phone:
                    invalid_phones += 1
                    continue

                valid_phones += 1

                # Prepare full_data JSONB
                full_data = {
                    'tutor_id': row.get('id', ''),
                    'name': row.get('name', ''),
                    'url': row.get('url', ''),
                    'phone': row.get('phone', ''),  # Original format
                    'rating': row.get('rating', ''),
                    'age': row.get('age', ''),
                    'experience': row.get('experience', ''),
                    'city': row.get('city', ''),
                    'teaching_language': row.get('teaching_language', ''),
                    'teaching_format': row.get('teaching_format', ''),
                    'subject_category': row.get('subject_category', ''),
                    'subject_name': row.get('subject_name', ''),
                    'reviews_count': row.get('reviews_count', ''),
                    'description': row.get('description', ''),
                    'subject_taught': row.get('subject_taught', ''),
                    'price_teacher_location': row.get('price_teacher_location', ''),
                    'price_student_location': row.get('price_student_location', ''),
                    'price_online': row.get('price_online', ''),
                    'education_year': row.get('education_year', ''),
                    'education_institution': row.get('education_institution', ''),
                    'education_specialty': row.get('education_specialty', ''),
                    'source_type': 'tutors'  # Mark as tutors data
                }

                batch_data.append((
                    phone,
                    'repetitor.az',
                    row.get('url', ''),
                    json.dumps(full_data, ensure_ascii=False)
                ))

                # Insert in batches of 1000
                if len(batch_data) >= 1000:
                    try:
                        execute_batch(
                            cursor,
                            """
                            INSERT INTO leads.leads (phone_number, website, source, full_data)
                            VALUES (%s, %s, %s, %s::jsonb)
                            ON CONFLICT (phone_number) DO NOTHING
                            """,
                            batch_data
                        )
                        inserted += len(batch_data)
                        conn.commit()
                        print(f"Inserted batch: {inserted} records so far...")
                        batch_data = []
                    except Exception as e:
                        print(f"Error inserting batch: {e}")
                        conn.rollback()
                        batch_data = []

            # Insert remaining records
            if batch_data:
                try:
                    # Get initial count
                    cursor.execute("SELECT COUNT(*) FROM leads.leads")
                    count_before = cursor.fetchone()[0]

                    execute_batch(
                        cursor,
                        """
                        INSERT INTO leads.leads (phone_number, website, source, full_data)
                        VALUES (%s, %s, %s, %s::jsonb)
                        ON CONFLICT (phone_number) DO NOTHING
                        """,
                        batch_data
                    )
                    conn.commit()

                    # Get final count
                    cursor.execute("SELECT COUNT(*) FROM leads.leads")
                    count_after = cursor.fetchone()[0]

                    actually_inserted = count_after - count_before
                    inserted += actually_inserted
                    duplicate_phones += (len(batch_data) - actually_inserted)

                    print(f"Inserted final batch: {actually_inserted} new records")
                except Exception as e:
                    print(f"Error inserting final batch: {e}")
                    conn.rollback()

        # Print summary
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Total rows in CSV:        {total_rows:,}")
        print(f"Valid phone numbers:      {valid_phones:,}")
        print(f"Invalid phone numbers:    {invalid_phones:,}")
        print(f"Successfully inserted:    {inserted:,}")
        print(f"Duplicate phones skipped: {duplicate_phones:,}")
        print("="*60)

        # Check total leads count
        cursor.execute("SELECT COUNT(*) FROM leads.leads")
        total_leads = cursor.fetchone()[0]
        print(f"Total leads in database:  {total_leads:,}")

        # Check repetitor.az count
        cursor.execute("SELECT COUNT(*) FROM leads.leads WHERE website = 'repetitor.az'")
        tutor_leads = cursor.fetchone()[0]
        print(f"Tutor leads (repetitor.az): {tutor_leads:,}")
        print("="*60)

    except FileNotFoundError:
        print(f"Error: CSV file not found: {CSV_FILE}")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    print("Starting tutors data import...")
    print(f"CSV file: {CSV_FILE}")
    print(f"Database: {DATABASE_URL[:50]}...")
    print()

    import_tutors_data()
