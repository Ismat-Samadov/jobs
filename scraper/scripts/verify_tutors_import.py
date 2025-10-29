"""
Verify the imported tutors data
"""
import os
import psycopg2
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('../.env.local')

DATABASE_URL = os.getenv('DATABASE_URL')

def verify_import():
    """Verify the tutors data import"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        print("="*70)
        print("TUTOR DATA VERIFICATION")
        print("="*70)

        # Count by website
        cursor.execute("""
            SELECT website, COUNT(*) as count
            FROM leads.leads
            GROUP BY website
            ORDER BY count DESC
        """)

        print("\nLeads by Website:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]:,}")

        # Sample tutor records
        cursor.execute("""
            SELECT phone_number, website, source, full_data
            FROM leads.leads
            WHERE website = 'repetitor.az'
            LIMIT 3
        """)

        print("\n" + "="*70)
        print("SAMPLE TUTOR RECORDS")
        print("="*70)

        for idx, row in enumerate(cursor.fetchall(), 1):
            phone, website, source, full_data = row
            # full_data is already a dict from psycopg2
            data = full_data if full_data else {}

            print(f"\nRecord #{idx}:")
            print(f"  Phone: {phone}")
            print(f"  Website: {website}")
            print(f"  Source URL: {source[:60]}...")
            print(f"  Name: {data.get('name', 'N/A')}")
            print(f"  City: {data.get('city', 'N/A')}")
            print(f"  Subject: {data.get('subject_taught', 'N/A')}")
            print(f"  Experience: {data.get('experience', 'N/A')}")
            print(f"  Rating: {data.get('rating', 'N/A')}")
            print(f"  Price (online): {data.get('price_online', 'N/A')}")

        # Statistics by subject
        cursor.execute("""
            SELECT
                full_data->>'subject_taught' as subject,
                COUNT(*) as count
            FROM leads.leads
            WHERE website = 'repetitor.az'
            AND full_data->>'subject_taught' IS NOT NULL
            AND full_data->>'subject_taught' != ''
            GROUP BY full_data->>'subject_taught'
            ORDER BY count DESC
            LIMIT 10
        """)

        print("\n" + "="*70)
        print("TOP 10 SUBJECTS TAUGHT")
        print("="*70)
        for row in cursor.fetchall():
            subject, count = row
            print(f"  {subject}: {count:,} tutors")

        # Statistics by city
        cursor.execute("""
            SELECT
                full_data->>'city' as city,
                COUNT(*) as count
            FROM leads.leads
            WHERE website = 'repetitor.az'
            AND full_data->>'city' IS NOT NULL
            AND full_data->>'city' != ''
            GROUP BY full_data->>'city'
            ORDER BY count DESC
            LIMIT 10
        """)

        print("\n" + "="*70)
        print("TOP 10 CITIES")
        print("="*70)
        for row in cursor.fetchall():
            city, count = row
            print(f"  {city}: {count:,} tutors")

        print("\n" + "="*70)

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    verify_import()
