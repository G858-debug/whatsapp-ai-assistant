"""
Trainer Command Handler
Main coordinator for all trainer-specific commands
"""
from typing import Dict
from utils.logger import log_info, log_error

# Import habit commands
from .habits.creation_commands import handle_create_habit, handle_edit_habit, handle_delete_habit
from .habits.assignment_commands import handle_assign_habits, handle_view_client_habits
from .habits.reporting_commands import handle_view_habit_progress, handle_export_habit_data
from .dashboard_commands import handle_trainer_dashboard, handle_client_progress_dashboard

# Import relationship commands
from .relationships.invitation_commands import handle_invite_client, handle_create_client
from .relationships.management_commands import handle_view_trainees, handle_remove_trainee


class TrainerCommandHandler:
    """Handles all trainer-specific commands"""
    
    def __init__(self, db, whatsapp, task_service, reg_service=None):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.reg_service = reg_service
    
    # Habit Management Commands
    def handle_create_habit(self, phone: str, trainer_id: str) -> Dict:
        """Handle /create-habit command"""
        return handle_create_habit(phone, trainer_id, self.db, self.whatsapp, self.task_service)
    
    def handle_edit_habit(self, phone: str, trainer_id: str) -> Dict:
        """Handle /edit-habit command"""
        return handle_edit_habit(phone, trainer_id, self.db, self.whatsapp, self.task_service)
    
    def handle_delete_habit(self, phone: str, trainer_id: str) -> Dict:
        """Handle /delete-habit command"""
        return handle_delete_habit(phone, trainer_id, self.db, self.whatsapp, self.task_service)
    
    def handle_assign_habit(self, phone: str, trainer_id: str) -> Dict:
        """Handle /assign-habit command"""
        return handle_assign_habits(phone, trainer_id, self.db, self.whatsapp, self.task_service)
    
    def handle_view_habits(self, phone: str, trainer_id: str) -> Dict:
        """Handle /view-habits command"""
        return handle_view_client_habits(phone, trainer_id, self.db, self.whatsapp)
    
    def handle_view_trainee_progress(self, phone: str, trainer_id: str) -> Dict:
        """Handle /view-trainee-progress command"""
        return handle_view_habit_progress(phone, trainer_id, self.db, self.whatsapp, self.task_service)
    
    def handle_trainee_weekly_report(self, phone: str, trainer_id: str) -> Dict:
        """Handle /trainee-weekly-report command"""
        return handle_export_habit_data(phone, trainer_id, self.db, self.whatsapp, self.task_service, 'weekly')
    
    def handle_trainee_monthly_report(self, phone: str, trainer_id: str) -> Dict:
        """Handle /trainee-monthly-report command"""
        return handle_export_habit_data(phone, trainer_id, self.db, self.whatsapp, self.task_service, 'monthly')
    
    # Relationship Management Commands
    def handle_invite_trainee(self, phone: str, trainer_id: str) -> Dict:
        """Handle /invite-trainee command"""
        return handle_invite_client(phone, trainer_id, self.db, self.whatsapp, self.task_service)
    
    def handle_create_trainee(self, phone: str, trainer_id: str) -> Dict:
        """Handle /create-trainee command"""
        return handle_create_client(phone, trainer_id, self.db, self.whatsapp, self.reg_service, self.task_service)
    
    def handle_view_trainees(self, phone: str, trainer_id: str) -> Dict:
        """Handle /view-trainees command"""
        return handle_view_trainees(phone, trainer_id, self.db, self.whatsapp)
    
    def handle_remove_trainee(self, phone: str, trainer_id: str) -> Dict:
        """Handle /remove-trainee command"""
        return handle_remove_trainee(phone, trainer_id, self.db, self.whatsapp, self.task_service)
    
    def handle_dashboard_clients(self, phone: str, trainer_id: str) -> Dict:
        """Handle /dashboard-clients command"""
        from services.commands.dashboard import generate_dashboard_link
        return generate_dashboard_link(phone, trainer_id, 'trainer', self.db, self.whatsapp)
    
    def handle_trainer_dashboard(self, phone: str, trainer_id: str) -> Dict:
        """Handle /trainer-dashboard command"""
        log_info(f"TrainerCommandHandler: handle_trainer_dashboard called for {trainer_id}")
        try:
            result = handle_trainer_dashboard(phone, trainer_id, self.db, self.whatsapp)
            log_info(f"TrainerCommandHandler: handle_trainer_dashboard result: {result}")
            return result
        except Exception as e:
            log_error(f"TrainerCommandHandler: handle_trainer_dashboard error: {str(e)}")
            raise
    
    def handle_client_progress(self, phone: str, trainer_id: str) -> Dict:
        """Handle /client-progress command"""
        return handle_client_progress_dashboard(phone, trainer_id, self.db, self.whatsapp, self.task_service)