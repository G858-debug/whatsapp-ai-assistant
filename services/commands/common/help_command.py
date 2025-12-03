"""
Help Command Handler - Phases 1, 2 & 3
Shows available commands based on user's role using interactive list messages
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_help(phone: str, auth_service, whatsapp) -> Dict:
    """Show help message with available commands using WhatsApp List Messages"""
    try:
        # Get user's login status
        login_status = auth_service.get_login_status(phone)
        
        if not login_status:
            # Not logged in - simple message
            help_msg = (
                "📚 *Refiloe Help*\n\n"
                "*Universal Commands:*\n"
                "• /help - Show this help message\n"
                "• /register - Start registration\n"
                "• /stop - Cancel any stuck tasks\n\n"
                "Please register or login to see more commands!"
            )
            whatsapp.send_message(phone, help_msg)
            
        elif login_status == 'trainer':
            # Trainer - show all commands grouped by category
            help_msg = (
                "📚 *Refiloe Help - Trainer*\n\n"
                "Browse command categories below, then just tell me what you want to do!\n\n"
                "💡 *Example:* Say \"view my profile\" or \"invite a client\""
            )
            
            sections = [
                {
                    "title": "Available Commands",
                    "rows": [
                        {
                            "id": "help_account",
                            "title": "Account Management",
                            "description": "view profile, edit profile, delete account, logout, switch role"
                        },
                        {
                            "id": "help_clients",
                            "title": "Client Management",
                            "description": "invite client, create client, view clients, remove client"
                        },
                        {
                            "id": "help_habits",
                            "title": "Habit Management",
                            "description": "create habit, edit habit, delete habit, view habits"
                        },
                        {
                            "id": "help_assign",
                            "title": "Habit Assignment",
                            "description": "assign habit, unassign habit, view client habits"
                        },
                        {
                            "id": "help_progress",
                            "title": "Progress Tracking",
                            "description": "view client progress, weekly report, monthly report"
                        },
                        {
                            "id": "help_dashboard",
                            "title": "Dashboard & Reports",
                            "description": "trainer dashboard, export habit data"
                        },
                        {
                            "id": "help_system",
                            "title": "System Commands",
                            "description": "help, stop task, register"
                        }
                    ]
                }
            ]
            
            whatsapp.send_list_message(
                phone=phone,
                body=help_msg,
                button_text="Browse Commands",
                sections=sections
            )
            
        else:  # client
            # Client - show all commands grouped by category
            help_msg = (
                "📚 *Refiloe Help - Client*\n\n"
                "Browse command categories below, then just tell me what you want to do!\n\n"
                "💡 *Example:* Say \"log my habits\" or \"view progress\""
            )
            
            sections = [
                {
                    "title": "Available Commands",
                    "rows": [
                        {
                            "id": "help_account",
                            "title": "Account Management",
                            "description": "view profile, edit profile, delete account"
                        },
                        {
                            "id": "help_trainers",
                            "title": "Trainer Management",
                            "description": "search trainers, invite trainer, view trainers, remove trainer"
                        },
                        {
                            "id": "help_habits",
                            "title": "Habit Tracking",
                            "description": "view my habits, log habits, view progress"
                        },
                        {
                            "id": "help_reports",
                            "title": "Progress Reports",
                            "description": "weekly report, monthly report"
                        },
                        {
                            "id": "help_reminders",
                            "title": "Reminders",
                            "description": "reminder settings, test reminder"
                        },
                        {
                            "id": "help_system",
                            "title": "System Commands",
                            "description": "help, stop task"
                        }
                    ]
                }
            ]
            
            whatsapp.send_list_message(
                phone=phone,
                body=help_msg,
                button_text="Browse Commands",
                sections=sections
            )
        
        return {
            'success': True,
            'response': help_msg,
            'handler': 'help_command'
        }
        
    except Exception as e:
        log_error(f"Error in help command: {str(e)}")
        import traceback
        log_error(f"Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load the help information.",
            'handler': 'help_error'
        }
