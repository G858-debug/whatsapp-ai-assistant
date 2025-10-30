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
        """Get all clients for a trainer"""
        try:
            # Get relationship records
            relationships = self.db.table('trainer_client_list').select('*').eq(
                'trainer_id', trainer_id
            ).eq('connection_status', status).execute()
            
            if not relationships.data:
                return []
            
            # Get client details for each relationship
            clients = []
            for rel in relationships.data:
                client_result = self.db.table('clients').select('*').eq(
                    'client_id', rel['client_id']
                ).execute()
                
                if client_result.data:
                    client_data = client_result.data[0]
                    client_data['relationship'] = rel  # Include relationship info
                    clients.append(client_data)
            
            return clients
            
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
        """Check if relationship already exists"""
        try:
            result = self.db.table('trainer_client_list').select('*').eq(
                'trainer_id', trainer_id
            ).eq('client_id', client_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            log_error(f"Error checking relationship: {str(e)}")
            return None
    
    def approve_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Approve pending relationship"""
        try:
            now = datetime.now(self.sa_tz).isoformat()
            
            # Update trainer_client_list
            self.db.table('trainer_client_list').update({
                'connection_status': 'active',
                'approved_at': now,
                'updated_at': now
            }).eq('trainer_id', trainer_id).eq('client_id', client_id).execute()
            
            # Update client_trainer_list
            self.db.table('client_trainer_list').update({
                'connection_status': 'active',
                'approved_at': now,
                'updated_at': now
            }).eq('client_id', client_id).eq('trainer_id', trainer_id).execute()
            
            log_info(f"Approved relationship: trainer {trainer_id} <-> client {client_id}")
            return True, "Relationship approved"
            
        except Exception as e:
            log_error(f"Error approving relationship: {str(e)}")
            return False, str(e)
    
    def decline_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Decline pending relationship"""
        try:
            now = datetime.now(self.sa_tz).isoformat()
            
            # Update both tables to declined
            self.db.table('trainer_client_list').update({
                'connection_status': 'declined',
                'updated_at': now
            }).eq('trainer_id', trainer_id).eq('client_id', client_id).execute()
            
            self.db.table('client_trainer_list').update({
                'connection_status': 'declined',
                'updated_at': now
            }).eq('client_id', client_id).eq('trainer_id', trainer_id).execute()
            
            log_info(f"Declined relationship: trainer {trainer_id} <-> client {client_id}")
            return True, "Relationship declined"
            
        except Exception as e:
            log_error(f"Error declining relationship: {str(e)}")
            return False, str(e)
    
    def remove_relationship(self, trainer_id: str, client_id: str) -> Tuple[bool, str]:
        """Remove existing relationship"""
        try:
            # Delete from both tables
            self.db.table('trainer_client_list').delete().eq(
                'trainer_id', trainer_id
            ).eq('client_id', client_id).execute()
            
            self.db.table('client_trainer_list').delete().eq(
                'client_id', client_id
            ).eq('trainer_id', trainer_id).execute()
            
            log_info(f"Removed relationship: trainer {trainer_id} <-> client {client_id}")
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