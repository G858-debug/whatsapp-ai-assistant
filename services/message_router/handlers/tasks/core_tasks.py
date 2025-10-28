"""
Core Task Handler
Handles core system tasks like registration, profile editing, and account deletion
"""
from typing import Dict
from utils.logger import log_error


class CoreTaskHandler:
    """Handles core system tasks"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
    
    def handle_core_task(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Handle core system tasks"""
        try:
            task_type = task.get('task_type')
            
            if task_type == 'registration':
                return self._continue_registration_task(phone, message, role, task)
            
            elif task_type == 'edit_profile':
                return self._continue_profile_task(phone, message, role, user_id, task, 'edit')
            
            elif task_type == 'delete_account':
                return self._continue_profile_task(phone, message, role, user_id, task, 'delete')
            
            else:
                return {'success': False, 'response': 'Unknown core task', 'handler': 'unknown_core_task'}
                
        except Exception as e:
            log_error(f"Error handling core task: {str(e)}")
            return {'success': False, 'response': 'Error continuing core task', 'handler': 'core_task_error'}
    
    def _continue_registration_task(self, phone: str, message: str, role: str, task: Dict) -> Dict:
        """Continue registration task"""
        try:
            from services.flows import RegistrationFlowHandler
            handler = RegistrationFlowHandler(
                self.db, self.whatsapp, None, None, self.task_service
            )
            return handler.continue_registration(phone, message, role, task)
        except Exception as e:
            log_error(f"Error continuing registration task: {str(e)}")
            return {'success': False, 'response': 'Error continuing registration', 'handler': 'registration_task_error'}
    
    def _continue_profile_task(self, phone: str, message: str, role: str, user_id: str, task: Dict, task_action: str) -> Dict:
        """Continue profile-related tasks"""
        try:
            from services.flows import ProfileFlowHandler
            handler = ProfileFlowHandler(
                self.db, self.whatsapp, None, self.task_service
            )
            
            if task_action == 'edit':
                return handler.continue_edit_profile(phone, message, role, user_id, task)
            elif task_action == 'delete':
                return handler.continue_delete_account(phone, message, role, user_id, task)
            else:
                return {'success': False, 'response': 'Unknown profile task', 'handler': 'profile_task_error'}
                
        except Exception as e:
            log_error(f"Error continuing profile task: {str(e)}")
            return {'success': False, 'response': 'Error continuing profile task', 'handler': 'profile_task_error'}