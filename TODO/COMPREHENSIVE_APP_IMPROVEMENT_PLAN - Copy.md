After reviewing your plan, I found it to be comprehensive and well-thought-out. Here are a few improvements for clarity and to address potential edge cases:

# App Plan - Improved Version

## Core Architecture

The application code will be organized into three main folders: trainer, trainee, and common. Within each folder, features will have their own separate folders - for example, a register folder that contains all registration-related code. The code will be split into multiple files for easy maintenance, rather than having all the code in a single file.

## Message Flow and User Authentication

When the app's WhatsApp account receives a message from a visitor, the system will first check if the sender's number exists in the user table.

**If user not found:**
The AI will ask how you want to register and will give button handlers for register as trainer or trainee. On button click, the onboarding task will start for the visitor number. Based on the handler clicked (trainer or trainee), the app will retrieve fields from trainer_registration_inputs.json or client_registration_inputs.json respectively, and collect the necessary information one by one. After the last input, the system will generate a unique id (5-7 characters based on the user's name and join date, adding 2-3 numbers if needed to ensure uniqueness), save the data in the respective trainer or trainee table, create a user entry with the generated trainer or trainee id, and mark logged in as trainer or trainee accordingly.

**If user found - checking login status:**

**Case 1: Login status is empty**

- If found in trainer table only: Automatically mark login as trainer and inform "You are logged in as trainer now. You can ask me for any trainer related tasks to perform. You can also ask to logout and then register as trainee."
- If found in trainee table only: Automatically mark login as trainee and inform "You are logged in as trainee now. You can ask me for any trainee related tasks to perform. You can also ask to logout and then register as trainer."
- If found in both tables: AI will ask "How do you want to login?" and provide handler buttons for "Login as Trainer" and "Login as Trainee". This creates a choosing login task. Based on the selected role, mark the user login as the chosen role and inform "You are logged in as [chosen role] now. You can ask me for any [chosen role] related tasks to perform. You can also ask to logout or switch role."

**Case 2: Login status is trainer**

- Verify the user exists in the trainer table
- Check if the message is a task invoking handler (like /view-profile, /invite-trainee, etc.)
- If it's a valid trainer handler, run the corresponding task and save it as running in the trainer task list
- If not a handler message, check for any last running trainer task
  - If there is a running task and it's not marked as stopped: Continue with the next step of that task
  - If there is no running task OR the last task is stopped: Retrieve the last 5 completed trainer tasks and last 10 chat history entries, provide this context to Claude AI (which has all app task information in its prompt), and let the AI determine if the user is asking to perform any trainer allowable task
    - If asking for a task: AI provides relevant handler buttons (like /view-profile) which can trigger the task and save it as running
    - If not asking for a task: AI provides a relevant message with next task suggestions based on last tasks data and chat history

**Case 3: Login status is trainee**

- Verify the user exists in the trainee table
- Check if the message is a task invoking handler (like /view-profile, /log-habits, etc.)
- If it's a valid trainee handler, run the corresponding task and save it as running in the trainee task list
- If not a handler message, check for any last running trainee task
  - If there is a running task and it's not marked as stopped: Continue with the next step of that task
  - If there is no running task OR the last task is stopped: Retrieve the last 5 completed trainee tasks and last 10 chat history entries, provide this context to Claude AI (which has all app task information in its prompt), and let the AI determine if the user is asking to perform any trainee allowable task
    - If asking for a task: AI provides relevant handler buttons (like /view-profile) which can trigger the task and save it as running
    - If not asking for a task: AI provides a relevant message with next task suggestions based on last tasks data and chat history

## Universal Direct Commands

Users can directly send these commands regardless of their current state:

- **/logout** - Clears the login status (marks as empty) and informs the user they are logged out
- **/switch-role** - Only works if opposite role exists. Switches login status to the opposite role (trainer↔trainee)
- **/register** - Only works if login status is empty. Starts registration flow for new role
- **/stop** - Marks the currently running task as stopped. AI informs users about this command at the beginning of each task

## Common Account Management Features

### Profile Viewing

**Trainer and Trainee can:**

- Ask AI to show profile info, AI provides handler button
- Handler retrieves and displays data from user table (showable fields) + respective role table (trainer/trainee)
- Direct command: **/view-profile**

### Profile Editing

**Trainer and Trainee can:**

- Ask AI to edit profile, AI provides handler button to start edit profile task
- Task retrieves fields from trainer_registration_inputs.json or client_registration_inputs.json (based on role)
- For each field, system shows current value and asks to skip or provide updated answer
- After collecting all updates, validate and update profile or show error and retry
- Direct command: **/edit-profile**

### Account Deletion

**Trainer and Trainee can:**

- Ask AI to delete account, AI provides handler button to start delete account task
- Task asks confirmation to delete as trainer/trainee
- If confirmed:
  - Delete all data from the respective role table (trainer/trainee) that doesn't affect other users
  - If deleting trainer account:
    - Remove trainer id from all associated trainees' subscribed trainer lists
    - Delete all entries from the trainer's trainee list table
    - Delete all habits created by this trainer from fitness habit table
    - Remove all habit assignments for these habits from trainee habit assignment table
  - If deleting trainee account:
    - Remove trainee id from all associated trainers' trainee lists
    - Delete all entries from the trainee's trainer list table
    - Delete all habit logs for this trainee from habit log table
  - Delete the role id field from user table
  - If no opposite role id exists, delete the user table entry completely
- Direct command: **/delete-account**

## Trainer-Trainee Relationship Management

### ID Generation System

Both trainer ids and trainee ids are generated as unique identifiers of 5-7 characters, created using a combination of the user's name and join date. If the generated id already exists in the system, 2-3 additional numbers are appended to make it unique. This ensures ids are easy to type and remember while maintaining uniqueness.

### Inviting Existing Trainee (by Trainer)

**Flow:**

1. Trainer asks AI to invite a trainee
2. AI provides handler button to start invite trainee task
3. Task asks trainer to provide the trainee id
4. System checks if trainee id exists in trainee table
5. If found:
   - Send invitation message to that trainee's WhatsApp number
   - Include trainer's basic info (name, id) in invitation
   - Provide handler buttons: Accept / Reject
   - If trainee accepts:
     - Add trainer id to trainee's subscribed trainer list
     - Add trainee id to trainer's trainee list
     - Notify both parties of successful connection
   - If trainee rejects:
     - Notify trainer that invitation was declined
6. If trainee id not found: Inform trainer that trainee doesn't exist

- Direct command: **/invite-trainee**

### Creating and Inviting New Trainee (by Trainer)

**Flow:**

1. Trainer asks AI to create and invite a trainee
2. AI provides handler button to start create trainee task
3. Task retrieves fields from client_registration_inputs.json
4. Ask trainer to provide all necessary trainee information one by one, including phone number
5. After collecting all information:
   - Check if phone number already exists in trainee table
   - If exists:
     - Inform trainer "This trainee already exists with ID: [trainee_id]"
     - Ask "Do you want to invite this existing trainee instead?"
     - If yes: Proceed with invite existing trainee flow using that trainee id
     - If no: End task
   - If doesn't exist:
     - Send invitation message to that phone number
     - Display all prefilled information clearly in the message
     - Provide handler buttons: Approve / Reject
     - If user approves:
       - Generate unique trainee id (5-7 characters based on name and join date)
       - Create trainee account with provided information
       - Create user entry with trainee id
       - Mark logged in as trainee
       - Add trainer id to trainee's subscribed trainer list
       - Add trainee id to trainer's trainee list
       - Notify both parties of successful registration and connection
     - If user rejects:
       - Notify trainer that invitation was declined
       - Don't save any data

- Direct command: **/create-trainee**

### Searching and Inviting Trainer (by Trainee)

**Flow for searching:**

1. Trainee asks AI to search for trainers
2. AI provides handler button to start search trainer task
3. Task asks trainee to provide trainer name to search
4. System searches trainer table by matching trainer name
5. Display up to 5 results with: name, specialization, experience, trainer id
6. Inform trainee to copy the trainer id and ask AI to send invite

- Direct command: **/search-trainer**

**Flow for inviting:**

1. Trainee asks AI to invite a trainer (provides trainer id)
2. AI provides handler button to start invite trainer task
3. Task verifies trainer id exists in trainer table
4. If found:
   - Send invitation message to that trainer's WhatsApp number
   - Include trainee's basic info (name, id) in invitation
   - Provide handler buttons: Accept / Reject
   - If trainer accepts:
     - Add trainer id to trainee's subscribed trainer list
     - Add trainee id to trainer's trainee list
     - Notify both parties of successful connection
   - If trainer rejects:
     - Notify trainee that invitation was declined
5. If trainer id not found: Inform trainee that trainer doesn't exist

- Direct command: **/invite-trainer**

### Viewing Trainees (by Trainer)

**Flow:**

1. Trainer asks AI to view trainees
2. AI provides handler button
3. Handler retrieves all trainees from trainer's trainee list
4. Display information: name, contact, registration date, trainee id
5. If list has 05 or fewer trainees: Display directly in chat
6. If list has more than 05 trainees: Generate and provide CSV downloadable file with all trainee information

- Direct command: **/view-trainees**

### Viewing Trainers (by Trainee)

**Flow:**

1. Trainee asks AI to view trainers
2. AI provides handler button
3. Handler retrieves all trainers from trainee's subscribed trainer list
4. Display information: name, specialization, contact, trainer id
5. If list has ~~05~~ or fewer trainers: Display directly in chat
6. If list has more than 05 trainers: Generate and provide CSV downloadable file with all trainer information

- Direct command: **/view-trainers**

### Removing Trainee (by Trainer)

**Flow:**

1. Trainer asks AI to remove a trainee
2. AI provides handler button to start remove trainee task
3. Task asks trainer to provide trainee id
4. System verifies trainee id exists in trainer's trainee list
5. If found:
   - Ask confirmation: "Are you sure you want to remove trainee [name] ([id])?"
   - If confirmed:
     - Remove trainee id from trainer's trainee list
     - Remove trainer id from that trainee's subscribed trainer list
     - Remove all habit assignments for this trainee from this trainer
     - Notify both trainer and trainee about the removal
     - Inform trainee they need to send new invite to be added again
6. If not found: Inform trainer this trainee is not in their list

- Direct command: **/remove-trainee**

### Removing Trainer (by Trainee)

**Flow:**

1. Trainee asks AI to remove a trainer
2. AI provides handler button to start remove trainer task
3. Task asks trainee to provide trainer id
4. System verifies trainer id exists in trainee's subscribed trainer list
5. If found:
   - Ask confirmation: "Are you sure you want to remove trainer [name] ([id])?"
   - If confirmed:
     - Remove trainer id from trainee's subscribed trainer list
     - Remove trainee id from that trainer's trainee list
     - Remove all habit assignments from this trainer for this trainee
     - Notify both trainee and trainer about the removal
6. If not found: Inform trainee this trainer is not in their list

- Direct command: **/remove-trainer**

### Trainer-Created Trainee Account Capabilities

Any trainee created by a trainer functions exactly the same as a self-registered trainee with full access to:

- Edit profile using client_registration_inputs.json fields
- Delete their own account (follows standard trainee deletion flow)
- All trainee features including habit logging, progress viewing, etc.

## Fitness Habit Management System

### Habit Creation (by Trainer)

**Flow:**

1. Trainer asks AI to create a fitness habit
2. AI provides handler button to start create habit task
3. Task retrieves fields from habit_creation_inputs.json file (allows easy customization)
4. System asks for each field one by one:
   - Habit name (examples: water_intake, sleep_hours, daily_steps_walked, body_weight_monitoring, number_of_meals_logged)
   - Habit description
   - Target value/goal
   - Unit of measurement (liters, hours, steps, kg, meals, etc.)
   - Frequency (daily, weekly)
   - Any other fields defined in the JSON
5. After collecting all information:
   - Generate unique habit id (5-7 characters based on habit name and creation date, adding 2-3 numbers if needed for uniqueness)
   - Save habit in fitness habit table with trainer id
   - Confirm habit creation to trainer

- Direct command: **/create-habit**

### Habit Editing (by Trainer)

**Flow:**

1. Trainer asks AI to edit a habit
2. AI provides handler button to start edit habit task
3. Task asks trainer to provide habit id
4. System verifies habit belongs to this trainer
5. If verified:
   - Display current habit information
   - Retrieve editable fields from habit_creation_inputs.json
   - For each field, ask if trainer wants to update
   - Trainer can skip or provide updated answer
   - After collecting all updates, validate data
   - If valid: Update habit and confirm
   - If invalid: Show error message and ask to try again
6. If not verified: Inform trainer this habit doesn't belong to them

- Direct command: **/edit-habit**

### Habit Deletion (by Trainer)

**Flow:**

1. Trainer asks AI to delete a habit
2. AI provides handler button to start delete habit task
3. Task asks trainer to provide habit id
4. System verifies habit belongs to this trainer
5. If verified:
   - Ask confirmation: "Are you sure you want to delete habit [name] ([id])? This will remove it from all assigned trainees."
   - If confirmed:
     - Delete habit from fitness habit table
     - Remove all habit assignments from trainee habit assignment table for this habit
     - Delete all habit logs for this habit from habit log table
     - Notify all assigned trainees that this habit has been removed by their trainer
6. If not verified: Inform trainer this habit doesn't belong to them

- Direct command: **/delete-habit**

### Habit Assignment (by Trainer)

**Flow:**

1. Trainer asks AI to assign a habit to trainees
2. AI provides handler button to start assign habit task
3. Task asks trainer to provide habit id
4. System verifies habit belongs to this trainer
5. If verified:
   - Display habit details (name, description, target, unit, frequency)
   - Ask trainer to provide one or more trainee ids (can be comma-separated or provided one by one)
   - Verify each trainee id exists in trainer's trainee list
   - For valid trainee ids:
     - Create entries in trainee habit assignment table (link trainee id with habit id)
     - Set assignment date
     - Send notification to each assigned trainee with habit details and target goals
   - For invalid trainee ids: Inform which ids are not in trainer's trainee list
6. If not verified: Inform trainer this habit doesn't belong to them

- Direct command: **/assign-habit**

### Viewing Created Habits (by Trainer)

**Flow:**

1. Trainer asks AI to view created habits
2. AI provides handler button
3. Handler retrieves all habits created by trainer from fitness habit table
4. Display information: habit name, description, target value, unit, frequency, number of assigned trainees, habit id
5. If list has 5 or fewer habits: Display directly in chat
6. If list has more than 5 habits: Generate and provide CSV downloadable file with all habit information

- Direct command: **/view-habits**

### Viewing Assigned Habits (by Trainee)

**Flow:**

1. Trainee asks AI to view assigned habits
2. AI provides handler button
3. Handler retrieves all habits assigned to trainee from trainee habit assignment table
4. Display information: habit name, description, target value, unit, frequency, assigned by trainer name, assignment date, habit id
5. Display all assigned habits directly in chat (no CSV needed as trainees typically have fewer habits)

- Direct command: **/view-my-habits**

### Daily Habit Reminder and Logging (by Trainee)

**Automated Daily Reminder:**

- Every day at scheduled time (e.g., 8 AM), system automatically sends message to each trainee with assigned habits
- Message lists all habits for the day: habit names, target values, units
- Includes handler button to start logging

**Logging Flow:**

1. Trainee clicks reminder button OR asks AI to log habits
2. AI provides handler button to start log habits task
3. Task goes through each assigned habit one by one
4. For each habit, ask trainee to provide actual value completed (e.g., "How many liters of water did you drink?")
5. After collecting value for each habit:
   - Save to habit log table: trainee id, habit id, log date and time, completed value
   - Note: Trainee can log multiple times per day - each entry saved separately with timestamp
6. After all habits are logged:
   - For each habit, retrieve target value from habit table
   - Calculate total completed value (sum all log entries for that habit for today)
   - Calculate due value (target - total completed)
   - Calculate completion percentage ((total completed / target) × 100)
   - Display summary: habit name, total completed, due, completion percentage

- Direct command: **/log-habits**

### Viewing Habit Progress (by Trainee)

**Flow:**

1. Trainee asks AI to view habit progress for a specific day
2. AI provides handler button to start view progress task
3. Task asks trainee to provide date (day, month, year)
4. System retrieves all habit logs for that trainee for specified date
5. Group logs by habit id
6. For each habit:
   - Retrieve target value from habit table
   - Sum all completed values logged for that day
   - Calculate due value (target - total completed)
   - Calculate completion percentage ((total completed / target) × 100)
7. Display each habit: name, target, total completed, due, completion percentage
8. If no logs for that date: Inform trainee no habit logs found

- Direct command: **/view-progress**

### Requesting Progress Reports (by Trainee)

**Flow:**

1. Trainee asks AI for progress report
2. AI provides handler buttons: "Weekly Report" / "Monthly Report"
3. If weekly selected:
   - Ask which week (provide start date OR week number and year)
4. If monthly selected:
   - Ask which month and year
5. After collecting time period:
   - Retrieve all habit logs for trainee for specified period
   - For each day and each habit:
     - Retrieve target value from habit table
     - Sum all completed values for that day
     - Calculate due value (target - total completed)
     - Calculate completion percentage ((total completed / target) × 100)
6. Generate CSV file containing:
   - Columns: Date, Habit Name, Target Value, Total Completed Value, Due Value, Completion Percentage
   - Summary statistics: average completion percentage per habit, total days logged, overall completion rate
7. Provide CSV file for download

- Direct commands: **/weekly-report** or **/monthly-report**

### Viewing Trainee Habit Progress (by Trainer)

**Flow:**

1. Trainer asks AI to view a trainee's habit progress
2. AI provides handler button to start view trainee progress task
3. Task asks trainer to provide trainee id
4. System verifies trainee id exists in trainer's trainee list
5. If verified:
   - Task asks trainer to provide date (day, month, year)
   - Retrieve all habit logs for that trainee for specified date
   - Group logs by habit id
   - For each habit:
     - Retrieve target value from habit table
     - Sum all completed values logged for that day
     - Calculate due value (target - total completed)
     - Calculate completion percentage ((total completed / target) × 100)
   - Display each habit: name, target, total completed, due, completion percentage
   - If no logs for that date: Inform trainer no habit logs found for that trainee
6. If not verified: Inform trainer this trainee is not in their list

- Direct command: **/view-trainee-progress**

### Requesting Trainee Progress Reports (by Trainer)

**Flow:**

1. Trainer asks AI for a trainee's progress report
2. AI provides handler button to start trainee report task
3. Task asks trainer to provide trainee id
4. System verifies trainee id exists in trainer's trainee list
5. If verified:
   - AI provides handler buttons: "Weekly Report" / "Monthly Report"
   - If weekly selected: Ask which week (provide start date OR week number and year)
   - If monthly selected: Ask which month and year
   - After collecting time period:
     - Retrieve all habit logs for that trainee for specified period
     - For each day and each habit:
       - Retrieve target value from habit table
       - Sum all completed values for that day
       - Calculate due value (target - total completed)
       - Calculate completion percentage ((total completed / target) × 100)
   - Generate CSV file containing:
     - Columns: Date, Habit Name, Target Value, Total Completed Value, Due Value, Completion Percentage
     - Summary statistics: average completion percentage per habit, total days logged, overall completion rate
   - Provide CSV file for download
6. If not verified: Inform trainer this trainee is not in their list

- Direct commands: **/trainee-weekly-report** or **/trainee-monthly-report**

### Data Integrity for Habit Logs

- Trainees cannot edit or delete entries in habit log table
- Once logged, data is permanent and immutable for accurate tracking
- Trainees can log additional values for same habit on same day (saved as new entries)
- All values are summed when calculating progress
- This ensures data integrity and prevents manipulation while allowing flexible logging throughout the day

## Summary Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Message Received                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Check User in DB     │
          └──────────┬────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ┌─────────┐            ┌──────────┐
    │  Found  │            │Not Found │
    └────┬────┘            └────┬─────┘
         │                      │
         │                      ▼
         │              ┌───────────────┐
         │              │ Registration  │
         │              │  Flow (P1)    │
         │              └───────────────┘
         │
         ▼
   ┌──────────────────┐
   │Check Login Status│
   └─────┬────────────┘
         │
    ┌────┴─────┬──────────┬──────────┐
    │          │          │          │
    ▼          ▼          ▼          ▼
┌───────┐  ┌─────┐  ┌────────┐  ┌────────────┐
│ Empty │  │Trainr│  │Trainee │  │  Command   │
└───┬───┘  └──┬──┘  └───┬────┘  └──────┬─────┘
    │         │         │              │
    │         │         │              ▼
    │         │         │       ┌──────────────┐
    │         │         │       │ /logout      │
    │         │         │       │ /switch-role │
    │         │         │       │ /register    │
    │         │         │       │ /stop        │
    │         │         │       │ /help        │
    │         │         │       └──────────────┘
    │         │         │
    │         ▼         ▼
    │    ┌─────────────────────────┐
    │    │  Check Handler Message  │
    │    └──────┬──────────────────┘
    │           │
    │      ┌────┴─────┐
    │      │          │
    │      ▼          ▼
    │   ┌──────┐  ┌──────────────┐
    │   │ Yes  │  │      No      │
    │   └──┬───┘  └──────┬───────┘
    │      │             │
    │      ▼             ▼
    │   ┌─────────┐  ┌────────────────┐
    │   │ Execute │  │Check Running   │
    │   │ Handler │  │     Task       │
    │   └─────────┘  └──────┬─────────┘
    │                       │
    │                  ┌────┴─────┐
    │                  │          │
    │                  ▼          ▼
    │              ┌────────┐ ┌─────────┐
    │              │Running │ │No/Stopped│
    │              │& !Stop │ └────┬────┘
    │              └───┬────┘      │
    │                  │           │
    │                  ▼           ▼
    │              ┌─────────┐ ┌──────────────┐
    │              │Continue │ │ AI Assistant │
    │              │  Task   │ │  (Context:   │
    │              └─────────┘ │ Last 5 Tasks,│
    │                          │Last 10 Chats)│
    │                          └──────┬───────┘
    │                                 │
    │                            ┌────┴─────┐
    │                            │          │
    │                            ▼          ▼
    │                        ┌────────┐ ┌────────┐
    │                        │Task    │ │Convers-│
    │                        │Request │ │ation   │
    │                        └───┬────┘ └────────┘
    │                            │
    │                            ▼
    │                     ┌─────────────┐
    │                     │   Provide   │
    │                     │   Handler   │
    │                     │   Buttons   │
    │                     └─────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│              Role-Specific Features                   │
├──────────────────────────────────────────────────────┤
│                                                       │
│  TRAINER (Phase 2 & 3):                              │
│  • Invite/Create Trainee                             │
│  • View/Remove Trainees                              │
│  • Create/Edit/Delete Habits                         │
│  • Assign Habits                                     │
│  • View Trainee Progress & Reports                   │
│                                                       │
│  TRAINEE (Phase 2 & 3):                              │
│  • Search/Invite Trainer                             │
│  • View/Remove Trainers                              │
│  • View Assigned Habits                              │
│  • Log Habits (Multiple times/day)                   │
│  • View Progress & Generate Reports                  │
│                                                       │
│  COMMON (Phase 1):                                   │
│  • View/Edit/Delete Profile                          │
│  • Logout/Switch Role                                │
│                                                       │
│  ENHANCED (Phase 4):                                 │
│  • AI Suggestions                                    │
│  • Stats Dashboard                                   │
│  • Help System                                       │
│                                                       │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│              Scheduled Jobs & Notifications           │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Daily 8 AM:                                         │
│  • Query all trainees with assigned habits           │
│  • Send habit reminder with log button               │
│                                                       │
│  Weekly (if enabled):                                │
│  • Send weekly summary to trainees                   │
│  • Send trainer team summary                         │
│                                                       │
│  Event-driven:                                       │
│  • Invitation notifications                          │
│  • Assignment notifications                          │
│  • Removal notifications                             │
│  • Milestone achievements                            │
│                                                       │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│         Monitoring & Logging (Phase 5)                │
├──────────────────────────────────────────────────────┤
│                                                       │
│  • Log all interactions                              │
│  • Track errors and exceptions                       │
│  • Monitor performance metrics                       │
│  • Alert on critical issues                          │
│  • Analytics dashboards                              │
│                                                       │
└──────────────────────────────────────────────────────┘
```

## Task Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    TASK LIFECYCLE                            │
└─────────────────────────────────────────────────────────────┘

1. TASK INITIATION
   ┌──────────────────────────────────────┐
   │  User sends handler command OR       │
   │  AI provides handler button          │
   │  User clicks button                  │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Create task entry in task_list      │
   │  Status: "running"                   │
   │  Save task_type and initial data     │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Inform user about /stop option      │
   │  "You can type /stop to cancel"      │
   └──────────────┬───────────────────────┘
                  │
                  ▼

2. TASK EXECUTION (Multi-step)
   ┌──────────────────────────────────────┐
   │  Load task data from task_list       │
   │  Determine current step              │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Ask for next required input         │
   │  (Based on JSON config or logic)     │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Wait for user response              │
   └──────────────┬───────────────────────┘
                  │
     ┌────────────┴────────────┐
     │                         │
     ▼                         ▼
┌──────────┐            ┌──────────┐
│ /stop    │            │ Response │
│ received │            │ received │
└────┬─────┘            └────┬─────┘
     │                       │
     ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│ Update task      │   │ Validate input   │
│ status: stopped  │   └────┬─────────────┘
│ Confirm to user  │        │
└──────────────────┘   ┌────┴──────┐
                       │           │
                       ▼           ▼
                  ┌────────┐  ┌────────┐
                  │ Valid  │  │Invalid │
                  └───┬────┘  └───┬────┘
                      │           │
                      │           ▼
                      │      ┌────────────────┐
                      │      │ Show error     │
                      │      │ Ask again      │
                      │      └───┬────────────┘
                      │          │
                      │          └──────┐
                      │                 │
                      ▼                 ▼
                ┌─────────────────────────┐
                │ Save to task_data       │
                │ Move to next step       │
                │ Update task_list        │
                └──────────┬──────────────┘
                           │
                           │
    ┌──────────────────────┴──────────────┐
    │                                     │
    ▼                                     ▼
┌──────────────┐                  ┌──────────────┐
│ More steps?  │                  │ Last step?   │
└───┬──────────┘                  └───┬──────────┘
    │                                 │
    │ YES                             │ YES
    │                                 │
    └────► Loop back to              ▼
           "Ask for next      ┌────────────────┐
            required input"   │ TASK COMPLETION│
                              └────────────────┘

3. TASK COMPLETION
   ┌──────────────────────────────────────┐
   │  Execute final action                │
   │  (Save to DB, send notifications)    │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Update task status: "completed"     │
   │  Save completion timestamp           │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Show success message to user        │
   │  Provide summary of actions taken    │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  AI suggests next possible actions   │
   │  (Based on context and history)      │
   └──────────────────────────────────────┘
```

## Habit Logging Calculation Flow

```
┌─────────────────────────────────────────────────────────────┐
│              HABIT LOGGING & CALCULATION                     │
└─────────────────────────────────────────────────────────────┘

1. USER INITIATES LOGGING
   ┌──────────────────────────────────────┐
   │  Trainee: /log-habits OR             │
   │  Clicks daily reminder button        │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Query: trainee_habit_assignment     │
   │  WHERE trainee_id = [current user]   │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Get list of assigned habit_ids      │
   └──────────────┬───────────────────────┘
                  │
                  ▼

2. COLLECT VALUES (Loop through each habit)
   ┌──────────────────────────────────────┐
   │  Get habit details from              │
   │  fitness_habit table by habit_id     │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Display: "How much [habit_name]?"   │
   │  "Target: [target_value] [unit]"     │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  User enters completed_value         │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Validate: numeric, positive         │
   └──────────────┬───────────────────────┘
                  │
     ┌────────────┴────────────┐
     │                         │
     ▼                         ▼
┌──────────┐            ┌──────────┐
│ Invalid  │            │  Valid   │
└────┬─────┘            └────┬─────┘
     │                       │
     ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│ Show error       │   │ INSERT INTO      │
│ Ask again        │   │ habit_log:       │
└────┬─────────────┘   │ - trainee_id     │
     │                 │ - habit_id       │
     └─────────────────│ - log_date (now) │
                       │ - log_time (now) │
                       │ - completed_value│
                       └────┬─────────────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │ Next habit?      │
                    └────┬─────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
         ┌────────┐            ┌────────┐
         │  YES   │            │   NO   │
         └───┬────┘            └───┬────┘
             │                     │
             │                     ▼
             └────► Loop back      │
                    to "Get        │
                    habit          │
                    details"       │
                                   │
                                   ▼
3. CALCULATE & DISPLAY SUMMARY
   ┌──────────────────────────────────────┐
   │  For each logged habit today:        │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Query: SELECT habit_id,             │
   │         SUM(completed_value)         │
   │  FROM habit_log                      │
   │  WHERE trainee_id = [user]           │
   │    AND log_date = [today]            │
   │  GROUP BY habit_id                   │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  For each habit_id in results:       │
   │                                      │
   │  1. Get target_value from            │
   │     fitness_habit table              │
   │                                      │
   │  2. total_completed = SUM result     │
   │                                      │
   │  3. due_value =                      │
   │     target_value - total_completed   │
   │                                      │
   │  4. completion_percentage =          │
   │     (total_completed / target) × 100 │
   │                                      │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Display Summary Table:              │
   │  ┌────────────────────────────────┐  │
   │  │ Habit | Target | Done | Due | %│  │
   │  ├────────────────────────────────┤  │
   │  │ Water │ 3L  │ 2.5L│0.5L│83% │  │
   │  │ Steps │ 10K │ 8K  │ 2K │80% │  │
   │  │ Sleep │ 8hr │ 7hr │ 1hr│87% │  │
   │  └────────────────────────────────┘  │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  "Great job! Keep it up! 💪"         │
   └──────────────────────────────────────┘
```

## Report Generation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  REPORT GENERATION                           │
└─────────────────────────────────────────────────────────────┘

1. REPORT REQUEST
   ┌──────────────────────────────────────┐
   │  User: /weekly-report OR             │
   │        /monthly-report               │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Ask for time period:                │
   │  Weekly: start date or week#/year    │
   │  Monthly: month/year                 │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Calculate date range                │
   │  Weekly: 7 days from start           │
   │  Monthly: all days in month          │
   └──────────────┬───────────────────────┘
                  │
                  ▼

2. DATA RETRIEVAL
   ┌──────────────────────────────────────┐
   │  Query all assigned habits:          │
   │  FROM trainee_habit_assignment       │
   │  WHERE trainee_id = [user]           │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  For each date in range:             │
   │    For each habit:                   │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Query habit_log:                    │
   │  SELECT habit_id,                    │
   │         SUM(completed_value)         │
   │  FROM habit_log                      │
   │  WHERE trainee_id = [user]           │
   │    AND log_date = [current_date]     │
   │  GROUP BY habit_id                   │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  For each result:                    │
   │                                      │
   │  1. Get target from fitness_habit    │
   │  2. Calculate due & percentage       │
   │  3. Add row to CSV buffer            │
   │                                      │
   └──────────────┬───────────────────────┘
                  │
                  ▼

3. STATISTICS CALCULATION
   ┌──────────────────────────────────────┐
   │  Calculate summary stats:            │
   │                                      │
   │  • Avg completion % per habit        │
   │  • Total days logged                 │
   │  • Overall completion rate           │
   │  • Days with 100% completion         │
   │  • Best performing habit             │
   │  • Habits needing attention          │
   │  • Streak days (consecutive logs)    │
   │                                      │
   └──────────────┬───────────────────────┘
                  │
                  ▼

4. CSV GENERATION
   ┌──────────────────────────────────────┐
   │  Create CSV structure:               │
   │                                      │
   │  ┌────────────────────────────────┐  │
   │  │ SUMMARY SECTION               │  │
   │  │ - Report period               │  │
   │  │ - Generated for: [user]       │  │
   │  │ - Generated on: [timestamp]   │  │
   │  │ - Summary statistics          │  │
   │  ├────────────────────────────────┤  │
   │  │ DETAILED DATA                 │  │
   │  │ Date|Habit|Target|Done|Due|%  │  │
   │  │ [All rows from buffer]        │  │
   │  └────────────────────────────────┘  │
   │                                      │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Save CSV to file storage            │
   │  Generate download link              │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │  Send download link to user          │
   │  "Your report is ready! 📊"          │
   └──────────────────────────────────────┘
```
