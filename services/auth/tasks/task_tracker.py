"""
Task Tracker
Handles task status tracking and updates
"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error


class TaskTracker:
    """Manages task status tracking and updates"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def update_task(self, task_id: str, role: str, task_data: Dict = None, status: str = None) -> bool:
        """
        Update task data and/or status
        """
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            
            update_data = {
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if task_data is not None:
                update_data['task_data'] = task_data
            
            if status:
                update_data['task_status'] = status
                
                if status == 'completed':
                    update_data['completed_at'] = datetime.now(self.sa_tz).isoformat()
                elif status == 'stopped':
                    update_data['stopped_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table(table).update(update_data).eq('id', task_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating task: {str(e)}")
            return False
    
    def complete_task(self, task_id: str, role: str) -> bool:
        """Mark task as completed"""
        return self.update_task(task_id, role, status='completed')
    
    def stop_task(self, task_id: str, role: str) -> bool:
        """Mark task as stopped"""
        return self.update_task(task_id, role, status='stopped')
    
    def stop_all_running_tasks(self, user_id: str, role: str) -> bool:
        """Stop all running tasks for user"""
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            result = self.db.table(table).update({
                'task_status': 'stopped',
                'stopped_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq(id_column, user_id).eq('task_status', 'running').execute()
            
            log_info(f"Stopped all running tasks for {role} {user_id}")
            return True
            
        except Exception as e:
            log_error(f"Error stopping tasks: {str(e)}")
            return False