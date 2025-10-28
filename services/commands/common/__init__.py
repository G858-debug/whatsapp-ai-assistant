"""
Common Commands Package
Handles commands available to all users
"""

from .profile_commands import handle_edit_profile, handle_view_profile
from .help_command import handle_help
from .logout_command import handle_logout
from .register_command import handle_register
from .stop_command import handle_stop
from .switch_role_command import handle_switch_role

__all__ = [
    'handle_edit_profile',
    'handle_view_profile', 
    'handle_help',
    'handle_logout',
    'handle_register',
    'handle_stop',
    'handle_switch_role'
]