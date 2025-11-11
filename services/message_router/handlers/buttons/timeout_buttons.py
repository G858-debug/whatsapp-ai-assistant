"""
Timeout Button Handler
Handles Continue/Start Over buttons from timeout reminders
"""
from typing import Dict
from utils.logger import log_info, log_error


class TimeoutButtonHandler:
    """Handles timeout reminder button responses"""

    def __init__(self, supabase_client, whatsapp_service, task_service, timeout_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
        self.timeout_service = timeout_service

    def handle_timeout_button(self, phone: str, button_id: str) -> Dict:
        """Handle timeout reminder buttons"""
        try:
            # Determine role
            role = self._determine_role(phone)

            if not role:
                msg = "❌ Unable to identify your account."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'timeout_button_no_role'}

            # Handle resume buttons differently (they work with abandoned tasks)
            if button_id in ['resume_add_client', 'start_fresh_add_client']:
                return self._handle_resume_buttons(phone, button_id, role)

            # Get the running task
            task = self.task_service.get_running_task(phone, role)

            if not task:
                msg = "No active task found. Please start over with your command."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'timeout_button_no_task'}

            if button_id == 'continue_task':
                return self._handle_continue(phone, task, role)
            elif button_id == 'start_over':
                return self._handle_start_over(phone, task, role)
            else:
                return {'success': False, 'response': 'Unknown timeout button', 'handler': 'timeout_button_unknown'}

        except Exception as e:
            log_error(f"Error handling timeout button: {str(e)}")
            return {'success': False, 'response': 'Error processing timeout button', 'handler': 'timeout_button_error'}

    def _handle_continue(self, phone: str, task: Dict, role: str) -> Dict:
        """Handle 'Continue' button - resume the task where they left off"""
        try:
            task_type = task.get('task_type')
            task_data = task.get('task_data', {})

            # Update activity timestamp to prevent another timeout
            self.timeout_service.update_task_activity(task['id'], role)

            # Build context-aware continuation message
            msg = self._build_continuation_message(task_type, task_data)

            self.whatsapp.send_message(phone, msg)

            log_info(f"User {phone} continued task {task['id']}")

            return {
                'success': True,
                'response': msg,
                'handler': 'timeout_continue'
            }

        except Exception as e:
            log_error(f"Error handling continue: {str(e)}")
            msg = "Error continuing task. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'timeout_continue_error'}

    def _handle_start_over(self, phone: str, task: Dict, role: str) -> Dict:
        """Handle 'Start Over' button - clear current task and restart"""
        try:
            task_type = task.get('task_type')

            # Stop the current task
            self.task_service.stop_task(task['id'], role)

            # Determine what command to restart with
            restart_command = self._get_restart_command(task_type)

            if restart_command:
                msg = (
                    f"✅ *Starting fresh!*\n\n"
                    f"Let's begin again. {restart_command}"
                )
            else:
                msg = (
                    f"✅ *Task cleared!*\n\n"
                    f"Ready when you are. Type /help to see available commands."
                )

            self.whatsapp.send_message(phone, msg)

            # If we have a restart command, initiate it
            if restart_command and restart_command.startswith('/'):
                # Import here to avoid circular dependency
                from services.message_router.message_router import MessageRouter
                router = MessageRouter(self.db, self.whatsapp)
                router.route_message(phone, restart_command)

            log_info(f"User {phone} started over from task {task['id']}")

            return {
                'success': True,
                'response': msg,
                'handler': 'timeout_start_over'
            }

        except Exception as e:
            log_error(f"Error handling start over: {str(e)}")
            msg = "Error starting over. Please try your command again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'timeout_start_over_error'}

    def _build_continuation_message(self, task_type: str, task_data: Dict) -> str:
        """Build context-aware message for continuing a task"""
        step = task_data.get('step', 'unknown')

        if task_type == 'add_client_choice':
            return (
                "👍 *Let's continue!*\n\n"
                "How would you like to add your client?\n\n"
                "Choose below:"
            )
        elif task_type == 'add_client_type_details':
            current_field_index = task_data.get('current_field_index', 0)
            fields = task_data.get('fields', [])

            if current_field_index < len(fields):
                next_field = fields[current_field_index]
                return (
                    f"👍 *Let's continue!*\n\n"
                    f"Question {current_field_index + 1} of {len(fields)}:\n\n"
                    f"{next_field.get('prompt', 'Please provide the next detail.')}"
                )
            else:
                return "👍 Let's finish adding your client!"

        elif task_type == 'add_client_contact':
            return (
                "👍 *Let's continue!*\n\n"
                "Please share the contact to add them as a client."
            )
        else:
            return "👍 Let's continue where you left off!"

    def _get_restart_command(self, task_type: str) -> str:
        """Get the command to restart a task"""
        if task_type in ['add_client_choice', 'add_client_type_details', 'add_client_contact']:
            return '/add-client'
        # Add other task types as needed
        return None

    def _handle_resume_buttons(self, phone: str, button_id: str, role: str) -> Dict:
        """Handle resume/start fresh buttons for abandoned tasks"""
        try:
            if button_id == 'resume_add_client':
                # Get the most recent abandoned add_client task
                abandoned_task = self.timeout_service.get_resumable_task(
                    phone=phone,
                    role=role,
                    task_type='add_client_choice'
                )

                if not abandoned_task:
                    msg = "❌ No resumable task found. Let's start fresh!"
                    self.whatsapp.send_message(phone, msg)
                    # Start fresh
                    from services.message_router.message_router import MessageRouter
                    router = MessageRouter(self.db, self.whatsapp)
                    return router.route_message(phone, '/add-client')

                # Resume the task
                new_task_id = self.timeout_service.resume_task(abandoned_task, role)

                if new_task_id:
                    task_data = abandoned_task.get('task_data', {}).get('task_data', {})
                    collected_data = task_data.get('collected_data', {})
                    client_name = collected_data.get('name', 'your client')

                    msg = (
                        f"✅ *Resuming!*\n\n"
                        f"Let's continue adding {client_name}.\n\n"
                        f"Where were we..."
                    )
                    self.whatsapp.send_message(phone, msg)

                    # Continue with the flow based on where they left off
                    # This would need to be integrated with the actual add_client flow
                    log_info(f"Resumed task {abandoned_task['id']} as {new_task_id}")

                    return {
                        'success': True,
                        'response': msg,
                        'handler': 'resume_add_client_success'
                    }
                else:
                    msg = "❌ Error resuming. Let's start fresh!"
                    self.whatsapp.send_message(phone, msg)
                    from services.message_router.message_router import MessageRouter
                    router = MessageRouter(self.db, self.whatsapp)
                    return router.route_message(phone, '/add-client')

            elif button_id == 'start_fresh_add_client':
                msg = "✅ *Starting fresh!*\n\n"
                self.whatsapp.send_message(phone, msg)

                # Start the add-client flow from scratch
                from services.message_router.message_router import MessageRouter
                router = MessageRouter(self.db, self.whatsapp)
                return router.route_message(phone, '/add-client')

        except Exception as e:
            log_error(f"Error handling resume buttons: {str(e)}")
            msg = "Error processing request. Please try /add-client again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'resume_button_error'}

    def _determine_role(self, phone: str) -> str:
        """Determine if user is trainer or client"""
        try:
            # Check if trainer
            trainer = self.db.table('trainers').select('id').eq('whatsapp', phone).execute()
            if trainer.data:
                return 'trainer'

            # Check if client
            client = self.db.table('clients').select('id').eq('whatsapp', phone).execute()
            if client.data:
                return 'client'

            return None

        except Exception as e:
            log_error(f"Error determining role: {str(e)}")
            return None
