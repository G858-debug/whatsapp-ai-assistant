"""Registration state management for multi-step flows"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info

class RegistrationStateManager:
    """Manages registration session state"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.SESSION_TIMEOUT_MINUTES = 90  # 90 minutes timeout
        self.registration_state = {}  # In-memory state cache for recovery
    
    def create_session(self, phone: str, user_type: str, initial_step: str = 'name') -> str:
        """Create a new registration session"""
        try:
            # Expire any existing sessions for this phone
            self.db.table('registration_sessions').update({
                'status': 'expired'
            }).eq('phone', phone).eq('status', 'active').execute()
            
            # Create new session
            result = self.db.table('registration_sessions').insert({
                'phone': phone,
                'user_type': user_type,
                'status': 'active',
                'step': initial_step,
                'data': {},
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            return result.data[0]['id'] if result.data else None
            
        except Exception as e:
            log_error(f"Error creating registration session: {str(e)}")
            return None
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get registration session by ID"""
        try:
            result = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            return result.data
            
        except Exception as e:
            log_error(f"Error getting session: {str(e)}")
            return None
    
    def update_session(self, session_id: str, step: str = None, 
                      data_update: Dict = None) -> bool:
        """Update registration session"""
        try:
            update_data = {
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if step:
                update_data['step'] = step
            
            if data_update:
                # Get current data
                session = self.get_session(session_id)
                if session:
                    current_data = session.get('data', {})
                    current_data.update(data_update)
                    update_data['data'] = current_data
            
            result = self.db.table('registration_sessions').update(
                update_data
            ).eq('id', session_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating session: {str(e)}")
            return False
    
    def complete_session(self, session_id: str) -> bool:
        """Mark session as completed"""
        try:
            result = self.db.table('registration_sessions').update({
                'status': 'completed',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error completing session: {str(e)}")
            return False
    
    def expire_old_sessions(self):
        """Expire sessions older than 24 hours"""
        try:
            cutoff = datetime.now(self.sa_tz) - timedelta(hours=24)
            
            self.db.table('registration_sessions').update({
                'status': 'expired'
            }).eq('status', 'active').lt(
                'updated_at', cutoff.isoformat()
            ).execute()
            
            log_info("Expired old registration sessions")
            
        except Exception as e:
            log_error(f"Error expiring sessions: {str(e)}")