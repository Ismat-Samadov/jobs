"""
Import kurstap_courses.csv into database with bulk insert
"""
import csv
import os
import sys
import json
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.validator import PhoneValidator

load_dotenv()


class KurstapImporter:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, self.database_url)

    def bulk_insert(self, batch):
        """Bulk insert multiple records at once"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cur = conn.cursor()

            query = """
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (phone_number) DO NOTHING
            """

            cur.executemany(query, batch)
            inserted = cur.rowcount
            conn.commit()
            cur.close()
            self.db_pool.putconn(conn)
            return inserted
        except Exception as e:
            if conn:
                conn.rollback()
                self.db_pool.putconn(conn)
            print(f"DB error: {e}")
            return 0

    def import_kurstap(self, csv_path):
        print(f"\n{'='*70}")
        print(f"Importing KURSTAP.AZ: {csv_path}")
        print(f"{'='*70}")

        stats = {'total_rows': 0, 'total_phones': 0, 'saved': 0, 'duplicates': 0, 'invalid': 0}

        # Batch insert for speed
        batch = []
        batch_size = 500

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total_rows'] += 1

                # Get phone numbers (can be comma-separated)
                phone_str = row.get('phone_numbers', '').strip()
                if not phone_str:
                    stats['invalid'] += 1
                    continue

                # Split by comma if multiple phones
                phones = [p.strip() for p in phone_str.split(',') if p.strip()]

                for phone in phones:
                    stats['total_phones'] += 1

                    validated_phone = PhoneValidator.validate_phone(phone)
                    if not validated_phone:
                        stats['invalid'] += 1
                        continue

                    # Build full_data object
                    full_data = {
                        'listing_type': 'course',
                        'course_id': row.get('course_id', ''),
                        'institution_name': row.get('institution_name', ''),
                        'course_title': row.get('course_title', ''),
                        'duration': row.get('duration', ''),
                        'price': row.get('price', ''),
                        'location': row.get('location', ''),
                        'emails': row.get('emails', ''),
                        'address': row.get('address', ''),
                        'website': row.get('website', '')
                    }

                    batch.append((validated_phone, 'kurstap.az', row.get('url', ''), json.dumps(full_data, ensure_ascii=False)))

                    # Insert batch when it reaches batch_size
                    if len(batch) >= batch_size:
                        inserted = self.bulk_insert(batch)
                        stats['saved'] += inserted
                        stats['duplicates'] += (len(batch) - inserted)
                        batch = []
                        print(f"Processed: {stats['total_rows']} rows | Phones: {stats['total_phones']} | Saved: {stats['saved']}", flush=True)

            # Insert remaining batch
            if batch:
                inserted = self.bulk_insert(batch)
                stats['saved'] += inserted
                stats['duplicates'] += (len(batch) - inserted)
                batch = []

        print(f"\n{'='*70}")
        print("KURSTAP.AZ IMPORT COMPLETE")
        print(f"{'='*70}")
        print(f"Total rows: {stats['total_rows']}")
        print(f"Total phones: {stats['total_phones']}")
        print(f"Saved: {stats['saved']}")
        print(f"Duplicates: {stats['duplicates']}")
        print(f"Invalid: {stats['invalid']}")
        print(f"{'='*70}")
        return stats

    def close(self):
        if self.db_pool:
            self.db_pool.closeall()


if __name__ == "__main__":
    importer = KurstapImporter()
    try:
        stats = importer.import_kurstap('/Users/ismatsamadov/lead_generator/scraper/backup_removed_files/phone/2025/kurstap_courses.csv')
    finally:
        importer.close()
