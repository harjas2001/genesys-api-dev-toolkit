"""
Genesys Cloud — Interval Parameter Test

Verifies that the Genesys reporting turns API accepts the `interval` query
parameter for server-side date filtering.

The API uses an ISO 8601 interval string (`start/end`) rather than separate
startDate/endDate parameters. This script confirms the parameter works on
your deployment before relying on it in a full extraction.

Usage:
    python interval_parameter_test.py
    python interval_parameter_test.py --credentials /path/to/credentials.json
"""

import json
import requests
import argparse
from datetime import datetime, timedelta


def load_credentials(filepath='credentials.json'):
    with open(filepath, 'r') as f:
        return json.load(f)


def get_access_token(creds):
    response = requests.post(
        f"https://login.{creds['region']}/oauth/token",
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


def test_interval_parameter(creds, access_token):
    """
    Compare responses with and without the interval parameter.

    Test 1 — no interval filter → expect data from all dates
    Test 2 — with interval filter → expect data within specified range
    """
    base_url = f"https://api.{creds['region']}"
    endpoint = f"/api/v2/analytics/botflows/{creds['botflow_id']}/divisions/reportingturns"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type':  'application/json'
    }

    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=1)
    interval = (
        f"{start_dt.strftime('%Y-%m-%dT%H:%M:%S')}Z/"
        f"{end_dt.strftime('%Y-%m-%dT%H:%M:%S')}Z"
    )

    print("=" * 80)
    print("TESTING SERVER-SIDE DATE FILTERING (interval parameter)")
    print("=" * 80)
    print(f"\nTest interval: {interval}")

    # Test 1: Without interval
    print("\n─── Test 1: WITHOUT interval (unfiltered) ───")
    try:
        r = requests.get(
            base_url + endpoint,
            headers=headers,
            params={'pageSize': 5},
            timeout=30,
            verify=creds.get('verify_cert', True)
        )
        if r.status_code == 200:
            data = r.json()
            entities = data.get('entities', [])
            print(f"   ✅ {len(entities)} records returned")
            if entities:
                print(f"   First record date: {entities[0].get('dateCreated', 'N/A')}")
        else:
            print(f"   ❌ HTTP {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return False

    # Test 2: With interval
    print("\n─── Test 2: WITH interval (date-filtered) ───")
    try:
        r = requests.get(
            base_url + endpoint,
            headers=headers,
            params={'pageSize': 5, 'interval': interval},
            timeout=30,
            verify=creds.get('verify_cert', True)
        )

        if r.status_code == 200:
            data     = r.json()
            entities = data.get('entities', [])
            print(f"   ✅ {len(entities)} records returned")

            if entities:
                print(f"   First record date: {entities[0].get('dateCreated', 'N/A')}")

            in_range = 0
            for entity in entities:
                date_str = entity.get('dateCreated')
                if date_str:
                    entity_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    if start_dt <= entity_dt.replace(tzinfo=None) <= end_dt:
                        in_range += 1

            print(f"   Records within date range: {in_range}/{len(entities)}")

            if entities and in_range == len(entities):
                print("\n   🎉 Server-side date filtering is WORKING")
                return True
            elif not entities:
                print("\n   ⚠️  No records in this date window — try a wider range")
                return True
            else:
                print("\n   ⚠️  Some records fall outside the requested window")
                return False

        elif r.status_code == 400:
            print(f"   ❌ 400 Bad Request — interval parameter may not be supported")
            print(f"   Response: {r.text[:300]}")
            return False
        else:
            print(f"   ❌ HTTP {r.status_code}: {r.text[:200]}")
            return False

    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Verify the Genesys API accepts the interval date-filter parameter'
    )
    parser.add_argument('--credentials', default='credentials.json',
                        help='Path to credentials JSON file (default: credentials.json)')
    args = parser.parse_args()

    creds = load_credentials(args.credentials)

    print("\n🔐 Authenticating...")
    access_token = get_access_token(creds)
    print("✅ Authentication successful")

    success = test_interval_parameter(creds, access_token)

    print("\n" + "=" * 80)
    if success:
        print("✅ TEST PASSED — interval filtering works on this deployment")
        print("=" * 80)
        print("\nYou can safely use the interval parameter in extraction scripts.")
        print("This avoids fetching all historical data and filtering client-side.")
    else:
        print("⚠️  TEST FAILED — interval parameter not working as expected")
        print("=" * 80)
        print("\nOptions:")
        print("1. Run oauth_diagnostics.py to confirm API access is correct")
        print("2. Contact Genesys Cloud support about interval parameter support")
        print("3. Fall back to client-side date filtering after extraction")
    print("=" * 80)


if __name__ == "__main__":
    main()
