"""
Common Command Handler
Handles commands that are available to both trainers and clients
"""
from typing import Dict, Optional
from utils.logger import log_error


class CommonCommandHandler:
    """Handles commands common to both trainers and clients"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.task_service = task_service
    
    def handle_common_command(self, phone: str, cmd: str, role: str, user_id: str) -> Optional[Dict]:
        """Handle common commands, return None if not a common command"""
        try:
            if cmd == '/view-profile':
                return self._handle_view_profile(phone, role, user_id)
            
            elif cmd == '/edit-profile':
                return self._handle_edit_profile(phone, role, user_id)
            
            elif cmd == '/delete-account':
                return self._handle_delete_account(phone, role, user_id)
            
            else:
                # Not a common command
                return None
                
        except Exception as e:
            log_error(f"Error handling common command: {str(e)}")
            return {
                'success': False,
                'response': f"Error processing common command: {str(e)}",
                'handler': 'common_command_error'
            }
    
    def _handle_view_profile(self, phone: str, role: str, user_id: str) -> Dict:
        """Handle view profile command"""
        try:
            from services.commands import handle_view_profile
            return handle_view_profile(phone, role, user_id, self.db, self.whatsapp, None)
        except Exception as e:
            log_error(f"Error handling view profile: {str(e)}")
            return {'success': False, 'response': 'Error viewing profile', 'handler': 'view_profile_error'}
    
    def _handle_edit_profile(self, phone: str, role: str, user_id: str) -> Dict:
        """Handle edit profile command"""
        try:
            from services.commands import handle_edit_profile
            return handle_edit_profile(phone, role, user_id, self.db, self.whatsapp, 
                                      None, self.task_service)
        except Exception as e:
            log_error(f"Error handling edit profile: {str(e)}")
            return {'success': False, 'response': 'Error starting profile edit', 'handler': 'edit_profile_error'}
    
    def _handle_delete_account(self, phone: str, role: str, user_id: str) -> Dict:
        """Handle delete account command"""
        try:
            from services.commands import handle_delete_account
            return handle_delete_account(phone, role, user_id, self.db, self.whatsapp,
                                        self.auth_service, self.task_service)
        except Exception as e:
            log_error(f"Error handling delete account: {str(e)}")
            return {'success': False, 'response': 'Error starting account deletion', 'handler': 'delete_account_error'}