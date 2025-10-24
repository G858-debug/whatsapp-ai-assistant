"""
Help Command Handler - Phase 1
Shows available commands based on user's role
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_help(phone: str, auth_service, whatsapp) -> Dict:
    """Show help message with available commands"""
    try:
        # Get user's login status
        login_status = auth_service.get_login_status(phone)
        
        if not login_status:
            # Not logged in
            help_msg = (
                "📚 *Refiloe Help*\n\n"
                "*Universal Commands:*\n"
                "• /help - Show this help message\n"
                "• /register - Start registration\n\n"
                "Please register or login to see more commands!"
            )
        elif login_status == 'trainer':
            help_msg = (
                "📚 *Refiloe Help - Trainer*\n\n"
                "*Universal Commands:*\n"
                "• /help - Show this help\n"
                "• /logout - Logout\n"
                "• /switch-role - Switch to client (if registered)\n"
                "• /stop - Cancel current task\n\n"
                "*Profile Management:*\n"
                "• /view-profile - View your profile\n"
                "• /edit-profile - Edit your information\n"
                "• /delete-account - Delete your account\n\n"
                "*Client Management:* (Phase 2)\n"
                "• /invite-trainee - Invite a client\n"
                "• /create-trainee - Create & invite client\n"
                "• /view-trainees - View your clients\n"
                "• /remove-trainee - Remove a client\n\n"
                "*Habit Management:* (Phase 3)\n"
                "• /create-habit - Create fitness habit\n"
                "• /assign-habit - Assign habit to clients\n"
                "• /view-habits - View created habits\n\n"
                "💡 *Tip:* You can also just tell me what you want to do!"
            )
        else:  # client
            help_msg = (
                "📚 *Refiloe Help - Client*\n\n"
                "*Universal Commands:*\n"
                "• /help - Show this help\n"
                "• /logout - Logout\n"
                "• /switch-role - Switch to trainer (if registered)\n"
                "• /stop - Cancel current task\n\n"
                "*Profile Management:*\n"
                "• /view-profile - View your profile\n"
                "• /edit-profile - Edit your information\n"
                "• /delete-account - Delete your account\n\n"
                "*Trainer Management:* (Phase 2)\n"
                "• /search-trainer - Search for trainers\n"
                "• /invite-trainer - Invite a trainer\n"
                "• /view-trainers - View your trainers\n"
                "• /remove-trainer - Remove a trainer\n\n"
                "*Habit Tracking:* (Phase 3)\n"
                "• /view-my-habits - View assigned habits\n"
                "• /log-habits - Log today's habits\n"
                "• /view-progress - View your progress\n\n"
                "💡 *Tip:* You can also just tell me what you want to do!"
            )
        
        whatsapp.send_message(phone, help_msg)
        
        return {
            'success': True,
            'response': help_msg,
            'handler': 'help_command'
        }
        
    except Exception as e:
        log_error(f"Error in help command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load the help information.",
            'handler': 'help_error'
        }
