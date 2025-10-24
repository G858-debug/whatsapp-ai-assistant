# Context for New Chat Session - Phase 2 Continuation

## 🎯 Current Status

**Project:** WhatsApp AI Fitness Assistant (Refiloe)
**Current Phase:** Phase 2 - Trainer-Client Relationships (40% complete)
**Previous Phase:** Phase 1 - Authentication (100% complete)
**Database:** Supabase
**Platform:** WhatsApp Business API

---

## ✅ What's Been Completed

### Phase 1: Authentication & Account Management (100% ✅)

**Database Schema:**

- ✅ Created `users` table (central authentication)
- ✅ Created `trainer_client_list` table (relationships)
- ✅ Created `client_trainer_list` table (relationships)
- ✅ Created `trainer_tasks` and `client_tasks` tables
- ✅ Added `trainer_id` (VARCHAR 5-7 chars) to trainers table
- ✅ Added `client_id` (VARCHAR 5-7 chars) to clients table
- ✅ SQL File: `database_updates/phase1_authentication_schema.sql`

**Services Created:**

- ✅ `services/auth/authentication_service.py` - User auth, login, unique ID generation
- ✅ `services/auth/registration_service.py` - Registration flows
- ✅ `services/auth/task_service.py` - Task tracking

**Configuration:**

- ✅ `config/trainer_registration_inputs.json` - 13 trainer fields
- ✅ `config/client_registration_inputs.json` - 7 client fields
- ✅ `config/command_handlers.json` - Command definitions

**Integration:**

- ✅ `services/message_router.py` - Main message routing
- ✅ `services/flows/registration_flow.py` - Registration flow
- ✅ `services/flows/login_flow.py` - Login flow
- ✅ `services/flows/profile_flow.py` - Profile management
- ✅ `services/commands/help_command.py` - Help command
- ✅ `services/commands/logout_command.py` - Logout
- ✅ `services/commands/switch_role_command.py` - Role switching
- ✅ `services/commands/register_command.py` - Register new role
- ✅ `services/commands/stop_command.py` - Stop tasks
- ✅ `services/commands/profile_commands.py` - View/edit/delete profile
- ✅ `services/ai_intent_handler_phase1.py` - Natural language AI (Claude)
- ✅ Updated `routes/webhooks.py` - Integrated MessageRouter

**Phase 1 Status:** ✅ COMPLETE - Ready for testing (needs SQL migration run by user)

---

### Phase 2: Trainer-Client Relationships (40% ✅)

**Services Created:**

- ✅ `services/relationships/relationship_service.py` - Relationship CRUD operations
- ✅ `services/relationships/invitation_service.py` - Invitation sending

**Command Handlers Created:**

- ✅ `services/commands/trainer_relationship_commands.py`
  - handle_invite_trainee
  - handle_create_trainee
  - handle_view_trainees (with CSV for >5 clients)
  - handle_remove_trainee
- ✅ `services/commands/client_relationship_commands.py`
  - handle_search_trainer
  - handle_invite_trainer
  - handle_view_trainers (with CSV for >5 trainers)
  - handle_remove_trainer

---

## ⏳ What Needs to Be Done (Phase 2 - 60% Remaining)

### CRITICAL: Flow Handlers (Must Create)

#### 1. `services/flows/trainer_relationship_flows.py`

**Purpose:** Handle multi-step flows for trainer relationship tasks

**Methods Needed:**

- `continue_invite_trainee(phone, message, trainer_id, task)`
  - Get client_id from message
  - Verify client exists
  - Check if already connected
  - Create pending relationship
  - Send invitation to client
  - Complete task
- `continue_create_trainee(phone, message, trainer_id, task)`
  - Collect client registration fields one by one
  - Include phone number field
  - After all fields: check if phone exists
  - If exists: ask to invite existing instead
  - If not: send invitation with prefilled data
  - On approval: create client account, establish relationship
  - On rejection: notify trainer, don't save
- `continue_remove_trainee(phone, message, trainer_id, task)`
  - Get client_id from message
  - Verify client in trainer's list
  - Show client info
  - Ask confirmation
  - If confirmed: remove relationship, notify both parties
  - Complete task

#### 2. `services/flows/client_relationship_flows.py`

**Purpose:** Handle multi-step flows for client relationship tasks

**Methods Needed:**

- `continue_search_trainer(phone, message, client_id, task)`
  - Get search term from message
  - Search trainers table
  - Display up to 5 results with details
  - Inform to copy trainer_id and use /invite-trainer
  - Complete task
- `continue_invite_trainer(phone, message, client_id, task)`
  - Get trainer_id from message
  - Verify trainer exists
  - Check if already connected
  - Create pending relationship
  - Send invitation to trainer
  - Complete task
- `continue_remove_trainer(phone, message, client_id, task)`
  - Get trainer_id from message
  - Verify trainer in client's list
  - Show trainer info
  - Ask confirmation
  - If confirmed: remove relationship, notify both parties
  - Complete task

### CRITICAL: Button Response Handling

**Location:** Update `services/message_router.py` or create `services/button_handler.py`

**Button IDs to Handle:**

- `accept_trainer_{trainer_id}` - Client accepts trainer invitation
- `decline_trainer_{trainer_id}` - Client declines trainer invitation
- `accept_client_{client_id}` - Trainer accepts client invitation
- `decline_client_{client_id}` - Trainer declines client invitation
- `approve_new_client_{trainer_id}` - New client approves account creation
- `reject_new_client_{trainer_id}` - New client rejects account creation

**Logic:**

- Parse button ID to extract trainer_id or client_id
- Get user's ID from phone
- Call relationship_service.approve_relationship() or decline_relationship()
- Send notifications to both parties
- For new client approval: create client account + relationship

### CRITICAL: Integration Updates

#### 1. Update `services/message_router.py`

**Add to `_handle_role_command()` method:**

```python
# Trainer commands (Phase 2)
elif role == 'trainer':
    if cmd == '/invite-trainee':
        from services.commands.trainer_relationship_commands import handle_invite_trainee
        return handle_invite_trainee(phone, user_id, self.db, self.whatsapp, self.task_service)
    elif cmd == '/create-trainee':
        from services.commands.trainer_relationship_commands import handle_create_trainee
        return handle_create_trainee(phone, user_id, self.db, self.whatsapp, self.reg_service, self.task_service)
    elif cmd == '/view-trainees':
        from services.commands.trainer_relationship_commands import handle_view_trainees
        return handle_view_trainees(phone, user_id, self.db, self.whatsapp)
    elif cmd == '/remove-trainee':
        from services.commands.trainer_relationship_commands import handle_remove_trainee
        return handle_remove_trainee(phone, user_id, self.db, self.whatsapp, self.task_service)

# Client commands (Phase 2)
elif role == 'client':
    if cmd == '/search-trainer':
        from services.commands.client_relationship_commands import handle_search_trainer
        return handle_search_trainer(phone, user_id, self.db, self.whatsapp, self.task_service)
    elif cmd == '/invite-trainer':
        from services.commands.client_relationship_commands import handle_invite_trainer
        return handle_invite_trainer(phone, user_id, self.db, self.whatsapp, self.task_service)
    elif cmd == '/view-trainers':
        from services.commands.client_relationship_commands import handle_view_trainers
        return handle_view_trainers(phone, user_id, self.db, self.whatsapp)
    elif cmd == '/remove-trainer':
        from services.commands.client_relationship_commands import handle_remove_trainer
        return handle_remove_trainer(phone, user_id, self.db, self.whatsapp, self.task_service)
```

**Add to `_continue_task()` method:**

```python
elif task_type == 'invite_trainee':
    from services.flows.trainer_relationship_flows import TrainerRelationshipFlows
    handler = TrainerRelationshipFlows(self.db, self.whatsapp, self.task_service)
    return handler.continue_invite_trainee(phone, message, user_id, task)

elif task_type == 'create_trainee':
    from services.flows.trainer_relationship_flows import TrainerRelationshipFlows
    handler = TrainerRelationshipFlows(self.db, self.whatsapp, self.reg_service, self.task_service)
    return handler.continue_create_trainee(phone, message, user_id, task)

elif task_type == 'remove_trainee':
    from services.flows.trainer_relationship_flows import TrainerRelationshipFlows
    handler = TrainerRelationshipFlows(self.db, self.whatsapp, self.task_service)
    return handler.continue_remove_trainee(phone, message, user_id, task)

elif task_type == 'search_trainer':
    from services.flows.client_relationship_flows import ClientRelationshipFlows
    handler = ClientRelationshipFlows(self.db, self.whatsapp, self.task_service)
    return handler.continue_search_trainer(phone, message, user_id, task)

elif task_type == 'invite_trainer':
    from services.flows.client_relationship_flows import ClientRelationshipFlows
    handler = ClientRelationshipFlows(self.db, self.whatsapp, self.task_service)
    return handler.continue_invite_trainer(phone, message, user_id, task)

elif task_type == 'remove_trainer':
    from services.flows.client_relationship_flows import ClientRelationshipFlows
    handler = ClientRelationshipFlows(self.db, self.whatsapp, self.task_service)
    return handler.continue_remove_trainer(phone, message, user_id, task)
```

#### 2. Update `services/ai_intent_handler_phase1.py`

**Update available features in `_create_intent_prompt()` method:**

For trainers, change from:

```
Coming Soon (Phase 2):
- Invite clients
- Manage clients
- View client list
```

To:

```
Available Features (Phase 2):
- Invite existing client (/invite-trainee)
- Create new client (/create-trainee)
- View clients (/view-trainees)
- Remove client (/remove-trainee)
```

For clients, change from:

```
Coming Soon (Phase 2):
- Search trainers
- Invite trainers
- View trainer list
```

To:

```
Available Features (Phase 2):
- Search trainers (/search-trainer)
- Invite trainer (/invite-trainer)
- View trainers (/view-trainers)
- Remove trainer (/remove-trainer)
```

**Add new intents to detect:**

```python
"intent": "one of: view_profile, edit_profile, delete_account, logout, switch_role, help,
          invite_trainee, create_trainee, view_trainees, remove_trainee,
          search_trainer, invite_trainer, view_trainers, remove_trainer,
          general_conversation, unclear"
```

---

## 📋 Implementation Requirements (From Plan)

### Terminology Note

**IMPORTANT:** Plan uses "trainee" but code uses "client"

- trainer_id ✅ (correct)
- client_id ✅ (not trainee_id)
- trainer_client_list ✅ (not trainer_trainee_list)
- This is intentional - "client" is more professional

### Key Requirements

1. **ID Generation:** 5-7 characters based on name + numbers (✅ Already implemented in Phase 1)

2. **Invite Existing Client:**

   - Ask for client_id
   - Verify exists
   - Send invitation with trainer info
   - Buttons: Accept/Reject
   - On accept: add to both relationship tables
   - On reject: notify trainer

3. **Create New Client:**

   - Collect all client fields (from client_registration_inputs.json)
   - Include phone number
   - Check if phone exists
   - If exists: ask to invite existing instead
   - If not: send invitation with prefilled data
   - On approve: create account + relationship
   - On reject: don't save

4. **Search Trainers:**

   - Ask for name
   - Search trainers table (ILIKE)
   - Show up to 5 results
   - Display: name, specialization, experience, trainer_id

5. **View Lists:**

   - If ≤5: display in chat
   - If >5: generate CSV

6. **Remove Relationships:**
   - Ask for ID
   - Verify in list
   - Ask confirmation
   - Remove from both tables
   - Notify both parties

---

## 🗂️ File Structure

```
services/
├── auth/                           ✅ Phase 1
│   ├── authentication_service.py
│   ├── registration_service.py
│   └── task_service.py
│
├── relationships/                  ✅ Phase 2 (Partial)
│   ├── __init__.py                ✅ Created
│   ├── relationship_service.py    ✅ Created
│   └── invitation_service.py      ✅ Created
│
├── flows/                          ✅ Phase 1, ⏳ Phase 2
│   ├── __init__.py                ✅ Created
│   ├── registration_flow.py       ✅ Phase 1
│   ├── login_flow.py              ✅ Phase 1
│   ├── profile_flow.py            ✅ Phase 1
│   ├── trainer_relationship_flows.py  ⏳ NEEDS TO BE CREATED
│   └── client_relationship_flows.py   ⏳ NEEDS TO BE CREATED
│
├── commands/                       ✅ Phase 1, ✅ Phase 2 (Partial)
│   ├── __init__.py                ✅ Created
│   ├── help_command.py            ✅ Phase 1
│   ├── logout_command.py          ✅ Phase 1
│   ├── switch_role_command.py     ✅ Phase 1
│   ├── register_command.py        ✅ Phase 1
│   ├── stop_command.py            ✅ Phase 1
│   ├── profile_commands.py        ✅ Phase 1
│   ├── trainer_relationship_commands.py  ✅ Created
│   └── client_relationship_commands.py   ✅ Created
│
├── message_router.py              ✅ Phase 1, ⏳ Needs Phase 2 updates
└── ai_intent_handler_phase1.py    ✅ Phase 1, ⏳ Needs Phase 2 updates

config/
├── trainer_registration_inputs.json  ✅ Phase 1
├── client_registration_inputs.json   ✅ Phase 1
└── command_handlers.json             ✅ Phase 1

database_updates/
└── phase1_authentication_schema.sql  ✅ Phase 1 (includes relationship tables)
```

---

## 📝 Important Notes

### Database

- **Status:** SQL file created but NOT YET RUN by user
- **Action:** User will run `database_updates/phase1_authentication_schema.sql` in Supabase
- **Tables:** All Phase 1 & 2 tables are in the same SQL file
- **Note:** Don't create new SQL file unless adding new tables

### Terminology

- Use "client" not "trainee" in code
- Use "trainer" consistently
- Plan document uses "trainee" but implementation uses "client"

### Code Style

- Use existing services where possible
- Review existing code before creating new
- Don't create duplicate files
- Follow existing patterns
- Use proper error handling
- Add comprehensive logging

### Testing

- Don't create test files (user will test manually)
- Focus on implementation only

### Development Guidelines

- Review current implementations before extending
- Ask user if conflicts or better approaches found
- Don't assume - ask when needed
- Mark TODO items as done
- Don't skip to Phase 3 before Phase 2 is complete

---

## 🎯 Immediate Tasks for New Chat

### Task 1: Create Trainer Relationship Flows

**File:** `services/flows/trainer_relationship_flows.py`

**Class:** `TrainerRelationshipFlows`

**Methods:**

1. `continue_invite_trainee()` - Handle invite existing client flow
2. `continue_create_trainee()` - Handle create new client flow
3. `continue_remove_trainee()` - Handle remove client flow

**Reference:** See requirements in "Implementation Requirements" section above

### Task 2: Create Client Relationship Flows

**File:** `services/flows/client_relationship_flows.py`

**Class:** `ClientRelationshipFlows`

**Methods:**

1. `continue_search_trainer()` - Handle search trainer flow
2. `continue_invite_trainer()` - Handle invite trainer flow
3. `continue_remove_trainer()` - Handle remove trainer flow

### Task 3: Create Button Handler

**File:** `services/button_handler.py` or add to `message_router.py`

**Handle these button IDs:**

- `accept_trainer_{trainer_id}`
- `decline_trainer_{trainer_id}`
- `accept_client_{client_id}`
- `decline_client_{client_id}`
- `approve_new_client_{trainer_id}`
- `reject_new_client_{trainer_id}`

### Task 4: Update Message Router

**File:** `services/message_router.py`

**Updates:**

1. Add Phase 2 commands to `_handle_role_command()`
2. Add Phase 2 task types to `_continue_task()`
3. Add button response handling to `route_message()`

### Task 5: Update AI Intent Handler

**File:** `services/ai_intent_handler_phase1.py`

**Updates:**

1. Update available features list
2. Add Phase 2 intents
3. Update intent detection

### Task 6: Update Help Command

**File:** `services/commands/help_command.py`

**Updates:**

1. Change "Phase 2" to "Available Features"
2. Update command lists

---

## 📚 Key Files to Reference

### For Understanding Current Implementation

- `services/message_router.py` - Main routing logic
- `services/flows/registration_flow.py` - Example of flow handler
- `services/flows/profile_flow.py` - Example of task continuation
- `services/auth/registration_service.py` - Field collection pattern

### For Phase 2 Implementation

- `services/relationships/relationship_service.py` - Use these methods
- `services/relationships/invitation_service.py` - Use these methods
- `services/commands/trainer_relationship_commands.py` - Command starters
- `services/commands/client_relationship_commands.py` - Command starters

### For Requirements

- `TODO/TODO_PHASE2_RELATIONSHIPS.md` - Detailed task list
- `TODO/COMPREHENSIVE_APP_IMPROVEMENT_PLAN - Copy.md` - Original plan
- `PHASE2_PROGRESS_CHECKPOINT1.md` - Current progress

---

## 🔧 Code Patterns to Follow

### Flow Handler Pattern

```python
class SomeFlowHandler:
    def __init__(self, db, whatsapp, task_service, other_services):
        self.db = db
        self.whatsapp = whatsapp
        self.task = task_service
        # ... other services

    def continue_some_task(self, phone, message, user_id, task):
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step')

            if step == 'ask_something':
                # Validate input
                # Store in task_data
                # Move to next step or complete
                pass

            # Update task
            self.task.update_task(task['id'], role, task_data)

            # Or complete task
            self.task.complete_task(task['id'], role)

        except Exception as e:
            log_error(f"Error: {str(e)}")
            return {'success': False, 'response': 'Error message'}
```

### Command Handler Pattern

```python
def handle_some_command(phone, user_id, db, whatsapp, task_service):
    try:
        # Create task
        task_id = task_service.create_task(
            user_id=user_id,
            role='trainer',  # or 'client'
            task_type='some_task',
            task_data={'step': 'initial_step'}
        )

        # Send initial message
        msg = "Some message"
        whatsapp.send_message(phone, msg)

        return {'success': True, 'response': msg, 'handler': 'some_handler'}

    except Exception as e:
        log_error(f"Error: {str(e)}")
        return {'success': False, 'response': 'Error', 'handler': 'error'}
```

---

## 🚨 Critical Reminders

1. **Don't create duplicate files** - Check if file exists first
2. **Use existing services** - relationship_service, invitation_service already created
3. **Follow existing patterns** - Look at Phase 1 flows for examples
4. **Handle errors properly** - Try-catch, log, user-friendly messages
5. **Test logic** - Think through edge cases
6. **Button IDs** - Must match what invitation_service sends
7. **Notifications** - Send to both parties on accept/decline/remove
8. **CSV** - Only for lists >5 items

---

## 📊 Progress Tracking

**Phase 1:** ✅ 100% Complete
**Phase 2:** 🟡 40% Complete

- Services: ✅ 100%
- Commands: ✅ 100%
- Flows: ⏳ 0%
- Integration: ⏳ 0%

**Next Milestone:** Phase 2 Complete (60% remaining)

---

## 🎯 Success Criteria for Phase 2

When complete, these should work:

- [ ] Trainer can invite existing client by ID
- [ ] Trainer can create new client account
- [ ] Trainer can view all clients
- [ ] Trainer can remove client
- [ ] Client can search for trainers
- [ ] Client can invite trainer by ID
- [ ] Client can view all trainers
- [ ] Client can remove trainer
- [ ] Invitations sent with buttons
- [ ] Accept/decline works
- [ ] Both parties notified
- [ ] CSV generated for large lists

---

## 💬 Prompt for New Chat

**Copy this to new chat:**

```
Continue Phase 2 implementation for WhatsApp AI Fitness Assistant.

CONTEXT:
- Phase 1 (Authentication) is 100% complete
- Phase 2 (Relationships) is 40% complete
- Services and command handlers are created
- Need to create flow handlers and integrate

CURRENT STATUS:
- Created: relationship_service.py, invitation_service.py
- Created: trainer_relationship_commands.py, client_relationship_commands.py
- Need: trainer_relationship_flows.py, client_relationship_flows.py
- Need: Button handler integration
- Need: Message router updates
- Need: AI intent updates

REQUIREMENTS:
Read and follow: CONTEXT_FOR_NEW_CHAT.md

KEY POINTS:
- Use "client" not "trainee" in code
- Don't create duplicate files
- Review existing code before extending
- Follow patterns from Phase 1 flows
- No test files
- Ask if conflicts found
- Mark TODO items as done

IMMEDIATE TASKS:
1. Create services/flows/trainer_relationship_flows.py
2. Create services/flows/client_relationship_flows.py
3. Add button handling to message_router.py
4. Update message_router.py with Phase 2 commands
5. Update ai_intent_handler_phase1.py with Phase 2 features
6. Update help_command.py
7. Test all flows

Start with Task 1: Create trainer_relationship_flows.py
```

---

**Status:** ✅ Context document complete
**File:** CONTEXT_FOR_NEW_CHAT.md
**Ready for:** New chat session
