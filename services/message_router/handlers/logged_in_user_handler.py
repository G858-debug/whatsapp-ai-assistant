"""
Logged In User Handler
Handles messages from authenticated users, including role commands, tasks, and AI intent
"""
from typing import Dict
from utils.logger import log_info, log_error

from .role_command_handler import RoleCommandHandler
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
        self.role_command_handler = RoleCommandHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service, self.reg_service
        )
        self.task_handler = TaskHandler(
            self.db, self.whatsapp, self.task_service, self.reg_service
        )
        self.ai_intent_handler = AIIntentHandler(
            self.db, self.whatsapp, self.task_service
        )
    
    def handle_logged_in_user(self, phone: str, message: str, role: str) -> Dict:
        """Handle messages from logged-in users"""
        try:
            # Get user ID for this role
            user_id = self.auth_service.get_user_id_by_role(phone, role)
            
            if not user_id:
                log_error(f"User ID not found for {phone} with role {role}")
                return {
                    'success': False,
                    'response': "Sorry, there was an error with your account. Please try logging in again.",
                    'handler': 'user_id_error'
                }
            
            # Check for role-specific commands
            if message.startswith('/'):
                return self.role_command_handler.handle_role_command(phone, message, role, user_id)
            
            # Check for running task
            running_task = self.task_service.get_running_task(user_id, role)
            
            if running_task and running_task.get('task_status') == 'running':
                # Continue with the running task
                return self.task_handler.continue_task(phone, message, role, user_id, running_task)
            
            # No running task - use AI to determine intent
            return self.ai_intent_handler.handle_ai_intent(phone, message, role, user_id)
            
        except Exception as e:
            log_error(f"Error handling logged-in user: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'logged_in_error'
            }