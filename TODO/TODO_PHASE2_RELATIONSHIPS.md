# Phase 2: Trainer-Client Relationships - TODO

## 🎯 Phase Overview

Implement trainer-client connections, invitations, search, and relationship management.

---

## 📋 TASKS

### 1. Database Schema (if needed)

- [ ] Review existing relationship tables
- [ ] Add any missing columns
- [ ] Create invitation_tokens table if needed
- [ ] Add indexes for search optimization
- [ ] Test relationship queries

### 2. Trainer Features

#### 2.1 Invite Existing Client (/invite-trainee)

- [ ] Create invite_trainee handler
- [ ] Create invite_trainee task
- [ ] Ask for client ID
- [ ] Validate client ID exists
- [ ] Check if already connected
- [ ] Generate invitation token
- [ ] Send invitation to client's WhatsApp
- [ ] Include trainer info in invitation
- [ ] Create handler buttons (Accept/Reject)
- [ ] Store invitation in database
- [ ] Handle acceptance:
  - [ ] Add to trainer_client_list
  - [ ] Add to client_trainer_list
  - [ ] Set connection_status to 'active'
  - [ ] Notify both parties
- [ ] Handle rejection:
  - [ ] Update invitation status
  - [ ] Notify trainer
- [ ] Handle errors (client not found)
- [ ] Complete task

#### 2.2 Create & Invite New Client (/create-trainee)

- [ ] Create create_trainee handler
- [ ] Create create_trainee task
- [ ] Get client registration fields
- [ ] Ask trainer for each field
- [ ] Include phone number field
- [ ] Validate all inputs
- [ ] Check if phone already exists
- [ ] If exists:
  - [ ] Show existing client info
  - [ ] Ask "Invite existing client?"
  - [ ] If yes, use invite flow
  - [ ] If no, end task
- [ ] If doesn't exist:
  - [ ] Send invitation to phone number
  - [ ] Show all prefilled info
  - [ ] Create handler buttons (Approve/Reject)
  - [ ] If approved:
    - [ ] Generate client_id
    - [ ] Create client account
    - [ ] Create user entry
    - [ ] Set login status
    - [ ] Add to relationship tables
    - [ ] Notify both parties
  - [ ] If rejected:
    - [ ] Notify trainer
    - [ ] Don't save data
- [ ] Complete task
- [ ] Handle errors

#### 2.3 View Clients (/view-trainees)

- [ ] Create view_trainees handler
- [ ] Get trainer_id from user
- [ ] Query trainer_client_list
- [ ] Get client details for each
- [ ] Count total clients
- [ ] If ≤ 5 clients:
  - [ ] Format as message
  - [ ] Show: name, contact, registration date, client_id
  - [ ] Send in chat
- [ ] If > 5 clients:
  - [ ] Generate CSV file
  - [ ] Include all client info
  - [ ] Send as downloadable file
- [ ] Handle no clients case
- [ ] Handle errors

#### 2.4 Remove Client (/remove-trainee)

- [ ] Create remove_trainee handler
- [ ] Create remove_trainee task
- [ ] Ask for client ID
- [ ] Validate client in trainer's list
- [ ] Show client info
- [ ] Ask confirmation
- [ ] If confirmed:
  - [ ] Remove from trainer_client_list
  - [ ] Remove from client_trainer_list
  - [ ] Remove habit assignments (Phase 3)
  - [ ] Notify both parties
  - [ ] Send removal message to client
- [ ] If cancelled, end task
- [ ] Handle errors (client not in list)
- [ ] Complete task

### 3. Client Features

#### 3.1 Search Trainers (/search-trainer)

- [ ] Create search_trainer handler
- [ ] Create search_trainer task
- [ ] Ask for trainer name
- [ ] Search trainers table by name
- [ ] Use ILIKE for partial matching
- [ ] Limit to 5 results
- [ ] Format results:
  - [ ] Name
  - [ ] Specialization
  - [ ] Experience
  - [ ] Trainer ID
- [ ] Send results message
- [ ] Inform to copy trainer_id
- [ ] Handle no results
- [ ] Handle errors
- [ ] Complete task

#### 3.2 Invite Trainer (/invite-trainer)

- [ ] Create invite_trainer handler
- [ ] Create invite_trainer task
- [ ] Ask for trainer ID
- [ ] Validate trainer ID exists
- [ ] Check if already connected
- [ ] Generate invitation token
- [ ] Send invitation to trainer's WhatsApp
- [ ] Include client info in invitation
- [ ] Create handler buttons (Accept/Reject)
- [ ] Store invitation in database
- [ ] Handle acceptance:
  - [ ] Add to trainer_client_list
  - [ ] Add to client_trainer_list
  - [ ] Set connection_status to 'active'
  - [ ] Notify both parties
- [ ] Handle rejection:
  - [ ] Update invitation status
  - [ ] Notify client
- [ ] Handle errors (trainer not found)
- [ ] Complete task

#### 3.3 View Trainers (/view-trainers)

- [ ] Create view_trainers handler
- [ ] Get client_id from user
- [ ] Query client_trainer_list
- [ ] Get trainer details for each
- [ ] Count total trainers
- [ ] If ≤ 5 trainers:
  - [ ] Format as message
  - [ ] Show: name, specialization, contact, trainer_id
  - [ ] Send in chat
- [ ] If > 5 trainers:
  - [ ] Generate CSV file
  - [ ] Include all trainer info
  - [ ] Send as downloadable file
- [ ] Handle no trainers case
- [ ] Handle errors

#### 3.4 Remove Trainer (/remove-trainer)

- [ ] Create remove_trainer handler
- [ ] Create remove_trainer task
- [ ] Ask for trainer ID
- [ ] Validate trainer in client's list
- [ ] Show trainer info
- [ ] Ask confirmation
- [ ] If confirmed:
  - [ ] Remove from client_trainer_list
  - [ ] Remove from trainer_client_list
  - [ ] Remove habit assignments (Phase 3)
  - [ ] Notify both parties
- [ ] If cancelled, end task
- [ ] Handle errors (trainer not in list)
- [ ] Complete task

### 4. Invitation System

#### 4.1 Invitation Service

- [ ] Create InvitationService class
- [ ] Method: create_invitation()
- [ ] Method: get_invitation()
- [ ] Method: accept_invitation()
- [ ] Method: reject_invitation()
- [ ] Method: expire_old_invitations()
- [ ] Generate unique tokens
- [ ] Set expiration time (24-48 hours)
- [ ] Track invitation status

#### 4.2 Invitation Handlers

- [ ] Handle invitation acceptance
- [ ] Handle invitation rejection
- [ ] Handle expired invitations
- [ ] Send notifications
- [ ] Update relationship tables

### 5. Search Functionality

#### 5.1 Trainer Search

- [ ] Implement name search
- [ ] Implement specialization filter
- [ ] Implement location filter
- [ ] Implement experience filter
- [ ] Optimize search queries
- [ ] Add pagination if needed
- [ ] Cache search results

#### 5.2 Client Search (for trainers)

- [ ] Implement name search
- [ ] Implement goal filter
- [ ] Implement experience level filter
- [ ] Optimize search queries

### 6. Relationship Management

#### 6.1 Connection Status

- [ ] Track: pending, active, declined, removed
- [ ] Update status on actions
- [ ] Query by status
- [ ] Handle status transitions

#### 6.2 Relationship Validation

- [ ] Prevent duplicate connections
- [ ] Validate before operations
- [ ] Check permissions
- [ ] Handle edge cases

### 7. Notifications

#### 7.1 Invitation Notifications

- [ ] Format invitation messages
- [ ] Include sender info
- [ ] Add action buttons
- [ ] Send via WhatsApp

#### 7.2 Connection Notifications

- [ ] Notify on acceptance
- [ ] Notify on rejection
- [ ] Notify on removal
- [ ] Format nicely with emojis

### 8. CSV Generation

#### 8.1 Client List CSV

- [ ] Create CSV generator
- [ ] Include all relevant fields
- [ ] Format dates properly
- [ ] Add headers
- [ ] Generate file
- [ ] Send via WhatsApp

#### 8.2 Trainer List CSV

- [ ] Create CSV generator
- [ ] Include all relevant fields
- [ ] Format data properly
- [ ] Add headers
- [ ] Generate file
- [ ] Send via WhatsApp

### 9. Trainer-Created Client Capabilities

- [ ] Ensure full client access
- [ ] Allow profile editing
- [ ] Allow account deletion
- [ ] Allow adding more trainers
- [ ] Test all client features

### 10. Testing

#### 10.1 Unit Tests

- [ ] Test invitation creation
- [ ] Test invitation acceptance
- [ ] Test invitation rejection
- [ ] Test search functionality
- [ ] Test relationship creation
- [ ] Test relationship removal

#### 10.2 Integration Tests

- [ ] Test trainer invites existing client
- [ ] Test trainer creates new client
- [ ] Test client searches trainers
- [ ] Test client invites trainer
- [ ] Test view clients/trainers
- [ ] Test remove relationships
- [ ] Test CSV generation

#### 10.3 End-to-End Tests

- [ ] Complete trainer-client connection flow
- [ ] Complete client-trainer connection flow
- [ ] Test multiple trainers per client
- [ ] Test multiple clients per trainer
- [ ] Test removal flows
- [ ] Test edge cases

### 11. Error Handling

- [ ] Handle invalid IDs
- [ ] Handle duplicate connections
- [ ] Handle expired invitations
- [ ] Handle network errors
- [ ] Handle database errors
- [ ] User-friendly error messages

### 12. Documentation

- [ ] Document invitation flow
- [ ] Document search functionality
- [ ] Document relationship management
- [ ] Update API documentation
- [ ] Create user guide

---

## 🎯 Success Criteria

### Must Have

- [ ] Trainers can invite existing clients
- [ ] Trainers can create and invite new clients
- [ ] Clients can search for trainers
- [ ] Clients can invite trainers
- [ ] Both can view their connections
- [ ] Both can remove connections
- [ ] Invitations work properly
- [ ] Notifications sent correctly

### Should Have

- [ ] CSV export for large lists
- [ ] Search filters work
- [ ] Invitation expiration
- [ ] Clear error messages

### Nice to Have

- [ ] Advanced search filters
- [ ] Trainer ratings
- [ ] Client reviews
- [ ] Connection analytics

---

## 📊 Progress Tracking

**Database:** ⏳ 0% Complete
**Trainer Features:** ⏳ 0% Complete
**Client Features:** ⏳ 0% Complete
**Invitation System:** ⏳ 0% Complete
**Testing:** ⏳ 0% Complete

**Overall Phase 2:** ⏳ 0% Complete

---

## 🚨 Blockers & Dependencies

### Blockers

- Phase 1 must be complete
- Relationship tables must exist

### Dependencies

- WhatsApp message sending
- CSV file generation library
- Search optimization

---

## 🔄 Next Phase

After Phase 2 is complete, move to:
**Phase 3: Fitness Habit Management**
