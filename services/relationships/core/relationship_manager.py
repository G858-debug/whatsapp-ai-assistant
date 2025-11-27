"""
Relationship Manager - Relationship operations
Handles core relationship operations and management
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pytz
from utils.logger import log_info, log_error


class RelationshipManager:
    """Manages core relationship operations"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def get_trainer_clients(self, trainer_id: str, status: str = 'active') -> List[Dict]:
        """Get all clients for a trainer using relationship table"""
        try:
            # Get client IDs from trainer_client_list relationship table
            relationships = self.db.table('trainer_client_list')\
                .select('client_id')\
                .eq('trainer_id', trainer_id)\
                .eq('connection_status', status)\
                .execute()

            if not relationships.data:
                return []

            # Extract client_ids
            client_ids = [rel['client_id'] for rel in relationships.data]

            # Fetch full client data
            clients = self.db.table('clients')\
                .select('*')\
                .in_('client_id', client_ids)\
                .order('name')\
                .execute()

            return clients.data if clients.data else []

        except Exception as e:
            log_error(f"Error getting trainer clients: {str(e)}")
            return []
    
    def get_client_trainers(self, client_id: str, status: str = 'active') -> List[Dict]:
        """Get all trainers for a client"""
        try:
            # Get relationship records
            relationships = self.db.table('client_trainer_list').select('*').eq(
                'client_id', client_id
            ).eq('connection_status', status).execute()
            
            if not relationships.data:
                return []
            
            # Get trainer details for each relationship
            trainers = []
            for rel in relationships.data:
                trainer_result = self.db.table('trainers').select('*').eq(
                    'trainer_id', rel['trainer_id']
                ).execute()
                
                if trainer_result.data:
                    trainer_data = trainer_result.data[0]
                    trainer_data['relationship'] = rel  # Include relationship info
                    trainers.append(trainer_data)
            
            return trainers
            
        except Exception as e:
            log_error(f"Error getting client trainers: {str(e)}")
            return []
    
    def check_relationship_exists(self, trainer_id: str, client_id: str) -> Optional[Dict]:
        """Check if active or pending relationship already exists (case-insensitive)"""
        try:
            result = self.db.table('trainer_client_list').select('*').ilike(
                'trainer_id', trainer_id
            ).ilike('client_id', client_id).in_(
                'connection_status', ['active', 'pending']
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            log_error(f"Error checking relationship: {str(e)}")
            return None
    
    def check_any_relationship(self, trainer_id: str, client_id: str) -> Optional[Dict]:
        """Check if any relationship exists regardless of status (case-insensitive)"""
        try:
            result = self.db.table('trainer_client_list').select('*').ilike(
                'trainer_id', trainer_id
            ).ilike('client_id', client_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            log_error(f"Error checking relationship: {str(e)}")
            return None
    
    def approve_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Approve pending relationship"""
        try:
            # Check if relationship exists and get exact IDs
            relationship = self.check_relationship_exists(trainer_id, client_id)
            if not relationship:
                return False, "Relationship not found"
            
            # Get exact IDs from database
            actual_trainer_id = relationship.get('trainer_id')
            actual_client_id = relationship.get('client_id')
            
            now = datetime.now(self.sa_tz).isoformat()
            
            # Update trainer_client_list
            self.db.table('trainer_client_list').update({
                'connection_status': 'active',
                'approved_at': now,
                'updated_at': now
            }).eq('trainer_id', actual_trainer_id).eq('client_id', actual_client_id).execute()
            
            # Update client_trainer_list
            self.db.table('client_trainer_list').update({
                'connection_status': 'active',
                'approved_at': now,
                'updated_at': now
            }).eq('client_id', actual_client_id).eq('trainer_id', actual_trainer_id).execute()
            
            # Update any pending invitations to accepted status
            self._update_invitation_status(actual_trainer_id, actual_client_id, 'accepted')
            
            log_info(f"Approved relationship: trainer {actual_trainer_id} <-> client {actual_client_id}")
            return True, "Relationship approved"
            
        except Exception as e:
            log_error(f"Error approving relationship: {str(e)}")
            return False, str(e)
    
    def decline_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Decline pending relationship"""
        try:
            # Check if relationship exists and get exact IDs
            relationship = self.check_relationship_exists(trainer_id, client_id)
            if not relationship:
                return False, "Relationship not found"
            
            # Get exact IDs from database
            actual_trainer_id = relationship.get('trainer_id')
            actual_client_id = relationship.get('client_id')
            
            now = datetime.now(self.sa_tz).isoformat()
            
            # Update both tables to declined
            self.db.table('trainer_client_list').update({
                'connection_status': 'declined',
                'updated_at': now
            }).eq('trainer_id', actual_trainer_id).eq('client_id', actual_client_id).execute()
            
            self.db.table('client_trainer_list').update({
                'connection_status': 'declined',
                'updated_at': now
            }).eq('client_id', actual_client_id).eq('trainer_id', actual_trainer_id).execute()
            
            # Update any pending invitations to declined status
            self._update_invitation_status(actual_trainer_id, actual_client_id, 'declined')
            
            log_info(f"Declined relationship: trainer {actual_trainer_id} <-> client {actual_client_id}")
            return True, "Relationship declined"
            
        except Exception as e:
            log_error(f"Error declining relationship: {str(e)}")
            return False, str(e)
    
    def remove_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Remove existing relationship"""
        try:
            # Check if relationship exists and get exact IDs
            relationship = self.check_relationship_exists(trainer_id, client_id)
            if not relationship:
                return False, "Relationship not found"
            
            # Get exact IDs from database
            actual_trainer_id = relationship.get('trainer_id')
            actual_client_id = relationship.get('client_id')
            
            # Delete from both tables
            self.db.table('trainer_client_list').delete().eq(
                'trainer_id', actual_trainer_id
            ).eq('client_id', actual_client_id).execute()
            
            self.db.table('client_trainer_list').delete().eq(
                'client_id', actual_client_id
            ).eq('trainer_id', actual_trainer_id).execute()
            
            log_info(f"Removed relationship: trainer {actual_trainer_id} <-> client {actual_client_id}")
            return True, "Relationship removed"
            
        except Exception as e:
            log_error(f"Error removing relationship: {str(e)}")
            return False, str(e)
    
    def search_trainers(self, search_term: str, limit: int = 5) -> List[Dict]:
        """Search for trainers by name"""
        try:
            # Search in trainers table
            result = self.db.table('trainers').select(
                'trainer_id, name, first_name, last_name, specialization, experience_years, city'
            ).ilike('name', f'%{search_term}%').limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error searching trainers: {str(e)}")
            return []
    
    def _update_invitation_status(self, trainer_id: str, client_id: str, status: str):
        """Update invitation status in client_invitations table"""
        try:
            # Get client phone number
            client_result = self.db.table('clients').select('whatsapp').eq(
                'client_id', client_id
            ).execute()
            
            if not client_result.data:
                log_error(f"Client {client_id} not found when updating invitation status")
                return
            
            client_phone = client_result.data[0]['whatsapp']
            
            # Get trainer UUID from string ID for client_invitations table
            trainer_result = self.db.table('trainers').select('id').eq(
                'trainer_id', trainer_id
            ).execute()
            
            if not trainer_result.data:
                log_error(f"Trainer {trainer_id} not found when updating invitation status")
                return
            
            trainer_uuid = trainer_result.data[0]['id']
            
            # Update any pending invitations between this trainer and client
            self.db.table('client_invitations').update({
                'status': status,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('trainer_id', trainer_uuid).eq('client_phone', client_phone).eq(
                'status', 'pending'
            ).execute()
            
            log_info(f"Updated invitation status to {status} for trainer {trainer_id} and client {client_id}")
            
        except Exception as e:
            log_error(f"Error updating invitation status: {str(e)}")