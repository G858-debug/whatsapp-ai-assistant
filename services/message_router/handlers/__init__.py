"""
Message Router Handlers Package
Contains all message handling logic split by responsibility
"""

from .buttons.button_handler import ButtonHandler
from .universal_command_handler import UniversalCommandHandler
from .new_user_handler import NewUserHandler
# from .login_handler import LoginHandler  # Not used
from .logged_in_user_handler import LoggedInUserHandler
# RoleCommandHandler is now in commands/ subdirectory, imported directly where needed
from .task_handler import TaskHandler
from .ai_intent_handler import AIIntentHandler

__all__ = [
    'ButtonHandler',
    'UniversalCommandHandler', 
    'NewUserHandler',
    # 'LoginHandler',
    'LoggedInUserHandler',
    # 'RoleCommandHandler',  # Removed - use commands.role_command_handler.RoleCommandHandler
    'TaskHandler',
    'AIIntentHandler'
]