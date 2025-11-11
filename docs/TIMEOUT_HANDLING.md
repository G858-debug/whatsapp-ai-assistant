# Add-Client Timeout Handling Implementation

## Overview
This document describes the implementation of timeout handling for abandoned add-client flows, addressing the issue of busy trainers getting distracted during client creation.

## Problem Statement
Trainers often start the add-client flow but get interrupted due to:
- Gym distractions
- Mobile interruptions
- Busy schedules
- Other urgent tasks

This led to incomplete client additions and poor user experience.

## Solution Architecture

### 1. Timeout Monitoring Service
**File:** `services/task_timeout_service.py`

**Features:**
- Monitors all add-client tasks (`add_client_choice`, `add_client_type_details`, `add_client_contact`)
- Tracks last activity timestamp for each task
- Implements two timeout thresholds:
  - **5 minutes:** Gentle reminder with Continue/Start Over options
  - **15 minutes:** Automatic cleanup and abandonment tracking

**Key Methods:**
- `check_and_process_timeouts()`: Main periodic check (called by scheduler)
- `_send_timeout_reminder()`: Sends gentle reminder at 5-minute mark
- `_cleanup_abandoned_task()`: Cleans up and stores analytics at 15-minute mark
- `get_resumable_task()`: Retrieves abandoned tasks for resume capability
- `resume_task()`: Creates new running task from abandoned task data
- `update_task_activity()`: Updates last activity to prevent premature timeouts

### 2. Timeout Button Handler
**File:** `services/message_router/handlers/buttons/timeout_buttons.py`

**Handles:**
- `continue_task`: Resume where they left off
- `start_over`: Clear task and restart command
- `resume_add_client`: Resume from abandoned task
- `start_fresh_add_client`: Start new add-client flow

**Context-Aware Messaging:**
- Builds appropriate continuation messages based on task type and progress
- Shows which field/step user was on
- Displays collected data (e.g., client name)

### 3. Integration Points

#### Scheduler Integration
**File:** `services/scheduler_service.py`

Added `_check_task_timeouts()` to periodic reminder checks:
```python
results = {
    'workout_reminders': ...,
    'payment_reminders': ...,
    'task_timeouts': self._check_task_timeouts()  # NEW
}
```

#### Button Handler Integration
**File:** `services/message_router/handlers/buttons/button_handler.py`

Added timeout button routing:
```python
elif button_id in ['continue_task', 'start_over', 'resume_add_client', 'start_fresh_add_client']:
    if self.timeout_handler:
        return self.timeout_handler.handle_timeout_button(phone, button_id)
```

#### Command Integration
**File:** `services/commands/trainer/relationships/client_management_commands.py`

Enhanced `/add-client` command to check for resumable tasks:
```python
if timeout_service:
    abandoned_task = timeout_service.get_resumable_task(...)
    if abandoned_task:
        return _offer_resume(...)  # Show resume option
```

### 4. Analytics Tracking

**Abandonment Event Structure:**
```json
{
    "event_type": "task_abandoned",
    "user_id": "trainer_phone",
    "user_type": "trainer",
    "metadata": {
        "task_type": "add_client_choice",
        "step": "choose_input_method",
        "field_index": 0,
        "reminder_sent": true,
        "time_spent_minutes": 7.5,
        "collected_fields": ["name", "email"]
    }
}
```

**Stored in:** `analytics_events` table

**Use Cases:**
- Identify which step trainers drop off most
- Optimize flow based on abandonment patterns
- Track effectiveness of reminder messages
- Measure time spent before abandonment

## User Experience Flow

### Scenario 1: 5-Minute Reminder
1. Trainer starts `/add-client`
2. Gets distracted for 5 minutes
3. Receives message:
   ```
   ⏰ Still there?

   You were adding a client...

   Would you like to continue?

   [Continue] [Start Over]
   ```
4. Clicks **Continue** → Returns to exact step
5. Clicks **Start Over** → Fresh start with `/add-client`

### Scenario 2: 15-Minute Cleanup
1. Trainer starts `/add-client`, types client name
2. Gets pulled away for 15 minutes
3. Task automatically cleaned up and saved
4. When trainer returns and types `/add-client` again:
   ```
   🔄 Resume Previous Session?

   You were adding John Doe.

   Would you like to:

   [Resume John Doe] [Start Fresh]
   ```
5. Can resume with all data intact or start fresh

### Scenario 3: Happy Path
1. Trainer completes add-client within 5 minutes
2. No timeout reminders sent
3. Activity timestamp updated on each interaction
4. No interruption to flow

## Database Changes

### Task Status Values
Added new status: `'abandoned'`
- Existing: `'running'`, `'completed'`, `'stopped'`
- New: `'abandoned'` (automatically cleaned up tasks)
- New: `'resumed'` (abandoned tasks that were resumed)

### Task Data Structure
Enhanced `task_data` JSONB field:
```json
{
    "step": "current_step",
    "collected_data": {...},
    "last_activity": "2025-11-11T10:30:00+02:00",
    "reminder_sent": false,
    "reminder_sent_at": null,
    "resumed": false,
    "original_task_id": null
}
```

For abandoned tasks:
```json
{
    "task_data": {original_task_data},
    "abandoned_at": "2025-11-11T10:45:00+02:00",
    "abandonment_reason": "timeout",
    "task_type": "add_client_choice"
}
```

## Configuration

### Timeout Thresholds
Defined in `TaskTimeoutService`:
```python
REMINDER_TIMEOUT_MINUTES = 5   # Gentle reminder
CLEANUP_TIMEOUT_MINUTES = 15   # Cleanup and store
```

### Monitored Task Types
```python
MONITORED_TASK_TYPES = [
    'add_client_choice',
    'add_client_type_details',
    'add_client_contact',
]
```

### Resume Window
Abandoned tasks can be resumed within **24 hours** of abandonment.

## Testing Recommendations

### Manual Testing
1. **5-Minute Reminder:**
   - Start `/add-client`
   - Wait 5+ minutes
   - Verify reminder message with buttons
   - Test both Continue and Start Over

2. **15-Minute Cleanup:**
   - Start `/add-client`, enter some data
   - Wait 15+ minutes
   - Verify task cleaned up
   - Start `/add-client` again
   - Verify resume offer

3. **Resume Flow:**
   - Click "Resume [Name]"
   - Verify data preserved
   - Verify correct step resumed

4. **Analytics:**
   - Check `analytics_events` table
   - Verify abandonment tracking
   - Verify metadata completeness

### Scheduler Testing
Run scheduler manually:
```python
from services.scheduler_service import SchedulerService
scheduler = SchedulerService(db, whatsapp, analytics)
results = scheduler.check_and_send_reminders()
print(results['task_timeouts'])
```

## Deployment Considerations

1. **Scheduler Frequency:**
   - Recommend checking every 1-2 minutes for timely reminders
   - Balance between responsiveness and system load

2. **Analytics Storage:**
   - Ensure `analytics_events` table has adequate capacity
   - Consider retention policy for old events

3. **Message Rate Limits:**
   - WhatsApp has rate limits on button messages
   - Timeout service batches by user, one reminder per task

4. **Backward Compatibility:**
   - Timeout service is optional (graceful degradation)
   - Works with existing task structure
   - No breaking changes to existing flows

## Future Enhancements

1. **Adaptive Timeouts:**
   - Learn from user patterns
   - Adjust timeout thresholds per trainer

2. **Multi-Step Resume:**
   - Resume any interrupted flow (not just add-client)
   - Generalize timeout handling

3. **Smart Reminders:**
   - Consider time of day
   - Avoid sending during typical gym hours

4. **Progress Indicators:**
   - Show completion percentage in reminders
   - "You were 3/5 questions in..."

5. **Abandonment Insights Dashboard:**
   - Visualize drop-off points
   - A/B test different timeout strategies
   - Trainer-specific patterns

## Files Modified

### New Files
- `services/task_timeout_service.py` - Core timeout monitoring
- `services/message_router/handlers/buttons/timeout_buttons.py` - Button handling
- `docs/TIMEOUT_HANDLING.md` - This documentation

### Modified Files
- `services/scheduler_service.py` - Added timeout checking
- `services/message_router/handlers/buttons/button_handler.py` - Added timeout button routing
- `services/commands/trainer/relationships/client_management_commands.py` - Added resume capability

## Summary

This implementation provides a comprehensive solution to the abandoned add-client flow problem by:
- ✅ Gentle reminders after 5 minutes of inactivity
- ✅ Automatic cleanup after 15 minutes
- ✅ Resume capability for interrupted flows
- ✅ Analytics tracking for optimization
- ✅ Context-aware messaging
- ✅ Non-intrusive integration
- ✅ Graceful degradation without timeout service

The solution respects the trainer's workflow while ensuring data isn't lost and providing clear paths to complete or restart their intended action.
