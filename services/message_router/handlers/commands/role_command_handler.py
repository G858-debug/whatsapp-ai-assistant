"""
Main Role Command Handler
Coordinates role-specific commands and delegates to specialized handlers
"""
from typing import Dict
from utils.logger import log_error

from .common_commands import CommonCommandHandler
from .trainer_commands import TrainerCommandHandler
from .client_commands import ClientCommandHandler


class RoleCommandHandler:
    """Main role command handler that delegates to specific command handlers"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service, task_service, reg_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.task_service = task_service
        self.reg_service = reg_service
        
        # Initialize sub-handlers
        # todo: reg_service will be deleted after client onboarding clean
        self.common_handler = CommonCommandHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service, self.reg_service
        )
        self.trainer_handler = TrainerCommandHandler(
            self.db, self.whatsapp, self.task_service
        )
        self.client_handler = ClientCommandHandler(
            self.db, self.whatsapp, self.task_service
        )
    
    def handle_role_command(self, phone: str, command: str, role: str, user_id: str) -> Dict:
        """Handle role-specific commands by delegating to appropriate handler"""
        try:
            cmd = command.lower().strip()
            
            # Check for common commands first (both roles)
            common_result = self.common_handler.handle_common_command(phone, cmd, role, user_id)
            if common_result is not None:
                return common_result
            
            # Delegate to role-specific handlers
            if role == 'trainer':
                return self.trainer_handler.handle_trainer_command(phone, cmd, user_id)
            elif role == 'client':
                return self.client_handler.handle_client_command(phone, cmd, user_id)
            else:
                return {
                    'success': True,
                    'response': f"❓ Unknown role: {role}",
                    'handler': 'unknown_role'
                }
            
        except Exception as e:
            log_error(f"Error handling role command: {str(e)}")
            return {
                'success': False,
                'response': f"Error processing command: {str(e)}",
                'handler': 'role_command_error'
            }