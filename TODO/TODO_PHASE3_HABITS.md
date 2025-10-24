# Phase 3: Fitness Habit Management - TODO

## 🎯 Phase Overview

Implement complete habit tracking system: creation, assignment, logging, progress tracking, and reporting.

---

## 📋 TASKS

### 1. Database Schema

#### 1.1 Fitness Habits Table

- [ ] Create fitness_habits table
- [ ] Columns:
  - [ ] habit_id (VARCHAR 5-7 chars, unique)
  - [ ] trainer_id (creator)
  - [ ] habit_name
  - [ ] habit_description
  - [ ] target_value
  - [ ] unit_of_measurement
  - [ ] frequency (daily/weekly)
  - [ ] created_at, updated_at
- [ ] Add indexes
- [ ] Test queries

#### 1.2 Habit Assignments Table

- [ ] Create habit_assignments table
- [ ] Columns:
  - [ ] id (UUID)
  - [ ] habit_id
  - [ ] client_id
  - [ ] trainer_id
  - [ ] assigned_at
  - [ ] status (active/inactive)
- [ ] Add indexes
- [ ] Add foreign keys
- [ ] Test queries

#### 1.3 Habit Logs Table

- [ ] Create habit_logs table
- [ ] Columns:
  - [ ] id (UUID)
  - [ ] habit_id
  - [ ] client_id
  - [ ] log_date
  - [ ] log_time
  - [ ] completed_value
  - [ ] notes (optional)
  - [ ] created_at
- [ ] Add indexes (especially on date)
- [ ] Prevent editing/deletion
- [ ] Test queries

#### 1.4 Habit Configuration

- [ ] Create habit_creation_inputs.json
- [ ] Define habit fields:
  - [ ] habit_name
  - [ ] habit_description
  - [ ] target_value
  - [ ] unit_of_measurement
  - [ ] frequency
- [ ] Add validation rules
- [ ] Add prompts

### 2. Trainer Features - Habit Management

#### 2.1 Create Habit (/create-habit)

- [ ] Create create_habit handler
- [ ] Create create_habit task
- [ ] Load habit_creation_inputs.json
- [ ] Ask for each field:
  - [ ] Habit name (with examples)
  - [ ] Description
  - [ ] Target value
  - [ ] Unit (liters, hours, steps, kg, meals, etc.)
  - [ ] Frequency (daily/weekly)
- [ ] Validate each input
- [ ] Generate unique habit_id
- [ ] Save to fitness_habits table
- [ ] Include trainer_id
- [ ] Send confirmation with habit_id
- [ ] Complete task
- [ ] Handle errors

#### 2.2 Edit Habit (/edit-habit)

- [ ] Create edit_habit handler
- [ ] Create edit_habit task
- [ ] Ask for habit_id
- [ ] Verify habit belongs to trainer
- [ ] Show current habit info
- [ ] Load editable fields
- [ ] For each field:
  - [ ] Show current value
  - [ ] Ask to skip or update
  - [ ] Validate if updating
- [ ] Apply all updates
- [ ] Send confirmation
- [ ] Complete task
- [ ] Handle errors (not owner, not found)

#### 2.3 Delete Habit (/delete-habit)

- [ ] Create delete_habit handler
- [ ] Create delete_habit task
- [ ] Ask for habit_id
- [ ] Verify habit belongs to trainer
- [ ] Show habit info
- [ ] Show impact (assigned clients count)
- [ ] Ask confirmation
- [ ] If confirmed:
  - [ ] Delete from fitness_habits
  - [ ] Remove all assignments
  - [ ] Delete all logs for this habit
  - [ ] Notify assigned clients
  - [ ] Send confirmation
- [ ] If cancelled, end task
- [ ] Complete task
- [ ] Handle errors

#### 2.4 Assign Habit (/assign-habit)

- [ ] Create assign_habit handler
- [ ] Create assign_habit task
- [ ] Ask for habit_id
- [ ] Verify habit belongs to trainer
- [ ] Show habit details
- [ ] Ask for client ID(s)
- [ ] Support comma-separated IDs
- [ ] Verify each client in trainer's list
- [ ] For valid clients:
  - [ ] Create assignment record
  - [ ] Set assignment date
  - [ ] Send notification to client
  - [ ] Include habit details
  - [ ] Include target goals
- [ ] Show summary (assigned/failed)
- [ ] Complete task
- [ ] Handle errors

#### 2.5 View Created Habits (/view-habits)

- [ ] Create view_habits handler
- [ ] Get trainer_id
- [ ] Query fitness_habits table
- [ ] Get assignment counts
- [ ] If ≤ 5 habits:
  - [ ] Format as message
  - [ ] Show: name, description, target, unit, frequency, assigned count, habit_id
  - [ ] Send in chat
- [ ] If > 5 habits:
  - [ ] Generate CSV file
  - [ ] Include all habit info
  - [ ] Send as download
- [ ] Handle no habits case
- [ ] Handle errors

#### 2.6 View Client Progress (/view-trainee-progress)

- [ ] Create view_trainee_progress handler
- [ ] Create task
- [ ] Ask for client_id
- [ ] Verify client in trainer's list
- [ ] Ask for date
- [ ] Query habit_logs for that date
- [ ] Group by habit_id
- [ ] For each habit:
  - [ ] Get target value
  - [ ] Sum completed values
  - [ ] Calculate due value
  - [ ] Calculate completion %
- [ ] Format and send results
- [ ] Handle no logs case
- [ ] Complete task
- [ ] Handle errors

#### 2.7 Client Progress Reports

- [ ] Create trainee_report handler
- [ ] Ask for client_id
- [ ] Verify client in trainer's list
- [ ] Show report type buttons:
  - [ ] Weekly Report
  - [ ] Monthly Report
- [ ] If weekly:
  - [ ] Ask for week (start date or week number)
  - [ ] Query logs for that week
- [ ] If monthly:
  - [ ] Ask for month and year
  - [ ] Query logs for that month
- [ ] For each day and habit:
  - [ ] Calculate totals
  - [ ] Calculate completion %
- [ ] Generate CSV:
  - [ ] Columns: Date, Habit, Target, Completed, Due, %
  - [ ] Add summary statistics
  - [ ] Average completion per habit
  - [ ] Total days logged
  - [ ] Overall completion rate
- [ ] Send CSV file
- [ ] Complete task
- [ ] Handle errors

### 3. Client Features - Habit Tracking

#### 3.1 View Assigned Habits (/view-my-habits)

- [ ] Create view_my_habits handler
- [ ] Get client_id
- [ ] Query habit_assignments
- [ ] Get habit details for each
- [ ] Get trainer info for each
- [ ] Format message:
  - [ ] Habit name
  - [ ] Description
  - [ ] Target value & unit
  - [ ] Frequency
  - [ ] Assigned by (trainer name)
  - [ ] Assignment date
  - [ ] Habit ID
- [ ] Send all habits (no CSV needed)
- [ ] Handle no habits case
- [ ] Handle errors

#### 3.2 Daily Habit Reminder (Automated)

- [ ] Create scheduled job
- [ ] Run daily at 8 AM (configurable)
- [ ] Query all clients with active habits
- [ ] For each client:
  - [ ] Get assigned habits
  - [ ] Format reminder message
  - [ ] List all habits with targets
  - [ ] Add log button
  - [ ] Send via WhatsApp
- [ ] Log reminder sent
- [ ] Handle errors

#### 3.3 Log Habits (/log-habits)

- [ ] Create log_habits handler
- [ ] Create log_habits task
- [ ] Get client_id
- [ ] Get assigned habits
- [ ] For each habit:
  - [ ] Show habit name and target
  - [ ] Ask for completed value
  - [ ] Validate input (number)
  - [ ] Save to habit_logs
  - [ ] Include date and time
  - [ ] Allow multiple logs per day
- [ ] After all habits logged:
  - [ ] For each habit:
    - [ ] Get target value
    - [ ] Sum today's logs
    - [ ] Calculate due value
    - [ ] Calculate completion %
  - [ ] Format summary
  - [ ] Send summary message
- [ ] Complete task
- [ ] Handle errors

#### 3.4 View Progress (/view-progress)

- [ ] Create view_progress handler
- [ ] Create task
- [ ] Ask for date (day, month, year)
- [ ] Parse date input
- [ ] Query habit_logs for that date
- [ ] Group by habit_id
- [ ] For each habit:
  - [ ] Get target value
  - [ ] Sum completed values
  - [ ] Calculate due value
  - [ ] Calculate completion %
- [ ] Format results
- [ ] Send message
- [ ] Handle no logs case
- [ ] Complete task
- [ ] Handle errors

#### 3.5 Progress Reports

- [ ] Create progress_report handler
- [ ] Show report type buttons:
  - [ ] Weekly Report
  - [ ] Monthly Report
- [ ] If weekly:
  - [ ] Ask for week (start date or week number)
  - [ ] Query logs for that week
- [ ] If monthly:
  - [ ] Ask for month and year
  - [ ] Query logs for that month
- [ ] For each day and habit:
  - [ ] Calculate totals
  - [ ] Calculate completion %
- [ ] Generate CSV:
  - [ ] Columns: Date, Habit, Target, Completed, Due, %
  - [ ] Add summary statistics
  - [ ] Average completion per habit
  - [ ] Total days logged
  - [ ] Overall completion rate
- [ ] Send CSV file
- [ ] Complete task
- [ ] Handle errors

### 4. Habit Service

#### 4.1 HabitService Class

- [ ] Create HabitService class
- [ ] Method: create_habit()
- [ ] Method: update_habit()
- [ ] Method: delete_habit()
- [ ] Method: get_habit()
- [ ] Method: get_trainer_habits()
- [ ] Method: assign_habit()
- [ ] Method: unassign_habit()
- [ ] Method: get_client_habits()
- [ ] Method: log_habit()
- [ ] Method: get_habit_logs()
- [ ] Method: calculate_progress()
- [ ] Method: generate_report()

#### 4.2 ID Generation

- [ ] Generate unique habit_id (5-7 chars)
- [ ] Based on habit name + date
- [ ] Check uniqueness
- [ ] Retry if collision

### 5. Progress Calculation

#### 5.1 Daily Progress

- [ ] Query logs for specific date
- [ ] Group by habit
- [ ] Sum completed values
- [ ] Get target from habit
- [ ] Calculate due (target - completed)
- [ ] Calculate percentage
- [ ] Handle multiple logs per day

#### 5.2 Weekly Progress

- [ ] Query logs for date range
- [ ] Group by date and habit
- [ ] Calculate daily totals
- [ ] Calculate weekly averages
- [ ] Generate statistics

#### 5.3 Monthly Progress

- [ ] Query logs for month
- [ ] Group by date and habit
- [ ] Calculate daily totals
- [ ] Calculate monthly averages
- [ ] Generate statistics

### 6. Report Generation

#### 6.1 CSV Generator

- [ ] Create CSVGenerator class
- [ ] Method: generate_progress_report()
- [ ] Format data properly
- [ ] Add headers
- [ ] Add summary section
- [ ] Calculate statistics
- [ ] Save to file
- [ ] Return file path

#### 6.2 Report Statistics

- [ ] Average completion per habit
- [ ] Total days logged
- [ ] Overall completion rate
- [ ] Best performing habits
- [ ] Habits needing attention
- [ ] Streak tracking

### 7. Data Integrity

#### 7.1 Immutable Logs

- [ ] Prevent log editing
- [ ] Prevent log deletion
- [ ] Only allow new entries
- [ ] Ensure data accuracy

#### 7.2 Validation

- [ ] Validate habit data
- [ ] Validate log values
- [ ] Validate dates
- [ ] Validate relationships

### 8. Notifications

#### 8.1 Daily Reminders

- [ ] Format reminder messages
- [ ] Include all habits
- [ ] Add motivational text
- [ ] Include log button
- [ ] Send at scheduled time

#### 8.2 Assignment Notifications

- [ ] Notify client of new habit
- [ ] Include habit details
- [ ] Include trainer info
- [ ] Include target goals

#### 8.3 Removal Notifications

- [ ] Notify when habit deleted
- [ ] Notify when habit unassigned
- [ ] Include reason if provided

### 9. Testing

#### 9.1 Unit Tests

- [ ] Test habit creation
- [ ] Test habit editing
- [ ] Test habit deletion
- [ ] Test habit assignment
- [ ] Test habit logging
- [ ] Test progress calculation
- [ ] Test report generation

#### 9.2 Integration Tests

- [ ] Test complete habit creation flow
- [ ] Test habit assignment flow
- [ ] Test habit logging flow
- [ ] Test progress viewing
- [ ] Test report generation
- [ ] Test daily reminders
- [ ] Test multiple logs per day

#### 9.3 End-to-End Tests

- [ ] Trainer creates habit
- [ ] Trainer assigns to clients
- [ ] Clients receive notifications
- [ ] Clients log habits
- [ ] Clients view progress
- [ ] Clients generate reports
- [ ] Trainer views client progress
- [ ] Trainer generates client reports

### 10. Error Handling

- [ ] Handle invalid habit IDs
- [ ] Handle unauthorized access
- [ ] Handle invalid log values
- [ ] Handle date parsing errors
- [ ] Handle database errors
- [ ] User-friendly error messages

### 11. Performance Optimization

- [ ] Index habit_logs by date
- [ ] Index habit_logs by client_id
- [ ] Optimize progress queries
- [ ] Cache habit data
- [ ] Optimize report generation

### 12. Documentation

- [ ] Document habit system
- [ ] Document logging process
- [ ] Document progress calculation
- [ ] Document report generation
- [ ] Update API documentation
- [ ] Create user guide

---

## 🎯 Success Criteria

### Must Have

- [ ] Trainers can create habits
- [ ] Trainers can edit habits
- [ ] Trainers can delete habits
- [ ] Trainers can assign habits to clients
- [ ] Clients can view assigned habits
- [ ] Clients can log habits (multiple times/day)
- [ ] Clients can view daily progress
- [ ] Clients can generate reports
- [ ] Trainers can view client progress
- [ ] Trainers can generate client reports
- [ ] Daily reminders work
- [ ] Progress calculation accurate

### Should Have

- [ ] CSV export for reports
- [ ] Summary statistics
- [ ] Streak tracking
- [ ] Motivational messages

### Nice to Have

- [ ] Habit templates
- [ ] Habit categories
- [ ] Progress charts
- [ ] Achievement badges
- [ ] Leaderboards

---

## 📊 Progress Tracking

**Database:** ⏳ 0% Complete
**Trainer Features:** ⏳ 0% Complete
**Client Features:** ⏳ 0% Complete
**Habit Service:** ⏳ 0% Complete
**Progress Calculation:** ⏳ 0% Complete
**Report Generation:** ⏳ 0% Complete
**Testing:** ⏳ 0% Complete

**Overall Phase 3:** ⏳ 0% Complete

---

## 🚨 Blockers & Dependencies

### Blockers

- Phase 1 must be complete
- Phase 2 must be complete
- Habit tables must exist

### Dependencies

- Scheduled job system (for reminders)
- CSV generation library
- Date/time handling
- WhatsApp message sending

---

## 🔄 Next Phase

After Phase 3 is complete:
**Phase 4: Enhanced Features** (Optional)

- AI suggestions
- Analytics dashboard
- Advanced reporting
- Gamification
