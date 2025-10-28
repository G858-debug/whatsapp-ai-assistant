"""
Role Command Handler
Delegates role-specific commands to specialized handlers
"""
from typing import Dict
from utils.logger import log_error

from .commands.role_command_handler import RoleCommandHandler as RoleCommandHandlerImpl


class RoleCommandHandler:
    """Main role command handler that delegates to the implementation"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service, task_service):
        self.handler = RoleCommandHandlerImpl(supabase_client, whatsapp_service, auth_service, task_service)
    
    def handle_role_command(self, phone: str, command: str, role: str, user_id: str) -> Dict:
        """Delegate role command handling to the implementation"""
        return self.handler.handle_role_command(phone, command, role, user_id)
