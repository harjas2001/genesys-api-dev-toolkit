"""
Genesys Cloud — OAuth & Division Diagnostics

Tests OAuth scope acquisition, available divisions, accessible bot flows,
and token permissions. Run this when troubleshooting authentication or
access control issues.

Usage:
    python oauth_diagnostics.py
    python oauth_diagnostics.py --credentials /path/to/credentials.json
"""

import requests
import json
import argparse
from datetime import datetime


def load_credentials(filepath='credentials.json'):
    with open(filepath, 'r') as f:
        return json.load(f)


def get_access_token(creds, scope):
    """Attempt to acquire an OAuth token with a specific scope."""
    token_url = f"https://login.{creds['region']}/oauth/token"
    try:
        response = requests.post(
            token_url,
            data={'grant_type': 'client_credentials', 'scope': scope},
            auth=(creds['client_id'], creds['client_secret']),
            timeout=30,
            verify=creds.get('verify_cert', True)
        )
        response.raise_for_status()
        return response.json()['access_token'], None
    except requests.exceptions.HTTPError as e:
        try:
            return None, response.json()
        except Exception:
            return None, str(e)
    except Exception as e:
        return None, str(e)


def test_scope(creds, scope):
    """Print pass/fail for a specific OAuth scope."""
    print(f"\n🔑 Scope: {scope}")
    print("   " + "─" * 76)
    token, error = get_access_token(creds, scope)
    if token:
        print("   ✅ Token acquired")
        return token
    else:
        print(f"   ❌ Failed — {error}")
        return None


def check_divisions(creds, access_token):
    """List all divisions accessible to this OAuth client."""
    print(f"\n📂 Accessible Divisions")
    print("   " + "─" * 76)

    response = requests.get(
        f"https://api.{creds['region']}/api/v2/authorization/divisions",
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=30,
        verify=creds.get('verify_cert', True)
    )

    if response.status_code == 200:
        divisions = response.json().get('entities', [])
        print(f"   Found {len(divisions)} division(s):\n")
        for div in divisions:
            tag = " ⭐ (Home)" if div.get('home') else ""
            print(f"   • {div.get('name', 'Unknown')}  (ID: {div.get('id', 'N/A')}){tag}")
        return divisions
    else:
        print(f"   ❌ HTTP {response.status_code}")
        try:
            print(f"   {response.json()}")
        except Exception:
            pass
        return []


def check_bot_flows(creds, access_token):
    """List bot flows visible to this OAuth client."""
    print(f"\n🤖 Bot Flows")
    print("   " + "─" * 76)

    response = requests.get(
        f"https://api.{creds['region']}/api/v2/flows",
        headers={'Authorization': f'Bearer {access_token}'},
        params={'type': 'bot', 'pageSize': 100},
        timeout=30,
        verify=creds.get('verify_cert', True)
    )

    if response.status_code == 200:
        flows = response.json().get('entities', [])
        print(f"   Found {len(flows)} bot flow(s):\n")
        for flow in flows:
            print(f"   • {flow.get('name', 'Unknown')}")
            print(f"     ID: {flow.get('id', 'N/A')}")
            div = flow.get('division')
            if div:
                print(f"     Division: {div.get('name', '?')} ({div.get('id', '?')})")
            ver = flow.get('publishedVersion')
            print(f"     Published: {'v' + str(ver.get('version', '?')) if ver else '⚠️  not published'}")
            print()
        return flows
    elif response.status_code == 403:
        print("   ⚠️  403 — insufficient permission (needs architect:flow:view)")
        return []
    else:
        print(f"   ❌ HTTP {response.status_code}")
        return []


def check_token_info(creds, access_token):
    """Print OAuth client and organisation info for the active token."""
    print(f"\n🔐 Token Info")
    print("   " + "─" * 76)

    response = requests.get(
        f"https://api.{creds['region']}/api/v2/tokens/me",
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=30,
        verify=creds.get('verify_cert', True)
    )

    if response.status_code == 200:
        data = response.json()
        client = data.get('OAuthClient', {})
        org    = data.get('organization', {})
        print(f"   Client ID:   {client.get('id', 'N/A')}")
        print(f"   Client Name: {client.get('name', 'N/A')}")
        print(f"   Org:         {org.get('name', 'N/A')}")
        print(f"   Scope:       {data.get('scope', ['N/A'])}")
        return data
    else:
        print(f"   ❌ HTTP {response.status_code}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Diagnose Genesys Cloud OAuth scopes and division access'
    )
    parser.add_argument('--credentials', default='credentials.json',
                        help='Path to credentials JSON file (default: credentials.json)')
    args = parser.parse_args()

    print("=" * 80)
    print("GENESYS CLOUD — OAUTH & DIVISION DIAGNOSTICS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    creds = load_credentials(args.credentials)
    print(f"Region: {creds.get('region', 'unknown')}\n")

    scopes = [
        'analytics:botFlowDivisionAwareReportingTurn:view',
        'authorization:division:view',
        'architect:flow:view',
    ]

    tokens = {}
    for scope in scopes:
        token = test_scope(creds, scope)
        if token:
            tokens[scope] = token

    main_token = tokens.get('analytics:botFlowDivisionAwareReportingTurn:view')

    if main_token:
        check_token_info(creds, main_token)
        check_divisions(creds, main_token)
        flow_token = tokens.get('architect:flow:view', main_token)
        check_bot_flows(creds, flow_token)
    else:
        print("\n" + "=" * 80)
        print("❌ CRITICAL — Cannot acquire the required analytics scope")
        print("=" * 80)
        print("\nSteps to fix:")
        print("1. Admin > Integrations > OAuth > [your client] > Roles tab")
        print("2. Confirm the assigned role has:")
        print("     Analytics > Bot Flow > Reporting Turn > View")
        print("3. If using a custom role, verify it's assigned to the OAuth client")
        print("4. Allow ~2 minutes after permission changes before retrying")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
