# Quick Reference Card

## 🚀 Getting Started

### 1. Run Database Migration

```bash
# Open Supabase SQL Editor
# Execute: database_updates/phase1_authentication_schema.sql
```

### 2. Test Services

```python
from services.auth import AuthenticationService, RegistrationService, TaskService
from supabase import create_client

supabase = create_client(URL, KEY)
auth = AuthenticationService(supabase)
```

### 3. Start Integration

- Read: `TODO_PHASE1_AUTHENTICATION.md`
- Follow: Integration section

---

## 📁 File Locations

### Database

- `database_updates/phase1_authentication_schema.sql`

### Services

- `services/auth/authentication_service.py`
- `services/auth/registration_service.py`
- `services/auth/task_service.py`

### Configuration

- `config/trainer_registration_inputs.json`
- `config/client_registration_inputs.json`
- `config/command_handlers.json`

### Documentation

- `PHASE1_README.md` - Start here
- `PHASE1_COMPLETE_SUMMARY.md` - Complete guide
- `PHASE1_FLOW_DIAGRAM.md` - Visual flows
- `PHASE1_TESTING_GUIDE.md` - Testing

### TODO Lists

- `TODO_MASTER_CHECKLIST.md` - Overall progress
- `TODO_PHASE1_AUTHENTICATION.md` - Phase 1 tasks
- `TODO_PHASE2_RELATIONSHIPS.md` - Phase 2 tasks
- `TODO_PHASE3_HABITS.md` - Phase 3 tasks

---

## 🎯 Current Status

**Phase 1:** 🟡 50% (Backend ✅, Integration ⏳)
**Phase 2:** ⏳ 0% (Not Started)
**Phase 3:** ⏳ 0% (Not Started)

---

## 📋 Immediate Next Steps

1. [ ] Run SQL migration in Supabase
2. [ ] Test service imports
3. [ ] Implement message router
4. [ ] Build registration flow
5. [ ] Test end-to-end

---

## 🔧 Key Services

### AuthenticationService

```python
auth.check_user_exists(phone)
auth.get_user_roles(phone)
auth.set_login_status(phone, 'trainer')
auth.generate_unique_id(name, 'trainer')
```

### RegistrationService

```python
reg.get_registration_fields('trainer')
reg.validate_field_value(field, value)
reg.save_trainer_registration(phone, data)
```

### TaskService

```python
task.create_task(user_id, 'trainer', 'registration', {})
task.get_running_task(user_id, 'trainer')
task.complete_task(task_id, 'trainer')
```

---

## 🎮 Commands

### Universal

- `/logout` `/switch-role` `/register` `/stop` `/help`

### Common

- `/view-profile` `/edit-profile` `/delete-account`

### Trainer (Phase 2)

- `/invite-trainee` `/create-trainee` `/view-trainees` `/remove-trainee`

### Trainer (Phase 3)

- `/create-habit` `/edit-habit` `/delete-habit` `/assign-habit` `/view-habits`

### Client (Phase 2)

- `/search-trainer` `/invite-trainer` `/view-trainers` `/remove-trainer`

### Client (Phase 3)

- `/view-my-habits` `/log-habits` `/view-progress` `/weekly-report`

---

## 🗄️ Database Tables

### Phase 1

- `users` - Central auth
- `trainer_client_list` - Relationships
- `client_trainer_list` - Relationships
- `trainer_tasks` - Task tracking
- `client_tasks` - Task tracking

### Phase 3

- `fitness_habits` - Habit definitions
- `habit_assignments` - Habit assignments
- `habit_logs` - Habit logging

---

## 🐛 Troubleshooting

**"Table does not exist"**
→ Run SQL migration

**"Import error"**
→ Check `services/auth/__init__.py` exists

**"Validation error"**
→ Check JSON config files

**"User not found"**
→ Check users table

---

## 📞 Need Help?

1. Check `PHASE1_README.md`
2. Review `PHASE1_COMPLETE_SUMMARY.md`
3. Follow `PHASE1_TESTING_GUIDE.md`
4. Check `TODO_MASTER_CHECKLIST.md`

---

## ✅ Quick Checklist

- [ ] SQL migration run
- [ ] Services tested
- [ ] Message router created
- [ ] Registration flow working
- [ ] Login flow working
- [ ] Commands working
- [ ] Profile management working

---

**Current Focus:** Phase 1 Integration
**Next Milestone:** Phase 1 Complete
**Estimated Time:** 3-4 days
