"""
Test the sources API query to see if repetitor.az is included
"""
import os
import psycopg2
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('../.env.local')

DATABASE_URL = os.getenv('DATABASE_URL')

def test_sources_api():
    """Test the exact query used by /api/sources/route.ts"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        # This is the EXACT query from /api/sources/route.ts
        cursor.execute("""
            SELECT DISTINCT website as source
            FROM leads.leads
            WHERE website IS NOT NULL
            ORDER BY website
        """)

        sources = [row[0] for row in cursor.fetchall()]

        print("Sources returned by API query:")
        print(json.dumps({"sources": sources}, indent=2))

        print(f"\nTotal sources: {len(sources)}")
        print(f"\nDoes it include repetitor.az? {('repetitor.az' in sources)}")

        if 'repetitor.az' in sources:
            print("✅ repetitor.az IS in the sources list!")
        else:
            print("❌ repetitor.az is NOT in the sources list!")

        # Double-check the database
        cursor.execute("SELECT COUNT(*) FROM leads.leads WHERE website = 'repetitor.az'")
        count = cursor.fetchone()[0]
        print(f"\nRecords with website='repetitor.az' in database: {count:,}")

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    test_sources_api()
