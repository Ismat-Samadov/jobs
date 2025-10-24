"""
Import turbo.az CSV file into database
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


class TurboImporter:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, self.database_url)

    def bulk_insert(self, batch):
        """Bulk insert multiple records at once"""
        conn = None
        try:
            conn = self.db_pool.getconn()
            cur = conn.cursor()

            # Use executemany for bulk insert
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

    def save_to_database(self, phone, website, source_url, full_data):
        validated_phone = PhoneValidator.validate_phone(phone)
        if not validated_phone:
            return False

        conn = None
        try:
            conn = self.db_pool.getconn()
            cur = conn.cursor()
            query = """
                INSERT INTO leads.leads (phone_number, website, source, full_data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (phone_number) DO NOTHING
                RETURNING id
            """
            full_data_json = json.dumps(full_data, ensure_ascii=False)
            cur.execute(query, (validated_phone, website, source_url, full_data_json))
            conn.commit()
            result = cur.fetchone()
            cur.close()
            self.db_pool.putconn(conn)
            return True if result else False
        except Exception as e:
            if conn:
                self.db_pool.putconn(conn)
            print(f"DB error: {e}")
            return False

    def import_turbo(self, csv_path):
        print(f"\n{'='*70}")
        print(f"Importing TURBO.AZ: {csv_path}")
        print(f"{'='*70}")

        stats = {'total_rows': 0, 'total_phones': 0, 'saved': 0, 'duplicates': 0, 'invalid': 0}

        # Batch insert for speed
        batch = []
        batch_size = 500

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total_rows'] += 1

                # Get phone number
                phone = row.get('phone', '').strip()
                if not phone:
                    stats['invalid'] += 1
                    continue

                validated_phone = PhoneValidator.validate_phone(phone)
                if not validated_phone:
                    stats['invalid'] += 1
                    continue

                stats['total_phones'] += 1

                # Build full_data object
                full_data = {
                    'listing_type': 'car',
                    'listing_id': row.get('id', ''),
                    'title': row.get('title', ''),
                    'price': row.get('price', ''),
                    'city': row.get('city', ''),
                    'brand': row.get('brand', ''),
                    'model': row.get('model', ''),
                    'year': row.get('year', ''),
                    'body_type': row.get('body_type', ''),
                    'color': row.get('color', ''),
                    'engine': row.get('engine', ''),
                    'mileage': row.get('mileage', ''),
                    'transmission': row.get('transmission', ''),
                    'gear': row.get('gear', ''),
                    'is_new': row.get('is_new', ''),
                    'seats': row.get('seats', ''),
                    'condition': row.get('condition', ''),
                    'description': row.get('description', ''),
                    'extras': row.get('extras', ''),
                    'owner_name': row.get('owner_name', ''),
                    'owner_region': row.get('owner_region', ''),
                    'updated_date': row.get('updated_date', ''),
                    'view_count': row.get('view_count', ''),
                    'images': row.get('images', '').split(', ') if row.get('images') else [],
                    'labels': row.get('labels', '')
                }

                batch.append((validated_phone, 'turbo.az', row.get('url', ''), json.dumps(full_data, ensure_ascii=False)))

                # Insert batch when it reaches batch_size
                if len(batch) >= batch_size:
                    inserted = self.bulk_insert(batch)
                    stats['saved'] += inserted
                    stats['duplicates'] += (len(batch) - inserted)
                    batch = []
                    print(f"Processed: {stats['total_rows']} rows | Saved: {stats['saved']} | Duplicates: {stats['duplicates']}", flush=True)

            # Insert remaining batch
            if batch:
                inserted = self.bulk_insert(batch)
                stats['saved'] += inserted
                stats['duplicates'] += (len(batch) - inserted)
                batch = []

        print(f"\n{'='*70}")
        print("TURBO.AZ IMPORT COMPLETE")
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
    importer = TurboImporter()
    try:
        stats = importer.import_turbo('/Users/ismatsamadov/lead_generator/turbo_listings_async.csv')
    finally:
        importer.close()
