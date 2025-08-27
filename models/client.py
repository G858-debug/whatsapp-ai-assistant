from typing import Dict, Optional, List
from datetime import datetime
import pytz

from utils.logger import log_error, log_info

class ClientModel:
    """Handle all client-related database operations"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def get_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get client by phone number with trainer info"""
        try:
            result = self.db.table('clients').select(
                '*, trainers(*)'
            ).eq('whatsapp', phone_number).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            log_error(f"Error getting client by phone: {str(e)}")
            return None
    
    def get_by_id(self, client_id: str) -> Optional[Dict]:
        """Get client by ID"""
        try:
            result = self.db.table('clients').select(
                '*, trainers(*)'
            ).eq('id', client_id).single().execute()
            
            return result.data
            
        except Exception as e:
            log_error(f"Error getting client by ID: {str(e)}")
            return None
    
    def add_client(self, trainer_id: str, client_details: Dict) -> Dict:
        """Add a new client"""
        try:
            # Validate required fields
            if not client_details.get('name') or not client_details.get('phone'):
                return {
                    'success': False,
                    'error': 'Name and phone number are required'
                }
            
            # Get package details
            package = client_details.get('package', 'single')
            sessions = self.config.PACKAGE_SESSIONS.get(package, 1)
            
            # Prepare client record
            client_data = {
                'trainer_id': trainer_id,
                'name': client_details['name'],
                'whatsapp': client_details['phone'],
                'email': client_details.get('email'),
                'sessions_remaining': sessions,
                'package_type': package,
                'status': 'active',
                'custom_price_per_session': client_details.get('price'),  # ADD THIS LINE
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Check if client already exists
            existing = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).eq('whatsapp', client_details['phone']).execute()
            
            if existing.data:
                return {
                    'success': False,
                    'error': 'Client with this phone number already exists'
                }
            
            # Insert client
            result = self.db.table('clients').insert(client_data).execute()
            
            if result.data:
                log_info(f"Client added: {client_details['name']} for trainer {trainer_id}")
                return {
                    'success': True,
                    'client_id': result.data[0]['id'],
                    'sessions': sessions
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to add client'
                }
                
        except Exception as e:
            log_error(f"Error adding client: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_trainer_clients(self, trainer_id: str, status: str = 'active') -> List[Dict]:
        """Get all clients for a trainer"""
        try:
            query = self.db.table('clients').select('*').eq(
                'trainer_id', trainer_id
            )
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('name').execute()
            return result.data
            
        except Exception as e:
            log_error(f"Error getting trainer clients: {str(e)}")
            return []
    
    def update_client(self, client_id: str, update_data: Dict) -> Dict:
        """Update client information"""
        try:
            update_data['updated_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table('clients').update(update_data).eq(
                'id', client_id
            ).execute()
            
            if result.data:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Client not found'}
                
        except Exception as e:
            log_error(f"Error updating client: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def add_sessions(self, client_id: str, sessions_to_add: int) -> Dict:
        """Add sessions to a client's balance"""
        try:
            # Get current sessions
            client = self.get_by_id(client_id)
            if not client:
                return {'success': False, 'error': 'Client not found'}
            
            new_balance = client['sessions_remaining'] + sessions_to_add
            
            result = self.db.table('clients').update({
                'sessions_remaining': new_balance,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', client_id).execute()
            
            if result.data:
                log_info(f"Added {sessions_to_add} sessions to client {client_id}")
                return {'success': True, 'new_balance': new_balance}
            else:
                return {'success': False, 'error': 'Failed to update sessions'}
                
        except Exception as e:
            log_error(f"Error adding sessions: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_clients_needing_reminders(self, days_inactive: int = 7) -> List[Dict]:
        """Get clients who haven't had sessions in X days"""
        try:
            cutoff_date = (datetime.now(self.sa_tz) - timedelta(days=days_inactive)).isoformat()
            
            result = self.db.table('clients').select(
                '*, trainers(*)'
            ).eq('status', 'active').or_(
                f"last_session_date.lt.{cutoff_date},last_session_date.is.null"
            ).execute()
            
            return result.data
            
        except Exception as e:
            log_error(f"Error getting clients needing reminders: {str(e)}")
            return []
