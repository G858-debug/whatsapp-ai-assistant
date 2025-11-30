"""
 Handle Slash Command
Handle slash commands for trainers and clients
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_slash_command(self, phone: str, command: str) -> Dict:
    """Handle slash commands for trainers and clients"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Get user context to determine available commands
        context = self.get_user_context(phone)
        user_type = context.get('user_type', 'unknown')
        user_data = context.get('user_data')
        
        # Handle dual role selection needed
        if user_type == 'dual_role_selection_needed':
            response = "Please select your role first using the buttons above, then you can use commands."
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        # Route to specific command handlers
        if command == '/help':
            return self._handle_help_command(phone, user_type, user_data)
        elif command == '/profile':
            return self._handle_profile_command(phone, user_type, user_data)
        elif command == '/edit_profile':
            return self._handle_edit_profile_command(phone, user_type, user_data)
        elif command == '/registration':
            return self._handle_registration_command(phone, user_type)
        elif command == '/clients' and user_type == 'trainer':
            return self._handle_clients_command(phone, user_data)
        elif command == '/add_client' and user_type == 'trainer':
            return self._handle_add_client_command(phone, user_data)
        elif command == '/pending_requests' and user_type == 'trainer':
            return self._handle_pending_requests_command(phone, user_data)
        elif command.startswith('/approve_client') and user_type == 'trainer':
            return self._handle_approve_client_command(phone, command, user_data)
        elif command.startswith('/decline_client') and user_type == 'trainer':
            return self._handle_decline_client_command(phone, command, user_data)
        elif command == '/trainer' and user_type == 'client':
            return self._handle_trainer_info_command(phone, user_data)
        elif command == '/invitations' and user_type == 'client':
            return self._handle_client_invitations_command(phone, user_data)
        elif command.startswith('/accept_invitation') and user_type == 'client':
            return self._handle_accept_invitation_command(phone, command, user_data)
        elif command.startswith('/decline_invitation') and user_type == 'client':
            return self._handle_decline_invitation_command(phone, command, user_data)
        elif command == '/find_trainer' and user_type == 'client':
            return self._handle_find_trainer_command(phone, user_data)
        elif command.startswith('/request_trainer') and user_type == 'client':
            return self._handle_request_trainer_command(phone, command, user_data)
        elif command.startswith('/add_trainer') and user_type == 'client':
            return self._handle_add_trainer_command(phone, command, user_data)
        elif command == '/habits':
            return self._handle_habits_command(phone, user_type, user_data)
        elif command == '/log_habit':
            return self._handle_log_habit_command(phone, user_type, user_data)
        elif command == '/habit_streak':
            return self._handle_habit_streak_command(phone, user_type, user_data)
        elif command == '/habit_goals':
            return self._handle_habit_goals_command(phone, user_type, user_data)
        elif command == '/habit_progress' and user_type == 'client':
            return self._handle_habit_progress_command(phone, user_data)
        elif command == '/setup_habits' and user_type == 'trainer':
            return self._handle_setup_habits_command(phone, user_data)
        elif command == '/habit_challenges':
            return self._handle_habit_challenges_command(phone, user_type, user_data)
        elif command == '/habit_analytics' and user_type == 'trainer':
            return self._handle_habit_analytics_command(phone, user_type, user_data)
        elif command == '/send_reminders' and user_type == 'trainer':
            return self._handle_send_reminders_command(phone, user_type, user_data)
        elif command == '/create_challenge' and user_type == 'trainer':
            return self._handle_create_challenge_command(phone, user_data)
        elif command == '/test_flows':
            return self._test_habit_flows(phone, user_type, user_data)
        elif command == '/reset_me':
            return self._handle_reset_command(phone)
        else:
            # Unknown command
            available_commands = self._get_available_commands(user_type)
            response = (
                f"❓ Unknown command: `{command}`\n\n"
                f"Available commands:\n{available_commands}\n\n"
                f"Type `/help` for detailed information."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
    except Exception as e:
        log_error(f"Error handling slash command {command}: {str(e)}")
        return {'success': False, 'error': str(e)}
