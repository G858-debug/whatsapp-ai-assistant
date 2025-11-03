"""
Task Service - Enhanced Structure
Main coordinator for task management with delegation to specialized managers
"""
from typing import Dict, Optional, List
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

# Import specialized managers
from .tasks.task_manager import TaskManager
from .tasks.task_tracker import TaskTracker


class TaskService:
    """
    Main task service coordinator.
    Delegates to specialized managers while maintaining backward compatibility.
    """
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize specialized managers
        self.task_manager = TaskManager(supabase_client)
        self.task_tracker = TaskTracker(supabase_client)
    
    # Delegate to TaskManager
    def create_task(self, user_id: str, role: str, task_type: str, task_data: Dict = None) -> Optional[str]:
        """Create a new task"""
        return self.task_manager.create_task(user_id, role, task_type, task_data)
    
    def get_running_task(self, user_id: str, role: str) -> Optional[Dict]:
        """Get currently running task for user"""
        return self.task_manager.get_running_task(user_id, role)
    
    def get_task_by_id(self, task_id: str, role: str) -> Optional[Dict]:
        """Get specific task by ID"""
        return self.task_manager.get_task_by_id(task_id, role)
    
    def get_recent_completed_tasks(self, user_id: str, role: str, limit: int = 5) -> List[Dict]:
        """Get recent completed tasks for context"""
        return self.task_manager.get_recent_completed_tasks(user_id, role, limit)
    
    # Delegate to TaskTracker
    def update_task(self, task_id: str, role: str, task_data: Dict = None, status: str = None) -> bool:
        """Update task data and/or status"""
        return self.task_tracker.update_task(task_id, role, task_data, status)
    
    def complete_task(self, task_id: str, role: str) -> bool:
        """Mark task as completed"""
        return self.task_tracker.complete_task(task_id, role)
    
    def stop_task(self, task_id: str, role: str) -> bool:
        """Mark task as stopped"""
        return self.task_tracker.stop_task(task_id, role)
    
    def stop_all_running_tasks(self, user_id: str, role: str) -> bool:
        """Stop all running tasks for user"""
        return self.task_tracker.stop_all_running_tasks(user_id, role)
    
    def emergency_cleanup_all_tasks(self, phone: str, user_id: str = None, role: str = None) -> int:
        """Emergency cleanup - force complete ALL running tasks for a user (nuclear option)"""
        try:
            from datetime import datetime
            import pytz
            
            sa_tz = pytz.timezone('Africa/Johannesburg')
            now = datetime.now(sa_tz).isoformat()
            cleaned_count = 0
            
            # If we have user_id and role, clean those tasks
            if user_id and role:
                table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
                id_column = 'trainer_id' if role == 'trainer' else 'client_id'
                
                # Get all running tasks
                running_tasks = self.db.table(table).select('id, task_type').eq(
                    id_column, user_id
                ).eq('task_status', 'running').execute()
                
                # Force complete them
                for task in running_tasks.data:
                    self.db.table(table).update({
                        'task_status': 'completed',
                        'completed_at': now,
                        'updated_at': now
                    }).eq('id', task['id']).execute()
                    cleaned_count += 1
                    log_info(f"Emergency cleanup: completed task {task['id']} ({task.get('task_type')})")
            
            # Also clean registration tasks using phone as ID
            for reg_role in ['trainer', 'client']:
                try:
                    table = f'{reg_role}_tasks'
                    id_column = f'{reg_role}_id'
                    
                    reg_tasks = self.db.table(table).select('id, task_type').eq(
                        id_column, phone
                    ).eq('task_status', 'running').execute()
                    
                    for task in reg_tasks.data:
                        self.db.table(table).update({
                            'task_status': 'completed',
                            'completed_at': now,
                            'updated_at': now
                        }).eq('id', task['id']).execute()
                        cleaned_count += 1
                        log_info(f"Emergency cleanup: completed registration task {task['id']} for {reg_role}")
                        
                except Exception as role_error:
                    log_error(f"Emergency cleanup error for {reg_role}: {str(role_error)}")
            
            log_info(f"Emergency cleanup completed for {phone}: {cleaned_count} tasks cleaned")
            return cleaned_count
            
        except Exception as e:
            log_error(f"Emergency cleanup failed for {phone}: {str(e)}")
            return 0