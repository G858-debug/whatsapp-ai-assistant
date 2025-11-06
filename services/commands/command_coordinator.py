"""
Command Coordinator
Main entry point for all command handling with delegation to specialized handlers
"""
from typing import Dict
from utils.logger import log_info, log_error

# Import specialized handlers
from .trainer import TrainerCommandHandler
from .client import ClientCommandHandler

# Import common commands
from .common.profile_commands import handle_view_profile, handle_edit_profile, handle_delete_account
from .common.help_command import handle_help
from .common.logout_command import handle_logout
from .common.register_command import handle_register
from .common.stop_command import handle_stop
from .common.switch_role_command import handle_switch_role


class CommandCoordinator:
    """
    Main coordinator for all command handling.
    Delegates to specialized handlers based on user role and command type.
    """
    
    def __init__(self, db, whatsapp, auth_service, task_service, reg_service=None):
        self.db = db
        self.whatsapp = whatsapp
        self.auth_service = auth_service
        self.task_service = task_service
        self.reg_service = reg_service
        
        # Initialize specialized handlers
        self.trainer_handler = TrainerCommandHandler(db, whatsapp, task_service, reg_service)
        self.client_handler = ClientCommandHandler(db, whatsapp, task_service)
    
    def handle_command(self, phone: str, command: str, **kwargs) -> Dict:
        """
        Main command routing method.
        Routes commands to appropriate handlers based on command type and user role.
        """
        try:
            # Get user's current login status
            login_status = self.auth_service.get_login_status(phone)
            user_id = None
            
            if login_status:
                user_id = self.auth_service.get_user_id_by_role(phone, login_status)
            
            # Route common commands (available to all users)
            if command in ['/help']:
                return handle_help(phone, self.auth_service, self.whatsapp)
            
            elif command in ['/register']:
                return handle_register(phone, self.auth_service, self.whatsapp)
            
            elif command in ['/logout']:
                return handle_logout(phone, self.auth_service, self.task_service, self.whatsapp)
            
            elif command in ['/stop']:
                return handle_stop(phone, self.auth_service, self.task_service, self.whatsapp)
            
            elif command in ['/switch-role']:
                return handle_switch_role(phone, self.auth_service, self.task_service, self.whatsapp)
            
            # Commands that require login
            if not login_status or not user_id:
                msg = "Please login first by sending me a message."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'not_logged_in'}
            
            # Route profile management commands (available to logged-in users)
            if command in ['/view-profile']:
                return handle_view_profile(phone, login_status, user_id, self.db, self.whatsapp, self.reg_service)
            
            elif command in ['/edit-profile']:
                return handle_edit_profile(phone, login_status, user_id, self.db, self.whatsapp, self.reg_service, self.task_service)
            
            elif command in ['/delete-account']:
                return handle_delete_account(phone, login_status, user_id, self.db, self.whatsapp, self.auth_service, self.task_service)
            
            # Route role-specific commands
            elif login_status == 'trainer':
                return self._handle_trainer_command(phone, user_id, command)
            
            elif login_status == 'client':
                return self._handle_client_command(phone, user_id, command)
            
            else:
                msg = f"Unknown command: {command}"
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'unknown_command'}
                
        except Exception as e:
            log_error(f"Error in command coordinator: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error processing your command.",
                'handler': 'coordinator_error'
            }
    
    def _handle_trainer_command(self, phone: str, trainer_id: str, command: str) -> Dict:
        """Route trainer-specific commands"""
        
        # Habit management commands
        if command == '/create-habit':
            return self.trainer_handler.handle_create_habit(phone, trainer_id)
        elif command == '/edit-habit':
            return self.trainer_handler.handle_edit_habit(phone, trainer_id)
        elif command == '/delete-habit':
            return self.trainer_handler.handle_delete_habit(phone, trainer_id)
        elif command == '/assign-habit':
            return self.trainer_handler.handle_assign_habit(phone, trainer_id)
        elif command == '/view-habits':
            return self.trainer_handler.handle_view_habits(phone, trainer_id)
        
        # Client progress commands
        elif command == '/view-trainee-progress':
            return self.trainer_handler.handle_client_progress(phone, trainer_id)
            # return self.trainer_handler.handle_view_trainee_progress(phone, trainer_id)
        elif command == '/trainee-weekly-report':
            return self.trainer_handler.handle_trainee_weekly_report(phone, trainer_id)
        elif command == '/trainee-monthly-report':
            return self.trainer_handler.handle_trainee_monthly_report(phone, trainer_id)
        
        # Relationship management commands
        elif command == '/invite-trainee':
            return self.trainer_handler.handle_invite_trainee(phone, trainer_id)
        elif command == '/create-trainee':
            return self.trainer_handler.handle_create_trainee(phone, trainer_id)
        elif command == '/view-trainees':
            return self.trainer_handler.handle_view_trainees(phone, trainer_id)
        elif command == '/remove-trainee':
            return self.trainer_handler.handle_remove_trainee(phone, trainer_id)
        
        # Dashboard commands
        elif command == '/trainer-dashboard':
            try:
                return self.trainer_handler.handle_trainer_dashboard(phone, trainer_id)
            except Exception as e:
                log_error(f"Error in trainer-dashboard command: {str(e)}")
                msg = f"❌ Error processing trainer dashboard command: {str(e)}"
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'trainer_dashboard_error'}
        elif command == '/client-progress':
            return self.trainer_handler.handle_client_progress(phone, trainer_id)
        
        else:
            msg = f"Unknown trainer command: {command}\n\nType /help to see available commands."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'unknown_trainer_command'}
    
    def _handle_client_command(self, phone: str, client_id: str, command: str) -> Dict:
        """Route client-specific commands"""
        
        # Habit tracking commands
        if command == '/view-my-habits':
            return self.client_handler.handle_view_my_habits(phone, client_id)
        elif command.startswith('/log-habits'):
            # Extract habit ID if provided
            parts = command.split()
            habit_id = parts[1] if len(parts) > 1 else None
            return self.client_handler.handle_log_habits(phone, client_id, habit_id)
        elif command == '/view-progress':
            return self.client_handler.handle_view_progress(phone, client_id)
        elif command == '/weekly-report':
            return self.client_handler.handle_weekly_report(phone, client_id)
        elif command == '/monthly-report':
            return self.client_handler.handle_monthly_report(phone, client_id)
        elif command == '/reminder-settings':
            return self.client_handler.handle_reminder_settings(phone, client_id)
        elif command == '/test-reminder':
            return self.client_handler.handle_test_reminder(phone, client_id)
        
        # Relationship management commands
        elif command == '/search-trainer':
            return self.client_handler.handle_search_trainer(phone, client_id)
        elif command == '/view-trainers':
            return self.client_handler.handle_view_trainers(phone, client_id)
        elif command == '/invite-trainer':
            return self.client_handler.handle_invite_trainer(phone, client_id)
        elif command == '/remove-trainer':
            return self.client_handler.handle_remove_trainer(phone, client_id)
        
        else:
            msg = f"Unknown client command: {command}\n\nType /help to see available commands."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'unknown_client_command'}