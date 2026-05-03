"""
Conversation ID Filter & Extraction Tool

Extracts rows from a master data file based on a list of conversation IDs.
Handles multiple rows per conversation ID, reports missing IDs, and supports
both Excel and CSV master files.

Usage:
    python conversation_id_filter.py master_data.xlsx ids.csv output.csv
    python conversation_id_filter.py master_data.csv ids.csv output.csv --save-missing
"""

import pandas as pd
import sys
import argparse
from pathlib import Path


def load_master_data(filepath):
    """Load master data from Excel or CSV. Expects a 'conversation_id' column."""
    print(f"\n📂 Loading master data: {filepath}")

    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if path.suffix.lower() in ('.xlsx', '.xls'):
        df = pd.read_excel(filepath)
        print("   ✅ Loaded Excel file")
    elif path.suffix.lower() == '.csv':
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding='ISO-8859-1')
        print("   ✅ Loaded CSV file")
    else:
        raise ValueError(f"Unsupported file type: {path.suffix} — use .xlsx or .csv")

    print(f"   {len(df):,} rows · {len(df.columns)} columns")

    if 'conversation_id' not in df.columns:
        print(f"   Available columns: {', '.join(df.columns)}")
        raise ValueError("Master data must have a 'conversation_id' column")

    print(f"   Unique conversation IDs: {df['conversation_id'].nunique():,}")
    return df


def load_conversation_ids(filepath):
    """Load conversation IDs from the first column of a CSV file."""
    print(f"\n📂 Loading conversation IDs: {filepath}")

    if not Path(filepath).exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        df = pd.read_csv(filepath, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, encoding='ISO-8859-1')

    col  = df.columns[0]
    ids  = set(str(v).strip() for v in df[col].dropna().unique())

    print(f"   ✅ {len(ids):,} unique IDs (from column '{col}')")
    return ids


def extract_matching_rows(master_df, conversation_ids):
    """Filter master data to rows whose conversation_id is in the target set."""
    print(f"\n🔍 Filtering…")

    master_df['conversation_id'] = master_df['conversation_id'].astype(str).str.strip()
    filtered  = master_df[master_df['conversation_id'].isin(conversation_ids)].copy()

    matched   = set(filtered['conversation_id'].unique())
    not_found = conversation_ids - matched

    print(f"   ✅ {len(filtered):,} rows extracted")
    print(f"   ✅ {len(matched):,} / {len(conversation_ids):,} IDs matched")

    if not_found:
        print(f"   ⚠️  {len(not_found):,} IDs not found in master data")

    if len(filtered) > 0:
        dist = filtered.groupby('conversation_id').size()
        print(f"\n   Rows per conversation: min={dist.min()} | max={dist.max()} | avg={dist.mean():.1f}")

    return filtered, not_found


def save_output(df, output_path, not_found_ids, save_missing=False):
    """Save filtered output and optionally a missing-IDs report."""
    print(f"\n💾 Saving: {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"   ✅ {len(df):,} rows saved")

    if save_missing and not_found_ids:
        missing_path = str(output_path).replace('.csv', '_missing_ids.csv')
        pd.DataFrame({'conversation_id': sorted(not_found_ids)}).to_csv(
            missing_path, index=False, encoding='utf-8'
        )
        print(f"   📄 Missing IDs saved: {missing_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract rows from a master data file by conversation ID',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python conversation_id_filter.py master_data.xlsx ids.csv output.csv
  python conversation_id_filter.py master_data.csv ids.csv output.csv --save-missing
  python conversation_id_filter.py master_data.xlsx ids.csv output.csv --show-sample 10
        """
    )
    parser.add_argument('master_file', help='Master data file (.xlsx or .csv)')
    parser.add_argument('id_file',     help='CSV with conversation IDs (first column used)')
    parser.add_argument('output_file', help='Output CSV file path')
    parser.add_argument('--save-missing', action='store_true',
                        help='Save IDs not found to a separate file')
    parser.add_argument('--show-sample', type=int, metavar='N',
                        help='Print first N rows of output to console')

    args = parser.parse_args()

    try:
        print("=" * 80)
        print("CONVERSATION ID FILTER & EXTRACTION")
        print("=" * 80)

        master_df        = load_master_data(args.master_file)
        conversation_ids = load_conversation_ids(args.id_file)
        filtered, not_found = extract_matching_rows(master_df, conversation_ids)

        if len(filtered) == 0:
            print("\n⚠️  No matching rows found — check that IDs match exactly in both files")
            print("\n   Sample IDs from filter file:")
            for cid in list(conversation_ids)[:5]:
                print(f"      '{cid}'")
            print("\n   Sample IDs from master data:")
            for cid in master_df['conversation_id'].head(5).tolist():
                print(f"      '{cid}'")
            resp = input("\nContinue and save empty output? (yes/no): ")
            if resp.lower() not in ('yes', 'y'):
                print("Cancelled")
                sys.exit(0)

        save_output(filtered, args.output_file, not_found, args.save_missing)

        if args.show_sample and len(filtered) > 0:
            print(f"\n📋 Sample output (first {args.show_sample} rows):")
            print(filtered.head(args.show_sample).to_string())

        print("\n" + "=" * 80)
        print("✅ EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"\n   Rows extracted:  {len(filtered):,}")
        matched_count = len(set(filtered['conversation_id'].unique())) if len(filtered) > 0 else 0
        print(f"   IDs matched:     {matched_count:,}")
        print(f"   IDs not found:   {len(not_found):,}")
        if not_found and not args.save_missing:
            print("   (use --save-missing to export the missing IDs list)")
        print("=" * 80)

    except (FileNotFoundError, ValueError) as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
