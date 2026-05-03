"""
Genesys Cloud API Response Inspector

Tests the botflow reporting turns endpoint with different parameter combinations
and prints the full response structure. Run this before building an extractor
to confirm endpoint availability, field names, and pagination shape.

Usage:
    python api_response_inspector.py
    python api_response_inspector.py --credentials /path/to/credentials.json
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


def test_api_endpoint(creds, access_token):
    """
    Test endpoint variations and parameter combinations.
    Stops at the first successful response and prints full structure.
    """
    base_url   = f"https://api.{creds['region']}"
    bot_flow_id = creds['botflow_id']

    endpoints = [
        f'/api/v2/analytics/botflows/{bot_flow_id}/divisions/reportingturns',
        f'/api/v2/analytics/botflows/{bot_flow_id}/reportingturns',
    ]

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type':  'application/json'
    }

    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=7)
    interval = (
        f"{start_dt.strftime('%Y-%m-%dT%H:%M:%S')}Z/"
        f"{end_dt.strftime('%Y-%m-%dT%H:%M:%S')}Z"
    )

    param_sets = [
        {'pageSize': 5},
        {'pageSize': 5, 'pageNumber': 1},
        {'pageSize': 5, 'interval': interval},
    ]

    print("=" * 80)
    print("GENESYS CLOUD — API RESPONSE INSPECTOR")
    print("=" * 80)

    for endpoint in endpoints:
        print(f"\n📍 Endpoint: {endpoint}")
        print("-" * 80)

        for i, params in enumerate(param_sets, 1):
            print(f"\n   Attempt {i} — params: {params}")

            try:
                response = requests.get(
                    base_url + endpoint,
                    headers=headers,
                    params=params,
                    timeout=30,
                    verify=creds.get('verify_cert', True)
                )

                print(f"   Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()

                    print("\n   ✅ Response structure:")
                    print("   " + "─" * 76)
                    print(json.dumps(data, indent=4, default=str)[:2000])
                    print("   ...")
                    print("   " + "─" * 76)

                    print(f"\n   📊 Top-level keys: {list(data.keys())}")

                    if 'entities' in data:
                        n = len(data['entities'])
                        print(f"   entities[]: {n} items")
                        if data['entities']:
                            print(f"   entities[0] keys: {list(data['entities'][0].keys())}")

                    for pag_key in ('pageCount', 'nextUri', 'cursors', 'pagination'):
                        if pag_key in data:
                            print(f"   {pag_key}: {data[pag_key]}")

                    return True

                elif response.status_code == 404:
                    print("   ✗ 404 — bot flow ID may be incorrect or inaccessible")
                elif response.status_code == 400:
                    print(f"   ✗ 400 — bad request: {response.text[:300]}")
                elif response.status_code == 401:
                    print("   ✗ 401 — check OAuth client credentials")
                elif response.status_code == 403:
                    print("   ✗ 403 — check OAuth scope / permissions")
                else:
                    print(f"   ✗ {response.status_code}: {response.text[:300]}")

            except requests.exceptions.RequestException as e:
                print(f"   ✗ Request failed: {e}")

    return False


def main():
    parser = argparse.ArgumentParser(description='Inspect Genesys Cloud API response structure')
    parser.add_argument('--credentials', default='credentials.json',
                        help='Path to credentials JSON file (default: credentials.json)')
    args = parser.parse_args()

    creds = load_credentials(args.credentials)

    print("\n🔐 Authenticating...")
    access_token = get_access_token(creds)
    print("✅ Authentication successful\n")

    success = test_api_endpoint(creds, access_token)

    print("\n" + "=" * 80)
    if success:
        print("✅ NEXT STEPS")
        print("=" * 80)
        print("1. Review the response structure above")
        print("2. Confirm field names match your extractor's flatten_turn_data()")
        print("3. Run field_mapping_validator.py against a saved JSON sample")
        print("4. Run the full extraction pipeline")
    else:
        print("⚠️  TROUBLESHOOTING")
        print("=" * 80)
        print("1. Verify botflow_id in credentials.json")
        print("2. Confirm OAuth scope: analytics:botFlowDivisionAwareReportingTurn:view")
        print("3. Check the bot flow has had recent activity")
        print("4. Run oauth_diagnostics.py to inspect scope and division access")
    print("=" * 80)


if __name__ == "__main__":
    main()
