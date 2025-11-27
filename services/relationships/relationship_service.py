"""
Relationship Service - Main Entry Point
Main coordinator for relationship management with delegation to core services
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

# Import core services according to the plan
from .core.relationship_service import RelationshipService as CoreRelationshipService
from .invitations.invitation_service import InvitationService as CoreInvitationService


class RelationshipService:
    """
    Main relationship service entry point.
    Delegates to core services while maintaining backward compatibility.
    """
    
    def __init__(self, supabase_client, whatsapp_service=None):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize core services
        self.core_relationship_service = CoreRelationshipService(supabase_client)
        if whatsapp_service:
            self.core_invitation_service = CoreInvitationService(supabase_client, whatsapp_service)
    
    # Delegate to CoreRelationshipService
    def get_trainer_clients(self, trainer_id: str, status: str = 'active') -> List[Dict]:
        """Get all clients for a trainer"""
        return self.core_relationship_service.get_trainer_clients(trainer_id, status)
    
    def get_client_trainers(self, client_id: str, status: str = 'active') -> List[Dict]:
        """Get all trainers for a client"""
        return self.core_relationship_service.get_client_trainers(client_id, status)
    
    def check_relationship_exists(self, trainer_id: str, client_id: str) -> Optional[Dict]:
        """Check if relationship already exists"""
        return self.core_relationship_service.check_relationship_exists(trainer_id, client_id)
    
    def check_any_relationship(self, trainer_id: str, client_id: str) -> Optional[Dict]:
        """Check if any relationship exists regardless of status"""
        return self.core_relationship_service.check_any_relationship(trainer_id, client_id)
    
    def approve_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Approve pending relationship"""
        return self.core_relationship_service.approve_relationship(trainer_id, client_id)
    
    def decline_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Decline pending relationship"""
        return self.core_relationship_service.decline_relationship(trainer_id, client_id)
    
    def remove_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Remove existing relationship"""
        return self.core_relationship_service.remove_relationship(trainer_id, client_id)
    
    def search_trainers(self, search_term: str, limit: int = 5) -> List[Dict]:
        """Search for trainers by name"""
        return self.core_relationship_service.search_trainers(search_term, limit)
    
    # Delegate to CoreInvitationService (if available)
    def create_relationship(self, trainer_id: str, client_id: str, 
                          invited_by: str, invitation_token: str = None) -> Tuple[bool, str]:
        """Create bidirectional trainer-client relationship"""
        if hasattr(self, 'core_invitation_service'):
            return self.core_invitation_service.create_relationship(trainer_id, client_id, invited_by, invitation_token)
        else:
            log_error("CoreInvitationService not available - WhatsApp service required")
            return False, "Invitation service not available"
    
    def generate_invitation_token(self) -> str:
        """Generate unique invitation token"""
        if hasattr(self, 'core_invitation_service'):
            return self.core_invitation_service.generate_invitation_token()
        else:
            import secrets
            return secrets.token_urlsafe(16)
    
    def send_trainer_to_client_invitation(self, trainer_id: str, client_id: str, 
                                         client_phone: str) -> Tuple[bool, str]:
        """Send invitation from trainer to client"""
        if hasattr(self, 'core_invitation_service'):
            return self.core_invitation_service.send_trainer_to_client_invitation(trainer_id, client_id, client_phone)
        else:
            log_error("CoreInvitationService not available - WhatsApp service required")
            return False, "Invitation service not available"
    
    def send_client_to_trainer_invitation(self, client_id: str, trainer_id: str,
                                         trainer_phone: str) -> Tuple[bool, str]:
        """Send invitation from client to trainer"""
        if hasattr(self, 'core_invitation_service'):
            return self.core_invitation_service.send_client_to_trainer_invitation(client_id, trainer_id, trainer_phone)
        else:
            log_error("CoreInvitationService not available - WhatsApp service required")
            return False, "Invitation service not available"
    
    def send_new_client_invitation(self, trainer_id: str, client_data: Dict, 
                                   client_phone: str) -> Tuple[bool, str]:
        """Send invitation to new client with prefilled data"""
        if hasattr(self, 'core_invitation_service'):
            return self.core_invitation_service.send_new_client_invitation(trainer_id, client_data, client_phone)
        else:
            log_error("CoreInvitationService not available - WhatsApp service required")
            return False, "Invitation service not available"
