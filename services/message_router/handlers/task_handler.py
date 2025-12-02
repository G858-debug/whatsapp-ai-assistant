"""
Task Handler
Delegates task continuation to specialized handlers
"""
from typing import Dict
from utils.logger import log_info, log_error

from .tasks.task_handler import TaskHandler as TaskHandlerImpl


class TaskHandler:
    """Main task handler that delegates to the implementation"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service, reg_service=None):
        # todo: reg_service will be deleted after client onboarding clean
        self.handler = TaskHandlerImpl(supabase_client, whatsapp_service, task_service, reg_service)
    
    def continue_task(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Delegate task continuation to the implementation"""
        return self.handler.continue_task(phone, message, role, user_id, task)
