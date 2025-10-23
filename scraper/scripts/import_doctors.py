"""
Import doctors CSV files into database
"""
import csv
import os
import sys
import json
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.validator import PhoneValidator

load_dotenv()


class DoctorsImporter:
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

    def import_uzmandoktorlar(self, csv_path):
        print(f"\n{'='*70}")
        print(f"Importing UZMANDOKTORLAR.AZ: {csv_path}")
        print(f"{'='*70}")

        stats = {'total': 0, 'saved': 0, 'duplicates': 0, 'invalid': 0}

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total'] += 1
                phone = row.get('phone', '').strip()
                if not phone:
                    stats['invalid'] += 1
                    continue

                full_data = {
                    'listing_type': 'doctor',
                    'name': row.get('name', ''),
                    'specialty': row.get('specialty', ''),
                    'location': row.get('location', ''),
                    'hospital': row.get('hospital', ''),
                    'profile_url': row.get('profile_url', ''),
                    'image_url': row.get('image_url', '')
                }

                if self.save_to_database(phone, 'uzmandoktorlar.az', row.get('profile_url', ''), full_data):
                    stats['saved'] += 1
                else:
                    if PhoneValidator.validate_phone(phone):
                        stats['duplicates'] += 1
                    else:
                        stats['invalid'] += 1

        print(f"Total: {stats['total']} | Saved: {stats['saved']} | Duplicates: {stats['duplicates']} | Invalid: {stats['invalid']}")
        return stats

    def import_medportal(self, csv_path):
        print(f"\n{'='*70}")
        print(f"Importing MEDPORTAL.AZ: {csv_path}")
        print(f"{'='*70}")

        stats = {'total': 0, 'saved': 0, 'duplicates': 0, 'invalid': 0}

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total'] += 1
                phone = row.get('phone', '').strip()
                if not phone:
                    stats['invalid'] += 1
                    continue

                full_data = {
                    'listing_type': 'doctor',
                    'name': row.get('name', ''),
                    'specialty': row.get('specialty', ''),
                    'clinic_name': row.get('clinic_name', ''),
                    'working_hours': row.get('working_hours', ''),
                    'detail_url': row.get('detail_url', ''),
                    'image_url': row.get('image_url', ''),
                    'contact_url': row.get('contact_url', '')
                }

                if self.save_to_database(phone, 'medportal.az', row.get('detail_url', ''), full_data):
                    stats['saved'] += 1
                else:
                    if PhoneValidator.validate_phone(phone):
                        stats['duplicates'] += 1
                    else:
                        stats['invalid'] += 1

        print(f"Total: {stats['total']} | Saved: {stats['saved']} | Duplicates: {stats['duplicates']} | Invalid: {stats['invalid']}")
        return stats

    def close(self):
        if self.db_pool:
            self.db_pool.closeall()


if __name__ == "__main__":
    importer = DoctorsImporter()
    try:
        # Import both doctor CSV files
        stats1 = importer.import_uzmandoktorlar('/Users/ismatsamadov/lead_generator/doctors.csv')
        stats2 = importer.import_medportal('/Users/ismatsamadov/lead_generator/doctors_data.csv')

        print(f"\n{'='*70}")
        print("DOCTORS IMPORT SUMMARY")
        print(f"{'='*70}")
        print(f"Total processed: {stats1['total'] + stats2['total']}")
        print(f"Total saved: {stats1['saved'] + stats2['saved']}")
        print(f"Total duplicates: {stats1['duplicates'] + stats2['duplicates']}")
        print(f"Total invalid: {stats1['invalid'] + stats2['invalid']}")
        print(f"{'='*70}")
    finally:
        importer.close()
