# Trainer Add Client Flow Implementation

## Overview
This implementation provides a comprehensive WhatsApp Flow for trainers to add new clients with full profile information, dynamic pricing, and package deal support.

## Implementation Status: ✅ COMPLETE

### Files Updated

1. **whatsapp_flows/trainer_add_client_flow.json**
   - Comprehensive flow with 7 screens
   - Collects client contact, fitness goals, schedule, health info, and pricing
   - Supports dynamic pricing display and package deals

2. **services/whatsapp_flow_handler.py**
   - Updated `_extract_client_data_from_flow_response()` with proper type conversions
   - Updated `_create_and_send_invitation()` to store trainer_provided_data in JSONB
   - Added `send_trainer_add_client_flow()` to trigger flow with dynamic pricing data
   - Package deal handling already implemented in `_handle_trainer_add_client_response()`

## Flow Structure

### Screens:
1. **WELCOME** - Introduction with trainer's default price
2. **CLIENT_INFO** - Name, phone, email
3. **FITNESS_GOALS** - Goals (CheckboxGroup), specific goals, experience level
4. **TRAINING_SCHEDULE** - Sessions per week, preferred times
5. **HEALTH_INFO** - Health conditions, medications, notes
6. **PRICING** - Dynamic pricing (use default or custom) + package deals
7. **CONFIRMATION** - Review and submit

## Type Conversions (CRITICAL)

WhatsApp Flows return data as strings in most cases. Proper conversions happen in Python:

### Input Types from Flow:
- `has_package_deal`: **boolean** (OptIn component) - use directly
- `custom_price_amount`: **string** -> convert to `float` in Python
- `sessions_per_week`: **string** (RadioButtonsGroup) - keep as string
- `fitness_goals`: **array of strings** (CheckboxGroup)
- `preferred_times`: **array of strings** (CheckboxGroup)

### Conversion Logic in `_extract_client_data_from_flow_response()`:

```python
# has_package_deal: boolean from OptIn
has_package_deal = response_data.get('has_package_deal', False)
if isinstance(has_package_deal, str):
    has_package_deal = has_package_deal.lower() in ('true', 'yes', '1')
else:
    has_package_deal = bool(has_package_deal)

# custom_price_amount: string -> float
custom_price_amount = response_data.get('custom_price_amount', '').strip()
final_price = None
if pricing_choice == 'custom_price' and custom_price_amount:
    try:
        final_price = float(custom_price_amount)
    except (ValueError, TypeError):
        log_warning(f"Invalid custom price: {custom_price_amount}")

# fitness_goals: array
fitness_goals = response_data.get('fitness_goals', [])
if isinstance(fitness_goals, str):
    fitness_goals = [goal.strip() for goal in fitness_goals.split(',')]
```

## Flow Data Structure

### Expected from Webhook:
```json
{
  "client_name": "string",
  "client_phone": "string",
  "client_email": "string",
  "fitness_goals": ["array", "of", "strings"],
  "specific_goals": "string",
  "experience_level": "string",
  "sessions_per_week": "string",
  "preferred_times": ["array", "of", "strings"],
  "pricing_choice": "string (use_default or custom_price)",
  "custom_price_amount": "string (convert to float)",
  "has_package_deal": boolean,
  "package_deal_details": "string",
  "health_conditions": "string",
  "medications": "string",
  "additional_notes": "string",
  "trainer_filled": "true"
}
```

## Database Storage

### client_invitations Table:
```json
{
  "trainer_id": "uuid",
  "client_phone": "string",
  "client_name": "string",
  "client_email": "string",
  "invitation_token": "uuid",
  "status": "pending_client_acceptance",
  "profile_completion_method": "trainer_fills",
  "trainer_provided_data": {
    "name": "string",
    "email": "string",
    "fitness_goals": ["array"],
    "specific_goals": "string",
    "experience_level": "string",
    "sessions_per_week": "string",
    "preferred_times": ["array"],
    "health_conditions": "string",
    "medications": "string",
    "additional_notes": "string",
    "pricing_choice": "string",
    "custom_price": float,
    "has_package_deal": boolean,
    "package_deal_details": "string"
  },
  "pricing_choice": "string",
  "custom_price": float,
  "has_package_deal": boolean,
  "package_deal_details": "string",
  "expires_at": "ISO datetime"
}
```

## Pricing Logic

### Determine Actual Price:
```python
if pricing_choice == "use_default":
    # Use trainer's default_price_per_session
    actual_price = trainer.default_price_per_session

if pricing_choice == "custom_price":
    # Convert custom_price_amount to float
    actual_price = float(custom_price_amount)
```

### Default Price Handling:
- If trainer has no `default_price_per_session` set, use R500 as default
- Price is passed to flow as initial data: `data.trainer_default_price`
- Cascades through all flow screens

## Package Deal Handling

### When Client Creates Profile:
```python
if has_package_deal == true AND package_deal_details is not empty:
    if needs_clarification(package_deal_details):
        # Create AI clarification task
        # Ask: sessions count, total price, duration, expiry
        # Parse into structured format

    # Store in database as JSONB:
    package_info = {
        "sessions_count": int,
        "total_price": float,
        "duration_days": int,
        "expiry_date": "YYYY-MM-DD" or null,
        "terms": "string"
    }
```

### Clarification Check:
The `_check_package_needs_clarification()` method checks if package details are vague:
- Missing session count or price
- Contains vague phrases: "tbd", "discuss", "flexible", etc.
- Too short (< 10 characters)

If clarification needed, sets conversation state to `PACKAGE_DEAL_CLARIFICATION` for AI follow-up.

## Invitation Flow

### Trainer-Filled Profile Invitation:
Different message than regular invitation - shows ALL pre-filled information:

```
🎯 Training Profile Created

Hi {name}! 👋

{trainer_name} has created a fitness profile for you...

📋 Your Pre-filled Profile:
• Name: {name}
• Email: {email}
• Goals: {goals}
• Experience: {level}
• Sessions/week: {sessions}
• Price: R{price} per session
• Package Deal: {details} (if applicable)

👨‍🏫 Your Trainer:
• {trainer_name}
• {business_name}

✅ Review and Accept

Reply 'ACCEPT' to start training!
Reply 'CHANGES' if you need to update any information.
```

## Flow Trigger

### How to Trigger Flow:
```python
from services.whatsapp_flow_handler import WhatsAppFlowHandler

flow_handler = WhatsAppFlowHandler(supabase, whatsapp_service)

# Method 1: With trainer phone only
result = flow_handler.send_trainer_add_client_flow(trainer_phone="0821234567")

# Method 2: With trainer ID
result = flow_handler.send_trainer_add_client_flow(
    trainer_phone="0821234567",
    trainer_id="uuid-here"
)
```

### What Gets Passed to Flow:
```python
flow_action_payload = {
    "screen": "WELCOME",
    "data": {
        "trainer_default_price": 500  # From trainer.default_price_per_session
    }
}
```

This price cascades to:
- PRICING screen: Displays in RadioButton option "Use standard rate (R500)"

## Error Handling

### Validation:
1. ✅ Phone number format validation
2. ✅ Client duplicate check (using ClientChecker)
3. ✅ Custom price validation (must be valid number)
4. ✅ Handle missing trainer default price (use R500)
5. ✅ Handle empty package_deal_details gracefully

### Error Responses:
```python
{
    'success': False,
    'error': 'Invalid phone number: {error_details}'
}

{
    'success': False,
    'error': 'You already have a client with phone number {phone}'
}
```

## Integration Points

### 1. ClientChecker (Prompt 3.1)
- Used to check for duplicate clients before creating invitation

### 2. Invitation System
- Stores all data in `client_invitations` table
- Status: `pending_client_acceptance`
- Profile completion method: `trainer_fills`

### 3. AI Clarification
- Triggers for vague package deals
- Uses conversation state: `PACKAGE_DEAL_CLARIFICATION`
- Parses AI responses into structured package_info

## Setup Requirements

### 1. Flow Registration
Flow must be registered in `whatsapp_flows/flow_config.json` (already done):
```json
{
  "trainer_add_client_flow": {
    "id": "trainer_add_client_flow",
    "name": "Add New Client",
    "description": "Trainer adds a new client to their roster",
    "file": "trainer_add_client_flow.json",
    "endpoint": "https://web-production-26de5.up.railway.app/webhooks/whatsapp-flow",
    "categories": ["OTHER"],
    "status": "DRAFT"
  }
}
```

### 2. Meta Flow ID
**IMPORTANT**: Replace `YOUR_FLOW_ID_HERE` in `send_trainer_add_client_flow()` with actual flow ID from Meta Business Manager after uploading the flow.

Line 2216 in whatsapp_flow_handler.py:
```python
"flow_id": "YOUR_FLOW_ID_HERE",  # Replace with actual flow ID from Meta
```

### 3. Database Schema
Ensure `client_invitations` table has these columns:
- `trainer_provided_data` (JSONB)
- `profile_completion_method` (TEXT)
- `status` (TEXT) - supports 'pending_client_acceptance'
- `custom_price` (NUMERIC)
- `has_package_deal` (BOOLEAN)
- `package_deal_details` (TEXT)

## Testing Checklist

- [ ] Upload flow JSON to Meta Business Manager
- [ ] Get flow ID and update in code (line 2216)
- [ ] Test flow trigger with trainer phone
- [ ] Verify dynamic pricing displays correctly
- [ ] Test custom pricing (string to float conversion)
- [ ] Test package deal with OptIn (boolean handling)
- [ ] Test fitness goals CheckboxGroup (array handling)
- [ ] Test invitation message generation
- [ ] Test vague package deal -> AI clarification trigger
- [ ] Verify all data stored in trainer_provided_data JSONB
- [ ] Test client acceptance flow

## South African Context

- Currency: Rand (R)
- Phone format: South African (e.g., 0821234567)
- Default pricing: R500 per session
- Timezone: Africa/Johannesburg

## Notes

- All fields are properly typed and converted in Python backend
- Flow JSON is strict about types - conversions MUST happen server-side
- OptIn component (has_package_deal) returns boolean natively
- Number inputs with type "text" return strings - convert in Python
- trainer_default_price cascades through all flow screens
- Package deal clarification is optional and AI-driven
