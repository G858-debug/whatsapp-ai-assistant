# Scenario 2: Available Client Implementation

## Overview
This implementation handles the scenario where a client exists in the database but has no current trainer. It provides a streamlined invitation flow that allows trainers to send invitations to pre-registered clients.

## Implementation Status: ✅ COMPLETE

### Files Updated

1. **services/flows/relationships/trainer_flows/invitation_flow.py**
   - Added `handle_available_client_scenario()` method
   - Added `send_invitation_to_available_client()` method
   - Added `cancel_invitation_to_available_client()` method

2. **services/message_router/handlers/buttons/relationship_buttons.py**
   - Added `_handle_send_invitation()` method
   - Added `_handle_cancel_invitation()` method
   - Updated `handle_relationship_button()` to route new buttons

3. **services/message_router/handlers/buttons/button_handler.py**
   - Updated button routing to include `send_invitation_` and `cancel_invitation_` buttons

## Flow Description

### Step 1: Trainer Views Available Client
When a trainer searches for a client that exists but has no current trainer, the system displays:

```
👤 Client Found

Name: John Doe
Phone: 0821234567
Client ID: CLIENT001
Registered: 15 Nov 2024
Status: Registered, no current trainer

Goals: Weight loss, Muscle gain
Experience: Beginner
Email: john@example.com

Would you like to send a training invitation to John Doe?

[✉️ Send Invitation] [❌ Cancel]
```

### Step 2a: Trainer Sends Invitation
If trainer clicks "Send Invitation":

1. System creates a pending relationship in `trainer_client_list` and `client_trainer_list`
2. Client receives invitation message:

```
🎯 Training Invitation

{Trainer Name} (ID: TRAINER001) has invited you to join as their client!

Trainer Info:
• Specialization: Weight Training
• Experience: 5 years
• Location: Cape Town

Would you like to accept this invitation?

[✅ Accept] [❌ Decline]
```

3. Trainer receives confirmation:

```
✅ Invitation Sent!

Your training invitation has been sent to John Doe.

I'll notify you when they respond.
```

### Step 2b: Trainer Cancels
If trainer clicks "Cancel":

```
✅ Cancelled

Invitation cancelled. No invitation was sent to the client.

You can search for other clients or add a new one anytime.
```

### Step 3: Client Responds

#### 3a: Client Accepts
- Relationship status updated to "active"
- Both parties receive confirmation:

**To Client:**
```
✅ You're now connected with {Trainer Name}!
```

**To Trainer:**
```
✅ John Doe accepted your invitation!
```

#### 3b: Client Declines
- Relationship status updated to "declined"
- Both parties receive notification:

**To Client:**
```
You declined the invitation from {Trainer Name}.
```

**To Trainer:**
```
ℹ️ John Doe declined your invitation.
```

## Usage Example

```python
from services.flows.relationships.trainer_flows.invitation_flow import InvitationFlow
from services.relationships.client_checker import ClientChecker, SCENARIO_AVAILABLE

# Initialize services
checker = ClientChecker(supabase_client)
invitation_flow = InvitationFlow(db, whatsapp, task_service)

# Check client status
result = checker.check_client_status('+27821234567', 'TRAINER001')

if result['scenario'] == SCENARIO_AVAILABLE:
    # Handle available client scenario
    invitation_flow.handle_available_client_scenario(
        trainer_phone='0821234567',
        client_data=result['client_data'],
        trainer_id='TRAINER001'
    )
```

## Database Schema

### Tables Involved

1. **clients** - Contains registered client information
   - client_id (primary key)
   - name
   - whatsapp
   - email
   - fitness_goals
   - experience_level
   - created_at

2. **trainer_client_list** - Tracks relationships from trainer perspective
   - trainer_id
   - client_id
   - connection_status (pending, active, declined)
   - invited_by
   - invited_at
   - updated_at

3. **client_trainer_list** - Tracks relationships from client perspective
   - client_id
   - trainer_id
   - connection_status (pending, active, declined)
   - invited_by
   - invited_at
   - updated_at

## Button IDs

The following button IDs are used in this flow:

- `send_invitation_{client_id}` - Trainer sends invitation to client
- `cancel_invitation_{client_id}` - Trainer cancels invitation
- `accept_trainer_{trainer_id}` - Client accepts trainer invitation (existing)
- `decline_trainer_{trainer_id}` - Client declines trainer invitation (existing)

## Integration with ClientChecker

This flow is designed to work with the ClientChecker service:

```python
# ClientChecker returns SCENARIO_AVAILABLE when:
# 1. Client exists in database
# 2. Client has no active trainer relationship

if result['scenario'] == SCENARIO_AVAILABLE:
    # Client is available - use this flow
    invitation_flow.handle_available_client_scenario(...)
```

## Error Handling

The implementation includes comprehensive error handling:

1. **Client not found** - Returns error message if client_id is invalid
2. **Missing phone number** - Returns error if client has no phone number
3. **Invitation service failure** - Catches and reports invitation sending errors
4. **Button handler errors** - Graceful error handling in button responses

## Key Features

- ✅ Shows complete client information to trainer
- ✅ Simple invitation process (no profile filling needed)
- ✅ Bidirectional relationship tracking
- ✅ Real-time notifications to both parties
- ✅ Handles acceptance and decline scenarios
- ✅ Graceful error handling
- ✅ Integration with existing invitation system

## Testing Checklist

- [ ] Test with valid client that has no trainer
- [ ] Verify client info display is accurate
- [ ] Test "Send Invitation" button
- [ ] Test "Cancel" button
- [ ] Verify invitation message sent to client
- [ ] Test client acceptance flow
- [ ] Test client decline flow
- [ ] Verify both parties receive correct notifications
- [ ] Test error scenarios (invalid client_id, missing phone, etc.)

## Integration Points

### 1. ClientChecker (SCENARIO_AVAILABLE)
Identifies clients that exist but have no trainer

### 2. InvitationService
Uses existing `send_trainer_to_client_invitation()` method

### 3. RelationshipService
Uses existing `approve_relationship()` and `decline_relationship()` methods

### 4. Button Handler System
Integrates with existing button routing infrastructure

## Differences from Other Scenarios

### vs. Scenario 1 (New Client)
- **Scenario 1**: Client doesn't exist, requires full profile creation
- **Scenario 2**: Client exists, only needs invitation (no profile filling)

### vs. Scenario 3 (Already Connected)
- **Scenario 2**: Client has no trainer, can send invitation
- **Scenario 3**: Client already connected, shows relationship status

### vs. Scenario 4 (Has Other Trainer)
- **Scenario 2**: Client available, can invite immediately
- **Scenario 4**: Client has trainer, may require approval or special handling

## Notes

- This is a simplified onboarding flow since the client already has a profile
- No need for profile filling or additional data collection
- Leverages existing invitation and relationship management infrastructure
- Maintains consistency with other invitation flows in the system
- All existing acceptance/decline logic is reused

## South African Context

- Phone format: South African (e.g., 0821234567)
- Timezone: Africa/Johannesburg
- Currency: Rand (R) - not applicable for this flow but used in other scenarios
