"""
Invitation Service - Main Entry Point
Main coordinator for invitation management with delegation to organized components
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

# Import organized components
from .invitations.invitation_service import InvitationService as CoreInvitationService


class InvitationService:
    """
    Main invitation service entry point.
    Delegates to organized components while maintaining backward compatibility.
    """
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize core invitation service
        self.core_invitation_service = CoreInvitationService(supabase_client, whatsapp_service)
    
    # Delegate to CoreInvitationService
    def generate_invitation_token(self) -> str:
        """Generate unique invitation token"""
        return self.core_invitation_service.generate_invitation_token()
    
    def send_trainer_to_client_invitation(self, trainer_id: str, client_id: str, 
                                         client_phone: str) -> Tuple[bool, str]:
        """Send invitation from trainer to client"""
        return self.core_invitation_service.send_trainer_to_client_invitation(trainer_id, client_id, client_phone)
    
    def send_client_to_trainer_invitation(self, client_id: str, trainer_id: str,
                                         trainer_phone: str) -> Tuple[bool, str]:
        """Send invitation from client to trainer"""
        return self.core_invitation_service.send_client_to_trainer_invitation(client_id, trainer_id, trainer_phone)
    
    def send_new_client_invitation(self, trainer_id: str, client_data: Dict, 
                                   client_phone: str) -> Tuple[bool, str]:
        """Send invitation to new client with prefilled data"""
        return self.core_invitation_service.send_new_client_invitation(trainer_id, client_data, client_phone)
    
    def create_relationship(self, trainer_id: str, client_id: str, 
                          invited_by: str, invitation_token: str = None) -> Tuple[bool, str]:
        """Create bidirectional trainer-client relationship"""
        return self.core_invitation_service.create_relationship(trainer_id, client_id, invited_by, invitation_token)
