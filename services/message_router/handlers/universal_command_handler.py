"""
Universal Command Handler
Handles commands that work in any authentication state
"""
from typing import Dict, Optional
from utils.logger import log_error


class UniversalCommandHandler:
    """Handles universal commands that work in any state"""
    
    def __init__(self, auth_service, task_service, whatsapp_service):
        self.auth_service = auth_service
        self.task_service = task_service
        self.whatsapp = whatsapp_service
    
    def handle_universal_command(self, phone: str, command: str) -> Optional[Dict]:
        """Handle universal commands that work in any state"""
        try:
            cmd = command.lower().strip()
            
            if cmd == '/help':
                from services.commands import handle_help
                return handle_help(phone, self.auth_service, self.whatsapp)
            
            elif cmd == '/logout':
                from services.commands import handle_logout
                return handle_logout(phone, self.auth_service, self.task_service, self.whatsapp)
            
            elif cmd == '/switch-role':
                from services.commands import handle_switch_role
                return handle_switch_role(phone, self.auth_service, self.task_service, self.whatsapp)
            
            elif cmd == '/register':
                from services.commands import handle_register
                return handle_register(phone, self.auth_service, self.whatsapp)
            
            elif cmd == '/stop':
                from services.commands import handle_stop
                return handle_stop(phone, self.auth_service, self.task_service, self.whatsapp)
            
            else:
                # Not a universal command, return None to continue routing
                return None
                
        except Exception as e:
            log_error(f"Error handling universal command: {str(e)}")
            return {
                'success': False,
                'response': f"Error processing command: {str(e)}",
                'handler': 'universal_command_error'
            }