"""
Command Handlers - Organized Structure
Universal and role-specific command handlers with delegation pattern
"""

from .command_coordinator import CommandCoordinator

# Backward compatibility imports - re-export all command functions
# Common commands (available to all users)
from .common.profile_commands import handle_view_profile, handle_edit_profile, handle_delete_account
from .common.help_command import handle_help
from .common.logout_command import handle_logout
from .common.register_command import handle_register
from .common.stop_command import handle_stop
from .common.switch_role_command import handle_switch_role

# Trainer commands
from .trainer.habits.creation_commands import handle_create_habit, handle_edit_habit, handle_delete_habit
from .trainer.habits.assignment_commands import handle_assign_habits, handle_view_client_habits
from .trainer.habits.unassignment_commands import handle_unassign_habit
from .trainer.habits.reporting_commands import handle_view_habit_progress, handle_export_habit_data
from .trainer.relationships.invitation_commands import handle_invite_client, handle_create_client
from .trainer.relationships.management_commands import handle_view_trainees, handle_remove_trainee

# Client commands
from .client.habits.logging_commands import handle_view_my_habits, handle_log_habits
from .client.habits.progress_commands import handle_view_progress, handle_weekly_report, handle_monthly_report
from .client.relationships.search_commands import handle_search_trainers, handle_view_trainers
from .client.relationships.invitation_commands import handle_invite_trainer, handle_remove_trainer

# Backward compatibility aliases for old function names
# Trainer aliases
handle_invite_trainee = handle_invite_client  # /invite-trainee -> handle_invite_client
handle_create_trainee = handle_create_client  # /create-trainee -> handle_create_client
handle_assign_habit = handle_assign_habits    # /assign-habit -> handle_assign_habits
handle_view_habits = handle_view_client_habits # /view-habits -> handle_view_client_habits
handle_view_trainee_progress = handle_view_habit_progress # /view-trainee-progress -> handle_view_habit_progress
handle_trainee_report = handle_export_habit_data # trainee reports -> handle_export_habit_data

# Client aliases
handle_search_trainer = handle_search_trainers # /search-trainer -> handle_search_trainers

# Main coordinator
__all__ = [
    'CommandCoordinator',
    # Common commands
    'handle_view_profile',
    'handle_edit_profile', 
    'handle_delete_account',
    'handle_help',
    'handle_logout',
    'handle_register',
    'handle_stop',
    'handle_switch_role',
    # Trainer commands
    'handle_create_habit',
    'handle_edit_habit',
    'handle_delete_habit',
    'handle_assign_habits',
    'handle_view_client_habits',
    'handle_view_habit_progress',
    'handle_export_habit_data',
    'handle_invite_client',
    'handle_create_client',
    'handle_view_trainees',
    'handle_remove_trainee',
    # Client commands
    'handle_view_my_habits',
    'handle_log_habits',
    'handle_view_progress',
    'handle_weekly_report',
    'handle_monthly_report',
    'handle_search_trainers',
    'handle_view_trainers',
    'handle_invite_trainer',
    'handle_remove_trainer',
    # Backward compatibility aliases
    'handle_invite_trainee',
    'handle_create_trainee',
    'handle_assign_habit',
    'handle_view_habits',
    'handle_view_trainee_progress',
    'handle_trainee_report',
    'handle_search_trainer'
]
