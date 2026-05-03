"""
Duplicate ID Finder

Identifies duplicate values in a specified column of a CSV file.
Useful for validating extraction outputs and detecting unexpected repeat records.

Usage:
    python duplicate_id_finder.py <csv_file> <column_name>
    python duplicate_id_finder.py output.csv conversation_id
    python duplicate_id_finder.py output.csv session_id
"""

import pandas as pd
import sys
import argparse
from pathlib import Path


def find_duplicates(csv_path, column):
    """Report duplicate values in a CSV column."""
    if not Path(csv_path).exists():
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    if column not in df.columns:
        print(f"❌ Column '{column}' not found")
        print(f"   Available columns: {', '.join(df.columns)}")
        sys.exit(1)

    print(f"\n📂 {csv_path}")
    print(f"   {len(df):,} rows · checking column: '{column}'")

    dupes = df[df.duplicated(column, keep=False)][column].value_counts()

    if dupes.empty:
        print(f"\n✅ No duplicates found in '{column}'")
    else:
        total_dupe_rows = df.duplicated(column, keep=False).sum()
        print(f"\n⚠️  {len(dupes):,} values appear more than once ({total_dupe_rows:,} total rows):\n")
        for value, count in dupes.items():
            print(f"   '{value}'  →  {count} occurrences")

    return dupes


def main():
    parser = argparse.ArgumentParser(
        description='Find duplicate values in a CSV column',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python duplicate_id_finder.py output.csv conversation_id
  python duplicate_id_finder.py output.csv session_id
        """
    )
    parser.add_argument('csv_file', help='CSV file to check')
    parser.add_argument('column',   help='Column name to check for duplicates')
    args = parser.parse_args()

    find_duplicates(args.csv_file, args.column)


if __name__ == '__main__':
    main()
