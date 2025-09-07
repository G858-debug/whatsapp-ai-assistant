<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0018 -->
<!-- Max Tokens: 8000 -->
<!-- Step 1 of 5 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS
For Step 1, I'll analyze the codebase for occurrences of `completions.create` and `select('content')` that need to be replaced. This requires a review of the AI and database interaction components.

## CHANGES NEEDED

### EDIT: services/ai_intent_core.py

**Change 1:** Update OpenAI/Anthropic API calls
Location: AI response handling function
```python
# REMOVE:
response = client.completions.create(
    model="claude-2",
    prompt=prompt,
    max_tokens=1000
)

# ADD:
response = client.messages.create(
    model="claude-2",
    max_tokens=1000,
    messages=[
        {"role": "user", "content": prompt}
    ]
)
```

### EDIT: services/refiloe.py

**Change 1:** Update database content selection
Location: Message processing function
```python
# REMOVE:
result = db.table('messages').select('content').execute()

# ADD:
result = db.table('messages').select('message_text').execute()
```

### EDIT: services/whatsapp.py

**Change 1:** Update message content handling
Location: Message retrieval function
```python
# REMOVE:
messages = db.table('chat_history').select('content').eq('user_id', user_id).execute()

# ADD:
messages = db.table('chat_history').select('message_text').eq('user_id', user_id).execute()
```

## MIGRATION: 20250325_content_to_message_text.sql
```sql
-- Update column name in relevant tables
ALTER TABLE messages RENAME COLUMN content TO message_text;
ALTER TABLE chat_history RENAME COLUMN content TO message_text;
```

## SUMMARY
- Identified and updated AI API calls from `completions.create` to `messages.create`
- Changed database column selections from `content` to `message_text`
- Created migration for database column renaming
- Files affected: ai_intent_core.py, refiloe.py, whatsapp.py

## CONTINUE_NEEDED
Next step: Step 2: Update dependent functions and error handling
Run @claude @continue to proceed with next step