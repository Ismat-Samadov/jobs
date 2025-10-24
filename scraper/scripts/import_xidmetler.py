"""
Import xidmetler.az CSV file into database
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


class XidmetlerImporter:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, self.database_url)

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

    def import_xidmetler(self, csv_path):
        print(f"\n{'='*70}")
        print(f"Importing XIDMETLER.AZ: {csv_path}")
        print(f"{'='*70}")

        stats = {'total_rows': 0, 'total_phones': 0, 'saved': 0, 'duplicates': 0, 'invalid': 0}

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total_rows'] += 1

                # Get phone number(s) - can be comma-separated
                phone_str = row.get('phone', '').strip()
                if not phone_str:
                    stats['invalid'] += 1
                    continue

                # Split by comma if multiple phones
                phones = [p.strip() for p in phone_str.split(',') if p.strip()]

                for phone in phones:
                    stats['total_phones'] += 1

                    # Build full_data object
                    full_data = {
                        'listing_type': 'service',
                        'listing_id': row.get('id', ''),
                        'listing_code': row.get('listing_code', ''),
                        'title': row.get('title', ''),
                        'price': row.get('price', ''),
                        'contact_name': row.get('contact_name', ''),
                        'location': row.get('location', ''),
                        'date': row.get('date', ''),
                        'categories': row.get('categories', ''),
                        'description': row.get('description', ''),
                        'image_url': row.get('image_url', ''),
                        'images': row.get('images', '').split(', ') if row.get('images') else []
                    }

                    if self.save_to_database(phone, 'xidmetler.az', row.get('url', ''), full_data):
                        stats['saved'] += 1
                    else:
                        if PhoneValidator.validate_phone(phone):
                            stats['duplicates'] += 1
                        else:
                            stats['invalid'] += 1

                # Progress update every 100 rows
                if stats['total_rows'] % 100 == 0:
                    print(f"Processed: {stats['total_rows']} rows | {stats['total_phones']} phones | Saved: {stats['saved']}")

        print(f"\n{'='*70}")
        print("XIDMETLER.AZ IMPORT COMPLETE")
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
    importer = XidmetlerImporter()
    try:
        stats = importer.import_xidmetler('/Users/ismatsamadov/lead_generator/xidmetler_listings.csv')
    finally:
        importer.close()
