# Context for Phase 3: Fitness Habit Management

## 🎯 Current Status

**Project:** WhatsApp AI Fitness Assistant (Refiloe)
**Current Phase:** Phase 3 - Fitness Habit Management (0% complete)
**Previous Phases:**

- Phase 1 - Authentication (100% ✅)
- Phase 2 - Trainer-Client Relationships (100% ✅)
  **Database:** Supabase
  **Platform:** WhatsApp Business API

---

## ✅ What's Been Completed (Phases 1 & 2)

### Phase 1: Authentication & Account Management (100% ✅)

**Database Schema:**

- ✅ `users` table (central authentication)
- ✅ `trainers` table with `trainer_id` (VARCHAR 5-7 chars)
- ✅ `clients` table with `client_id` (VARCHAR 5-7 chars)
- ✅ `trainer_tasks` and `client_tasks` tables
- ✅ `message_history` table
- ✅ SQL File: `database_updates/phase1_authentication_schema.sql`

**Services:**

- ✅ `services/auth/authentication_service.py` - User auth, login, unique ID generation
- ✅ `services/auth/registration_service.py` - Registration flows
- ✅ `services/auth/task_service.py` - Task tracking

**Flows:**

- ✅ `services/flows/registration_flow.py` - Registration
- ✅ `services/flows/login_flow.py` - Login
- ✅ `services/flows/profile_flow.py` - Profile management

**Commands:**

- ✅ Universal: `/help`, `/logout`, `/switch-role`, `/register`, `/stop`
- ✅ Profile: `/view-profile`, `/edit-profile`, `/delete-account`

**Integration:**

- ✅ `services/message_router.py` - Main message routing with button handling
- ✅ `services/ai_intent_handler_phase1.py` - Natural language AI (Claude)
- ✅ `routes/webhooks.py` - Integrated MessageRouter with button_id support

### Phase 2: Trainer-Client Relationships (100% ✅)

**Database Schema:**

- ✅ `trainer_client_list` table (bidirectional relationships)
- ✅ `client_trainer_list` table (bidirectional relationships)
- ✅ `client_invitations` table (stores prefilled data for new clients)

**Services:**

- ✅ `services/relationships/relationship_service.py` - CRUD operations
- ✅ `services/relationships/invitation_service.py` - Invitation sending
- ✅ `services/helpers/supabase_storage.py` - CSV file upload to Supabase Storage

**Flows:**

- ✅ `services/flows/trainer_relationship_flows.py` - Trainer relationship flows
- ✅ `services/flows/client_relationship_flows.py` - Client relationship flows

**Commands:**

- ✅ Trainer: `/invite-trainee`, `/create-trainee`, `/view-trainees`, `/remove-trainee`
- ✅ Client: `/search-trainer`, `/invite-trainer`, `/view-trainers`, `/remove-trainer`

**Features:**

- ✅ Invitation system with accept/decline buttons
- ✅ Account creation for new clients
- ✅ CSV export with Supabase Storage (for lists >5)
- ✅ Bidirectional relationships
- ✅ Notifications to both parties

---

## 🎯 Phase 3: Fitness Habit Management (0% - TO IMPLEMENT)

### Overview

Implement complete habit tracking system where:

- Trainers create habits and assign to clients
- Clients log habits daily (multiple times per day allowed)
- Progress tracking and reporting
- Daily reminders

### Key Requirements from Plan

**Terminology:**

- Use "habit" (not "task" or "goal")
- Habit IDs: 5-7 characters (e.g., HAB123)
- Multiple logs per day allowed (immutable once logged)

**Core Features:**

1. Habit Creation (Trainers)
2. Habit Assignment (Trainers)
3. Habit Logging (Clients - multiple times/day)
4. Progress Viewing (Both)
5. Reports (Weekly/Monthly)
6. Daily Reminders (Automated)

---

## 📋 Phase 3 Implementation Plan

### 1. Database Schema (REQUIRED)

**New Tables Needed:**

```sql
-- fitness_habits table
CREATE TABLE fitness_habits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    habit_id VARCHAR(10) UNIQUE NOT NULL,
    trainer_id VARCHAR(10) NOT NULL REFERENCES trainers(trainer_id),
    habit_name VARCHAR(100) NOT NULL,
    description TEXT,
    target_value DECIMAL(10,2) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    frequency VARCHAR(20) NOT NULL, -- 'daily' or 'weekly'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- trainee_habit_assignments table
CREATE TABLE trainee_habit_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    habit_id VARCHAR(10) NOT NULL REFERENCES fitness_habits(habit_id),
    client_id VARCHAR(10) NOT NULL REFERENCES clients(client_id),
    trainer_id VARCHAR(10) NOT NULL REFERENCES trainers(trainer_id),
    assigned_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(habit_id, client_id)
);

-- habit_logs table (IMMUTABLE - no edits/deletes allowed)
CREATE TABLE habit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    habit_id VARCHAR(10) NOT NULL REFERENCES fitness_habits(habit_id),
    client_id VARCHAR(10) NOT NULL REFERENCES clients(client_id),
    log_date DATE NOT NULL,
    log_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_value DECIMAL(10,2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_fitness_habits_trainer ON fitness_habits(trainer_id);
CREATE INDEX idx_habit_assignments_client ON trainee_habit_assignments(client_id);
CREATE INDEX idx_habit_assignments_habit ON trainee_habit_assignments(habit_id);
CREATE INDEX idx_habit_logs_client_date ON habit_logs(client_id, log_date);
CREATE INDEX idx_habit_logs_habit_date ON habit_logs(habit_id, log_date);
```

**Action:** Create `database_updates/phase3_habits_schema.sql` with above schema

### 2. Configuration Files

**Create:** `config/habit_creation_inputs.json`

```json
{
  "fields": [
    {
      "name": "habit_name",
      "label": "Habit Name",
      "prompt": "What habit do you want to track?\n\nExamples: Water Intake, Daily Steps, Sleep Hours, Meals Logged",
      "type": "text",
      "required": true
    },
    {
      "name": "description",
      "label": "Description",
      "prompt": "Describe this habit (optional):",
      "type": "text",
      "required": false
    },
    {
      "name": "target_value",
      "label": "Target Value",
      "prompt": "What's the daily target?\n\nExample: 8 (for 8 glasses of water)",
      "type": "number",
      "required": true
    },
    {
      "name": "unit",
      "label": "Unit",
      "prompt": "What unit of measurement?\n\nExamples: glasses, liters, steps, hours, meals",
      "type": "text",
      "required": true
    },
    {
      "name": "frequency",
      "label": "Frequency",
      "prompt": "How often should this be tracked?",
      "type": "choice",
      "options": ["daily", "weekly"],
      "required": true
    }
  ]
}
```

### 3. Services to Create

**A. Habit Service**

- File: `services/habits/habit_service.py`
- Methods:
  - `create_habit(trainer_id, habit_data)` - Generate habit_id, create habit
  - `get_trainer_habits(trainer_id)` - Get all habits by trainer
  - `get_habit_by_id(habit_id)` - Get single habit
  - `update_habit(habit_id, updates)` - Update habit details
  - `delete_habit(habit_id)` - Soft delete (set is_active=False)
  - `search_habits(trainer_id, search_term)` - Search trainer's habits

**B. Assignment Service**

- File: `services/habits/assignment_service.py`
- Methods:
  - `assign_habit(habit_id, client_ids, trainer_id)` - Assign to one or more clients
  - `get_client_habits(client_id)` - Get all assigned habits for client
  - `get_habit_assignments(habit_id)` - Get all clients assigned to habit
  - `unassign_habit(habit_id, client_id)` - Remove assignment
  - `unassign_all_for_habit(habit_id)` - Remove all assignments for habit

**C. Logging Service**

- File: `services/habits/logging_service.py`
- Methods:
  - `log_habit(client_id, habit_id, value, notes=None)` - Create log entry
  - `get_daily_logs(client_id, date)` - Get all logs for a day
  - `get_habit_logs(client_id, habit_id, start_date, end_date)` - Get logs for date range
  - `calculate_daily_progress(client_id, date)` - Calculate progress for all habits
  - `calculate_habit_progress(client_id, habit_id, date)` - Calculate progress for one habit

**D. Report Service**

- File: `services/habits/report_service.py`
- Methods:
  - `generate_weekly_report(client_id, week_start)` - Generate weekly CSV
  - `generate_monthly_report(client_id, month, year)` - Generate monthly CSV
  - `generate_trainer_report(trainer_id, client_id, period)` - Trainer view of client progress

### 4. Command Handlers to Create

**A. Trainer Commands**

- File: `services/commands/trainer_habit_commands.py`
- Commands:
  - `handle_create_habit()` - `/create-habit`
  - `handle_edit_habit()` - `/edit-habit`
  - `handle_delete_habit()` - `/delete-habit`
  - `handle_assign_habit()` - `/assign-habit`
  - `handle_view_habits()` - `/view-habits`
  - `handle_view_trainee_progress()` - `/view-trainee-progress`
  - `handle_trainee_report()` - `/trainee-weekly-report`, `/trainee-monthly-report`

**B. Client Commands**

- File: `services/commands/client_habit_commands.py`
- Commands:
  - `handle_view_my_habits()` - `/view-my-habits`
  - `handle_log_habits()` - `/log-habits`
  - `handle_view_progress()` - `/view-progress`
  - `handle_weekly_report()` - `/weekly-report`
  - `handle_monthly_report()` - `/monthly-report`

### 5. Flow Handlers to Create

**A. Trainer Habit Flows**

- File: `services/flows/trainer_habit_flows.py`
- Methods:
  - `continue_create_habit()` - Multi-step habit creation
  - `continue_edit_habit()` - Multi-step habit editing
  - `continue_delete_habit()` - Confirmation flow
  - `continue_assign_habit()` - Multi-step assignment
  - `continue_view_trainee_progress()` - Date selection flow

**B. Client Habit Flows**

- File: `services/flows/client_habit_flows.py`
- Methods:
  - `continue_log_habits()` - Multi-step logging for all habits
  - `continue_view_progress()` - Date selection flow
  - `continue_weekly_report()` - Week selection flow
  - `continue_monthly_report()` - Month selection flow

### 6. Integration Updates

**A. Message Router**

- File: `services/message_router.py`
- Add Phase 3 commands to `_handle_role_command()`
- Add Phase 3 task types to `_continue_task()`

**B. AI Intent Handler**

- File: `services/ai_intent_handler_phase1.py`
- Update to `ai_intent_handler.py` (remove phase1 from name)
- Add Phase 3 intents
- Update available features list

**C. Help Command**

- File: `services/commands/help_command.py`
- Update to show Phase 3 commands as available
- Remove "Coming Soon" label

### 7. Daily Reminder System (Optional for MVP)

**Scheduler:**

- File: `services/scheduler/habit_reminders.py`
- Send daily reminders at 8 AM to clients with assigned habits
- Include list of habits and log button

---

## 🔧 Implementation Guidelines

### Code Patterns to Follow

**1. Service Pattern (from Phase 2):**

```python
class HabitService:
    def __init__(self, supabase_client):
        self.db = supabase_client

    def create_habit(self, trainer_id: str, habit_data: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        Returns: (success, message, habit_id)
        """
        try:
            # Generate unique habit_id
            # Insert into database
            # Return success
        except Exception as e:
            log_error(f"Error: {str(e)}")
            return False, str(e), None
```

**2. Command Handler Pattern:**

```python
def handle_create_habit(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    try:
        # Create task
        task_id = task_service.create_task(
            user_id=trainer_id,
            role='trainer',
            task_type='create_habit',
            task_data={'step': 'start'}
        )

        # Send initial message
        msg = "Let's create a new habit! ..."
        whatsapp.send_message(phone, msg)

        return {'success': True, 'response': msg, 'handler': 'create_habit'}
    except Exception as e:
        log_error(f"Error: {str(e)}")
        return {'success': False, 'response': 'Error', 'handler': 'error'}
```

**3. Flow Handler Pattern:**

```python
class TrainerHabitFlows:
    def __init__(self, db, whatsapp, task_service, habit_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.habit_service = habit_service

    def continue_create_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step')

            # Handle each step
            # Update task_data
            # Move to next step or complete

        except Exception as e:
            log_error(f"Error: {str(e)}")
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error', 'handler': 'error'}
```

### Important Notes

**1. Multiple Logs Per Day:**

- Clients can log same habit multiple times per day
- Each log is a separate entry with timestamp
- Sum all logs for the day to calculate progress
- Logs are IMMUTABLE (no edit/delete)

**2. Progress Calculation:**

```python
# Get all logs for habit on date
logs = get_logs(client_id, habit_id, date)
total_completed = sum(log['completed_value'] for log in logs)
target = habit['target_value']
due = target - total_completed
percentage = (total_completed / target) * 100
```

**3. CSV Reports:**

- Use Supabase Storage (like Phase 2)
- Upload and send as WhatsApp document
- Include: Date, Habit, Target, Completed, Due, Percentage

**4. ID Generation:**

- Use existing `generate_unique_id()` from `authentication_service.py`
- Format: HAB + name-based + numbers (e.g., HAB123, HABWAT45)

---

## 📁 File Structure for Phase 3

```
services/
├── habits/                         ⏳ TO CREATE
│   ├── __init__.py
│   ├── habit_service.py
│   ├── assignment_service.py
│   ├── logging_service.py
│   └── report_service.py
│
├── flows/
│   ├── trainer_habit_flows.py      ⏳ TO CREATE
│   └── client_habit_flows.py       ⏳ TO CREATE
│
├── commands/
│   ├── trainer_habit_commands.py   ⏳ TO CREATE
│   └── client_habit_commands.py    ⏳ TO CREATE
│
├── scheduler/                      ⏳ OPTIONAL
│   └── habit_reminders.py
│
├── message_router.py               ⏳ UPDATE
└── ai_intent_handler.py            ⏳ UPDATE (rename from phase1)

config/
└── habit_creation_inputs.json      ⏳ TO CREATE

database_updates/
└── phase3_habits_schema.sql        ⏳ TO CREATE
```

---

## 🚨 Critical Reminders

### DO:

- ✅ Review existing code before creating new
- ✅ Use existing services where possible
- ✅ Follow patterns from Phase 1 & 2
- ✅ Use Supabase Storage for CSV exports
- ✅ Handle errors properly with try-catch
- ✅ Add comprehensive logging
- ✅ Test logic for edge cases
- ✅ Ask user if conflicts or better approaches found

### DON'T:

- ❌ Create duplicate files
- ❌ Create test files
- ❌ Skip to Phase 4 before Phase 3 complete
- ❌ Make assumptions - ask when needed
- ❌ Allow editing/deleting of habit logs (immutable)
- ❌ Update `working/current schemas` manually (user will do it)

### Database:

- User is using Supabase
- Provide SQL file for updates
- User will run SQL and update schema files manually
- Check `working/current schemas/` for existing tables

---

## 📊 Phase 3 Success Criteria

When complete, these should work:

**Trainer:**

- [ ] Create habit with all fields
- [ ] Edit habit details
- [ ] Delete habit (soft delete)
- [ ] Assign habit to one or more clients
- [ ] View all created habits
- [ ] View client's progress for specific date
- [ ] Generate client reports (weekly/monthly)

**Client:**

- [ ] View all assigned habits
- [ ] Log habit (multiple times per day)
- [ ] View progress for specific date
- [ ] Generate own reports (weekly/monthly)

**System:**

- [ ] Multiple logs per day supported
- [ ] Progress calculated correctly
- [ ] CSV reports generated and sent
- [ ] Notifications sent
- [ ] Natural language understanding works

---

## 🎯 Implementation Order

### Step 1: Database & Config (30 min)

1. Create `database_updates/phase3_habits_schema.sql`
2. Create `config/habit_creation_inputs.json`
3. User runs SQL in Supabase

### Step 2: Core Services (2-3 hours)

1. Create `services/habits/habit_service.py`
2. Create `services/habits/assignment_service.py`
3. Create `services/habits/logging_service.py`
4. Create `services/habits/report_service.py`

### Step 3: Command Handlers (2 hours)

1. Create `services/commands/trainer_habit_commands.py`
2. Create `services/commands/client_habit_commands.py`

### Step 4: Flow Handlers (3-4 hours)

1. Create `services/flows/trainer_habit_flows.py`
2. Create `services/flows/client_habit_flows.py`

### Step 5: Integration (1-2 hours)

1. Update `services/message_router.py`
2. Rename and update `services/ai_intent_handler.py`
3. Update `services/commands/help_command.py`

### Step 6: Testing (1-2 hours)

1. Test habit creation
2. Test assignment
3. Test logging (multiple times)
4. Test progress calculation
5. Test reports

**Total Estimated Time:** 10-14 hours

---

## 📚 Key Files to Reference

### For Understanding Current Implementation:

- `services/message_router.py` - Routing logic
- `services/flows/trainer_relationship_flows.py` - Flow pattern
- `services/relationships/relationship_service.py` - Service pattern
- `services/commands/trainer_relationship_commands.py` - Command pattern
- `services/helpers/supabase_storage.py` - CSV upload pattern

### For Phase 3 Requirements:

- `TODO/TODO_PHASE3_HABITS.md` - Detailed task list
- `TODO/COMPREHENSIVE_APP_IMPROVEMENT_PLAN - Copy.md` - Original plan
- `working/current schemas/habit_tracking.sql` - Existing habit table (may need updates)
- `working/current schemas/habit_goals.sql` - Existing goals table (may need updates)

### For Database Schema:

- `working/current schemas/` - All existing tables
- `database_updates/phase1_authentication_schema.sql` - Example SQL file format

---

## 💡 Tips for Implementation

1. **Start with Database:**

   - Review existing habit-related tables in `working/current schemas/`
   - May need to modify or extend existing tables
   - Create comprehensive SQL file

2. **Build Services First:**

   - Core logic in services
   - Commands and flows use services
   - Easier to test and debug

3. **Test Incrementally:**

   - Test each service method
   - Test each command
   - Test each flow
   - Don't wait until everything is done

4. **Handle Edge Cases:**

   - What if habit has no assignments?
   - What if client logs 0 value?
   - What if date is in future?
   - What if no logs for date?

5. **Use Existing Patterns:**
   - CSV export like Phase 2
   - Task management like Phase 1
   - Flow handling like Phase 2
   - Button responses like Phase 2

---

## 🎯 Prompt for New Chat

**Copy this to new chat:**

```
Continue Phase 3 implementation for WhatsApp AI Fitness Assistant.

CONTEXT:
- Phase 1 (Authentication) is 100% complete ✅
- Phase 2 (Relationships) is 100% complete ✅
- Phase 3 (Habits) is 0% complete - TO IMPLEMENT
- Using Supabase for database and storage
- Using WhatsApp Business API

CURRENT STATUS:
- All Phase 1 & 2 features working
- Need to implement complete habit management system
- Database schema needs to be created
- Services, commands, and flows need to be built

REQUIREMENTS:
Read and follow: CONTEXT_FOR_PHASE3.md

KEY POINTS:
- Review existing code before creating new
- Use existing patterns from Phase 1 & 2
- Multiple logs per day allowed (immutable)
- Use Supabase Storage for CSV exports
- Provide SQL file for database updates
- Don't create test files
- Ask if conflicts or better approaches found
- Follow implementation order in context doc

DEVELOPMENT GUIDELINES:
- Review current implementations and improve/extend them
- Implement all features from the plan
- Ask for input if conflicts or problems found
- Don't assume - ask when needed
- Mark TODO items as done
- Take breaks if needed but keep context

IMMEDIATE TASKS:
1. Review existing habit-related tables in working/current schemas/
2. Create database_updates/phase3_habits_schema.sql
3. Create config/habit_creation_inputs.json
4. Create services/habits/ with all 4 services
5. Create command handlers
6. Create flow handlers
7. Update integrations

Start with: Review existing schema and create Phase 3 database schema
```

---

**Status:** ✅ Context document complete for Phase 3
**File:** CONTEXT_FOR_PHASE3.md
**Ready for:** New chat session to implement Phase 3
