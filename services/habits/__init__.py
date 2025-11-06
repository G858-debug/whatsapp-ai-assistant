# Habit Management Services - Phase 3
from services.habits.habit_service import HabitService
from services.habits.assignment_service import AssignmentService
from services.habits.logging_service import LoggingService
from services.habits.report_service import ReportService

# For backward compatibility with old code
# TODO: Refactor old code to use new Phase 3 services
class HabitTrackingService:
    """Legacy compatibility wrapper - redirects to new Phase 3 services"""
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.habit_service = HabitService(supabase_client)
        self.assignment_service = AssignmentService(supabase_client)
        self.logging_service = LoggingService(supabase_client)
        self.report_service = ReportService(supabase_client)
    
    # Add legacy method stubs that redirect to new services
    def get_client_habits(self, client_id):
        """Legacy method - use assignment_service.get_client_habits instead"""
        success, msg, habits = self.assignment_service.get_client_habits(client_id)
        return habits if success else []
    
    def get_current_streak(self, client_id):
        """Legacy method - placeholder for streak calculation"""
        # TODO: Implement streak calculation in Phase 3
        return 0
    
    def log_habit(self, client_id, habit_id, value, notes=None):
        """Legacy method - use logging_service.log_habit instead"""
        return self.logging_service.log_habit(client_id, habit_id, value, notes)
    
    def get_habit_logs(self, client_id, habit_id, start_date, end_date):
        """Legacy method - use logging_service.get_habit_logs instead"""
        success, msg, logs = self.logging_service.get_habit_logs(client_id, habit_id, start_date, end_date)
        return logs if success else []

__all__ = [
    'HabitService',
    'AssignmentService', 
    'LoggingService',
    'ReportService',
    'HabitTrackingService'  # Legacy compatibility
]
