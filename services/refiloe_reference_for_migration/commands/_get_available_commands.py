"""
 Get Available Commands
Get list of available commands for user type
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _get_available_commands(self, user_type: str) -> str:
    """Get list of available commands for user type"""
    if user_type == 'trainer':
        return (
            "• `/help` - Show all commands\n"
            "• `/profile` - View your profile\n"
            "• `/edit_profile` - Edit your profile\n"
            "• `/clients` - Manage your clients\n"
            "• `/add_client` - Add a new client\n"
            "• `/pending_requests` - View client requests\n"
            "• `/approve_client [name]` - Approve client\n"
            "• `/decline_client [name]` - Decline client\n"
            "• `/habits` - Client habit management\n"
            "• `/setup_habits` - Setup client habits\n"
            "• `/habit_challenges` - Manage habit challenges\n"
            "• `/create_challenge` - Create new challenge\n"
            "• `/habit_analytics` - View habit analytics\n"
            "• `/send_reminders` - Send habit reminders"
        )
    elif user_type == 'client':
        return (
            "• `/help` - Show all commands\n"
            "• `/profile` - View your profile\n"
            "• `/edit_profile` - Edit your profile\n"
            "• `/trainer` - View trainer info\n"
            "• `/invitations` - View trainer invitations\n"
            "• `/accept_invitation [token]` - Accept invitation\n"
            "• `/decline_invitation [token]` - Decline invitation\n"
            "• `/find_trainer` - Search for trainers\n"
            "• `/request_trainer [email/phone]` - Request specific trainer\n"
            "• `/add_trainer [email/phone]` - Add trainer directly\n"
            "• `/habits` - View your habit progress\n"
            "• `/log_habit` - Log today's habits\n"
            "• `/habit_progress` - Detailed progress view\n"
            "• `/habit_streak` - Check your streaks\n"
            "• `/habit_goals` - Manage habit goals\n"
            "• `/habit_challenges` - View available challenges"
        )
    else:
        return (
            "• `/help` - Show all commands\n"
            "• `/registration` - Start registration"
        )
