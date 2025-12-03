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
            # Trainer - interactive list
            help_msg = (
                "📚 *Refiloe Help - Trainer*\n\n"
                "Select a category below to see available commands:\n\n"
                "💡 *Tip:* You can also just tell me what you want to do!"
            )
            
            sections = [
                {
                    "title": "🔧 System & Profile",
                    "rows": [
                        {
                            "id": "/view-profile",
                            "title": "👤 View Profile",
                            "description": "View your trainer profile"
                        },
                        {
                            "id": "/edit-profile",
                            "title": "✏️ Edit Profile",
                            "description": "Update your information"
                        },
                        {
                            "id": "/logout",
                            "title": "🚪 Logout",
                            "description": "Logout from your account"
                        },
                        {
                            "id": "/stop",
                            "title": "⛔ Stop Task",
                            "description": "Cancel any stuck tasks"
                        }
                    ]
                },
                {
                    "title": "👥 Client Management",
                    "rows": [
                        {
                            "id": "/invite-trainee",
                            "title": "📧 Invite Client",
                            "description": "Invite a new client"
                        },
                        {
                            "id": "/create-trainee",
                            "title": "➕ Create Client",
                            "description": "Create & invite client"
                        },
                        {
                            "id": "/view-trainees",
                            "title": "📋 View Clients",
                            "description": "See all your clients"
                        },
                        {
                            "id": "/remove-trainee",
                            "title": "❌ Remove Client",
                            "description": "Remove a client"
                        }
                    ]
                },
                {
                    "title": "🎯 Habit Management",
                    "rows": [
                        {
                            "id": "/create-habit",
                            "title": "➕ Create Habit",
                            "description": "Create new fitness habit"
                        },
                        {
                            "id": "/assign-habit",
                            "title": "📌 Assign Habit",
                            "description": "Assign habit to clients"
                        },
                        {
                            "id": "/view-habits",
                            "title": "📋 View Habits",
                            "description": "See all created habits"
                        },
                        {
                            "id": "/edit-habit",
                            "title": "✏️ Edit Habit",
                            "description": "Modify habit details"
                        }
                    ]
                },
                {
                    "title": "📊 Progress & Reports",
                    "rows": [
                        {
                            "id": "/view-trainee-progress",
                            "title": "📈 Client Progress",
                            "description": "View client's progress"
                        },
                        {
                            "id": "/trainee-weekly-report",
                            "title": "📅 Weekly Report",
                            "description": "Get weekly report"
                        },
                        {
                            "id": "/trainer-dashboard",
                            "title": "📊 Dashboard",
                            "description": "Main trainer dashboard"
                        }
                    ]
                }
            ]
            
            whatsapp.send_list_message(
                phone=phone,
                body=help_msg,
                button_text="View Commands",
                sections=sections
            )
            
        else:  # client
            # Client - interactive list
            help_msg = (
                "📚 *Refiloe Help - Client*\n\n"
                "Select a category below to see available commands:\n\n"
                "💡 *Tip:* You can also just tell me what you want to do!"
            )
            
            sections = [
                {
                    "title": "🔧 System & Profile",
                    "rows": [
                        {
                            "id": "/view-profile",
                            "title": "👤 View Profile",
                            "description": "View your client profile"
                        },
                        {
                            "id": "/edit-profile",
                            "title": "✏️ Edit Profile",
                            "description": "Update your information"
                        },
                        {
                            "id": "/stop",
                            "title": "⛔ Stop Task",
                            "description": "Cancel any stuck tasks"
                        }
                    ]
                },
                {
                    "title": "👨‍🏫 Trainer Management",
                    "rows": [
                        {
                            "id": "/search-trainer",
                            "title": "🔍 Search Trainers",
                            "description": "Find trainers near you"
                        },
                        {
                            "id": "/invite-trainer",
                            "title": "📧 Invite Trainer",
                            "description": "Invite a trainer"
                        },
                        {
                            "id": "/view-trainers",
                            "title": "📋 View Trainers",
                            "description": "See your trainers"
                        },
                        {
                            "id": "/remove-trainer",
                            "title": "❌ Remove Trainer",
                            "description": "Remove a trainer"
                        }
                    ]
                },
                {
                    "title": "🎯 Habit Tracking",
                    "rows": [
                        {
                            "id": "/view-my-habits",
                            "title": "📋 My Habits",
                            "description": "View assigned habits"
                        },
                        {
                            "id": "/log-habits",
                            "title": "✅ Log Habits",
                            "description": "Log today's habits"
                        },
                        {
                            "id": "/view-progress",
                            "title": "📈 View Progress",
                            "description": "See your progress"
                        }
                    ]
                },
                {
                    "title": "📊 Reports & Reminders",
                    "rows": [
                        {
                            "id": "/weekly-report",
                            "title": "📅 Weekly Report",
                            "description": "Get weekly report"
                        },
                        {
                            "id": "/monthly-report",
                            "title": "📆 Monthly Report",
                            "description": "Get monthly report"
                        },
                        {
                            "id": "/reminder-settings",
                            "title": "⏰ Reminder Settings",
                            "description": "Configure reminders"
                        }
                    ]
                }
            ]
            
            whatsapp.send_list_message(
                phone=phone,
                body=help_msg,
                button_text="View Commands",
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