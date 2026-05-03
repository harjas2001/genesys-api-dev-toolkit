"""
Genesys Cloud — Available Date Range Inspector

Checks what date range of botflow reporting turn data is available before
committing to a full extraction. Fetches the first few pages of the API to
determine the oldest and newest records, and assesses whether last week's
data is complete.

Run this before any extraction to avoid pulling stale or incomplete windows.

Usage:
    python api_date_range_inspector.py
    python api_date_range_inspector.py --credentials /path/to/credentials.json
"""

import requests
import json
import argparse
from datetime import datetime, timedelta


def load_credentials(filepath='credentials.json'):
    with open(filepath, 'r') as f:
        return json.load(f)


def get_access_token(creds):
    token_url = f"https://login.{creds['region']}/oauth/token"
    response = requests.post(
        token_url,
        data={
            'grant_type': 'client_credentials',
            'scope': 'analytics:botFlowDivisionAwareReportingTurn:view'
        },
        auth=(creds['client_id'], creds['client_secret']),
        timeout=30,
        verify=creds.get('verify_cert', True)
    )
    response.raise_for_status()
    return response.json()['access_token']


def inspect_date_range(creds, access_token, page_scan_limit=5):
    """
    Fetch the first N pages to determine the available date range.

    Args:
        creds:           Credentials dict
        access_token:    OAuth access token
        page_scan_limit: How many pages to scan when estimating oldest date
    """
    base_url   = f"https://api.{creds['region']}"
    bot_flow_id = creds['botflow_id']
    endpoint   = f"/api/v2/analytics/botflows/{bot_flow_id}/divisions/reportingturns"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type':  'application/json'
    }

    print("\n" + "=" * 80)
    print("AVAILABLE DATA INSPECTION")
    print("=" * 80)

    # First page — most recent data
    print("\n📊 Fetching first page (most recent records)...")
    response = requests.get(
        base_url + endpoint,
        headers=headers,
        params={'pageSize': 100},
        timeout=60,
        verify=creds.get('verify_cert', True)
    )

    if response.status_code != 200:
        print(f"❌ Failed: HTTP {response.status_code}")
        try:
            print(f"   Error: {response.json()}")
        except Exception:
            print(f"   Response: {response.text[:500]}")
        return

    first_page     = response.json()
    first_entities = first_page.get('entities', [])

    if not first_entities:
        print("⚠️  No data returned — bot flow may have no recorded turns")
        return

    first_page_dates = [e.get('dateCreated') for e in first_entities if e.get('dateCreated')]

    if not first_page_dates:
        print("⚠️  Records have no dateCreated field")
        return

    most_recent  = max(first_page_dates)
    oldest_date  = min(first_page_dates)
    print(f"   ✅ {len(first_entities)} records — most recent: {most_recent}")

    # Walk further pages to narrow down oldest date
    next_uri   = first_page.get('nextUri')
    page_count = 1

    if next_uri:
        print(f"\n   Multiple pages exist — scanning up to {page_scan_limit} more pages for oldest date...")

        for _ in range(page_scan_limit):
            if not next_uri:
                break

            page_count += 1
            print(f"   Page {page_count}...", end='', flush=True)

            resp = requests.get(
                base_url + next_uri,
                headers=headers,
                timeout=60,
                verify=creds.get('verify_cert', True)
            )

            if resp.status_code != 200:
                break

            page_data   = resp.json()
            page_entities = page_data.get('entities', [])

            if page_entities:
                page_dates  = [e.get('dateCreated') for e in page_entities if e.get('dateCreated')]
                if page_dates:
                    oldest_date = min(oldest_date, min(page_dates))
                    print(f" oldest so far: {oldest_date}")

            next_uri = page_data.get('nextUri')

        if next_uri:
            print(f"\n   ⚠️  More pages exist beyond page {page_count} — oldest date is an estimate")
        else:
            print(f"\n   ✅ Reached last page at page {page_count}")
    else:
        print("   ✅ Only one page of data available")

    # Summary
    print("\n" + "=" * 80)
    print("DATE RANGE SUMMARY")
    print("=" * 80)

    try:
        newest_dt = datetime.fromisoformat(most_recent.replace('Z', '+00:00'))
        oldest_dt = datetime.fromisoformat(oldest_date.replace('Z', '+00:00'))
        span_days = (newest_dt - oldest_dt).days

        print(f"\n📅 Available range:")
        print(f"   Oldest:  {oldest_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   Newest:  {newest_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   Span:    {span_days} days")

        today        = datetime.now()
        last_monday  = today - timedelta(days=today.weekday() + 7)
        last_sunday  = last_monday + timedelta(days=6)

        print(f"\n📋 Last week:")
        print(f"   Mon {last_monday.strftime('%Y-%m-%d')} → Sun {last_sunday.strftime('%Y-%m-%d')}")

        if oldest_dt.date() <= last_monday.date() and newest_dt.date() >= last_sunday.date():
            print("   ✅ Complete last-week data IS available")
        elif newest_dt.date() < last_monday.date():
            print(f"   ⚠️  Newest data is {newest_dt.strftime('%Y-%m-%d')} — retention may have expired")
        elif oldest_dt.date() > last_sunday.date():
            print(f"   ⚠️  Oldest data is {oldest_dt.strftime('%Y-%m-%d')} — last week already purged")
        else:
            print("   ⚠️  Only partial last-week data available")

        print(f"\n💡 Suggested extraction window:")
        print(f"   --start-date {last_monday.strftime('%Y-%m-%d')}T00:00:00Z")
        print(f"   --end-date   {last_sunday.strftime('%Y-%m-%d')}T23:59:59Z")

        if span_days < 14:
            print(f"\n⚠️  Short retention ({span_days} days) — extract weekly to avoid data loss")
        else:
            print(f"\n✅ Retention looks healthy ({span_days} days)")

    except Exception as e:
        print(f"❌ Error parsing dates: {e}")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Check what date range of data is available in the Genesys API'
    )
    parser.add_argument('--credentials', default='credentials.json',
                        help='Path to credentials JSON file (default: credentials.json)')
    parser.add_argument('--page-scan-limit', type=int, default=5,
                        help='How many pages to scan when estimating oldest date (default: 5)')
    args = parser.parse_args()

    print("=" * 80)
    print("GENESYS CLOUD — DATA RANGE INSPECTOR")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    creds = load_credentials(args.credentials)

    print("\n🔐 Authenticating...")
    access_token = get_access_token(creds)
    print("✅ Authentication successful")

    inspect_date_range(creds, access_token, page_scan_limit=args.page_scan_limit)

    print("\n✅ Inspection complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
