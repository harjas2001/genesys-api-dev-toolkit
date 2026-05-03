"""
Genesys Cloud — Field Mapping Validator

After extracting a raw JSON sample, validates that the actual API field names
match the expected CSV column mappings. Identifies missing or renamed fields,
suggests corrections to flatten_turn_data(), and prints a sample record.

Usage:
    python field_mapping_validator.py raw_extract.json
"""

import json
import sys
from pathlib import Path


# ── Expected field mappings ────────────────────────────────────────────────────
# Maps CSV column name → list of possible API field paths to check.
# Add or adjust these if your bot flow uses different field names.

EXPECTED_FIELDS = {
    'session_id':         ['sessionId', 'session_id'],
    'conversation_id':    ['conversation.id', 'conversationId'],
    'date_created':       ['dateCreated', 'date_created'],
    'date_completed':     ['dateCompleted', 'date_completed'],
    'user_input':         ['userInput', 'user_input', 'input'],
    'bot_prompts_all':    ['botPrompts', 'bot_prompt', 'prompts'],
    'bot_prompt_first':   ['botPrompts', 'bot_prompt'],
    'bot_prompt_count':   ['botPrompts'],
    'action_name':        ['askAction.actionName', 'actionName'],
    'action_type':        ['askAction.actionType', 'actionType'],
    'action_number':      ['askAction.actionNumber', 'actionNumber'],
    'ask_action_result':  ['askActionResult', 'ask_action_result'],
    'intent_name':        ['intent.name', 'intentName'],
    'intent_confidence':  ['intent.confidence', 'intentConfidence'],
}


def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        sys.exit(1)


def get_nested_value(obj, path):
    """Resolve dot-notation paths (e.g. 'intent.name') against a dict."""
    keys = path.split('.')
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def collect_all_fields(entities):
    """Collect all top-level and nested field paths from the entity list."""
    all_fields = set()
    nested     = {}
    for entity in entities:
        all_fields.update(entity.keys())
        for key, val in entity.items():
            if isinstance(val, dict):
                nested[key] = set(val.keys())
                for sub in val.keys():
                    all_fields.add(f"{key}.{sub}")
    return all_fields, nested


def validate_fields(entities):
    print("=" * 80)
    print("FIELD MAPPING VALIDATION")
    print("=" * 80)
    print(f"\n📊 Records analysed: {len(entities)}")

    all_fields, nested = collect_all_fields(entities)
    top_level = [f for f in all_fields if '.' not in f]
    print(f"   Top-level fields:   {len(top_level)}")
    print(f"   Nested objects:     {len(nested)}")

    print("\n" + "=" * 80)
    print("FIELD VALIDATION RESULTS")
    print("=" * 80)

    found_mappings = {}
    missing_fields = []

    for csv_col, candidates in EXPECTED_FIELDS.items():
        print(f"\n🔍 {csv_col}")
        print(f"   Candidates: {candidates}")

        found     = False
        found_key = None
        samples   = []

        for path in candidates:
            for entity in entities[:10]:
                val = get_nested_value(entity, path)
                if val is not None:
                    found     = True
                    found_key = path
                    samples.append(val)
                    break
            if found:
                break

        if found:
            sample_strs = list(dict.fromkeys(str(s)[:60] for s in samples[:3]))
            print(f"   ✅ FOUND:  {found_key}")
            print(f"   Samples:  {' | '.join(sample_strs)}")
            found_mappings[csv_col] = found_key
        else:
            print(f"   ❌ NOT FOUND in data")
            missing_fields.append(csv_col)

    # Unmapped API fields
    print("\n" + "=" * 80)
    print("UNMAPPED API FIELDS")
    print("=" * 80)
    mapped_api = set(found_mappings.values())
    unmapped   = sorted(f for f in all_fields if f not in mapped_api)

    if unmapped:
        print("\nFields present in API but not mapped to any CSV column:")
        for field in unmapped[:25]:
            sample = None
            for entity in entities[:1]:
                sample = get_nested_value(entity, field)
                if sample is not None:
                    break
            if isinstance(sample, (list, dict)):
                sample_str = f"({type(sample).__name__})"
            else:
                sample_str = str(sample)[:60] if sample is not None else ''
            print(f"   - {field:<45} {sample_str}")
        if len(unmapped) > 25:
            print(f"   ... and {len(unmapped) - 25} more")
    else:
        print("\n✅ All API fields mapped")

    # Suggested code
    print("\n" + "=" * 80)
    print("SUGGESTED flatten_turn_data() IMPLEMENTATION")
    print("=" * 80)

    if missing_fields:
        print(f"\n⚠️  No API source found for: {', '.join(missing_fields)}")
        print("   These will default to empty string in the suggestion below.\n")

    print("\n```python")
    print("def flatten_turn_data(turn):")
    print("    flattened = {")
    for csv_col, api_path in sorted(found_mappings.items()):
        if '.' in api_path:
            parts  = api_path.split('.')
            access = f"turn.get('{parts[0]}', {{}}).get('{parts[1]}', '')"
        else:
            access = f"turn.get('{api_path}', '')"
        print(f"        '{csv_col}': {access},")
    for col in missing_fields:
        print(f"        '{col}': '',  # NOT FOUND — verify field name")
    print("    }")
    print("    return flattened")
    print("```")

    # Sample record
    print("\n" + "=" * 80)
    print("SAMPLE RECORD")
    print("=" * 80)
    if entities:
        print(json.dumps(entities[0], indent=2, default=str))


def main():
    if len(sys.argv) < 2:
        print("Usage: python field_mapping_validator.py <raw_json_file>")
        print("\nExample:")
        print("  python field_mapping_validator.py raw_extract_20250106.json")
        sys.exit(1)

    json_file = sys.argv[1]
    print(f"\nAnalysing: {json_file}\n")

    entities = load_json(json_file)

    if not isinstance(entities, list):
        print("❌ Expected a JSON array at root level")
        sys.exit(1)

    validate_fields(entities)

    print("\n" + "=" * 80)
    print("✅ VALIDATION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Copy the suggested flatten_turn_data() if fields need updating")
    print("2. Re-run the full extraction with corrected mappings")
    print("=" * 80)


if __name__ == "__main__":
    main()
