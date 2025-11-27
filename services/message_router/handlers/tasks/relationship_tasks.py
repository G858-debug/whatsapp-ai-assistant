"""
Relationship Task Handler
Handles trainer-client relationship tasks (Phase 2)
"""
from typing import Dict
from utils.logger import log_error


class RelationshipTaskHandler:
    """Handles relationship-related tasks"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service, reg_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
        self.reg_service = reg_service
    
    def handle_relationship_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle relationship tasks"""
        try:
            task_type = task.get('task_type')
            
            # Trainer relationship tasks
            if task_type in ['invite_trainee', 'create_trainee', 'remove_trainee']:
                return self._handle_trainer_relationship_task(phone, message, user_id, task)
            
            # Client relationship tasks
            elif task_type in ['search_trainer', 'invite_trainer', 'remove_trainer']:
                return self._handle_client_relationship_task(phone, message, user_id, task)
            
            else:
                return {'success': False, 'response': 'Unknown relationship task', 'handler': 'unknown_relationship_task'}
                
        except Exception as e:
            log_error(f"Error handling relationship task: {str(e)}")
            return {'success': False, 'response': 'Error continuing relationship task', 'handler': 'relationship_task_error'}
    
    def _handle_trainer_relationship_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle trainer relationship tasks"""
        try:
            from services.flows import TrainerRelationshipFlows
            handler = TrainerRelationshipFlows(self.db, self.whatsapp, self.task_service, self.reg_service)
            
            task_type = task.get('task_type')
            if task_type == 'invite_trainee':
                return handler.continue_invite_trainee(phone, message, user_id, task)
            elif task_type == 'create_trainee':
                return handler.continue_create_trainee(phone, message, user_id, task)
            elif task_type == 'remove_trainee':
                return handler.continue_remove_trainee(phone, message, user_id, task)
            else:
                return {'success': False, 'response': 'Unknown trainer relationship task', 'handler': 'trainer_relationship_task_error'}
                
        except Exception as e:
            log_error(f"Error continuing trainer relationship task: {str(e)}")
            return {'success': False, 'response': 'Error continuing trainer task', 'handler': 'trainer_relationship_task_error'}
    
    def _handle_client_relationship_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle client relationship tasks"""
        try:
            from services.flows import ClientRelationshipFlows
            handler = ClientRelationshipFlows(self.db, self.whatsapp, self.task_service)
            
            task_type = task.get('task_type')
            if task_type == 'search_trainer':
                return handler.continue_search_trainer(phone, message, user_id, task)
            elif task_type == 'invite_trainer':
                return handler.continue_invite_trainer(phone, message, user_id, task)
            elif task_type == 'remove_trainer':
                return handler.continue_remove_trainer(phone, message, user_id, task)
            else:
                return {'success': False, 'response': 'Unknown client relationship task', 'handler': 'client_relationship_task_error'}
                
        except Exception as e:
            log_error(f"Error continuing client relationship task: {str(e)}")
            return {'success': False, 'response': 'Error continuing client task', 'handler': 'client_relationship_task_error'}