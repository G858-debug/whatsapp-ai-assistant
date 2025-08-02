from typing import Dict, Optional, List
from datetime import datetime
import pytz

from utils.logger import log_error, log_info

class TrainerModel:
    """Handle all trainer-related database operations"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def get_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get trainer by phone number"""
        try:
            result = self.db.table('trainers').select('*').eq(
                'whatsapp', phone_number
            ).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            log_error(f"Error getting trainer by phone: {str(e)}")
            return None
    
    def get_by_id(self, trainer_id: str) -> Optional[Dict]:
        """Get trainer by ID"""
        try:
            result = self.db.table('trainers').select('*').eq(
                'id', trainer_id
            ).single().execute()
            
            return result.data
            
        except Exception as e:
            log_error(f"Error getting trainer by ID: {str(e)}")
            return None
    
    def create_trainer(self, trainer_data: Dict) -> Dict:
        """Create a new trainer"""
        try:
            # Validate required fields
            required = ['name', 'whatsapp', 'email']
            for field in required:
                if field not in trainer_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Set defaults
            trainer_data.setdefault('status', 'active')
            trainer_data.setdefault('pricing_per_session', self.config.DEFAULT_SESSION_PRICE)
            trainer_data['created_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table('trainers').insert(trainer_data).execute()
            
            if result.data:
                log_info(f"Trainer created: {trainer_data['name']}")
                return {
                    'success': True,
                    'trainer_id': result.data[0]['id']
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create trainer'
                }
                
        except Exception as e:
            log_error(f"Error creating trainer: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_trainer(self, trainer_id: str, update_data: Dict) -> Dict:
        """Update trainer information"""
        try:
            update_data['updated_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table('trainers').update(update_data).eq(
                'id', trainer_id
            ).execute()
            
            if result.data:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Trainer not found'}
                
        except Exception as e:
            log_error(f"Error updating trainer: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_trainer_stats(self, trainer_id: str) -> Dict:
        """Get trainer statistics"""
        try:
            # Get client count
            clients = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').execute()
            
            # Get booking count for this month
            now = datetime.now(self.sa_tz)
            month_start = now.replace(day=1, hour=0, minute=0, second=0)
            
            bookings = self.db.table('bookings').select('id, price, status').eq(
                'trainer_id', trainer_id
            ).gte('session_datetime', month_start.isoformat()).execute()
            
            # Calculate stats
            total_clients = len(clients.data)
            total_bookings = len(bookings.data)
            completed_bookings = sum(1 for b in bookings.data if b['status'] == 'completed')
            revenue = sum(b['price'] for b in bookings.data if b['status'] in ['completed', 'scheduled'])
            
            return {
                'total_clients': total_clients,
                'monthly_bookings': total_bookings,
                'completed_sessions': completed_bookings,
                'monthly_revenue': revenue
            }
            
        except Exception as e:
            log_error(f"Error getting trainer stats: {str(e)}")
            return {
                'total_clients': 0,
                'monthly_bookings': 0,
                'completed_sessions': 0,
                'monthly_revenue': 0
            }
