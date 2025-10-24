"""
Task Service - Phase 1
Manages task tracking for trainers and clients
"""
from typing import Dict, Optional, List
from datetime import datetime
import pytz
from utils.logger import log_info, log_error


class TaskService:
    """Manages task creation, tracking, and completion"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def create_task(self, user_id: str, role: str, task_type: str, task_data: Dict = None) -> Optional[str]:
        """
        Create a new task
        Returns: task_id if successful, None otherwise
        """
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            task_record = {
                id_column: user_id,
                'task_type': task_type,
                'task_status': 'running',
                'task_data': task_data or {},
                'started_at': datetime.now(self.sa_tz).isoformat(),
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table(table).insert(task_record).execute()
            
            if result.data and len(result.data) > 0:
                task_id = result.data[0]['id']
                log_info(f"Created {role} task: {task_type} for {user_id}")
                return task_id
            
            return None
            
        except Exception as e:
            log_error(f"Error creating task: {str(e)}")
            return None
    
    def get_running_task(self, user_id: str, role: str) -> Optional[Dict]:
        """
        Get currently running task for user
        Returns: task data if found, None otherwise
        """
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            result = self.db.table(table).select('*').eq(
                id_column, user_id
            ).eq(
                'task_status', 'running'
            ).order('started_at', desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return None
            
        except Exception as e:
            log_error(f"Error getting running task: {str(e)}")
            return None
    
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
    
    def get_recent_completed_tasks(self, user_id: str, role: str, limit: int = 5) -> List[Dict]:
        """
        Get recent completed tasks for context
        """
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            result = self.db.table(table).select('*').eq(
                id_column, user_id
            ).eq(
                'task_status', 'completed'
            ).order('completed_at', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting completed tasks: {str(e)}")
            return []
    
    def get_task_by_id(self, task_id: str, role: str) -> Optional[Dict]:
        """Get specific task by ID"""
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            
            result = self.db.table(table).select('*').eq('id', task_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return None
            
        except Exception as e:
            log_error(f"Error getting task: {str(e)}")
            return None
