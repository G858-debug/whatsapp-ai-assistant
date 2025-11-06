"""
Client Habit Flow Coordinator
Main coordinator for client habit flows - maintains backward compatibility
"""
from typing import Dict
from utils.logger import log_info, log_error
from .logging_flow import LoggingFlow
from .progress_flow import ProgressFlow
from .reminder_flow import ReminderFlow
from .reporting_flow import ReportingFlow


class ClientHabitFlows:
    """Main coordinator for client habit flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        
        # Initialize specialized flow handlers
        self.logging_flow = LoggingFlow(db, whatsapp, task_service)
        self.progress_flow = ProgressFlow(db, whatsapp, task_service)
        self.reminder_flow = ReminderFlow(db, whatsapp, task_service)
        self.reporting_flow = ReportingFlow(db, whatsapp, task_service)
    
    def continue_log_habits(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle log habits flow - delegates to LoggingFlow"""
        return self.logging_flow.continue_log_habits(phone, message, client_id, task)
    
    def continue_view_progress(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle view progress flow - delegates to ProgressFlow"""
        return self.progress_flow.continue_view_progress(phone, message, client_id, task)
    
    def continue_weekly_report(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle weekly report flow - delegates to ReportingFlow"""
        return self.reporting_flow.continue_weekly_report(phone, message, client_id, task)
    
    def continue_monthly_report(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle monthly report flow - delegates to ReportingFlow"""
        return self.reporting_flow.continue_monthly_report(phone, message, client_id, task)
    
    def continue_reminder_settings(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle reminder settings flow - delegates to ReminderFlow"""
        return self.reminder_flow.continue_reminder_settings(phone, message, client_id, task)