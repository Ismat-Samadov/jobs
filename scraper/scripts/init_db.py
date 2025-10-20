import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def init_database():
    """Initialize the database schema and tables"""
    DATABASE_URL = os.getenv('DATABASE_URL')

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in .env file")

    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Read and execute schema.sql (in same directory as this script)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(script_dir, 'schema.sql')

        with open(schema_path, 'r') as f:
            schema = f.read()
            cur.execute(schema)

        conn.commit()
        print("✓ Database schema and tables created successfully!")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        raise

if __name__ == "__main__":
    init_database()
