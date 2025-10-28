"""
Trainer Habit Flow Coordinator
Main coordinator for trainer habit flows - maintains backward compatibility
"""
from typing import Dict
from utils.logger import log_info, log_error
from .creation_flow import CreationFlow
from .editing_flow import EditingFlow
from .assignment_flow import AssignmentFlow
from .reporting_flow import ReportingFlow


class TrainerHabitFlows:
    """Main coordinator for trainer habit flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        
        # Initialize specialized flow handlers
        self.creation_flow = CreationFlow(db, whatsapp, task_service)
        self.editing_flow = EditingFlow(db, whatsapp, task_service)
        self.assignment_flow = AssignmentFlow(db, whatsapp, task_service)
        self.reporting_flow = ReportingFlow(db, whatsapp, task_service)
    
    def continue_create_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle create habit flow - delegates to CreationFlow"""
        return self.creation_flow.continue_create_habit(phone, message, trainer_id, task)
    
    def continue_edit_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle edit habit flow - delegates to EditingFlow"""
        return self.editing_flow.continue_edit_habit(phone, message, trainer_id, task)
    
    def continue_delete_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle delete habit flow - delegates to EditingFlow"""
        return self.editing_flow.continue_delete_habit(phone, message, trainer_id, task)
    
    def continue_assign_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle assign habit flow - delegates to AssignmentFlow"""
        return self.assignment_flow.continue_assign_habit(phone, message, trainer_id, task)
    
    def continue_view_trainee_progress(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle view trainee progress flow - delegates to ReportingFlow"""
        return self.reporting_flow.continue_view_trainee_progress(phone, message, trainer_id, task)
    
    def continue_trainee_report(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle trainee report flow - delegates to ReportingFlow"""
        return self.reporting_flow.continue_trainee_report(phone, message, trainer_id, task)