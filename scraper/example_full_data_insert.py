"""
Example of how to insert data with full_data JSON column

This script shows how to structure and insert the full listing details
into the new full_data column.
"""

import psycopg2
import json
from datetime import datetime

# Database connection
DATABASE_URL = "postgresql://trakio_db_owner:npg_I8pNtnDu3xRQ@ep-empty-sound-a2batz5g-pooler.eu-central-1.aws.neon.tech/trakio_db?sslmode=require"

def insert_lead_with_full_data():
    """Example: Insert a real estate listing with full details"""

    # Example full_data structure for a real estate listing
    full_data = {
        "listing_type": "real_estate",
        "title": "3 otaqlı mənzil Satılır, Mingəçevir - 59 000 AZN",
        "price": {
            "amount": 59000,
            "currency": "AZN",
            "price_per_sqm": 1204
        },
        "property_details": {
            "property_type": "Yeni tikili",
            "city": "Mingəçevir",
            "location": "Azdres qəs.",
            "document": "Kupça",
            "floor": "1/5",
            "area": "49 m²",
            "rooms": 3,
            "mortgage": "İpotekaya yararlı"
        },
        "description": "Bu mənzil Mingəçevir şəhər Azdres qəsəbəsində Fazil Əzimov 3 mənzil 1 yerləşir.5 mərtəbəli binanın 1-ci mərtəbəsi 2 otağın 3-e keçmə Menzilde kombi sistemi var mətbəx mebeli və kandisaner qalır. Qiymet razılaşma yolu ilə",
        "seller": {
            "name": "Coşqun",
            "type": "Sahibindən"
        },
        "listing_info": {
            "ad_id": "51906",
            "views": 28,
            "date_posted": "2025-09-09",
            "date_updated": "2025-10-21"
        },
        "images": [
            "https://www.evv.az/uploads/auto/bd82368fa6002a6503d5df76d34ab967_thumb6756980.webp",
            "https://www.evv.az/uploads/auto/d0b2f1fbac56d18fee49cb2155d098e4_thumb6756975.webp"
            # ... more images
        ],
        "price_comparison": {
            "market_price": 54800,
            "this_price": 59000,
            "difference": 4200,
            "is_above_market": True
        }
    }

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # Insert with full_data
        query = """
            INSERT INTO leads.leads (phone_number, website, source, full_data)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """

        cur.execute(query, (
            "0505833838",  # phone_number
            "evv.az",      # website
            "https://www.evv.az/3-otaqli-menzil-yeni-tikili-satilir-mingecevir-51906",  # source
            json.dumps(full_data)  # full_data as JSON
        ))

        new_id = cur.fetchone()[0]
        conn.commit()

        print(f"✅ Lead inserted successfully with ID: {new_id}")
        print(f"📦 Full data stored: {json.dumps(full_data, indent=2, ensure_ascii=False)}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        cur.close()
        conn.close()


def example_car_listing():
    """Example: Structure for a car listing"""

    full_data = {
        "listing_type": "car",
        "title": "Mercedes-Benz E-Class 2019",
        "price": {
            "amount": 45000,
            "currency": "AZN"
        },
        "car_details": {
            "make": "Mercedes-Benz",
            "model": "E-Class",
            "year": 2019,
            "mileage": "50,000 km",
            "engine": "2.0L",
            "fuel_type": "Petrol",
            "transmission": "Automatic",
            "color": "Black",
            "condition": "Used"
        },
        "description": "Perfect condition, full service history",
        "seller": {
            "name": "Ali",
            "type": "Dealer"
        },
        "features": [
            "Leather seats",
            "Navigation system",
            "Sunroof",
            "Parking sensors"
        ]
    }

    print("\n🚗 Example car listing structure:")
    print(json.dumps(full_data, indent=2, ensure_ascii=False))


def query_by_full_data():
    """Example: Query leads by JSON data"""

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # Query leads with specific property details
        # Example: Find all 3-room apartments
        query = """
            SELECT id, phone_number, website, source,
                   full_data->>'title' as title,
                   full_data->'property_details'->>'rooms' as rooms
            FROM leads.leads
            WHERE full_data->'property_details'->>'rooms' = '3'
            AND full_data->>'listing_type' = 'real_estate'
            LIMIT 5
        """

        cur.execute(query)
        results = cur.fetchall()

        print("\n🔍 Query results (3-room apartments):")
        for row in results:
            print(f"ID: {row[0]}, Phone: {row[1]}, Title: {row[4]}, Rooms: {row[5]}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("📝 Example: Using full_data JSON column")
    print("=" * 60)

    # Example 1: Insert real estate listing
    # insert_lead_with_full_data()

    # Example 2: Car listing structure
    example_car_listing()

    # Example 3: Query by JSON data
    # query_by_full_data()

    print("\n✨ Examples completed!")
    print("\n💡 Benefits of JSONB:")
    print("  - Store complete listing details in one column")
    print("  - Query specific JSON fields efficiently")
    print("  - Flexible schema for different listing types")
    print("  - GIN index for fast JSON queries")
