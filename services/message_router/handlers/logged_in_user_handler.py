"""
Logged In User Handler
Handles messages from authenticated users, including role commands, tasks, and AI intent
"""
from typing import Dict
from utils.logger import log_info, log_error

# Direct imports for cleaner code
from .commands.role_command_handler import RoleCommandHandler
from .task_handler import TaskHandler
from .ai_intent_handler import AIIntentHandler


class LoggedInUserHandler:
    """Handles messages from logged-in users"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service, task_service, reg_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.task_service = task_service
        self.reg_service = reg_service
        
        # Initialize sub-handlers
        # todo: reg_service will be deleted after client onboarding clean
        self.role_command_handler = RoleCommandHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service, self.reg_service
        )
        # todo: reg_service will be deleted after client onboarding clean
        self.task_handler = TaskHandler(
            self.db, self.whatsapp, self.task_service, self.reg_service
        )
        self.ai_intent_handler = AIIntentHandler(
            self.db, self.whatsapp, self.task_service
        )
    
    def _get_user_id(self, phone: str, role: str) -> str:
        """Get user_id by role, returns None if not found"""
        return self.auth_service.get_user_id_by_role(phone, role)
    
    def _user_id_error_response(self, phone: str, role: str) -> Dict:
        """Return error response when user_id not found"""
        log_error(f"User ID not found for {phone} with role {role}")
        return {
            'success': False,
            'response': "Sorry, there was an error with your account. Please try logging in again.",
            'handler': 'user_id_error'
        }
    
    def handle_logged_in_button(self, phone: str, button_id: str, role: str) -> Dict:
        """
        Handle button clicks from logged-in users that need role context.
        Called by ButtonHandler when button requires role-specific handling.
        """
        try:
            # If button_id is a command, route through command handler
            if button_id.startswith('/'):
                user_id = self._get_user_id(phone, role)
                if not user_id:
                    return self._user_id_error_response(phone, role)
                return self.role_command_handler.handle_role_command(phone, button_id, role, user_id)
            
            # For other buttons, treat as message
            return self.handle_logged_in_user(phone, button_id, role)
            
        except Exception as e:
            log_error(f"Error handling logged-in button: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'logged_in_button_error'
            }    
    
    def handle_logged_in_user(self, phone: str, message: str, role: str) -> Dict:
        """Handle messages from logged-in users"""
        try:
            # Step 1: Check for role-specific commands (starts with /)
            if message.startswith('/'):
                user_id = self._get_user_id(phone, role)
                if not user_id:
                    return self._user_id_error_response(phone, role)
                return self.role_command_handler.handle_role_command(phone, message, role, user_id)

            # Step 2: Check for running task
            running_task = self.task_service.get_running_task(phone, role)
            if running_task and running_task.get('task_status') == 'running':
                user_id = self._get_user_id(phone, role)
                if not user_id:
                    return self._user_id_error_response(phone, role)
                return self.task_handler.continue_task(phone, message, role, user_id, running_task)

            # Step 3: No running task - use AI to determine intent
            user_id = self._get_user_id(phone, role)
            if not user_id:
                return self._user_id_error_response(phone, role)
            return self.ai_intent_handler.handle_ai_intent(phone, message, role, user_id)
            
        except Exception as e:
            log_error(f"Error handling logged-in user: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'logged_in_error'
            }
    
