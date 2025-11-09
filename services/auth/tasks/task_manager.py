"""
Task Manager
Handles task CRUD operations
"""
from typing import Dict, Optional, List
from datetime import datetime
import pytz
from utils.logger import log_info, log_error


class TaskManager:
    """Manages task CRUD operations"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def create_task(self, phone: str, role: str, task_type: str, task_data: Dict = None) -> Optional[str]:
        """
        Create a new task using phone number
        Returns: task_id if successful, None otherwise
        """
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            phone_column = 'trainer_phone' if role == 'trainer' else 'client_phone'

            task_record = {
                phone_column: phone,
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
                log_info(f"Created {role} task: {task_type} for {phone}")
                return task_id

            return None

        except Exception as e:
            log_error(f"Error creating task: {str(e)}")
            return None
    
    def get_running_task(self, phone: str, role: str) -> Optional[Dict]:
        """
        Get currently running task using phone number
        Returns: task data if found, None otherwise
        """
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            phone_column = 'trainer_phone' if role == 'trainer' else 'client_phone'

            result = self.db.table(table).select('*').eq(
                phone_column, phone
            ).eq(
                'task_status', 'running'
            ).order('started_at', desc=True).limit(1).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]

            return None

        except Exception as e:
            log_error(f"Error getting running task: {str(e)}")
            return None
    
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
    
    def get_recent_completed_tasks(self, phone: str, role: str, limit: int = 5) -> List[Dict]:
        """
        Get recent completed tasks using phone number
        """
        try:
            table = 'trainer_tasks' if role == 'trainer' else 'client_tasks'
            phone_column = 'trainer_phone' if role == 'trainer' else 'client_phone'

            result = self.db.table(table).select('*').eq(
                phone_column, phone
            ).eq(
                'task_status', 'completed'
            ).order('completed_at', desc=True).limit(limit).execute()

            return result.data if result.data else []

        except Exception as e:
            log_error(f"Error getting completed tasks: {str(e)}")
            return []