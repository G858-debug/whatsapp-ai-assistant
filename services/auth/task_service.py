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
