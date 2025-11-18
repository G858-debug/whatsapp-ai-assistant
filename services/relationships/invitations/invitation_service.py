"""
Invitation Service - Main invitation logic
Core invitation service with main invitation logic
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

# Import the managers
from .invitation_manager import InvitationManager
from ..core.relationship_manager import RelationshipManager


class InvitationService:
    """Main invitation logic - delegates to InvitationManager"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize managers
        self.relationship_manager = RelationshipManager(supabase_client)
        self.invitation_manager = InvitationManager(supabase_client, whatsapp_service, self.relationship_manager)
    
    # Delegate all operations to InvitationManager
    def generate_invitation_token(self) -> str:
        """Generate unique invitation token"""
        return self.invitation_manager.generate_invitation_token()
    
    def send_trainer_to_client_invitation(self, trainer_id: str, client_id: str, 
                                         client_phone: str) -> Tuple[bool, str]:
        """Send invitation from trainer to client"""
        return self.invitation_manager.send_trainer_to_client_invitation(trainer_id, client_id, client_phone)
    
    def send_client_to_trainer_invitation(self, client_id: str, trainer_id: str,
                                         trainer_phone: str) -> Tuple[bool, str]:
        """Send invitation from client to trainer"""
        return self.invitation_manager.send_client_to_trainer_invitation(client_id, trainer_id, trainer_phone)
    
    def send_new_client_invitation(self, trainer_id: str, client_data: Dict,
                                   client_phone: str) -> Tuple[bool, str]:
        """Send invitation to new client with prefilled data"""
        return self.invitation_manager.send_new_client_invitation(trainer_id, client_data, client_phone)

    def send_client_fills_invitation(self, trainer_id: str, client_phone: str,
                                     client_name: str, selected_price: Optional[float] = None) -> Tuple[bool, str]:
        """Send invitation to client who will fill their own profile"""
        return self.invitation_manager.send_client_fills_invitation(trainer_id, client_phone, client_name, selected_price)

    def create_relationship(self, trainer_id: str, client_id: str,
                          invited_by: str, invitation_token: str = None) -> Tuple[bool, str]:
        """Create bidirectional trainer-client relationship"""
        return self.invitation_manager.create_relationship(trainer_id, client_id, invited_by, invitation_token)