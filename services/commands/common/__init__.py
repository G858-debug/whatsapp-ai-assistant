"""
Common Commands Package
Handles commands available to all users
"""

from .profile_commands import handle_edit_profile, handle_view_profile, handle_delete_account
from .help_command import handle_help
from .stop_command import handle_stop
# Note: logout, register, and switch_role are handled elsewhere

__all__ = [
    'handle_edit_profile',
    'handle_view_profile',
    'handle_delete_account',
    'handle_help',
    'handle_stop'
]