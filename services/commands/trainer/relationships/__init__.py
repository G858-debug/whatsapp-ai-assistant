"""
Trainer Relationship Commands Package
Handles trainer commands for relationship management
"""

from .invitation_commands import handle_invite_client, handle_create_client
from .management_commands import handle_view_trainees, handle_remove_trainee

__all__ = [
    'handle_invite_client',
    'handle_create_client',
    'handle_view_trainees',
    'handle_remove_trainee'
]