"""
Command Handlers - Organized Structure
Universal and role-specific command handlers with delegation pattern
"""

# Backward compatibility imports - re-export all command functions
# Common commands (available to all users)
from .common.profile_commands import handle_view_profile, handle_edit_profile, handle_delete_account
from .common.help_command import handle_help
from .common.stop_command import handle_stop

# Trainer commands - import only if needed
try:
    from .trainer.habits.creation_commands import handle_create_habit, handle_edit_habit, handle_delete_habit
    from .trainer.habits.assignment_commands import handle_assign_habits, handle_view_client_habits
    from .trainer.habits.unassignment_commands import handle_unassign_habit
    from .trainer.habits.reporting_commands import handle_view_habit_progress, handle_export_habit_data
    from .trainer.relationships.invitation_commands import handle_invite_client, handle_create_client
    from .trainer.relationships.management_commands import handle_view_trainees, handle_remove_trainee
    _trainer_commands_available = True
except ImportError as e:
    _trainer_commands_available = False
    # Provide dummy functions if imports fail
    def _not_available(*args, **kwargs):
        return {'success': False, 'response': 'Command not available', 'handler': 'command_not_available'}
    handle_create_habit = handle_edit_habit = handle_delete_habit = _not_available
    handle_assign_habits = handle_view_client_habits = _not_available
    handle_unassign_habit = _not_available
    handle_view_habit_progress = handle_export_habit_data = _not_available
    handle_invite_client = handle_create_client = _not_available
    handle_view_trainees = handle_remove_trainee = _not_available

# Client commands - import only if needed
try:
    from .client.habits.logging_commands import handle_view_my_habits, handle_log_habits
    from .client.habits.progress_commands import handle_view_progress, handle_weekly_report, handle_monthly_report
    from .client.relationships.search_commands import handle_search_trainers, handle_view_trainers
    from .client.relationships.invitation_commands import handle_invite_trainer, handle_remove_trainer
    _client_commands_available = True
except ImportError as e:
    _client_commands_available = False
    # Provide dummy functions if imports fail
    handle_view_my_habits = handle_log_habits = _not_available
    handle_view_progress = handle_weekly_report = handle_monthly_report = _not_available
    handle_search_trainers = handle_view_trainers = _not_available
    handle_invite_trainer = handle_remove_trainer = _not_available

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

# Exported functions
__all__ = [
    # Common commands
    'handle_view_profile',
    'handle_edit_profile', 
    'handle_delete_account',
    'handle_help',
    'handle_stop',
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
