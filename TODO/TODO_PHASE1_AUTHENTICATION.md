# Phase 1: Authentication & Account Management - TODO

## 🎯 Phase Overview

Complete user authentication, registration, login/logout, profile management, and account deletion.

---

## ✅ COMPLETED TASKS

### Backend Implementation

- [x] Create users table schema
- [x] Create trainer_client_list table
- [x] Create client_trainer_list table
- [x] Create trainer_tasks table
- [x] Create client_tasks table
- [x] Add trainer_id column to trainers table
- [x] Add client_id column to clients table
- [x] Add login_status to conversation_states
- [x] Create AuthenticationService
- [x] Create RegistrationService
- [x] Create TaskService
- [x] Create trainer_registration_inputs.json
- [x] Create client_registration_inputs.json
- [x] Create command_handlers.json
- [x] Write comprehensive documentation

---

## ⏳ PENDING TASKS

### 1. Database Setup

- [ ] **CRITICAL:** Run phase1_authentication_schema.sql in Supabase
- [ ] Verify all tables created successfully
- [ ] Verify all columns added successfully
- [ ] Verify all indexes created
- [ ] Test database queries
- [ ] Backup database before migration

### 2. Service Testing

- [ ] Test AuthenticationService.check_user_exists()
- [ ] Test AuthenticationService.generate_unique_id()
- [ ] Test AuthenticationService.create_user_entry()
- [ ] Test AuthenticationService.get_user_roles()
- [ ] Test AuthenticationService.set_login_status()
- [ ] Test AuthenticationService.auto_login_single_role()
- [ ] Test RegistrationService.get_registration_fields()
- [ ] Test RegistrationService.validate_field_value()
- [ ] Test RegistrationService.parse_field_value()
- [ ] Test RegistrationService.save_trainer_registration()
- [ ] Test RegistrationService.save_client_registration()
- [ ] Test TaskService.create_task()
- [ ] Test TaskService.get_running_task()
- [ ] Test TaskService.update_task()
- [ ] Test TaskService.complete_task()

### 3. Message Flow Integration

#### 3.1 Main Message Router

- [ ] Create/update main message handler
- [ ] Add user existence check
- [ ] Add login status check
- [ ] Add universal command detection
- [ ] Add role-based routing
- [ ] Add error handling
- [ ] Add logging

#### 3.2 Registration Flow Handler

- [ ] Create registration flow handler
- [ ] Show "Register as Trainer/Client" buttons
- [ ] Handle button clicks
- [ ] Create registration task
- [ ] Implement field collection loop
- [ ] Validate each field input
- [ ] Handle validation errors
- [ ] Parse and store field values
- [ ] Save complete registration
- [ ] Generate unique ID
- [ ] Create user entry
- [ ] Set login status
- [ ] Send success message with ID
- [ ] Handle registration errors

#### 3.3 Login Flow Handler

- [ ] Create login flow handler
- [ ] Check if user has single role
- [ ] Auto-login for single role
- [ ] Show role selection for multiple roles
- [ ] Handle role selection
- [ ] Set login status
- [ ] Send welcome message
- [ ] Handle login errors

### 4. Universal Commands

#### 4.1 Logout Command (/logout)

- [ ] Create logout handler
- [ ] Get current login status
- [ ] Stop all running tasks
- [ ] Clear login status
- [ ] Send confirmation message
- [ ] Handle errors

#### 4.2 Switch Role Command (/switch-role)

- [ ] Create switch role handler
- [ ] Check if user has both roles
- [ ] Get current login status
- [ ] Stop current role tasks
- [ ] Switch to opposite role
- [ ] Send confirmation message
- [ ] Handle errors (only one role)

#### 4.3 Register Command (/register)

- [ ] Create register handler
- [ ] Check if already logged in
- [ ] Check which roles user has
- [ ] Show available registration options
- [ ] Start registration flow
- [ ] Handle errors

#### 4.4 Stop Command (/stop)

- [ ] Create stop handler
- [ ] Get running task
- [ ] Stop the task
- [ ] Send confirmation message
- [ ] Handle no running task

#### 4.5 Help Command (/help)

- [ ] Create help handler
- [ ] Get user's login status
- [ ] Show available commands for role
- [ ] Show universal commands
- [ ] Format help message nicely

### 5. Profile Management

#### 5.1 View Profile (/view-profile)

- [ ] Create view profile handler
- [ ] Get user data from users table
- [ ] Get role data (trainer/client table)
- [ ] Filter showable fields
- [ ] Format profile data
- [ ] Send profile message
- [ ] Handle errors

#### 5.2 Edit Profile (/edit-profile)

- [ ] Create edit profile handler
- [ ] Create edit_profile task
- [ ] Get registration fields for role
- [ ] Loop through each field
- [ ] Show current value
- [ ] Ask "Skip or update?"
- [ ] Validate new value if updating
- [ ] Store updates in task_data
- [ ] Apply all updates to database
- [ ] Complete task
- [ ] Send success message
- [ ] Handle errors

#### 5.3 Delete Account (/delete-account)

- [ ] Create delete account handler
- [ ] Create delete_account task
- [ ] Show confirmation message
- [ ] Show what will be deleted
- [ ] Wait for confirmation
- [ ] If confirmed:
  - [ ] Delete role-specific data
  - [ ] Remove from relationship tables
  - [ ] Delete habits (if trainer)
  - [ ] Delete habit logs (if client)
  - [ ] Remove role_id from users table
  - [ ] Delete user entry if no other role
- [ ] Send confirmation message
- [ ] Handle cancellation
- [ ] Handle errors

### 6. Task Continuation Logic

- [ ] Create task continuation handler
- [ ] Get running task for user
- [ ] Check if task is stopped
- [ ] If running, continue next step
- [ ] If stopped/none, check for AI intent
- [ ] Handle task completion
- [ ] Handle task errors

### 7. AI Intent Detection

- [ ] Integrate with Claude AI
- [ ] Pass last 5 completed tasks
- [ ] Pass last 10 chat messages
- [ ] Detect if asking for task
- [ ] Provide relevant handler buttons
- [ ] Handle general conversation
- [ ] Suggest next actions

### 8. Button Handlers

- [ ] Create button handler system
- [ ] Map buttons to commands
- [ ] Handle button clicks
- [ ] Start appropriate tasks
- [ ] Send appropriate responses

### 9. Error Handling

- [ ] Add try-catch blocks
- [ ] Log all errors
- [ ] Send user-friendly error messages
- [ ] Handle database errors
- [ ] Handle validation errors
- [ ] Handle timeout errors

### 10. Testing & Validation

#### 10.1 Unit Tests

- [ ] Test all service methods
- [ ] Test field validation
- [ ] Test ID generation
- [ ] Test task management
- [ ] Test error handling

#### 10.2 Integration Tests

- [ ] Test complete registration flow (trainer)
- [ ] Test complete registration flow (client)
- [ ] Test login flow (single role)
- [ ] Test login flow (multiple roles)
- [ ] Test logout flow
- [ ] Test switch role flow
- [ ] Test view profile
- [ ] Test edit profile
- [ ] Test delete account
- [ ] Test task continuation
- [ ] Test error scenarios

#### 10.3 End-to-End Tests

- [ ] Test new user registration
- [ ] Test existing user login
- [ ] Test profile management
- [ ] Test account deletion
- [ ] Test role switching
- [ ] Test command handling

### 11. Documentation Updates

- [ ] Document message flow
- [ ] Document handler implementations
- [ ] Document error handling
- [ ] Update API documentation
- [ ] Create user guide

### 12. Code Review & Optimization

- [ ] Review all handler code
- [ ] Optimize database queries
- [ ] Add caching where needed
- [ ] Review error handling
- [ ] Check logging coverage
- [ ] Performance testing

---

## 🎯 Success Criteria

### Must Have

- [ ] New users can register as trainer
- [ ] New users can register as client
- [ ] Users can login automatically
- [ ] Users can logout
- [ ] Users can view their profile
- [ ] Users can edit their profile
- [ ] Users can delete their account
- [ ] Users with both roles can switch
- [ ] All commands work correctly
- [ ] Error handling works properly

### Should Have

- [ ] Smooth conversation flow
- [ ] Clear error messages
- [ ] Helpful prompts
- [ ] Task continuation works
- [ ] AI intent detection works

### Nice to Have

- [ ] Profile pictures
- [ ] Email verification
- [ ] Phone verification
- [ ] Password protection

---

## 📊 Progress Tracking

**Backend:** ✅ 100% Complete
**Integration:** ⏳ 0% Complete
**Testing:** ⏳ 0% Complete
**Documentation:** ✅ 100% Complete

**Overall Phase 1:** 🟡 50% Complete

---

## 🚨 Blockers & Dependencies

### Blockers

- Database migration must be run first
- Services must be tested before integration

### Dependencies

- Supabase database access
- WhatsApp API integration
- Claude AI API (for intent detection)

---

## 📝 Notes

- Keep registration fields customizable via JSON
- Ensure all user data is validated
- Log all important actions
- Handle edge cases (network errors, timeouts)
- Test with real phone numbers
- Consider rate limiting

---

## 🔄 Next Phase

After Phase 1 is complete, move to:
**Phase 2: Trainer-Client Relationships**
