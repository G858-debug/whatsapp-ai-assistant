"""
Main Message Router - Phase 1 Integration
Routes incoming messages based on authentication status and user role
"""
from typing import Dict, Optional
from utils.logger import log_info, log_error
from services.auth import AuthenticationService, RegistrationService, TaskService

from .handlers.button_handler import ButtonHandler
from .handlers.universal_command_handler import UniversalCommandHandler
from .handlers.new_user_handler import NewUserHandler
from .handlers.login_handler import LoginHandler
from .handlers.logged_in_user_handler import LoggedInUserHandler
from .utils.message_history import MessageHistoryManager


class MessageRouter:
    """Routes messages to appropriate handlers based on user authentication state"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = AuthenticationService(supabase_client)
        self.reg_service = RegistrationService(supabase_client)
        self.task_service = TaskService(supabase_client)
        
        # Initialize handlers
        self.button_handler = ButtonHandler(self.db, self.whatsapp, self.auth_service, self.reg_service, self.task_service)
        self.universal_command_handler = UniversalCommandHandler(
            self.auth_service, self.task_service, self.whatsapp
        )
        self.new_user_handler = NewUserHandler(
            self.db, self.whatsapp, self.auth_service, self.reg_service, self.task_service
        )
        self.login_handler = LoginHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service
        )
        self.logged_in_user_handler = LoggedInUserHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service, self.reg_service
        )
        self.message_history = MessageHistoryManager(self.db)
    
    def route_message(self, phone: str, message: str, button_id: str = None) -> Dict:
        """
        Main routing logic - determines where to send the message
        Returns: {'success': bool, 'response': str, 'handler': str}
        """
        try:
            log_info(f"Routing message from {phone}: {message[:50]}")
            
            # Step 0: Check for button responses (Phase 2 invitations)
            if button_id:
                return self.button_handler.handle_button_response(phone, button_id)

            # Step 0.5: Check for /reset_me command (highest priority - works in any state)
            if message.strip().lower() == '/reset_me':
                try:
                    from services.refiloe import RefiloeService
                    refiloe = RefiloeService(self.db)
                    return refiloe._handle_reset_command(phone)
                except Exception as e:
                    log_error(f"Error handling reset command: {str(e)}")
                    return {
                        'success': False,
                        'response': "❌ Reset failed. Please try again or contact support."
                    }

            # Step 1: Check for universal commands (work regardless of state)
            if message.startswith('/'):
                universal_result = self.universal_command_handler.handle_universal_command(phone, message)
                if universal_result is not None:
                    return universal_result
                # If None, it's not a universal command, continue routing
            
            # Step 2: Check for running registration tasks (before checking user exists)
            # This handles the case where registration is in progress but user not created yet
            trainer_task = self.task_service.get_running_task(phone, 'trainer')
            client_task = self.task_service.get_running_task(phone, 'client')
            
            if trainer_task and trainer_task.get('task_type') == 'registration':
                from services.flows import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.continue_registration(phone, message, 'trainer', trainer_task)
            
            if client_task and client_task.get('task_type') == 'registration':
                from services.flows import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.continue_registration(phone, message, 'client', client_task)
            
            # Step 3: Check if user exists
            user = self.auth_service.check_user_exists(phone)
            
            if not user:
                # New user - start registration flow
                return self.new_user_handler.handle_new_user(phone, message)
            
            # Step 4: Check login status
            login_status = self.auth_service.get_login_status(phone)
            
            if not login_status:
                # User exists but not logged in
                return self.login_handler.handle_login_flow(phone, message)
            
            # Step 5: User is logged in - route to role handler
            return self.logged_in_user_handler.handle_logged_in_user(phone, message, login_status)
            
        except Exception as e:
            log_error(f"Error routing message: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'error'
            }