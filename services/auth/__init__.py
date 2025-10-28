"""
Authentication Services - Enhanced Structure
User authentication, registration, and task management with organized components
"""

# Main services (backward compatibility)
from .authentication_service import AuthenticationService
from .registration_service import RegistrationService
from .task_service import TaskService

# Core components
from .core import LoginStatusManager, UserManager, RoleManager

# Registration components
from .registration import DataSaver, FieldManager, ValidationService

# Task components
from .tasks import TaskManager, TaskTracker

__all__ = [
    'AuthenticationService',
    'RegistrationService', 
    'TaskService',
    'LoginStatusManager',
    'UserManager',
    'RoleManager',
    'DataSaver',
    'FieldManager',
    'ValidationService',
    'TaskManager',
    'TaskTracker'
]
