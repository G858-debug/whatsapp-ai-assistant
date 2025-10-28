"""
Client Relationship Commands Package
Handles client commands for relationship management
"""

from .search_commands import handle_search_trainers, handle_view_trainers
from .invitation_commands import handle_invite_trainer, handle_remove_trainer

__all__ = [
    'handle_search_trainers',
    'handle_view_trainers',
    'handle_invite_trainer',
    'handle_remove_trainer'
]