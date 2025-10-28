"""
Main Task Handler
Coordinates task continuation and delegates to specialized handlers
"""
from typing import Dict
from utils.logger import log_info, log_error

from .core_tasks import CoreTaskHandler
from .relationship_tasks import RelationshipTaskHandler
from .habit_tasks import HabitTaskHandler


class TaskHandler:
    """Main task handler that delegates to specific task handlers"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service, reg_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
        self.reg_service = reg_service
        
        # Initialize sub-handlers
        self.core_handler = CoreTaskHandler(
            self.db, self.whatsapp, self.task_service, self.reg_service
        )
        self.relationship_handler = RelationshipTaskHandler(
            self.db, self.whatsapp, self.task_service
        )
        self.habit_handler = HabitTaskHandler(
            self.db, self.whatsapp, self.task_service
        )
    
    def continue_task(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Continue with a running task by delegating to appropriate handler"""
        try:
            task_type = task.get('task_type')
            task_id = task.get('id')
            
            log_info(f"Continuing task {task_type} for {phone}")
            
            # Delegate to appropriate handler based on task category
            if task_type in ['registration', 'edit_profile', 'delete_account']:
                return self.core_handler.handle_core_task(phone, message, role, user_id, task)
            
            elif task_type in ['invite_trainee', 'create_trainee', 'remove_trainee', 
                              'search_trainer', 'invite_trainer', 'remove_trainer']:
                return self.relationship_handler.handle_relationship_task(phone, message, user_id, task)
            
            elif task_type in ['create_habit', 'edit_habit', 'delete_habit', 'assign_habit',
                              'view_trainee_progress', 'trainee_report', 'log_habits', 
                              'view_progress', 'weekly_report', 'monthly_report']:
                return self.habit_handler.handle_habit_task(phone, message, user_id, task)
            
            else:
                log_error(f"Unknown task type: {task_type}")
                # Stop the unknown task
                self.task_service.stop_task(task_id, role)
                return {
                    'success': True,
                    'response': "Sorry, I lost track of what we were doing. Let's start fresh. What can I help you with?",
                    'handler': 'unknown_task'
                }
                
        except Exception as e:
            log_error(f"Error continuing task: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Type /stop to cancel the current task.",
                'handler': 'task_continue_error'
            }