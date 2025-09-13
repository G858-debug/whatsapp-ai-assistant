"""Registration state management for trainers and clients"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import pytz
import json
from utils.logger import log_info, log_error

class RegistrationStateManager:
    """Manages registration session state"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.SESSION_TIMEOUT_HOURS = 24
    
    def create_session(self, phone: str, user_type: str) -> Dict:
        """Create new registration session"""
        try:
            # Check for existing active session
            existing = self.db.table('registration_sessions').select('*').eq(
                'phone', phone
            ).eq('status', 'active').execute()
            
            if existing.data:
                # Update existing session
                session_id = existing.data[0]['id']
                self.db.table('registration_sessions').update({
                    'user_type': user_type,
                    'step': 'name',
                    'data': {},
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('id', session_id).execute()
                return {'success': True, 'session_id': session_id}
            
            # Create new session
            result = self.db.table('registration_sessions').insert({
                'phone': phone,
                'user_type': user_type,
                'status': 'active',
                'step': 'name',
                'data': {},
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            if result.data:
                return {'success': True, 'session_id': result.data[0]['id']}
            
            return {'success': False, 'error': 'Failed to create session'}
            
        except Exception as e:
            log_error(f"Error creating session: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get registration session by ID"""
        try:
            result = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if result.data:
                # Check if expired
                updated_at = datetime.fromisoformat(result.data['updated_at'])
                if (datetime.now(self.sa_tz) - updated_at).total_seconds() > self.SESSION_TIMEOUT_HOURS * 3600:
                    self.update_session_status(session_id, 'expired')
                    return None
                return result.data
            
            return None
            
        except Exception as e:
            log_error(f"Error getting session: {str(e)}")
            return None
    
    def update_session(self, session_id: str, step: str = None, 
                      data_update: Dict = None) -> Dict:
        """Update registration session"""
        try:
            # Get current session
            session = self.get_session(session_id)
            if not session:
                return {'success': False, 'error': 'Session not found or expired'}
            
            # Prepare update
            update_data = {
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if step:
                update_data['step'] = step
            
            if data_update:
                current_data = session.get('data', {})
                current_data.update(data_update)
                update_data['data'] = current_data
            
            # Update session
            result = self.db.table('registration_sessions').update(
                update_data
            ).eq('id', session_id).execute()
            
            if result.data:
                return {'success': True, 'session': result.data[0]}
            
            return {'success': False, 'error': 'Failed to update session'}
            
        except Exception as e:
            log_error(f"Error updating session: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status"""
        try:
            self.db.table('registration_sessions').update({
                'status': status,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            return True
            
        except Exception as e:
            log_error(f"Error updating session status: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            cutoff_time = datetime.now(self.sa_tz) - timedelta(hours=self.SESSION_TIMEOUT_HOURS)
            
            result = self.db.table('registration_sessions').update({
                'status': 'expired'
            }).eq('status', 'active').lt(
                'updated_at', cutoff_time.isoformat()
            ).execute()
            
            if result.data:
                log_info(f"Cleaned up {len(result.data)} expired sessions")
                
        except Exception as e:
            log_error(f"Error cleaning up sessions: {str(e)}")