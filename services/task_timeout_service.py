"""
Task Timeout Service
Monitors abandoned add-client flows and handles timeouts
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_info, log_error


class TaskTimeoutService:
    """Handles timeout monitoring and abandonment tracking for tasks"""

    # Timeout thresholds
    REMINDER_TIMEOUT_MINUTES = 5  # Send reminder after 5 minutes
    CLEANUP_TIMEOUT_MINUTES = 15  # Clear task after 15 minutes

    # Task types to monitor
    MONITORED_TASK_TYPES = [
        'add_client_choice',
        'add_client_type_details',
        'add_client_contact',
    ]

    def __init__(self, supabase_client, whatsapp_service, analytics_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.analytics = analytics_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')

    def check_and_process_timeouts(self) -> Dict:
        """Check for timed out tasks and send reminders or cleanup"""
        try:
            now = datetime.now(self.sa_tz)
            results = {
                'reminders_sent': 0,
                'tasks_cleaned': 0,
                'errors': []
            }

            # Check both trainer and client tasks
            for role in ['trainer', 'client']:
                table = f'{role}_tasks'

                # Get running tasks that are being monitored
                running_tasks = self._get_monitored_running_tasks(table)

                for task in running_tasks:
                    try:
                        last_activity = self._get_last_activity_time(task)
                        minutes_inactive = (now - last_activity).total_seconds() / 60

                        # Check if needs cleanup (15 min)
                        if minutes_inactive >= self.CLEANUP_TIMEOUT_MINUTES:
                            if self._cleanup_abandoned_task(task, role):
                                results['tasks_cleaned'] += 1

                        # Check if needs reminder (5 min) and hasn't been reminded yet
                        elif minutes_inactive >= self.REMINDER_TIMEOUT_MINUTES:
                            if not task.get('task_data', {}).get('reminder_sent'):
                                if self._send_timeout_reminder(task, role):
                                    results['reminders_sent'] += 1

                    except Exception as task_error:
                        log_error(f"Error processing task {task.get('id')}: {str(task_error)}")
                        results['errors'].append(str(task_error))

            log_info(f"Timeout check complete: {results['reminders_sent']} reminders, "
                    f"{results['tasks_cleaned']} cleanups")
            return results

        except Exception as e:
            log_error(f"Error checking timeouts: {str(e)}")
            return {'error': str(e)}

    def _get_monitored_running_tasks(self, table: str) -> List[Dict]:
        """Get all running tasks that should be monitored for timeouts"""
        try:
            result = self.db.table(table).select('*').eq(
                'task_status', 'running'
            ).in_('task_type', self.MONITORED_TASK_TYPES).execute()

            return result.data if result.data else []

        except Exception as e:
            log_error(f"Error getting monitored tasks: {str(e)}")
            return []

    def _get_last_activity_time(self, task: Dict) -> datetime:
        """Get the last activity time for a task"""
        # Check if there's a last_activity timestamp in task_data
        task_data = task.get('task_data', {})
        if 'last_activity' in task_data:
            return datetime.fromisoformat(task_data['last_activity'])

        # Otherwise use updated_at or started_at
        if task.get('updated_at'):
            return datetime.fromisoformat(task['updated_at'])

        return datetime.fromisoformat(task['started_at'])

    def _send_timeout_reminder(self, task: Dict, role: str) -> bool:
        """Send a gentle reminder to the user about their incomplete task"""
        try:
            phone_column = 'trainer_phone' if role == 'trainer' else 'client_phone'
            phone = task.get(phone_column)

            if not phone:
                log_error(f"No phone number found for task {task.get('id')}")
                return False

            # Get context from task data
            task_data = task.get('task_data', {})
            task_type = task.get('task_type', 'task')

            # Build context-aware message
            context = self._build_reminder_context(task_type, task_data)

            msg = (
                f"⏰ *Still there?*\n\n"
                f"You were {context}...\n\n"
                f"Would you like to continue?"
            )

            # Send message with buttons
            buttons = [
                {'id': 'continue_task', 'title': 'Continue'},
                {'id': 'start_over', 'title': 'Start Over'}
            ]

            self.whatsapp.send_button_message(phone, msg, buttons)

            # Mark reminder as sent in task data
            task_data['reminder_sent'] = True
            task_data['reminder_sent_at'] = datetime.now(self.sa_tz).isoformat()

            # Update task
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            self.db.table(table).update({
                'task_data': task_data,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', task['id']).execute()

            log_info(f"Sent timeout reminder for task {task['id']} to {phone}")
            return True

        except Exception as e:
            log_error(f"Error sending timeout reminder: {str(e)}")
            return False

    def _cleanup_abandoned_task(self, task: Dict, role: str) -> bool:
        """Clean up an abandoned task and store analytics"""
        try:
            task_id = task.get('id')
            task_type = task.get('task_type')
            task_data = task.get('task_data', {})
            phone_column = 'trainer_phone' if role == 'trainer' else 'client_phone'
            phone = task.get(phone_column)

            # Store abandonment analytics
            self._track_abandonment(task, role)

            # Mark task as abandoned (use custom status)
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            now = datetime.now(self.sa_tz).isoformat()

            # Store the incomplete task data for potential resume
            abandoned_data = {
                'task_data': task_data,
                'abandoned_at': now,
                'abandonment_reason': 'timeout',
                'task_type': task_type
            }

            # Update task status
            self.db.table(table).update({
                'task_status': 'abandoned',
                'task_data': abandoned_data,
                'completed_at': now,
                'updated_at': now
            }).eq('id', task_id).execute()

            log_info(f"Cleaned up abandoned task {task_id} for {phone}")
            return True

        except Exception as e:
            log_error(f"Error cleaning up abandoned task: {str(e)}")
            return False

    def _build_reminder_context(self, task_type: str, task_data: Dict) -> str:
        """Build context-aware reminder message"""
        if task_type == 'add_client_choice':
            return "adding a client"
        elif task_type == 'add_client_type_details':
            client_name = task_data.get('collected_data', {}).get('name', 'a client')
            return f"adding {client_name}"
        elif task_type == 'add_client_contact':
            return "adding a client via contact share"
        else:
            return "completing a task"

    def _track_abandonment(self, task: Dict, role: str) -> None:
        """Track abandonment patterns in analytics"""
        if not self.analytics:
            return

        try:
            task_type = task.get('task_type')
            task_data = task.get('task_data', {})
            phone_column = 'trainer_phone' if role == 'trainer' else 'client_phone'
            user_id = task.get(phone_column, 'unknown')

            # Determine which step they dropped off at
            step = task_data.get('step', 'unknown')
            current_field_index = task_data.get('current_field_index', 0)
            reminder_sent = task_data.get('reminder_sent', False)

            # Calculate time spent
            started_at = datetime.fromisoformat(task['started_at'])
            abandoned_at = datetime.now(self.sa_tz)
            time_spent_minutes = (abandoned_at - started_at).total_seconds() / 60

            metadata = {
                'task_type': task_type,
                'step': step,
                'field_index': current_field_index,
                'reminder_sent': reminder_sent,
                'time_spent_minutes': round(time_spent_minutes, 2),
                'collected_fields': list(task_data.get('collected_data', {}).keys())
            }

            self.analytics.track_event(
                event_type='task_abandoned',
                user_id=user_id,
                user_type=role,
                metadata=metadata
            )

            log_info(f"Tracked abandonment: {task_type} at step '{step}' by {user_id}")

        except Exception as e:
            log_error(f"Error tracking abandonment: {str(e)}")

    def get_resumable_task(self, phone: str, role: str, task_type: str = None) -> Optional[Dict]:
        """Get the most recent abandoned task that can be resumed"""
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            phone_column = 'trainer_phone' if role == 'trainer' else 'client_phone'

            # Query for abandoned tasks
            query = self.db.table(table).select('*').eq(
                phone_column, phone
            ).eq('task_status', 'abandoned')

            # Optionally filter by task type
            if task_type:
                query = query.eq('task_type', task_type)

            # Get most recent
            result = query.order('updated_at', desc=True).limit(1).execute()

            if result.data and len(result.data) > 0:
                abandoned_task = result.data[0]

                # Only allow resuming tasks from last 24 hours
                abandoned_at = datetime.fromisoformat(
                    abandoned_task.get('task_data', {}).get('abandoned_at')
                )
                hours_since_abandon = (datetime.now(self.sa_tz) - abandoned_at).total_seconds() / 3600

                if hours_since_abandon <= 24:
                    return abandoned_task

            return None

        except Exception as e:
            log_error(f"Error getting resumable task: {str(e)}")
            return None

    def resume_task(self, task: Dict, role: str) -> Optional[str]:
        """Resume an abandoned task by creating a new running task with the saved data"""
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            phone_column = 'trainer_phone' if role == 'trainer' else 'client_phone'

            # Get the saved task data
            abandoned_data = task.get('task_data', {})
            original_task_data = abandoned_data.get('task_data', {})
            task_type = abandoned_data.get('task_type')

            # Create new running task with the saved data
            now = datetime.now(self.sa_tz).isoformat()
            new_task = {
                phone_column: task.get(phone_column),
                'task_type': task_type,
                'task_status': 'running',
                'task_data': {
                    **original_task_data,
                    'resumed': True,
                    'resumed_at': now,
                    'original_task_id': task.get('id'),
                    'reminder_sent': False  # Reset reminder flag
                },
                'started_at': now,
                'created_at': now,
                'updated_at': now
            }

            result = self.db.table(table).insert(new_task).execute()

            if result.data and len(result.data) > 0:
                new_task_id = result.data[0]['id']

                # Mark old task as resumed (not abandoned anymore)
                self.db.table(table).update({
                    'task_status': 'resumed',
                    'updated_at': now
                }).eq('id', task['id']).execute()

                log_info(f"Resumed task {task['id']} as new task {new_task_id}")
                return new_task_id

            return None

        except Exception as e:
            log_error(f"Error resuming task: {str(e)}")
            return None

    def update_task_activity(self, task_id: str, role: str) -> bool:
        """Update the last activity timestamp for a task to prevent timeout"""
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'

            # Get current task
            task_result = self.db.table(table).select('*').eq('id', task_id).execute()

            if not task_result.data:
                return False

            task = task_result.data[0]
            task_data = task.get('task_data', {})

            # Update last activity
            task_data['last_activity'] = datetime.now(self.sa_tz).isoformat()

            self.db.table(table).update({
                'task_data': task_data,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', task_id).execute()

            return True

        except Exception as e:
            log_error(f"Error updating task activity: {str(e)}")
            return False
