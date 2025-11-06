"""
Dashboard Commands
Commands for generating dashboard links
"""
from .dashboard_commands import (
    generate_dashboard_link, 
    generate_trainer_browse_dashboard,
    generate_trainer_habits_dashboard,
    generate_trainee_progress_dashboard,
    generate_trainee_habits_dashboard,
    generate_client_habits_dashboard
)

__all__ = [
    'generate_dashboard_link', 
    'generate_trainer_browse_dashboard',
    'generate_trainer_habits_dashboard',
    'generate_trainee_progress_dashboard',
    'generate_trainee_habits_dashboard',
    'generate_client_habits_dashboard'
]