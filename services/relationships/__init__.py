"""
Relationship Services - Enhanced Structure
Handles trainer-client relationships, invitations, and connections with organized components
"""

# Main services (backward compatibility)
from .relationship_service import RelationshipService
from .invitation_service import InvitationService

# Core components
from .core import RelationshipService as CoreRelationshipService, RelationshipManager
from .invitations import InvitationService as CoreInvitationService, InvitationManager

__all__ = [
    'RelationshipService',
    'InvitationService',
    'CoreRelationshipService',
    'RelationshipManager',
    'CoreInvitationService',
    'InvitationManager'
]
