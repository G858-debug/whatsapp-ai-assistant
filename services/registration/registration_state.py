"""Registration state management for trainers and clients"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class RegistrationStateManager:
    """Manages registration flow state"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Registration steps
        self.TRAINER_STEPS = [
            'name', 'business_name', 'email', 'specialization', 
            'experience', 'location', 'pricing'
        ]
        
        self.CLIENT_STEPS = [
            'name', 'email', 'fitness_goals', 'experience_level',
            'health_conditions', 'availability'
        ]
    
    def get_registration_state(self, phone: str) -> Optional[Dict]:
        """Get current registration state"""
        try:
            result = self.db.table('registration_states').select('*').eq(
                'phone_number', phone
            ).eq('completed', False).single().execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            log_error(f"Error getting registration state: {str(e)}")
            return None
    
    def create_registration_state(self, phone: str, user_type: str) -> Dict:
        """Create new registration state"""
        try:
            state_data = {
                'phone_number': phone,
                'user_type': user_type,
                'current_step': 0,
                'data': {},
                'completed': False,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('registration_states').insert(
                state_data
            ).execute()
            
            return result.data[0] if result.data else state_data
            
        except Exception as e:
            log_error(f"Error creating registration state: {str(e)}")
            return {}
    
    def update_registration_state(self, phone: str, step: int, 
                                 data: Dict, completed: bool = False) -> bool:
        """Update registration state"""
        try:
            update_data = {
                'current_step': step,
                'data': data,
                'completed': completed,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if completed:
                update_data['completed_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table('registration_states').update(
                update_data
            ).eq('phone_number', phone).eq('completed', False).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating registration state: {str(e)}")
            return False
    
    def complete_registration(self, phone: str, user_type: str) -> bool:
        """Mark registration as completed"""
        try:
            update_data = {
                'completed': True,
                'completed_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('registration_states').update(
                update_data
            ).eq('phone_number', phone).eq('user_type', user_type).eq('completed', False).execute()
            
            if result.data:
                log_info(f"Marked registration as complete for {phone} ({user_type})")
                return True
            else:
                log_warning(f"No registration state found to complete for {phone}")
                return False
            
        except Exception as e:
            log_error(f"Error completing registration state: {str(e)}")
            return False
    
    def get_progress(self, phone: str, user_type: str) -> tuple:
        """Get registration progress"""
        state = self.get_registration_state(phone)
        if not state:
            return 0, 0
        
        total_steps = len(self.TRAINER_STEPS if user_type == 'trainer' else self.CLIENT_STEPS)
        current_step = state.get('current_step', 0)
        
        return current_step, total_steps