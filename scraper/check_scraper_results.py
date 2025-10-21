"""
Check scraper results in the database
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=" * 70)
print("SCRAPER RESULTS SUMMARY")
print("=" * 70)

# Total leads by website
cur.execute("""
    SELECT website, COUNT(*) as total
    FROM leads.leads
    GROUP BY website
    ORDER BY total DESC
""")

print("\nTotal Leads by Website:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Leads with full_data by website
cur.execute("""
    SELECT website, COUNT(*) as total
    FROM leads.leads
    WHERE full_data IS NOT NULL
    GROUP BY website
    ORDER BY total DESC
""")

print("\nLeads with full_data by Website:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Recent leads added (last 10 minutes)
cur.execute("""
    SELECT website, COUNT(*) as total
    FROM leads.leads
    WHERE created_at > NOW() - INTERVAL '10 minutes'
    GROUP BY website
    ORDER BY total DESC
""")

print("\nLeads added in last 10 minutes:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Sample of latest EVV.AZ lead
cur.execute("""
    SELECT phone_number, full_data->>'title' as title, full_data->'price'->>'amount' as price
    FROM leads.leads
    WHERE website = 'evv.az' AND full_data IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 3
""")

print("\nLatest EVV.AZ leads:")
for row in cur.fetchall():
    print(f"  Phone: {row[0]}, Title: {row[1][:60]}..., Price: {row[2]} AZN")

# Sample of latest Villa.AZ lead
cur.execute("""
    SELECT phone_number, full_data->>'title' as title, full_data->'price'->>'amount' as price
    FROM leads.leads
    WHERE website = 'villa.az' AND full_data IS NOT NULL
    ORDER BY created_at DESC
    LIMIT 3
""")

print("\nLatest Villa.AZ leads:")
for row in cur.fetchall():
    print(f"  Phone: {row[0]}, Title: {row[1][:60]}..., Price: {row[2]} AZN")

print("\n" + "=" * 70)

cur.close()
conn.close()
