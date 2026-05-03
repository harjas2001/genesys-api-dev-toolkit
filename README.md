# genesys-api-dev-toolkit

A collection of diagnostic and validation utilities for working with the Genesys Cloud Botflows Reporting API — built to validate API behaviour, confirm field mappings, and troubleshoot OAuth before committing to a full extraction pipeline.

---

## Background

Built as part of the development work behind [`voice-ai-qa-pipeline`](https://github.com/yourusername/voice-ai-qa-pipeline) between December 2025 and February 2026.

Before writing an extraction pipeline processing 100,000–150,000 voice conversation turns per week, the API behaviour needed to be validated: does cursor pagination actually work? Does the `interval` date filter apply server-side or client-side? What does the nested JSON schema look like, and do the field names match the documentation? Which OAuth scopes are required?

These scripts answered those questions systematically. The validation work meant the main extractor was built against confirmed API behaviour — no guessing on field names, pagination shape, or authentication scope.

---

## Scripts

| Script | Purpose |
|---|---|
| `api_response_inspector.py` | Tests endpoint variations and prints the full response structure |
| `api_date_range_inspector.py` | Checks what date range of data is available before extraction |
| `oauth_diagnostics.py` | Tests OAuth scope acquisition, lists divisions and bot flows |
| `interval_parameter_test.py` | Confirms the `interval` date-filter parameter works server-side |
| `field_mapping_validator.py` | Validates JSON field names against expected CSV column mappings |
| `conversation_id_filter.py` | Extracts rows from a master dataset by conversation ID list |
| `duplicate_id_finder.py` | Finds duplicate values in a specified CSV column |
| `sdk_usage_example.py` | SDK-based alternative to raw HTTP requests |
| `docs/field_mapping.md` | Reference: full API field → CSV column mapping with examples |

---

## Setup

```bash
git clone https://github.com/yourusername/genesys-api-dev-toolkit
cd genesys-api-dev-toolkit

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp credentials.example.json credentials.json
# Edit credentials.json with your Genesys Cloud OAuth client details
```

**credentials.json** (gitignored):
```json
{
  "client_id":     "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_secret": "your-client-secret",
  "region":        "mypurecloud.com.au",
  "botflow_id":    "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "verify_cert":   true
}
```

---

## Recommended Workflow

Run these scripts in order when setting up a new Genesys Cloud integration:

```bash
# 1. Confirm OAuth scope works and inspect available divisions + bot flows
python oauth_diagnostics.py

# 2. Test the API endpoint and inspect the response structure
python api_response_inspector.py

# 3. Confirm server-side date filtering works (required for efficient extraction)
python interval_parameter_test.py

# 4. Check what date range of data is currently available
python api_date_range_inspector.py

# 5. Validate field names against your expected CSV schema
python field_mapping_validator.py path/to/raw_sample.json
```

---

## Configuration

All scripts accept `--credentials` to override the default `credentials.json` path:

```bash
python oauth_diagnostics.py --credentials /path/to/credentials.json
python api_date_range_inspector.py --credentials /path/to/credentials.json --page-scan-limit 10
```

The SDK example can also be configured via environment variables (see `.env.example`).

---

## Utility Scripts

### conversation_id_filter.py

Cross-references a list of conversation IDs against a master data file (Excel or CSV) and extracts all matching rows. Supports multiple rows per ID and reports missing IDs.

```bash
python conversation_id_filter.py master_data.xlsx ids.csv output.csv
python conversation_id_filter.py master_data.csv ids.csv output.csv --save-missing
```

### duplicate_id_finder.py

Finds duplicate values in a specified CSV column — useful for validating extraction outputs.

```bash
python duplicate_id_finder.py output.csv conversation_id
python duplicate_id_finder.py output.csv session_id
```

---

## Field Mapping Reference

See [`docs/field_mapping.md`](docs/field_mapping.md) for the full API field → CSV column mapping, sample records, and the `flatten_turn_data()` implementation.

---

## Required OAuth Scope

```
analytics:botFlowDivisionAwareReportingTurn:view
```

Configure on the OAuth client in: **Genesys Cloud Admin → Integrations → OAuth → [client] → Roles**

---

## Stack

`Python · requests · pandas · PureCloudPlatformClientV2`
