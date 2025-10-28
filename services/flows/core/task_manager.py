"""
Flow Task Manager
Manages task state and progression for flows
"""
from typing import Dict, Any, Optional
from utils.logger import log_error


class FlowTaskManager:
    """Manages task state for conversation flows"""
    
    def __init__(self, task_service):
        self.task_service = task_service
    
    def create_flow_task(self, user_id: str, role: str, task_type: str, 
                        initial_data: Dict = None) -> Optional[str]:
        """Create a new flow task"""
        try:
            return self.task_service.create_task(
                user_id=user_id,
                role=role,
                task_type=task_type,
                task_data=initial_data or {}
            )
        except Exception as e:
            log_error(f"Error creating flow task: {str(e)}")
            return None
    
    def update_flow_task(self, task: Dict, role: str, updates: Dict) -> bool:
        """Update flow task data"""
        try:
            if not task or not task.get('id'):
                return False
            
            current_data = task.get('task_data', {})
            current_data.update(updates)
            
            return self.task_service.update_task(
                task_id=task['id'],
                role=role,
                task_data=current_data
            )
        except Exception as e:
            log_error(f"Error updating flow task: {str(e)}")
            return False
    
    def complete_flow_task(self, task: Dict, role: str) -> bool:
        """Complete a flow task"""
        try:
            if not task or not task.get('id'):
                return False
            
            return self.task_service.complete_task(task['id'], role)
        except Exception as e:
            log_error(f"Error completing flow task: {str(e)}")
            return False
    
    def stop_flow_task(self, task: Dict, role: str) -> bool:
        """Stop a flow task"""
        try:
            if not task or not task.get('id'):
                return False
            
            return self.task_service.stop_task(task['id'], role)
        except Exception as e:
            log_error(f"Error stopping flow task: {str(e)}")
            return False
    
    def get_task_data(self, task: Dict, key: str, default: Any = None) -> Any:
        """Get task data safely"""
        try:
            return task.get('task_data', {}).get(key, default)
        except Exception:
            return default
    
    def set_task_step(self, task: Dict, role: str, step: str, **kwargs) -> bool:
        """Set current step in task data"""
        updates = {'step': step}
        updates.update(kwargs)
        return self.update_flow_task(task, role, updates)
    
    def advance_field_index(self, task: Dict, role: str, field_index_key: str = 'current_field_index') -> bool:
        """Advance field index in task data"""
        current_index = self.get_task_data(task, field_index_key, 0)
        return self.update_flow_task(task, role, {field_index_key: current_index + 1})
    
    def store_field_data(self, task: Dict, role: str, field_name: str, value: Any,
                        data_key: str = 'collected_data') -> bool:
        """Store field data in task"""
        current_data = self.get_task_data(task, data_key, {})
        current_data[field_name] = value
        return self.update_flow_task(task, role, {data_key: current_data})
    
    def get_field_data(self, task: Dict, field_name: str, data_key: str = 'collected_data', 
                      default: Any = None) -> Any:
        """Get field data from task"""
        data = self.get_task_data(task, data_key, {})
        return data.get(field_name, default)
    
    def is_task_complete(self, task: Dict, total_fields: int, 
                        field_index_key: str = 'current_field_index') -> bool:
        """Check if task has processed all fields"""
        current_index = self.get_task_data(task, field_index_key, 0)
        return current_index >= total_fields