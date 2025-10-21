"""
Check which fields have null/empty values across multiple records
"""
import psycopg2
from dotenv import load_dotenv
import os
import json
from collections import defaultdict

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Get 10 most recent leads with full_data
cur.execute("""
    SELECT phone_number, full_data
    FROM leads.leads
    WHERE full_data IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 10
""")

results = cur.fetchall()

# Track which fields are null/empty
null_counts = defaultdict(int)
total_records = len(results)

print(f"Analyzing {total_records} records...\n")

for phone, full_data in results:
    # Check each top-level field
    if not full_data.get('title'):
        null_counts['title'] += 1

    if not full_data.get('description'):
        null_counts['description'] += 1

    if not full_data.get('price') or not full_data['price'].get('amount'):
        null_counts['price.amount'] += 1

    if not full_data.get('price') or not full_data['price'].get('price_per_sqm'):
        null_counts['price.price_per_sqm'] += 1

    if not full_data.get('property_details'):
        null_counts['property_details (all)'] += 1
    else:
        pd = full_data.get('property_details', {})
        if not pd.get('city'):
            null_counts['property_details.city'] += 1
        if not pd.get('property_type'):
            null_counts['property_details.property_type'] += 1
        if not pd.get('area'):
            null_counts['property_details.area'] += 1
        if not pd.get('floor'):
            null_counts['property_details.floor'] += 1
        if not pd.get('rooms'):
            null_counts['property_details.rooms'] += 1
        if not pd.get('document'):
            null_counts['property_details.document'] += 1

    if not full_data.get('seller') or not full_data['seller'].get('name'):
        null_counts['seller.name'] += 1

    if not full_data.get('seller') or not full_data['seller'].get('type'):
        null_counts['seller.type'] += 1

    if not full_data.get('listing_info') or not full_data['listing_info'].get('ad_id'):
        null_counts['listing_info.ad_id'] += 1

    if not full_data.get('images') or len(full_data['images']) == 0:
        null_counts['images'] += 1

print("=" * 70)
print("NULL/EMPTY FIELDS REPORT")
print("=" * 70)

if null_counts:
    for field, count in sorted(null_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_records) * 100
        print(f"  {field}: {count}/{total_records} ({percentage:.1f}%) records missing")
else:
    print("  ✓ All fields populated in all records!")

print("=" * 70)

# Show one complete example
print("\nSample complete record:")
print("=" * 70)
phone, full_data = results[0]
print(f"Phone: {phone}")
print(json.dumps(full_data, indent=2, ensure_ascii=False))

cur.close()
conn.close()
