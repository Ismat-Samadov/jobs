"""
Check if tutors were inserted as repetitor.az or unknown
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('../.env.local')

DATABASE_URL = os.getenv('DATABASE_URL')

def check_tutor_source():
    """Check the source/website field for imported tutors"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        # Check records with source_type = 'tutors' in full_data
        cursor.execute("""
            SELECT website, COUNT(*) as count
            FROM leads.leads
            WHERE full_data->>'source_type' = 'tutors'
            GROUP BY website
            ORDER BY count DESC
        """)

        print("="*70)
        print("TUTOR RECORDS BY WEBSITE (filtered by source_type='tutors')")
        print("="*70)
        results = cursor.fetchall()

        if results:
            for row in results:
                website, count = row
                print(f"  {website}: {count:,} records")
        else:
            print("  No records found with source_type='tutors'")

        # Check records from repetitor.az domain in source URL
        cursor.execute("""
            SELECT website, COUNT(*) as count
            FROM leads.leads
            WHERE source LIKE '%repetitor.az%'
            GROUP BY website
            ORDER BY count DESC
        """)

        print("\n" + "="*70)
        print("RECORDS WITH 'repetitor.az' IN SOURCE URL")
        print("="*70)
        results = cursor.fetchall()

        for row in results:
            website, count = row
            print(f"  {website}: {count:,} records")

        # Sample records to verify
        cursor.execute("""
            SELECT phone_number, website, source, full_data->>'source_type', full_data->>'name'
            FROM leads.leads
            WHERE source LIKE '%repetitor.az%'
            LIMIT 5
        """)

        print("\n" + "="*70)
        print("SAMPLE RECORDS WITH repetitor.az IN SOURCE URL")
        print("="*70)
        for row in cursor.fetchall():
            phone, website, source, source_type, name = row
            print(f"\n  Phone: {phone}")
            print(f"  Website field: {website}")
            print(f"  Source URL: {source[:60]}...")
            print(f"  Source type: {source_type}")
            print(f"  Name: {name}")

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    check_tutor_source()
