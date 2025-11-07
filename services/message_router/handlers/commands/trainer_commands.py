"""
Trainer Command Handler
Handles all trainer-specific commands (Phase 2 & 3)
"""
from typing import Dict
from utils.logger import log_error


class TrainerCommandHandler:
    """Handles trainer-specific commands"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
    
    def handle_trainer_command(self, phone: str, cmd: str, user_id: str) -> Dict:
        """Handle trainer-specific commands"""
        try:
            # Phase 2: Relationship commands
            relationship_result = self._handle_relationship_commands(phone, cmd, user_id)
            if relationship_result is not None:
                return relationship_result
            
            # Phase 3: Habit commands
            habit_result = self._handle_habit_commands(phone, cmd, user_id)
            if habit_result is not None:
                return habit_result
            
            # Unknown trainer command
            msg = f"❓ Unknown trainer command: {cmd}\n\nType /help to see available commands."
            self.whatsapp.send_message(phone, msg)
            return {
                'success': True,
                'response': msg,
                'handler': 'unknown_trainer_command'
            }
            
        except Exception as e:
            log_error(f"Error handling trainer command: {str(e)}")
            return {
                'success': False,
                'response': f"Error processing trainer command: {str(e)}",
                'handler': 'trainer_command_error'
            }
    
    def _handle_relationship_commands(self, phone: str, cmd: str, user_id: str) -> Dict:
        """Handle Phase 2 relationship commands"""
        try:
            if cmd == '/invite-trainee':
                from services.commands import handle_invite_trainee
                return handle_invite_trainee(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/create-trainee':
                from services.commands import handle_create_trainee
                return handle_create_trainee(phone, user_id, self.db, self.whatsapp, None, self.task_service)
            
            elif cmd == '/view-trainees':
                from services.commands import handle_view_trainees
                return handle_view_trainees(phone, user_id, self.db, self.whatsapp)
            
            elif cmd == '/remove-trainee':
                from services.commands import handle_remove_trainee
                return handle_remove_trainee(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/dashboard-clients':
                from services.commands.dashboard import generate_dashboard_link
                return generate_dashboard_link(phone, user_id, 'trainer', self.db, self.whatsapp)
            
            else:
                # Not a relationship command
                return None
                
        except Exception as e:
            log_error(f"Error handling trainer relationship command: {str(e)}")
            return {'success': False, 'response': 'Error processing relationship command', 'handler': 'trainer_relationship_error'}
    
    def _handle_habit_commands(self, phone: str, cmd: str, user_id: str) -> Dict:
        """Handle Phase 3 habit commands"""
        try:
            if cmd == '/create-habit':
                from services.commands import handle_create_habit
                return handle_create_habit(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/edit-habit':
                from services.commands import handle_edit_habit
                return handle_edit_habit(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/delete-habit':
                from services.commands import handle_delete_habit
                return handle_delete_habit(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/assign-habit':
                from services.commands import handle_assign_habit
                return handle_assign_habit(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/unassign-habit':
                from services.commands import handle_unassign_habit
                return handle_unassign_habit(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/view-habits':
                from services.commands.dashboard import generate_trainer_habits_dashboard
                return generate_trainer_habits_dashboard(phone, user_id, self.db, self.whatsapp)
            
            elif cmd == '/view-trainee-progress':
                from services.commands import handle_view_trainee_progress
                return handle_view_trainee_progress(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/trainer-dashboard':
                from services.commands.dashboard import generate_trainer_main_dashboard
                return generate_trainer_main_dashboard(phone, user_id, self.db, self.whatsapp)
            
            elif cmd == '/trainee-weekly-report':
                from services.commands import handle_trainee_report
                return handle_trainee_report(phone, user_id, self.db, self.whatsapp, self.task_service, 'weekly')
            
            elif cmd == '/trainee-monthly-report':
                from services.commands import handle_trainee_report
                return handle_trainee_report(phone, user_id, self.db, self.whatsapp, self.task_service, 'monthly')
            
            else:
                # Not a habit command
                return None
                
        except Exception as e:
            log_error(f"Error handling trainer habit command: {str(e)}")
            return {'success': False, 'response': 'Error processing habit command', 'handler': 'trainer_habit_error'}