"""
Client Command Handler
Main coordinator for all client-specific commands
"""
from typing import Dict
from utils.logger import log_info, log_error

# Import habit commands
from .habits.logging_commands import handle_log_habits, handle_view_my_habits
from .habits.progress_commands import handle_view_progress, handle_weekly_report, handle_monthly_report

# Import relationship commands
from .relationships.search_commands import handle_search_trainers, handle_view_trainers
from .relationships.invitation_commands import handle_invite_trainer, handle_remove_trainer


class ClientCommandHandler:
    """Handles all client-specific commands"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
    
    # Habit Management Commands
    def handle_view_my_habits(self, phone: str, client_id: str) -> Dict:
        """Handle /view-my-habits command"""
        return handle_view_my_habits(phone, client_id, self.db, self.whatsapp)
    
    def handle_log_habits(self, phone: str, client_id: str) -> Dict:
        """Handle /log-habits command"""
        return handle_log_habits(phone, client_id, self.db, self.whatsapp, self.task_service)
    
    def handle_view_progress(self, phone: str, client_id: str) -> Dict:
        """Handle /view-progress command"""
        return handle_view_progress(phone, client_id, self.db, self.whatsapp, self.task_service)
    
    def handle_weekly_report(self, phone: str, client_id: str) -> Dict:
        """Handle /weekly-report command"""
        return handle_weekly_report(phone, client_id, self.db, self.whatsapp, self.task_service)
    
    def handle_monthly_report(self, phone: str, client_id: str) -> Dict:
        """Handle /monthly-report command"""
        return handle_monthly_report(phone, client_id, self.db, self.whatsapp, self.task_service)
    
    # Relationship Management Commands
    def handle_search_trainer(self, phone: str, client_id: str) -> Dict:
        """Handle /search-trainer command"""
        return handle_search_trainers(phone, client_id, self.db, self.whatsapp, self.task_service)
    
    def handle_view_trainers(self, phone: str, client_id: str) -> Dict:
        """Handle /view-trainers command"""
        return handle_view_trainers(phone, client_id, self.db, self.whatsapp)
    
    def handle_invite_trainer(self, phone: str, client_id: str) -> Dict:
        """Handle /invite-trainer command"""
        return handle_invite_trainer(phone, client_id, self.db, self.whatsapp, self.task_service)
    
    def handle_remove_trainer(self, phone: str, client_id: str) -> Dict:
        """Handle /remove-trainer command"""
        return handle_remove_trainer(phone, client_id, self.db, self.whatsapp, self.task_service)
    
    def handle_dashboard_trainers(self, phone: str, client_id: str) -> Dict:
        """Handle /dashboard-trainers command"""
        from services.commands.dashboard import generate_dashboard_link
        return generate_dashboard_link(client_id, 'client', self.db, self.whatsapp)