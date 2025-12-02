"""
Flows Package - Refactored
Handles multi-step conversation flows for user interactions
"""

# Import main flow handlers for backward compatibility
from .profile.profile_flow import ProfileFlowHandler

# Import new relationship flows
from .relationships.trainer_flows.trainer_relationship_flows import TrainerRelationshipFlows
from .relationships.client_flows.client_relationship_flows import ClientRelationshipFlows

# Import new habit flows
from .habits.trainer_flows.trainer_habit_flows import TrainerHabitFlows
from .habits.client_flows.client_habit_flows import ClientHabitFlows

__all__ = [
    'ProfileFlowHandler',
    'TrainerRelationshipFlows',
    'ClientRelationshipFlows',
    'TrainerHabitFlows',
    'ClientHabitFlows'
]