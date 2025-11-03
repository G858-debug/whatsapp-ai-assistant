"""
Client Command Handler
Handles all client-specific commands (Phase 2 & 3)
"""
from typing import Dict
from utils.logger import log_error


class ClientCommandHandler:
    """Handles client-specific commands"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
    
    def handle_client_command(self, phone: str, cmd: str, user_id: str) -> Dict:
        """Handle client-specific commands"""
        try:
            # Phase 2: Relationship commands
            relationship_result = self._handle_relationship_commands(phone, cmd, user_id)
            if relationship_result is not None:
                return relationship_result
            
            # Phase 3: Habit commands
            habit_result = self._handle_habit_commands(phone, cmd, user_id)
            if habit_result is not None:
                return habit_result
            
            # Unknown client command
            msg = f"❓ Unknown client command: {cmd}\n\nType /help to see available commands."
            self.whatsapp.send_message(phone, msg)
            return {
                'success': True,
                'response': msg,
                'handler': 'unknown_client_command'
            }
            
        except Exception as e:
            log_error(f"Error handling client command: {str(e)}")
            return {
                'success': False,
                'response': f"Error processing client command: {str(e)}",
                'handler': 'client_command_error'
            }
    
    def _handle_relationship_commands(self, phone: str, cmd: str, user_id: str) -> Dict:
        """Handle Phase 2 relationship commands"""
        try:
            if cmd == '/search-trainer':
                from services.commands.dashboard import generate_trainer_browse_dashboard
                return generate_trainer_browse_dashboard(phone, user_id, self.db, self.whatsapp)
                # from services.commands import handle_search_trainer
                # return handle_search_trainer(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/invite-trainer':
                from services.commands import handle_invite_trainer
                return handle_invite_trainer(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/view-trainers':
                from services.commands import handle_view_trainers
                return handle_view_trainers(phone, user_id, self.db, self.whatsapp)
            
            elif cmd == '/remove-trainer':
                from services.commands import handle_remove_trainer
                return handle_remove_trainer(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/dashboard-trainers':
                from services.commands.dashboard import generate_dashboard_link
                return generate_dashboard_link(phone, user_id, 'client', self.db, self.whatsapp)
            
            else:
                # Not a relationship command
                return None
                
        except Exception as e:
            log_error(f"Error handling client relationship command: {str(e)}")
            return {'success': False, 'response': 'Error processing relationship command', 'handler': 'client_relationship_error'}
    
    def _handle_habit_commands(self, phone: str, cmd: str, user_id: str) -> Dict:
        """Handle Phase 3 habit commands"""
        try:
            if cmd == '/view-my-habits':
                from services.commands import handle_view_my_habits
                return handle_view_my_habits(phone, user_id, self.db, self.whatsapp)
            
            elif cmd == '/log-habits':
                from services.commands import handle_log_habits
                return handle_log_habits(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/view-progress':
                from services.commands import handle_view_progress
                return handle_view_progress(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/weekly-report':
                from services.commands import handle_weekly_report
                return handle_weekly_report(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            elif cmd == '/monthly-report':
                from services.commands import handle_monthly_report
                return handle_monthly_report(phone, user_id, self.db, self.whatsapp, self.task_service)
            
            else:
                # Not a habit command
                return None
                
        except Exception as e:
            log_error(f"Error handling client habit command: {str(e)}")
            return {'success': False, 'response': 'Error processing habit command', 'handler': 'client_habit_error'}