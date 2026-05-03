# Genesys Cloud Botflow API — Field Mapping Reference

Confirmed field mapping between the Genesys Cloud Botflows Reporting Turns API
response and the flat CSV output produced by the extraction pipeline.

---

## Simple Fields (Direct Mapping)

| CSV Column | API Field | Type | Notes |
|---|---|---|---|
| `session_id` | `sessionId` | string | May be empty in some records |
| `date_created` | `dateCreated` | ISO datetime string | When the turn was created |
| `date_completed` | `dateCompleted` | ISO datetime string | When the turn completed |
| `user_input` | `userInput` | string | What the caller said |

## Nested Fields (Object Access Required)

| CSV Column | API Path | Type | Notes |
|---|---|---|---|
| `conversation_id` | `conversation.id` | string | Nested inside `conversation` object |
| `action_name` | `askAction.actionName` | string | Nested inside `askAction` object |
| `action_type` | `askAction.actionType` | string | Nested inside `askAction` object |
| `action_number` | `askAction.actionNumber` | number | Nested inside `askAction` object |
| `intent_name` | `intent.name` | string | Nested inside `intent` object (conditional) |
| `intent_confidence` | `intent.confidence` | float | Nested inside `intent` object (conditional) |

## Array Fields (Processing Required)

| CSV Column | API Field | Type | Processing |
|---|---|---|---|
| `bot_prompts_all` | `botPrompts` | string array | Join with ` \| ` separator |
| `bot_prompt_first` | `botPrompts` | string array | Take first element |
| `bot_prompt_count` | `botPrompts` | string array | Count elements |

## Conditional Fields

These fields are not always present in a turn record:

| CSV Column | API Field | Present When |
|---|---|---|
| `intent_name` | `intent.name` | Intent was successfully matched |
| `intent_confidence` | `intent.confidence` | Intent was successfully matched |
| `ask_action_result` | `askActionResult` | Action produced a result (e.g. `SuccessCollection`, `NoMatchCollection`) |

---

## Sample Data Mapping

### Example 1 — No Intent Matched (opening prompt)

```json
{
  "userInput": "",
  "botPrompts": ["In a sentence, please tell me how I can help you today?"],
  "sessionId": "session-abc-123",
  "conversation": {"id": "conv-xyz-456"},
  "askAction": {
    "actionName": "Ask for Intent",
    "actionType": "AskForNLUIntentAction",
    "actionNumber": 55
  },
  "dateCreated":   "2025-01-06T06:24:43.165Z",
  "dateCompleted": "2025-01-06T06:24:43.179Z"
}
```

CSV output (no intent, empty user input):
```
session_id,conversation_id,date_created,...,user_input,intent_name,intent_confidence
session-abc-123,conv-xyz-456,2025-01-06T06:24:43.165Z,...,"","",""
```

---

### Example 2 — Intent Matched Successfully

```json
{
  "userInput": "I want to cancel my plan.",
  "botPrompts": ["Okay.", "Let me help you with your cancellation request."],
  "sessionId": "session-abc-123",
  "conversation": {"id": "conv-xyz-456"},
  "askAction": {
    "actionName": "Ask for Intent",
    "actionType": "AskForNLUIntentAction",
    "actionNumber": 55
  },
  "intent": {
    "name": "cancellation",
    "confidence": 0.768
  },
  "dateCreated":   "2025-01-06T06:24:54.274Z",
  "dateCompleted": "2025-01-06T06:24:54.288Z",
  "askActionResult": "SuccessCollection"
}
```

CSV output:
```
...,user_input,intent_name,intent_confidence,ask_action_result
...,"I want to cancel my plan.",cancellation,0.768,SuccessCollection
```

---

### Example 3 — NoMatch (intent recognition failed)

```json
{
  "userInput": "Yeah I'm not sure what I need.",
  "botPrompts": ["Sorry, I missed that.", "In a sentence, please tell me how I can help?"],
  "sessionId": "session-def-789",
  "conversation": {"id": "conv-mno-012"},
  "askAction": {
    "actionName": "Ask for Intent",
    "actionType": "AskForNLUIntentAction",
    "actionNumber": 55
  },
  "dateCreated":   "2025-01-06T06:24:53.880Z",
  "dateCompleted": "2025-01-06T06:24:53.895Z",
  "askActionResult": "NoMatchCollection"
}
```

CSV output (no intent, NoMatch result):
```
...,user_input,intent_name,intent_confidence,ask_action_result
...,"Yeah I'm not sure what I need.","","",NoMatchCollection
```

---

## Code Reference — `flatten_turn_data()`

```python
def flatten_turn_data(turn):
    flattened = {
        # Direct fields
        'session_id':      turn.get('sessionId', ''),
        'date_created':    turn.get('dateCreated', ''),
        'date_completed':  turn.get('dateCompleted', ''),
        'user_input':      turn.get('userInput', ''),

        # Nested: conversation object
        'conversation_id': turn.get('conversation', {}).get('id', ''),

        # Array: botPrompts
        'bot_prompts_all':  ' | '.join(str(p).strip() for p in turn.get('botPrompts', []) if p),
        'bot_prompt_first': str(turn.get('botPrompts', [''])[0]).strip() if turn.get('botPrompts') else '',
        'bot_prompt_count': len(turn.get('botPrompts', [])),

        # Nested: askAction object
        'action_name':   turn.get('askAction', {}).get('actionName', ''),
        'action_type':   turn.get('askAction', {}).get('actionType', ''),
        'action_number': turn.get('askAction', {}).get('actionNumber', ''),

        # Conditional field
        'ask_action_result': turn.get('askActionResult', ''),

        # Nested: intent object (conditional)
        'intent_name':       turn.get('intent', {}).get('name', ''),
        'intent_confidence': turn.get('intent', {}).get('confidence', ''),
    }
    return flattened
```

---

## Additional API Fields (Not Mapped)

These fields exist in the API response but are not extracted in the default pipeline:

| Field | Description |
|---|---|
| `conversation.selfUri` | URI path to the conversation resource |
| `askAction.actionId` | Unique identifier for the action node |
| `intent.slots` | Slot values filled during the turn (if slot filling enabled) |
| `knowledge` | Knowledge base result (if knowledge search is configured) |
| `knowledgeBaseEvents` | Events from a knowledge search |

Add any of these to `flatten_turn_data()` if needed for your use case.

---

## Validating Your Mapping

Run `field_mapping_validator.py` against a raw JSON sample to confirm field names
match before running a full extraction:

```bash
python field_mapping_validator.py raw_extract_sample.json
```
