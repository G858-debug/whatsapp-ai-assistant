"""
Relationship Service - Main relationship logic
Core relationship service with main relationship logic
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

# Import the relationship manager
from .relationship_manager import RelationshipManager


class RelationshipService:
    """Main relationship logic - delegates to RelationshipManager"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize relationship manager
        self.relationship_manager = RelationshipManager(supabase_client)
    
    # Delegate all operations to RelationshipManager
    def get_trainer_clients(self, trainer_id: str, status: str = 'active') -> List[Dict]:
        """Get all clients for a trainer"""
        return self.relationship_manager.get_trainer_clients(trainer_id, status)
    
    def get_client_trainers(self, client_id: str, status: str = 'active') -> List[Dict]:
        """Get all trainers for a client"""
        return self.relationship_manager.get_client_trainers(client_id, status)
    
    def check_relationship_exists(self, trainer_id: str, client_id: str) -> Optional[Dict]:
        """Check if relationship already exists"""
        return self.relationship_manager.check_relationship_exists(trainer_id, client_id)
    
    def check_any_relationship(self, trainer_id: str, client_id: str) -> Optional[Dict]:
        """Check if any relationship exists regardless of status"""
        return self.relationship_manager.check_any_relationship(trainer_id, client_id)
    
    def approve_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Approve pending relationship"""
        return self.relationship_manager.approve_relationship(trainer_id, client_id)
    
    def decline_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Decline pending relationship"""
        return self.relationship_manager.decline_relationship(trainer_id, client_id)
    
    def remove_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Remove existing relationship"""
        return self.relationship_manager.remove_relationship(trainer_id, client_id)
    
    def search_trainers(self, search_term: str, limit: int = 5) -> List[Dict]:
        """Search for trainers by name"""
        return self.relationship_manager.search_trainers(search_term, limit)