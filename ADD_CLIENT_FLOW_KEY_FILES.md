# Add-Client Flow - Key Files Summary

## Core Implementation Files

### 1. Flow Definition
- **File**: `/home/user/whatsapp-ai-assistant/whatsapp_flows/trainer_add_client_flow.json`
- **Purpose**: WhatsApp Flow UI definition with 7 interactive screens
- **Key Features**: Dynamic pricing, package deals, comprehensive fitness profile collection
- **Size**: ~470 lines JSON

### 2. Flow Configuration
- **File**: `/home/user/whatsapp-ai-assistant/config/trainer_add_client_inputs.json`
- **Purpose**: Text-based input configuration for fallback flow
- **Fields**: 8 input fields with validation rules
- **Size**: ~110 lines JSON

### 3. Flow Processing & Webhook Handling
- **File**: `/home/user/whatsapp-ai-assistant/services/whatsapp_flow_handler.py`
- **Lines of Interest**:
  - `send_trainer_add_client_flow()` at line 2136
  - `_handle_trainer_add_client_response()` at line 1270
  - `_extract_client_data_from_flow_response()` at line 1400
- **Purpose**: Triggers WhatsApp Flow, handles webhook responses, type conversions
- **Critical**: String-to-float conversion for prices, boolean handling for OptIn

### 4. Text-Based Flow Handler (Fallback)
- **File**: `/home/user/whatsapp-ai-assistant/services/flows/relationships/trainer_flows/creation_flow.py`
- **Key Method**: `continue_create_trainee()` (line 22)
- **Purpose**: Sequential field collection with early client detection
- **Features**: Multi-trainer scenario handling, invitation routing
- **Size**: ~1,300 lines Python

### 5. Validation Service
- **File**: `/home/user/whatsapp-ai-assistant/services/auth/registration/validation_service.py`
- **Key Method**: `validate_field_value()` (line 13)
- **Purpose**: Type-specific field validation (phone, email, choice, etc.)
- **Also provides**: `clean_phone_number()` for normalization

### 6. vCard (Contact) Handling
- **File**: `/home/user/whatsapp-ai-assistant/services/message_handlers/contact_share_handler.py`
- **Key Functions**:
  - `parse_vcard()` - Extracts contact from webhook
  - `handle_contact_message()` - Main orchestrator
  - `send_contact_confirmation_message()` - Confirmation buttons
- **Purpose**: Handle trainer contact sharing via WhatsApp vCard

### 7. Client Status Detection
- **File**: `/home/user/whatsapp-ai-assistant/services/relationships/client_checker.py`
- **Key Class**: `ClientChecker` (line 58)
- **Key Method**: `check_client_status()` (line 80)
- **Purpose**: Determines client scenario (new, available, yours, multi-trainer)
- **Size**: ~325 lines Python

### 8. Button Handlers
- **File**: `/home/user/whatsapp-ai-assistant/services/message_router/handlers/buttons/client_creation_buttons.py`
- **Key Class**: `ClientCreationButtonHandler`
- **Key Method**: `_create_client_account()` (line 156)
- **Purpose**: Handles button responses, creates client accounts
- **Handles**: Approval, rejection, invitations, multi-trainer buttons
- **Size**: ~351 lines Python

### 9. Command Entry Point
- **File**: `/home/user/whatsapp-ai-assistant/services/commands/trainer/relationships/client_management_commands.py`
- **Key Function**: `handle_add_client_command()` (line 9)
- **Purpose**: Entry point for /add-client command
- **Output**: Button message with "Type Details" vs "Share Contact"

### 10. Command Router
- **File**: `/home/user/whatsapp-ai-assistant/services/commands/trainer/trainer_command_handler.py`
- **Key Method**: `handle_create_trainee()` (line 66)
- **Purpose**: Routes /create-trainee command to text-based flow

### 11. Invitation Management (Facade)
- **File**: `/home/user/whatsapp-ai-assistant/services/relationships/invitations/invitation_service.py`
- **Key Class**: `InvitationService` (line 15)
- **Purpose**: Facade for invitation operations
- **Delegates to**: `InvitationManager`

### 12. Invitation Manager (Implementation)
- **File**: `/home/user/whatsapp-ai-assistant/services/relationships/invitations/invitation_manager.py`
- **Key Method**: `send_new_client_invitation()` (line 133)
- **Purpose**: Creates invitations, generates tokens, sends WhatsApp messages
- **Database**: Stores in `client_invitations` table with prefilled_data JSONB
- **Size**: ~150+ lines Python (partial read)

---

## Documentation Files Created

### 1. Comprehensive Analysis
- **File**: `/home/user/whatsapp-ai-assistant/ADD_CLIENT_FLOW_ANALYSIS.md`
- **Size**: 591 lines
- **Contents**:
  - Executive summary
  - Key files overview
  - Service layer details
  - Validation logic
  - State management architecture
  - Database schema integration
  - Testing scenarios
  - Deployment checklist

### 2. File Structure & Data Flow
- **File**: `/home/user/whatsapp-ai-assistant/ADD_CLIENT_FLOW_FILE_STRUCTURE.txt`
- **Size**: 390 lines
- **Contents**:
  - Entry points tree
  - File roles and relationships
  - Data flow examples for all scenarios
  - Validation flow diagrams
  - Configuration reference

### 3. Original Implementation Guide
- **File**: `/home/user/whatsapp-ai-assistant/TRAINER_ADD_CLIENT_FLOW_IMPLEMENTATION.md`
- **Size**: 337 lines
- **Contents**:
  - Type conversions guide
  - Flow structure
  - Database storage format
  - Pricing logic
  - Package deal handling

---

## Key Database Tables

### client_invitations
- Stores pending and accepted invitations
- JSONB column: `trainer_provided_data` or `prefilled_data`
- Statuses: pending, accepted, declined, pending_client_completion
- Tracks: invitation tokens, pricing, multi-trainer relationships

### clients
- Client account records
- Phone: `whatsapp` column (normalized)
- Profile: fitness_goals, experience_level, health_conditions
- Status: active/inactive

### trainer_client_list & client_trainer_list
- Bidirectional relationship tracking
- Connection statuses: pending, active, inactive
- Primary trainer flag for multi-trainer support

---

## Critical Implementation Details

### Type Conversions (WhatsApp Flow)
```python
# String to float (custom prices)
final_price = float(custom_price_amount)

# Boolean handling (OptIn component)
has_package_deal = bool(response_data.get('has_package_deal', False))

# Array handling (CheckboxGroup)
fitness_goals = response_data.get('fitness_goals', [])
preferred_times = response_data.get('preferred_times', [])
```

### Phone Normalization
```
Input: 0821234567 OR +27821234567 OR 27821234567
Stored: 27821234567
Lookup: Match against clients.whatsapp column
```

### Scenario Detection Sequence
1. Check if client exists by phone
2. Check for active relationships
3. Check if this trainer already has relationship
4. Determine scenario (new, available, yours, multi-trainer)

### State Management
- **Text flow**: Task-based (`task_data['step']`, `task_data['collected_data']`)
- **AI follow-up**: Conversation state (`PACKAGE_DEAL_CLARIFICATION`)
- **Flow tokens**: Track WhatsApp Flow submissions

---

## Validation Rules Reference

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| Phone | phone | Yes | 10-15 digits, ^[0-9]{10,15}$ |
| Full Name | text | Yes | 2-100 characters |
| Email | email | No | @ and . validation |
| Fitness Goals | multi_choice | Yes | Select from options |
| Experience | choice | Yes | Beginner/Intermediate/Advanced |
| Health Conditions | textarea | No | Max 500 chars, allow skip |
| Availability | multi_choice | Yes | Select from 5 time slots |
| Training Type | multi_choice | No | Allow skip |
| Pricing | text | No (conditional) | String to float, must > 0 |
| Package Details | textarea | No (conditional) | Triggers AI clarification if vague |

---

## Integration Points

### 1. With WhatsApp API
- Flow ID: Line 2216 in `whatsapp_flow_handler.py`
- Webhook endpoint: `/webhooks/whatsapp-flow`
- Message types: Interactive flows with buttons

### 2. With AI Intent Handler
- Detects: `/create-trainee` command
- Sets conversation state: `PACKAGE_DEAL_CLARIFICATION`
- Routes: To `TrainerCommandHandler`

### 3. With Subscription Manager
- Checks: `can_add_client(trainer_id)`
- Limits: Max clients per subscription tier
- Blocks: If limit reached

### 4. With Relationship Management
- Creates: Pending relationships
- Approves: On client acceptance
- Handles: Multi-trainer secondary relationships
- Notifies: Both trainer and client

---

## Testing Recommendations

### Unit Tests
- Phone number normalization
- Field validation (all types)
- Type conversions (string to float, boolean)
- vCard parsing
- Client status detection

### Integration Tests
- WhatsApp Flow webhook processing
- Text-based field collection
- Client creation with all scenarios
- Relationship creation and approval
- Multi-trainer scenario handling

### End-to-End Tests
- Trainer adds client via Flow (Scenario 1)
- Trainer creates client via text (Scenario 2)
- Trainer shares contact (Scenario 3)
- Trainer adds existing client with different trainer (Scenario 4)

---

## Deployment Notes

### Required Configuration
- [ ] Flow ID from Meta Business Manager (Line 2216)
- [ ] Webhook endpoint registered
- [ ] Database columns verified (JSONB support)
- [ ] Phone normalization utility available
- [ ] TimeZone: Africa/Johannesburg

### Default Values
- Default price per session: R500
- Max phone length: 15 digits
- Min phone length: 10 digits
- Invitation token length: 16 (urlsafe)

### Environment Variables
- Flow ID configuration
- Supabase connection
- WhatsApp API token
- (Optional) Package deal AI provider

---

## Quick Navigation Map

```
Entry Points:
/add-client          → client_management_commands.py
/create-trainee      → trainer_command_handler.py → creation_flow.py

Flow Processing:
trainer_add_client_flow.json → whatsapp_flow_handler.py → send_trainer_add_client_flow()
webhook response             → _handle_trainer_add_client_response()
                            → _extract_client_data_from_flow_response()

Validation:
Text input → validation_service.py → validate_field_value()
Flow data  → whatsapp_flow_handler.py → Type conversions

Client Management:
Client lookup    → client_checker.py → ClientChecker
vCard parsing    → contact_share_handler.py → parse_vcard()
Account creation → client_creation_buttons.py → _create_client_account()

Invitations:
Send invitation → invitation_manager.py → send_new_client_invitation()
Button handling → client_creation_buttons.py → handle_invitation_button()
```

