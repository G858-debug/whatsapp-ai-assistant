"""
Relationship Management Flows Package
Handles trainer-client relationship flows
"""

from .trainer_flows.trainer_relationship_flows import TrainerRelationshipFlows
from .client_flows.client_relationship_flows import ClientRelationshipFlows

__all__ = [
    'TrainerRelationshipFlows',
    'ClientRelationshipFlows'
]