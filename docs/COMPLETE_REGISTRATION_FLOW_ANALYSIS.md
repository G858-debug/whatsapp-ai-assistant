# Complete Registration Flow Analysis

## Scenario 1: New User Types "hi" (or any random message)

```
1. routes/webhooks.py
   └─> whatsapp_webhook() receives "hi"

2. services/message_router/message_router.py
   └─> MessageRouter.route_message(phone, "hi")
   └─> No button_id
   └─> No running registration task
   └─> User doesn't exist in database

3. services/message_router/handlers/new_user_handler.py
   └─> NewUserHandler.handle_new_user(phone, "hi")
   └─> "hi" doesn't match "trainer" or "client" keywords
   └─> _show_welcome_message(phone)

4. ✅ User receives:
   "👋 Hi, I'm Refiloe!

   I'm your AI fitness assistant...

   [Button: I'm a Trainer]
   [Button: I need a Trainer]"
```

**Task Status**: ❌ No task created
**User can type**: ✅ Yes, anytime

---

## Scenario 2: New User Types "trainer"

```
1. routes/webhooks.py
   └─> whatsapp_webhook() receives "trainer"

2. services/message_router/message_router.py
   └─> MessageRouter.route_message(phone, "trainer")
   └─> No button_id
   └─> No running registration task
   └─> User doesn't exist

3. services/message_router/handlers/new_user_handler.py
   └─> NewUserHandler.handle_new_user(phone, "trainer")
   └─> ✅ Matches "trainer" keyword
   └─> Routes to RegistrationButtonHandler

4. services/message_router/handlers/buttons/registration_buttons.py
   └─> RegistrationButtonHandler._handle_register_trainer(phone)
   └─> WhatsAppFlowTrainerOnboarding.send_flow(phone)

5. services/flows/whatsapp_flow_trainer_onboarding.py
   └─> send_flow(phone)
   └─> Generates flow_token: "trainer_onboarding_{phone}_{timestamp}"
   └─> Saves flow_token to database (flow_tokens table)
   └─> Sends WhatsApp Flow message

6. ✅ User receives WhatsApp Flow form
   "🚀 Get Ready!
   Let's set up your trainer profile!
   [Start Setup button]"
```

**Task Status**: ❌ No task created (Flow-based, not task-based)
**User can type**: ✅ Yes, anytime (Flow doesn't block messaging)
**Flow token saved**: ✅ Yes, in `flow_tokens` table with status='active'

---

## Scenario 3: New User Clicks "💪 I'm a Trainer" Button

```
1. routes/webhooks.py
   └─> whatsapp_webhook() receives button_id='register_trainer'

2. services/message_router/message_router.py
   └─> MessageRouter.route_message(phone, button_id='register_trainer')
   └─> ✅ Detects button_id exists
   └─> Routes to ButtonHandler

3. services/message_router/handlers/buttons/button_handler.py
   └─> ButtonHandler.handle_button_response(phone, 'register_trainer')
   └─> Routes to RegistrationButtonHandler

4. services/message_router/handlers/buttons/registration_buttons.py
   └─> RegistrationButtonHandler._handle_register_trainer(phone)
   └─> WhatsAppFlowTrainerOnboarding.send_flow(phone)

5-6. [Same as Scenario 2]
```

**Task Status**: ❌ No task created
**User can type**: ✅ Yes, anytime
**Flow token saved**: ✅ Yes

---

## Scenario 4a: User Submits Flow (Completes Registration Successfully)

```
1. User fills out WhatsApp Flow form and clicks "Submit"

2. WhatsApp sends webhook to routes/webhooks.py
   └─> whatsapp_webhook() receives interactive message type='nfm_reply'

3. handlers/flow_response_handler.py
   └─> process_flow_webhook(webhook_data, supabase, whatsapp)
   └─> Extracts flow_data from webhook
   └─> Detects flow_token contains "trainer_onboarding"
   └─> Routes to WhatsAppFlowTrainerOnboarding

4. services/flows/whatsapp_flow_trainer_onboarding.py
   └─> process_flow_completion(flow_data, phone)

   Steps:
   a. Validates required fields (first_name, surname, email, terms_accepted)
   b. Checks if trainer already exists (by phone or email)
   c. Generates trainer_id (e.g., "TR_JOHN_123")
   d. Saves to trainers table with status='active'
   e. Updates users table to link phone → trainer_id
   f. Sends confirmation message

5. ✅ User receives:
   "🎊 Welcome aboard, John!

   Your trainer profile is now active. 🚀

   ✅ Registration complete
   📧 Email: john@example.com
   ...

   Type 'help' anytime to see what I can do!"

6. Database Changes:
   ├─> trainers table: New row created
   │   ├─ trainer_id: "TR_JOHN_123" (VARCHAR)
   │   ├─ whatsapp: phone number
   │   ├─ status: 'active'
   │   └─ onboarding_method: 'flow'
   │
   ├─> users table: New/updated row
   │   ├─ phone_number: phone
   │   └─ trainer_id: "TR_JOHN_123"
   │
   └─> flow_tokens table: Updated
       ├─ status: 'active' → 'completed'
       └─ completed_at: timestamp
```

**Task Status**: ❌ No task
**User can type**: ✅ Yes, immediately
**Flow token**: ✅ Marked as 'completed'
**Registration complete**: ✅ Yes

---

## Scenario 4b: User Submits Flow with Validation Errors

```
1. User fills WhatsApp Flow but misses required fields
2. WhatsApp sends webhook
3. handlers/flow_response_handler.py processes webhook
4. services/flows/whatsapp_flow_trainer_onboarding.py
   └─> process_flow_completion()
   └─> Validation fails
   └─> Updates flow_tokens: status='failed'

5. Database Changes:
   └─> flow_tokens table: Updated
       ├─ status: 'active' → 'failed'
       ├─ error: 'Validation errors: ...'
       └─> completed_at: timestamp
```

**Task Status**: ❌ No task
**User can type**: ✅ Yes
**Flow token**: ✅ Marked as 'failed'
**User can retry**: ✅ Yes

---

## Scenario 4c: User Abandons Flow (Closes Without Submitting)

```
1. User receives WhatsApp Flow form
2. User closes form without submitting
3. ❌ No webhook sent
4. Flow token remains status='active'

If user types "trainer" again:

5. routes/webhooks.py receives "trainer"
6. message_router.py → new_user_handler.py
7. registration_buttons.py → send_flow()
8. services/flows/whatsapp_flow_trainer_onboarding.py
   └─> send_flow()
   └─> _mark_abandoned_flows()
   └─> Finds old active token
   └─> Updates: status='abandoned'
   └─> Creates new token
   └─> Sends new Flow

9. Database Changes:
   └─> flow_tokens table:
       ├─ Old token: status='active' → 'abandoned'
       └─ New token: status='active'
```

**Task Status**: ❌ No task
**User can type**: ✅ Yes, anytime
**Flow token**: ✅ Old marked 'abandoned', new created
**User can retry**: ✅ Yes, unlimited

---

## Registration Task Lifecycle

### WhatsApp Flow Registration (Current System)

**Task Created**: ❌ NO
**Why**: Flow-based registration doesn't use the task system

**Flow Token Lifecycle**:

1. Created when Flow is sent
2. Saved to `flow_tokens` table with status='active'
3. Used to identify flow type when webhook received
4. ❌ Never deleted or marked complete (stays 'active')

**User Messaging**:

- ✅ Can type anytime
- ✅ Not blocked by Flow
- ✅ Flow and messaging are independent

### Chat-Based Registration (Legacy System)

**Task Created**: ✅ YES (if used)
**When**: When `RegistrationFlowHandler.start_registration()` is called

**Task Lifecycle**:

1. Created in `tasks` table with status='active'
2. Updated as user answers each question
3. Completed when all fields collected
4. ❌ Never automatically deleted

**User Messaging**:

- ⚠️ Partially blocked
- User must answer current question
- Can type `/stop` to cancel
- Other messages treated as answers

**When Used**:

- Only for in-progress chat-based registrations
- NOT used for new users (they get Flow)
- Kept for backward compatibility

---

## Task Management Issues

### Current Problems:

1. **Flow tokens never cleaned up**

   - Saved to database when Flow sent
   - Never marked as 'completed' or 'expired'
   - Database grows indefinitely

2. **No timeout handling**

   - If user abandons Flow, token stays 'active' forever
   - No way to know if Flow was abandoned

3. **Chat-based tasks never deleted**
   - Old registration tasks remain in database
   - Even after completion

### Recommendations:

1. **Update flow_token status on completion**

   ```python
   # In process_flow_completion():
   self.db.table('flow_tokens').update({
       'status': 'completed',
       'completed_at': datetime.now().isoformat()
   }).eq('flow_token', flow_token).execute()
   ```

2. **Add timeout for abandoned flows**

   ```python
   # Periodic cleanup job:
   # Mark tokens as 'expired' if created > 24 hours ago and still 'active'
   ```

3. **Clean up completed tasks**
   ```python
   # After registration complete:
   task_service.complete_task(task_id)
   # Or delete old completed tasks periodically
   ```

---

## Summary

| Scenario            | Task Created? | User Can Type?  | When Task Ends         |
| ------------------- | ------------- | --------------- | ---------------------- |
| Types "hi"          | ❌ No         | ✅ Yes, anytime | N/A                    |
| Types "trainer"     | ❌ No         | ✅ Yes, anytime | N/A                    |
| Clicks button       | ❌ No         | ✅ Yes, anytime | N/A                    |
| Submits Flow        | ❌ No         | ✅ Yes, anytime | N/A                    |
| Abandons Flow       | ❌ No         | ✅ Yes, anytime | N/A                    |
| Chat-based (legacy) | ✅ Yes        | ⚠️ Partially    | When complete or /stop |

**Key Points**:

- ✅ WhatsApp Flow doesn't block user messaging
- ✅ User can type anytime during Flow process
- ✅ Flow and messaging are completely independent
- ⚠️ Flow tokens never cleaned up (needs fix)
- ⚠️ No timeout for abandoned flows (needs fix)

---

## Flow Token Status Management (Updated)

| Status      | When Set                | Can Retry?                                  |
| ----------- | ----------------------- | ------------------------------------------- |
| `active`    | Flow sent               | ✅ Yes (creates new, marks old 'abandoned') |
| `completed` | Registration successful | ❌ No (already registered)                  |
| `failed`    | Validation/error        | ✅ Yes                                      |
| `abandoned` | User requests new Flow  | ✅ Yes                                      |

## Updated Summary

| Scenario             | Task? | User Can Type? | Flow Token Status                            |
| -------------------- | ----- | -------------- | -------------------------------------------- |
| Types "hi"           | ❌ No | ✅ Anytime     | N/A                                          |
| Types "trainer"      | ❌ No | ✅ Anytime     | `active`                                     |
| Clicks button        | ❌ No | ✅ Anytime     | `active`                                     |
| Submits successfully | ❌ No | ✅ Anytime     | `completed`                                  |
| Validation fails     | ❌ No | ✅ Anytime     | `failed`                                     |
| Abandons & retries   | ❌ No | ✅ Anytime     | `active` → `abandoned` (old), `active` (new) |

**Implemented**:

- ✅ Flow tokens tracked with status
- ✅ Completed flows marked 'completed'
- ✅ Failed flows marked 'failed' with error
- ✅ Abandoned flows marked 'abandoned' on retry
- ✅ User can retry unlimited times
- ✅ User can type anytime (Flow doesn't block)
