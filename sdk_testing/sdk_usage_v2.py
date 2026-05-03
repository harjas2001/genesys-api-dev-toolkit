"""
Genesys Cloud Python SDK — Usage Example

Demonstrates how to call the Genesys Cloud analytics API using the official
PureCloudPlatformClientV2 Python SDK rather than raw HTTP requests.

The SDK handles token refresh automatically, which is useful for long-running
extractions. For most scripting purposes the raw requests approach in
genesys_extractor.py is simpler and has no additional dependency.

Requires:
    pip install PureCloudPlatformClientV2

Usage:
    Set environment variables before running:
        export GENESYS_CLIENT_ID=your-client-id
        export GENESYS_CLIENT_SECRET=your-client-secret
        export GENESYS_REGION=mypurecloud.com.au
        export GENESYS_BOTFLOW_ID=your-botflow-id

    Then run:
        python sdk_usage_example.py

    Or load from credentials.json:
        python sdk_usage_example.py --credentials credentials.json
"""

import os
import json
import argparse
from datetime import datetime, timedelta

try:
    import PureCloudPlatformClientV2
    from PureCloudPlatformClientV2.rest import ApiException
    from pprint import pprint
except ImportError:
    print("❌ PureCloudPlatformClientV2 not installed")
    print("   Run: pip install PureCloudPlatformClientV2")
    raise


def load_credentials(filepath=None):
    """Load credentials from file or environment variables."""
    if filepath and os.path.exists(filepath):
        with open(filepath, 'r') as f:
            creds = json.load(f)
        return {
            'client_id':     creds['client_id'],
            'client_secret': creds['client_secret'],
            'region':        creds.get('region', 'mypurecloud.com'),
            'botflow_id':    creds['botflow_id'],
        }

    client_id     = os.environ.get('GENESYS_CLIENT_ID')
    client_secret = os.environ.get('GENESYS_CLIENT_SECRET')
    region        = os.environ.get('GENESYS_REGION', 'mypurecloud.com')
    botflow_id    = os.environ.get('GENESYS_BOTFLOW_ID')

    missing = [k for k, v in {
        'GENESYS_CLIENT_ID':     client_id,
        'GENESYS_CLIENT_SECRET': client_secret,
        'GENESYS_BOTFLOW_ID':    botflow_id,
    }.items() if not v]

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"  Set them or pass --credentials path/to/credentials.json"
        )

    return {
        'client_id':     client_id,
        'client_secret': client_secret,
        'region':        region,
        'botflow_id':    botflow_id,
    }


def authenticate(creds):
    """Authenticate using SDK client credentials flow."""
    api_client = PureCloudPlatformClientV2.api_client.ApiClient()
    api_client.host = f"https://api.{creds['region']}"
    api_client.get_client_credentials_token(creds['client_id'], creds['client_secret'])
    return api_client


def fetch_reporting_turns(api_client, botflow_id, interval=None, page_size='50'):
    """
    Call the botflow reporting turns endpoint via the SDK.

    Args:
        api_client:  Authenticated ApiClient instance
        botflow_id:  Bot flow UUID
        interval:    ISO 8601 interval string (e.g. '2025-01-06T00:00:00Z/2025-01-06T23:59:59Z')
        page_size:   Records per page (max 250)

    Returns:
        API response object
    """
    analytics_api = PureCloudPlatformClientV2.AnalyticsApi(api_client)

    kwargs = {'page_size': page_size}
    if interval:
        kwargs['interval'] = interval

    return analytics_api.get_analytics_botflow_divisions_reportingturns(
        botflow_id, **kwargs
    )


def main():
    parser = argparse.ArgumentParser(
        description='Genesys Cloud SDK usage example — botflow reporting turns'
    )
    parser.add_argument('--credentials', default=None,
                        help='Path to credentials.json (default: use env vars)')
    parser.add_argument('--days', type=int, default=1,
                        help='Number of days back to query (default: 1)')
    args = parser.parse_args()

    print("=" * 80)
    print("GENESYS CLOUD SDK — REPORTING TURNS EXAMPLE")
    print("=" * 80)

    creds = load_credentials(filepath=args.credentials)

    print("\n🔐 Authenticating via SDK...")
    api_client = authenticate(creds)
    print("✅ Authentication successful")

    end_dt   = datetime.utcnow()
    start_dt = end_dt - timedelta(days=args.days)
    interval = (
        f"{start_dt.strftime('%Y-%m-%dT%H:%M:%S')}Z/"
        f"{end_dt.strftime('%Y-%m-%dT%H:%M:%S')}Z"
    )

    print(f"\n📊 Fetching turns for interval: {interval}")

    try:
        response = fetch_reporting_turns(
            api_client,
            botflow_id=creds['botflow_id'],
            interval=interval,
            page_size='10'  # Small for demonstration
        )

        entities = getattr(response, 'entities', []) or []
        print(f"\n✅ Response received — {len(entities)} entities")

        if entities:
            print("\n📋 First entity:")
            pprint(vars(entities[0]) if hasattr(entities[0], '__dict__') else entities[0])

        next_uri = getattr(response, 'next_uri', None)
        if next_uri:
            print(f"\n   Next page cursor: {next_uri}")

    except ApiException as e:
        print(f"\n❌ ApiException: {e}")

    print("\n" + "=" * 80)
    print("Notes:")
    print("  • The SDK auto-refreshes tokens — useful for multi-hour extractions")
    print("  • For scripting, the raw requests approach in genesys_extractor.py")
    print("    is simpler and has no additional SDK dependency")
    print("=" * 80)


if __name__ == "__main__":
    main()
