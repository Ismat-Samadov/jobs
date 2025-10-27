"""
Fast Bulk CSV Import Script
Imports CSV files to PostgreSQL database using batch inserts (300-400 records at once)
"""
import csv
import json
import psycopg2
from psycopg2.extras import execute_values
import sys
import os
from datetime import datetime
import re

# Add scraper scripts to path for validator
sys.path.append('/Users/ismatsamadov/lead_generator/scraper/scripts')
from validator import PhoneValidator

# Database connection from environment
from dotenv import load_dotenv
load_dotenv('.env.local')
DATABASE_URL = os.getenv('DATABASE_URL')

# Batch size for bulk inserts
BATCH_SIZE = 350


def extract_phones_from_cell(phone_cell):
    """Extract multiple phone numbers from a single cell"""
    if not phone_cell or not phone_cell.strip():
        return []

    phone_cell = phone_cell.strip()
    phone_candidates = []

    # Split by common separators
    for separator in [',', '/', ';', '|']:
        if separator in phone_cell:
            phone_candidates = [p.strip() for p in phone_cell.split(separator)]
            break

    # If no separators found, check for multiple phone patterns
    if not phone_candidates:
        phone_patterns = re.findall(r'[\d\(\)\-\+\s]{10,}', phone_cell)
        if len(phone_patterns) > 1:
            phone_candidates = phone_patterns
        else:
            phone_candidates = [phone_cell]

    return phone_candidates


def process_csv_file(file_path, phone_column, website_name, source_column=None):
    """
    Process CSV file and prepare data for bulk insert

    Returns: list of tuples (phone_number, website, source, full_data_json)
    """
    print(f"\n📂 Processing: {os.path.basename(file_path)}")

    records = []
    stats = {
        'total_rows': 0,
        'valid_phones': 0,
        'invalid_phones': 0,
        'empty_phones': 0,
        'multi_phone_rows': 0
    }

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        stats['total_rows'] = len(rows)

        for idx, row in enumerate(rows, 1):
            # Get phone cell
            phone_cell = row.get(phone_column, '').strip()

            if not phone_cell:
                stats['empty_phones'] += 1
                continue

            # Extract all phones from cell
            phone_candidates = extract_phones_from_cell(phone_cell)

            if len(phone_candidates) > 1:
                stats['multi_phone_rows'] += 1

            # Get source URL
            if source_column and row.get(source_column):
                source_url = row.get(source_column)
            else:
                # Generate a source identifier
                company = row.get('company') or row.get('store_name') or ''
                source_url = f"{website_name}/{company.replace(' ', '_').lower()}_{idx}"

            # Prepare full_data JSON (all CSV columns)
            full_data = dict(row)
            full_data['csv_row_number'] = idx
            full_data['import_timestamp'] = datetime.now().isoformat()

            # Validate and add each phone
            for phone in phone_candidates:
                validated_phone = PhoneValidator.validate_phone(phone)

                if validated_phone:
                    stats['valid_phones'] += 1

                    # Prepare record as tuple
                    full_data_json = json.dumps(full_data, ensure_ascii=False)
                    records.append((
                        validated_phone,
                        website_name,
                        source_url,
                        full_data_json
                    ))
                else:
                    stats['invalid_phones'] += 1

    print(f"   ✓ Processed {stats['total_rows']} rows")
    print(f"   ✓ Valid phones: {stats['valid_phones']}")
    print(f"   ✗ Invalid phones: {stats['invalid_phones']}")
    print(f"   ∅ Empty phones: {stats['empty_phones']}")
    print(f"   ⚡ Multi-phone rows: {stats['multi_phone_rows']}")
    print(f"   → Prepared {len(records)} database records")

    return records, stats


def bulk_insert_records(records, batch_size=BATCH_SIZE):
    """
    Bulk insert records using execute_values for maximum performance
    """
    if not records:
        print("⚠️  No records to insert")
        return 0, 0

    # Deduplicate records by phone_number (keep last occurrence)
    print(f"\n🔍 Deduplicating records...")
    phone_map = {}
    for record in records:
        phone_number = record[0]
        phone_map[phone_number] = record  # Last occurrence wins

    unique_records = list(phone_map.values())
    duplicates_removed = len(records) - len(unique_records)

    if duplicates_removed > 0:
        print(f"   ✓ Removed {duplicates_removed} duplicate phones from batch")

    print(f"\n💾 Starting bulk insert...")
    print(f"   Total records: {len(unique_records)}")
    print(f"   Batch size: {batch_size}")

    conn = None
    inserted = 0
    updated = 0

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Prepare the UPSERT query
        insert_query = """
            INSERT INTO leads.leads (phone_number, website, source, full_data)
            VALUES %s
            ON CONFLICT (phone_number)
            DO UPDATE SET
                source = EXCLUDED.source,
                full_data = EXCLUDED.full_data,
                website = EXCLUDED.website
            RETURNING (xmax = 0) AS inserted
        """

        # Process in batches
        total_batches = (len(unique_records) + batch_size - 1) // batch_size

        for i in range(0, len(unique_records), batch_size):
            batch = unique_records[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            print(f"   📦 Batch {batch_num}/{total_batches}: Inserting {len(batch)} records...", end='', flush=True)

            # Execute bulk insert
            result = execute_values(
                cur,
                insert_query,
                batch,
                template=None,
                page_size=len(batch),
                fetch=True
            )

            # Count inserts vs updates
            batch_inserted = sum(1 for row in result if row[0])
            batch_updated = len(batch) - batch_inserted

            inserted += batch_inserted
            updated += batch_updated

            print(f" ✓ ({batch_inserted} new, {batch_updated} updated)")

        # Commit all changes
        conn.commit()
        print(f"\n✅ Bulk insert completed!")
        print(f"   ✨ New records: {inserted}")
        print(f"   🔄 Updated records: {updated}")
        print(f"   📊 Total processed: {inserted + updated}")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n❌ Error during bulk insert: {e}")
        raise

    finally:
        if conn:
            cur.close()
            conn.close()

    return inserted, updated


def main():
    """Main import function"""
    print("\n" + "="*80)
    print("BULK CSV IMPORT TO DATABASE")
    print("="*80)

    # Check database connection
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment!")
        print("   Please set it in .env.local file")
        return

    print(f"🔗 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")
    print(f"⚡ Batch size: {BATCH_SIZE} records per batch")

    # Define CSV configurations
    csv_configs = [
        {
            'file': '/Users/ismatsamadov/lead_generator/tap_az_shops.csv',
            'phone_column': 'phone',
            'website': 'tap.az',
            'source_column': None  # Will generate source from company name
        },
        {
            'file': '/Users/ismatsamadov/lead_generator/umico_stores.csv',
            'phone_column': 'phone_numbers',
            'website': 'umico.az',
            'source_column': 'website'  # Use website column as source
        },
        {
            'file': '/Users/ismatsamadov/lead_generator/mymarket_stores.csv',
            'phone_column': 'phone',
            'website': 'mymarket.az',
            'source_column': 'store_url'  # Use store_url as source
        }
    ]

    # Process all CSV files
    all_records = []
    total_stats = {
        'total_rows': 0,
        'valid_phones': 0,
        'invalid_phones': 0,
        'empty_phones': 0
    }

    start_time = datetime.now()

    for config in csv_configs:
        records, stats = process_csv_file(
            config['file'],
            config['phone_column'],
            config['website'],
            config.get('source_column')
        )

        all_records.extend(records)
        total_stats['total_rows'] += stats['total_rows']
        total_stats['valid_phones'] += stats['valid_phones']
        total_stats['invalid_phones'] += stats['invalid_phones']
        total_stats['empty_phones'] += stats['empty_phones']

    processing_time = (datetime.now() - start_time).total_seconds()

    print(f"\n{'='*80}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*80}")
    print(f"📁 CSV files processed: {len(csv_configs)}")
    print(f"📊 Total CSV rows: {total_stats['total_rows']}")
    print(f"✅ Valid phones: {total_stats['valid_phones']}")
    print(f"❌ Invalid phones: {total_stats['invalid_phones']}")
    print(f"∅ Empty phones: {total_stats['empty_phones']}")
    print(f"📦 Records ready for insert: {len(all_records)}")
    print(f"⏱️  Processing time: {processing_time:.2f}s")

    # Bulk insert
    if all_records:
        insert_start = datetime.now()
        inserted, updated = bulk_insert_records(all_records, batch_size=BATCH_SIZE)
        insert_time = (datetime.now() - insert_start).total_seconds()

        total_time = (datetime.now() - start_time).total_seconds()

        print(f"\n{'='*80}")
        print(f"FINAL RESULTS")
        print(f"{'='*80}")
        print(f"✨ New leads added: {inserted}")
        print(f"🔄 Existing leads updated: {updated}")
        print(f"📊 Total database operations: {inserted + updated}")
        print(f"⏱️  Total execution time: {total_time:.2f}s")
        print(f"🚀 Import speed: {len(all_records)/total_time:.0f} records/second")
        print(f"\n{'='*80}\n")
    else:
        print("\n⚠️  No valid records to import!")


if __name__ == "__main__":
    main()
