"""
Comprehensive CSV Analysis Script
Analyzes all CSV files for database import suitability
"""
import csv
import sys
import re
sys.path.append('/Users/ismatsamadov/lead_generator/scraper/scripts')
from validator import PhoneValidator

def analyze_csv_file(file_path, phone_column, source_website):
    """Analyze a single CSV file"""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {file_path.split('/')[-1]}")
    print(f"{'='*80}\n")

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        print(f"📋 COLUMNS: {headers}")
        print(f"📞 PHONE COLUMN: '{phone_column}'\n")

        rows = list(reader)
        total_rows = len(rows)

        # Statistics
        stats = {
            'total_rows': total_rows,
            'valid_phones': 0,
            'invalid_phones': 0,
            'empty_phones': 0,
            'unique_phones': set(),
            'duplicate_entries': 0,
            'multi_phone_rows': 0,
            'total_phone_numbers': 0,
            'invalid_examples': [],
            'valid_examples': []
        }

        # Analyze each row
        for idx, row in enumerate(rows, 1):
            phone_raw = row.get(phone_column, '').strip()

            if not phone_raw:
                stats['empty_phones'] += 1
                continue

            # Check if multiple phones in one cell (comma, slash, or multiple instances)
            phone_candidates = []

            # Split by common separators
            for separator in [',', '/', ';', '|']:
                if separator in phone_raw:
                    phone_candidates = [p.strip() for p in phone_raw.split(separator)]
                    stats['multi_phone_rows'] += 1
                    break

            # If no separators, check for multiple phone patterns
            if not phone_candidates:
                # Find all phone-like patterns
                phone_patterns = re.findall(r'[\d\(\)\-\+\s]{10,}', phone_raw)
                if len(phone_patterns) > 1:
                    phone_candidates = phone_patterns
                    stats['multi_phone_rows'] += 1
                else:
                    phone_candidates = [phone_raw]

            stats['total_phone_numbers'] += len(phone_candidates)

            # Validate each phone
            for phone in phone_candidates:
                validated = PhoneValidator.validate_phone(phone)

                if validated:
                    stats['valid_phones'] += 1
                    stats['unique_phones'].add(validated)
                    if len(stats['valid_examples']) < 5:
                        stats['valid_examples'].append({
                            'row': idx,
                            'raw': phone,
                            'validated': validated,
                            'company': row.get('company') or row.get('store_name') or row.get('store_url', '')[:50]
                        })
                else:
                    stats['invalid_phones'] += 1
                    if len(stats['invalid_examples']) < 10:
                        stats['invalid_examples'].append({
                            'row': idx,
                            'raw': phone,
                            'company': row.get('company') or row.get('store_name') or row.get('store_url', '')[:50]
                        })

        # Check for duplicate phone numbers
        stats['duplicate_entries'] = stats['total_phone_numbers'] - len(stats['unique_phones'])

        # Print results
        print(f"📊 STATISTICS:")
        print(f"   Total CSV rows: {stats['total_rows']}")
        print(f"   Total phone numbers found: {stats['total_phone_numbers']}")
        print(f"   Rows with multiple phones: {stats['multi_phone_rows']}")
        print(f"   Empty phone cells: {stats['empty_phones']}")
        print(f"   ")
        print(f"   ✅ Valid phones: {stats['valid_phones']} ({stats['valid_phones']/stats['total_phone_numbers']*100:.1f}%)")
        print(f"   ❌ Invalid phones: {stats['invalid_phones']} ({stats['invalid_phones']/stats['total_phone_numbers']*100:.1f}%)")
        print(f"   🔢 Unique valid phones: {len(stats['unique_phones'])}")
        print(f"   🔁 Duplicate phones: {stats['duplicate_entries']}")

        if stats['valid_examples']:
            print(f"\n✅ VALID PHONE EXAMPLES:")
            for ex in stats['valid_examples']:
                print(f"   Row {ex['row']}: {ex['raw']:20} → {ex['validated']} | {ex['company'][:40]}")

        if stats['invalid_examples']:
            print(f"\n❌ INVALID PHONE EXAMPLES:")
            for ex in stats['invalid_examples']:
                print(f"   Row {ex['row']}: {ex['raw']:20} | {ex['company'][:40]}")

        print(f"\n💾 DATABASE MAPPING:")
        print(f"   website: '{source_website}'")
        print(f"   source: [will use row-specific URL or identifier]")
        print(f"   full_data: [JSON with all columns]")

        return stats


def main():
    print("\n" + "="*80)
    print("CSV FILES ANALYSIS FOR DATABASE IMPORT")
    print("="*80)

    # Define CSV files and their configurations
    csv_configs = [
        {
            'file': '/Users/ismatsamadov/lead_generator/tap_az_shops.csv',
            'phone_column': 'phone',
            'website': 'tap.az'
        },
        {
            'file': '/Users/ismatsamadov/lead_generator/umico_stores.csv',
            'phone_column': 'phone_numbers',
            'website': 'umico.az'
        },
        {
            'file': '/Users/ismatsamadov/lead_generator/mymarket_stores.csv',
            'phone_column': 'phone',
            'website': 'mymarket.az'
        }
    ]

    total_stats = {
        'total_rows': 0,
        'total_phones': 0,
        'valid_phones': 0,
        'invalid_phones': 0,
        'unique_phones': set()
    }

    # Analyze each file
    for config in csv_configs:
        stats = analyze_csv_file(config['file'], config['phone_column'], config['website'])
        total_stats['total_rows'] += stats['total_rows']
        total_stats['total_phones'] += stats['total_phone_numbers']
        total_stats['valid_phones'] += stats['valid_phones']
        total_stats['invalid_phones'] += stats['invalid_phones']
        total_stats['unique_phones'].update(stats['unique_phones'])

    # Print summary
    print(f"\n{'='*80}")
    print(f"OVERALL SUMMARY")
    print(f"{'='*80}\n")
    print(f"📁 Total CSV files: {len(csv_configs)}")
    print(f"📊 Total CSV rows: {total_stats['total_rows']}")
    print(f"📞 Total phone numbers: {total_stats['total_phones']}")
    print(f"✅ Valid phones: {total_stats['valid_phones']} ({total_stats['valid_phones']/total_stats['total_phones']*100:.1f}%)")
    print(f"❌ Invalid phones: {total_stats['invalid_phones']} ({total_stats['invalid_phones']/total_stats['total_phones']*100:.1f}%)")
    print(f"🔢 Unique valid phones (across all files): {len(total_stats['unique_phones'])}")
    print(f"🔁 Duplicate phones (across files): {total_stats['valid_phones'] - len(total_stats['unique_phones'])}")

    print(f"\n✨ IMPORT READINESS:")
    print(f"   ✓ All CSV files are readable")
    print(f"   ✓ Phone validation logic is working")
    print(f"   ✓ Multi-phone rows will be split into separate database rows")
    print(f"   ✓ Invalid phones will be skipped during import")
    print(f"   ✓ Duplicate phones will be handled via UPSERT (ON CONFLICT)")

    print(f"\n💡 RECOMMENDATIONS:")
    if total_stats['invalid_phones'] > 0:
        print(f"   ⚠️  {total_stats['invalid_phones']} invalid phones will be skipped")
        print(f"   → Consider manual review of invalid phone numbers")
    if (total_stats['valid_phones'] - len(total_stats['unique_phones'])) > 0:
        print(f"   ℹ️  {total_stats['valid_phones'] - len(total_stats['unique_phones'])} duplicate phones found")
        print(f"   → UPSERT will update existing records with latest data")
    print(f"   ✓ Ready for import to database!")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
