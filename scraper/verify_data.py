"""
Verify that full_data is correctly populated in the database
"""
import psycopg2
from dotenv import load_dotenv
import os
import json

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Get the latest lead with full_data
cur.execute("""
    SELECT phone_number, website, source, full_data
    FROM leads.leads
    WHERE full_data IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 1
""")

result = cur.fetchone()

if result:
    phone, website, source, full_data = result

    print("=" * 70)
    print("LATEST LEAD WITH FULL_DATA")
    print("=" * 70)
    print(f"Phone: {phone}")
    print(f"Website: {website}")
    print(f"Source: {source}")
    print("\nFull Data JSON:")
    print("=" * 70)
    print(json.dumps(full_data, indent=2, ensure_ascii=False))
    print("=" * 70)

    # Validate structure
    print("\n✓ Structure Validation:")
    print(f"  - listing_type: {full_data.get('listing_type', 'MISSING')}")
    print(f"  - title: {full_data.get('title', 'MISSING')[:60]}...")
    print(f"  - price: {full_data.get('price', 'MISSING')}")
    print(f"  - property_details: {len(full_data.get('property_details', {}))} fields - {list(full_data.get('property_details', {}).keys())}")
    print(f"  - description: {len(full_data.get('description', ''))} chars")
    print(f"  - seller: {full_data.get('seller', 'MISSING')}")
    print(f"  - listing_info: {full_data.get('listing_info', 'MISSING')}")
    print(f"  - images: {len(full_data.get('images', []))} images")
else:
    print("No leads with full_data found!")

cur.close()
conn.close()
