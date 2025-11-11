# WhatsApp AI Assistant - Add Client Flow Implementation Analysis

## Executive Summary

The add-client flow is a comprehensive system that allows trainers to add new clients to their roster through multiple input methods:
1. **WhatsApp Flows** - Modern interactive UI with dynamic pricing and package deals
2. **Text-based Input** - Sequential questions for clients who prefer text
3. **vCard (Contact Sharing)** - Direct contact import via WhatsApp

The system supports multiple scenarios:
- **Scenario 1**: New client (doesn't exist in system)
- **Scenario 2**: Available client (exists but no active trainer)
- **Scenario 3**: Already your client (trainer-client relationship exists)
- **Scenario 4**: Multi-trainer scenario (client has different trainer)

---

## Key Files Overview

### 1. Flow Definition Files

#### **whatsapp_flows/trainer_add_client_flow.json**
- **Purpose**: Defines the WhatsApp Flow UI for trainers adding clients
- **Screens**: 7 interactive screens
  1. WELCOME - Introduction with trainer's default price
  2. CLIENT_INFO - Name, phone, email collection
  3. FITNESS_GOALS - Goals (checkbox), specific goals, experience level
  4. TRAINING_SCHEDULE - Sessions per week, preferred times
  5. HEALTH_INFO - Health conditions, medications, notes
  6. PRICING - Dynamic pricing (default vs custom) + package deals
  7. CONFIRMATION - Review and submit

- **Key Features**:
  - Dynamic pricing display using trainer's default_price_per_session
  - Package deal support with OptIn component
  - Comprehensive fitness profile collection
  - Data validation through helper text and input types

#### **config/trainer_add_client_inputs.json**
- **Purpose**: Configuration for text-based add-client collection
- **Fields**: 8 input fields with validation rules
  - Phone number (required, pattern validation: 10-15 digits)
  - Full name (required, 2-100 characters)
  - Email (optional, pattern validation)
  - Fitness goals (multi-choice)
  - Experience level (single choice)
  - Health conditions (optional textarea, max 500 chars)
  - Availability (multi-choice)
  - Preferred training type (optional multi-choice)

---

### 2. Service Layer Files

#### **services/whatsapp_flow_handler.py**
**Location**: Line 1270, Line 2136

**Key Methods**:
1. **`send_trainer_add_client_flow(trainer_phone, trainer_id=None)`** (Line 2136)
   - Triggers the WhatsApp Flow for trainers
   - Passes trainer's default_price_per_session as initial data
   - Generates flow token for tracking
   - Handles flow ID routing to Meta's WhatsApp API

2. **`_handle_trainer_add_client_response(flow_response, phone_number, flow_token)`** (Line 1270)
   - Processes completed flow submissions
   - Extracts and validates client data
   - Checks subscription limits
   - Validates phone numbers
   - Detects duplicate clients
   - Routes to invitation or direct creation
   - Handles package deal clarification

3. **`_extract_client_data_from_flow_response(flow_response, trainer_phone)`** (Line 1400)
   - **CRITICAL TYPE CONVERSIONS**:
     - `has_package_deal`: boolean → use directly from OptIn
     - `custom_price_amount`: string → float conversion
     - `fitness_goals`: array of strings from CheckboxGroup
     - `preferred_times`: array of strings from CheckboxGroup
     - `sessions_per_week`: string from RadioButtonsGroup

**Type Conversion Examples**:
```python
# Boolean handling for OptIn component
has_package_deal = response_data.get('has_package_deal', False)
if isinstance(has_package_deal, str):
    has_package_deal = has_package_deal.lower() in ('true', 'yes', '1')
else:
    has_package_deal = bool(has_package_deal)

# String to float conversion for pricing
custom_price_amount = response_data.get('custom_price_amount', '').strip()
if pricing_choice == 'custom_price' and custom_price_amount:
    try:
        final_price = float(custom_price_amount)
    except (ValueError, TypeError):
        log_warning(f"Invalid custom price: {custom_price_amount}")
```

#### **services/flows/relationships/trainer_flows/creation_flow.py**
**Purpose**: Text-based flow for /create-trainee command (fallback from WhatsApp Flow)

**Key Method**: `continue_create_trainee(phone, message, trainer_id, task)`

**Flow Steps**:
1. Ask if create new or link existing
2. Load trainer_add_client_inputs.json fields
3. Collect fields sequentially with validation
4. **Early Client Detection**: Checks if client exists after phone number field
   - If exists with active trainer → Multi-trainer scenario
   - If exists without trainer → Ask to invite instead
5. Send invitation with prefilled data

**Validation Logic**:
- Uses `registration_service.validate_field_value()` if available
- Falls back to `_validate_field_value()` for basic validation
- Phone number cleaning and normalization

---

### 3. Validation & Input Processing

#### **services/auth/registration/validation_service.py**
**Class**: `ValidationService`

**Key Method**: `validate_field_value(field, value) → (is_valid, error_message)`

**Validation Rules**:
- **Required fields**: Non-empty after strip, not 'skip'
- **Email**: Contains '@' and '.' after @
- **Phone**: Digits only, min 10 digits
- **Numbers**: Min/max range validation
- **Text/TextArea**: Min/max length validation
- **Choice/Multi-choice**: Selection within option range
- **Length validation**: min_length/max_length parameters

**Also provides**:
- `clean_phone_number()`: Removes non-digits, adds country code

#### **services/auth/registration/field_manager.py**
- Provides field configuration management
- `get_trainer_add_client_fields()` method

---

### 4. Client & Contact Management

#### **services/message_handlers/contact_share_handler.py**
**Purpose**: Handles vCard contact messages shared by trainers

**Key Functions**:
1. **`parse_vcard(webhook_data) → Dict`**
   - Extracts contact from WhatsApp webhook payload
   - Returns: name, first_name, last_name, phones, emails, phone (primary)
   - Prefers mobile/cell numbers as primary

2. **`create_contact_confirmation_task(trainer_phone, contact_data, task_service, role)`**
   - Creates task to confirm shared contact details
   - Sets task_data['step'] = 'confirm_shared_contact'

3. **`send_contact_confirmation_message(trainer_phone, contact_data, whatsapp_service)`**
   - Sends button message with contact details
   - Options: "✅ Yes, Continue" or "❌ Edit Details"

4. **`handle_contact_message(trainer_phone, webhook_data, task_service, whatsapp_service, role)`**
   - Main handler that orchestrates the contact flow
   - Returns: {'success': bool, 'response': str, 'handler': str}

#### **services/relationships/client_checker.py**
**Class**: `ClientChecker`

**Purpose**: Determines which scenario applies when adding a client

**Scenarios**:
- `SCENARIO_NEW`: Client doesn't exist
- `SCENARIO_AVAILABLE`: Client exists but no active trainer
- `SCENARIO_ALREADY_YOURS`: Trainer already has this client
- `SCENARIO_HAS_OTHER_TRAINER`: Client has different active trainer

**Key Method**: `check_client_status(phone_number, trainer_id) → Dict`

**Relationship Checks**:
- Query `clients` table by whatsapp (normalized phone)
- Query `client_trainer_list` for active relationships (connection_status = 'active')
- Lookup specific trainer-client relationships in `trainer_client_list`

---

### 5. Button Handlers & Command Handlers

#### **services/message_router/handlers/buttons/client_creation_buttons.py**
**Class**: `ClientCreationButtonHandler`

**Handles**:
1. **New client creation buttons**:
   - `approve_new_client_{trainer_id}`
   - `reject_new_client_{trainer_id}`

2. **Invitation buttons (Scenario 1A)**:
   - `accept_invitation_{trainer_id}`
   - `decline_invitation_{trainer_id}`
   - `accept_multi_trainer_{trainer_id}` / `decline_multi_trainer_{trainer_id}`

**Methods**:
- **`_create_client_account(phone, trainer_id, prefilled_data, invitation_id)`**
  - Creates new client record in `clients` table
  - Creates user entry in `users` table
  - Creates relationship with immediate approval
  - Maps prefilled_data fields correctly
  - Handles email/None fields gracefully

- **`_send_approval_notifications(phone, trainer_id, client_id, prefilled_data)`**
  - Notifies client of account creation
  - Notifies trainer of new client

#### **services/commands/trainer/relationships/client_management_commands.py**
**Function**: `handle_add_client_command(phone, trainer_id, db, whatsapp, task_service)`

**Purpose**: Entry point for /add-client command

**Output**: Button message with two options:
1. "Type Details" - Text-based input flow
2. "Share Contact" - vCard input flow

---

### 6. Invitation System

#### **services/relationships/invitations/invitation_service.py**
**Class**: `InvitationService`

**Delegates to**: `InvitationManager`

**Methods**:
- `send_trainer_to_client_invitation(trainer_id, client_id, client_phone)`
- `send_client_to_trainer_invitation(client_id, trainer_id, trainer_phone)`
- `send_new_client_invitation(trainer_id, client_data, client_phone)`
- `create_relationship(trainer_id, client_id, invited_by, invitation_token=None)`

#### **services/relationships/invitations/invitation_manager.py**
**Class**: `InvitationManager`

**Key Method**: `send_new_client_invitation(trainer_id, client_data, client_phone)`

**Process**:
1. Get trainer info
2. Generate invitation token
3. Store in `client_invitations` table with status:
   - `pending_client_completion` - for Scenario 1A (client fills profile)
   - `pending` - for other scenarios
4. Send WhatsApp invitation message with buttons
5. Create pending relationship
6. Store complete prefilled_data as JSONB

**Invitation Statuses**:
- `pending`: Waiting for client to accept/decline
- `pending_client_completion`: Client needs to complete profile via flow
- `accepted`: Client accepted and account created
- `declined`: Client rejected invitation

---

## State Management Architecture

### Task-Based State Management

**Task Flow**:
```
1. Command triggered (/create-trainee, /add-client)
   ↓
2. Create task with initial state
   task_data = {
       'step': 'ask_create_or_link',  // or 'choosing_input_method'
       'trainer_id': trainer_id,
       'collected_data': {},
       'fields': [] // loaded from config
   }
   ↓
3. Process user message, validate, update state
   task_data['step'] = 'collecting'
   task_data['current_field_index'] = 1
   ↓
4. Detect scenarios during collection
   - Early detection after phone field
   - Full validation after all fields
   ↓
5. Create invitation/account and complete task
```

**Multi-Trainer Scenario Handling**:
```
task_data['multi_trainer_step'] = 'show_warning'
                                  'await_send_choice'
                                  'ask_pricing'
                                  'await_pricing_choice'
                                  'await_custom_price'
                                  'ask_profile_completion'
                                  'await_profile_completion_choice'
```

### Conversation State Management

**For Package Deal Clarification**:
```python
refiloe_service.update_conversation_state(
    phone_number,
    'PACKAGE_DEAL_CLARIFICATION',
    clarification_context
)
```

State persists across messages for AI to understand context.

---

## Database Schema Integration

### client_invitations Table
```json
{
  "id": "uuid (primary key)",
  "trainer_id": "uuid (foreign key to trainers.id)",
  "client_phone": "string",
  "client_name": "string",
  "client_email": "string (optional)",
  "invitation_token": "string",
  "status": "string (pending | accepted | declined | pending_client_completion)",
  "profile_completion_method": "string (trainer_fills | client_fills)",
  "trainer_provided_data": "JSONB (complete prefilled data)",
  "custom_price_per_session": "numeric (optional)",
  "is_secondary_trainer": "boolean (for multi-trainer)",
  "prefilled_data": "JSONB (legacy field, for backward compatibility)",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "accepted_at": "timestamp (optional)",
  "declined_at": "timestamp (optional)"
}
```

### clients Table
```json
{
  "client_id": "string (unique)",
  "whatsapp": "string (phone)",
  "name": "string",
  "email": "string (optional)",
  "fitness_goals": "string",
  "experience_level": "string",
  "health_conditions": "string (optional)",
  "availability": "string",
  "preferred_training_times": "string",
  "status": "string (active | inactive)",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### trainer_client_list & client_trainer_list
- Bidirectional relationship tracking
- Statuses: pending, active, inactive
- primary_trainer flag (for multi-trainer)

---

## Validation Logic Flow

### Phone Number Validation
```
Input (any format) → normalize_phone_number() → check format
                  → validate_phone_number()
                  → Check if exists in clients
                  → Return formatted phone
```

**Normalization Rules**:
- Remove all non-digits
- Convert 0-prefix SA numbers to 27-prefix
- Ensure 10-15 digit range

### Email Validation
```
Input → Check @ exists → Check . after @
     → Length check (optional field) → Valid
```

### Choice Validation
```
Input → Parse as integer → Check range (1 to num_options)
     → Return selected option text
```

### Multi-Choice Validation
```
Input → Split by comma → Parse each as integer
     → Check all in range → Return array of options
```

---

## Pricing Logic

### Default Price Handling
```
trainer.default_price_per_session = null/0 → Use R500
                                           → Pass to flow
                                           → Display on WELCOME & PRICING screens
```

### Custom Price Handling
```
User selects "Custom Price" on PRICING screen
                          ↓
Enters price (string, e.g., "350")
                          ↓
_extract_client_data_from_flow_response() converts to float
                          ↓
Validates (must be > 0)
                          ↓
Stores in client_invitations as custom_price_per_session
```

### Price Determination Logic
```
if pricing_choice == "use_default":
    actual_price = trainer.default_price_per_session
elif pricing_choice == "custom_price":
    actual_price = float(custom_price_amount)  // Already converted
```

---

## Package Deal Processing

### Vague Package Detection
```python
def _check_package_needs_clarification(package_details: str) -> bool:
    """Check if package deal needs AI clarification"""
    vague_phrases = ['tbd', 'discuss', 'flexible', 'to be determined']
    
    # Missing critical info
    if len(package_details) < 10:
        return True
    
    # Contains vague phrases
    if any(phrase in package_details.lower() for phrase in vague_phrases):
        return True
    
    return False
```

### Clarification Flow
```
Package deal marked with vague details
                    ↓
Set conversation state: PACKAGE_DEAL_CLARIFICATION
                    ↓
AI handles follow-up questions:
• How many sessions are included?
• What's the total package price?
• What's the package duration?
                    ↓
Parse AI response into structured format:
{
  "sessions_count": int,
  "total_price": float,
  "duration_days": int,
  "expiry_date": "YYYY-MM-DD" or null,
  "terms": "string"
}
```

---

## Error Handling & Validation Responses

### Field Validation Errors
```
❌ {error_message}

{previous_field['prompt']}
```
User must re-enter value

### Phone Number Validation Errors
```
❌ Invalid phone number: {error_details}
   (e.g., "Must be 10-15 digits with country code")
```

### Duplicate Client Errors
```
❌ You already have a client with phone number {phone}
```

### Subscription Limit Errors
```
❌ You've reached your client limit of {max_clients}
   Please upgrade your subscription.
```

---

## Integration Points

### 1. With AI Intent Handler
- Detects /create-trainee command
- Routes to `TrainerCommandHandler.handle_create_trainee()`
- For package deal clarification, sets conversation state
- AI processes follow-up questions in context

### 2. With WhatsApp Flow System
- Registers flow in `whatsapp_flows/flow_config.json`
- Flow ID from Meta Business Manager (Line 2216 in whatsapp_flow_handler.py)
- Webhook receives flow completions at `/webhooks/whatsapp-flow`

### 3. With Relationship Management
- Creates pending relationship entries
- Approves relationship when client accepts
- Handles multi-trainer relationships
- Notifies both trainer and client

### 4. With Subscription Manager
- Checks client limit before creating
- Blocks if limit reached
- Returns max_clients info

---

## Testing Scenarios

### Scenario 1: New Client (WhatsApp Flow)
1. Trainer sends message triggering flow
2. Completes all 7 screens
3. Flow webhook processes response
4. New client invitation sent with prefilled data
5. Client accepts via button
6. Client account created
7. Relationship approved

### Scenario 2: Existing Client (Text-based)
1. Trainer uses /create-trainee
2. Enters client phone number
3. System detects client exists
4. Trainer asked to send invitation instead
5. Client accepts invitation
6. Relationship created

### Scenario 3: vCard Contact
1. Trainer shares contact via WhatsApp
2. vCard parsed and confirmed
3. Confirmation buttons sent
4. Trainer edits if needed
5. Creates task to collect additional info

### Scenario 4: Multi-Trainer
1. Trainer adds client with different trainer
2. Warning message with current trainer info
3. If trainer continues:
   - Asks about pricing
   - Asks about profile completion method
   - Sends invitation with multi-trainer note
   - Notifies current trainer

---

## Deployment Checklist

- [ ] Upload trainer_add_client_flow.json to Meta Business Manager
- [ ] Get Flow ID from Meta and update Line 2216
- [ ] Ensure webhook endpoint is registered
- [ ] Verify all database tables exist with required columns
- [ ] Test phone number normalization
- [ ] Test price conversions (string to float)
- [ ] Test vCard parsing
- [ ] Test multi-trainer scenarios
- [ ] Verify subscription limit checks work
- [ ] Test package deal clarification triggering

---

## Key Implementation Notes

1. **Type Safety**: Flow responses arrive as strings; Python conversions are critical
2. **Phone Normalization**: Must be consistent across all table lookups
3. **Early Detection**: Client existence checked after phone field to avoid wasted input
4. **Task Persistence**: State maintained in task_data across message exchanges
5. **Relationship Creation**: Immediately creates pending relationship, approves on acceptance
6. **Multi-trainer Support**: Secondary relationships tracked separately
7. **Graceful Degradation**: WhatsApp Flow falls back to text-based input
8. **vCard Integration**: Seamless contact import with confirmation workflow

