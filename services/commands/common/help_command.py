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
            # Trainer - show all commands grouped by category (9 categories to fit in 10 row limit)
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
                            "description": "view profile, edit profile"
                        },
                        {
                            "id": "help_account2",
                            "title": "Account Management (More)",
                            "description": "delete account, stop task"
                        },
                        {
                            "id": "help_clients",
                            "title": "Client Management",
                            "description": "invite client, view clients"
                        },
                        {
                            "id": "help_clients2",
                            "title": "Client Management (More)",
                            "description": "remove client, create client"
                        },
                        {
                            "id": "help_habits",
                            "title": "Habit Management",
                            "description": "create habit, view habits"
                        },
                        {
                            "id": "help_habits2",
                            "title": "Habit Management (More)",
                            "description": "edit habit, delete habit"
                        },
                        {
                            "id": "help_assign",
                            "title": "Habit Assignment",
                            "description": "assign habit, unassign habit"
                        },
                        {
                            "id": "help_progress",
                            "title": "Progress Tracking",
                            "description": "client progress, weekly report"
                        },
                        {
                            "id": "help_dashboard",
                            "title": "Dashboard & Reports",
                            "description": "trainer dashboard, view clients"
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
            # Client - show all commands grouped by category (7 categories to fit in 10 row limit)
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
                            "description": "view profile, edit profile"
                        },
                        {
                            "id": "help_account2",
                            "title": "Account Management (More)",
                            "description": "delete account, stop task"
                        },
                        {
                            "id": "help_trainers",
                            "title": "Trainer Management",
                            "description": "search trainers, view trainers"
                        },
                        {
                            "id": "help_trainers2",
                            "title": "Trainer Management (More)",
                            "description": "remove trainer, invite trainer"
                        },
                        {
                            "id": "help_habits",
                            "title": "Habit Tracking",
                            "description": "my habits, log habits"
                        },
                        {
                            "id": "help_habits2",
                            "title": "Habit Tracking (More)",
                            "description": "view progress, weekly report"
                        },
                        {
                            "id": "help_reports",
                            "title": "Progress Reports",
                            "description": "weekly report, monthly report"
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
