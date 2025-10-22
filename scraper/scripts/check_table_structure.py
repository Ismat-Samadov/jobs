import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('../.env.local')

DATABASE_URL = os.getenv('DATABASE_URL')

def check_table_structure():
    """Check the structure of the leads.leads table"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        # Get table structure
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'leads' AND table_name = 'leads'
            ORDER BY ordinal_position
        """)

        print("Columns in leads.leads table:")
        for row in cursor.fetchall():
            col_name, data_type, max_len, nullable = row
            max_len_str = f"({max_len})" if max_len else ""
            print(f"  {col_name}: {data_type}{max_len_str} (nullable: {nullable})")

        # Check a sample record
        cursor.execute("SELECT * FROM leads.leads LIMIT 1")
        if cursor.rowcount > 0:
            columns = [desc[0] for desc in cursor.description]
            print(f"\nSample record columns: {columns}")
            sample = cursor.fetchone()
            if sample and len(columns) > 3:
                print(f"Sample data has {len(columns)} columns")

        # Count total records
        cursor.execute("SELECT COUNT(*) FROM leads.leads")
        count = cursor.fetchone()[0]
        print(f"\nTotal leads in database: {count:,}")

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    check_table_structure()
