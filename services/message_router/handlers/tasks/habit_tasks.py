"""
Habit Task Handler
Handles habit-related tasks (Phase 3)
"""
from typing import Dict
from utils.logger import log_error


class HabitTaskHandler:
    """Handles habit-related tasks"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
    
    def handle_habit_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle habit tasks"""
        try:
            task_type = task.get('task_type')
            
            # Trainer habit tasks
            if task_type in ['create_habit', 'edit_habit', 'delete_habit', 'assign_habit', 'unassign_habit',
                            'view_trainee_progress', 'trainee_report']:
                return self._handle_trainer_habit_task(phone, message, user_id, task)
            
            # Client habit tasks
            elif task_type in ['log_habits', 'view_progress', 'weekly_report', 'monthly_report']:
                return self._handle_client_habit_task(phone, message, user_id, task)
            
            else:
                return {'success': False, 'response': 'Unknown habit task', 'handler': 'unknown_habit_task'}
                
        except Exception as e:
            log_error(f"Error handling habit task: {str(e)}")
            return {'success': False, 'response': 'Error continuing habit task', 'handler': 'habit_task_error'}
    
    def _handle_trainer_habit_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle trainer habit tasks"""
        try:
            from services.flows import TrainerHabitFlows
            handler = TrainerHabitFlows(self.db, self.whatsapp, self.task_service)
            
            task_type = task.get('task_type')
            if task_type == 'create_habit':
                return handler.continue_create_habit(phone, message, user_id, task)
            elif task_type == 'edit_habit':
                return handler.continue_edit_habit(phone, message, user_id, task)
            elif task_type == 'delete_habit':
                return handler.continue_delete_habit(phone, message, user_id, task)
            elif task_type == 'assign_habit':
                return handler.continue_assign_habit(phone, message, user_id, task)
            elif task_type == 'unassign_habit':
                return handler.continue_unassign_habit(phone, message, user_id, task)
            elif task_type == 'view_trainee_progress':
                return handler.continue_view_trainee_progress(phone, message, user_id, task)
            elif task_type == 'trainee_report':
                return handler.continue_trainee_report(phone, message, user_id, task)
            else:
                return {'success': False, 'response': 'Unknown trainer habit task', 'handler': 'trainer_habit_task_error'}
                
        except Exception as e:
            log_error(f"Error continuing trainer habit task: {str(e)}")
            return {'success': False, 'response': 'Error continuing trainer habit task', 'handler': 'trainer_habit_task_error'}
    
    def _handle_client_habit_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle client habit tasks"""
        try:
            from services.flows import ClientHabitFlows
            handler = ClientHabitFlows(self.db, self.whatsapp, self.task_service)
            
            task_type = task.get('task_type')
            if task_type == 'log_habits':
                return handler.continue_log_habits(phone, message, user_id, task)
            elif task_type == 'view_progress':
                return handler.continue_view_progress(phone, message, user_id, task)
            elif task_type == 'weekly_report':
                return handler.continue_weekly_report(phone, message, user_id, task)
            elif task_type == 'monthly_report':
                return handler.continue_monthly_report(phone, message, user_id, task)
            else:
                return {'success': False, 'response': 'Unknown client habit task', 'handler': 'client_habit_task_error'}
                
        except Exception as e:
            log_error(f"Error continuing client habit task: {str(e)}")
            return {'success': False, 'response': 'Error continuing client habit task', 'handler': 'client_habit_task_error'}