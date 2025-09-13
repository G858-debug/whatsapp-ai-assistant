"""Registration state management"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_info, log_error

class RegistrationStateManager:
    """Manages registration session state"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.session_timeout = 30  # minutes
    
    def get_active_session(self, phone: str) -> Optional[Dict]:
        """Get active registration session for phone number"""
        try:
            # Check for active session
            result = self.db.table('registration_sessions').select('*').eq(
                'phone', phone
            ).order('created_at', desc=True).limit(1).execute()
            
            if not result.data:
                return None
            
            session = result.data[0]
            
            # Check if session is expired
            created_at = datetime.fromisoformat(session['created_at'])
            if (datetime.now(self.sa_tz) - created_at).total_seconds() > self.session_timeout * 60:
                # Session expired, delete it
                self.db.table('registration_sessions').delete().eq(
                    'id', session['id']
                ).execute()
                return None
            
            return session
            
        except Exception as e:
            log_error(f"Error getting active session: {str(e)}")
            return None
    
    def update_session_step(self, session_id: str, step: str, data: Dict = None) -> bool:
        """Update registration session step"""
        try:
            update_data = {
                'step': step,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if data:
                # Get current data
                session = self.db.table('registration_sessions').select('data').eq(
                    'id', session_id
                ).single().execute()
                
                current_data = session.data.get('data', {})
                current_data.update(data)
                update_data['data'] = current_data
            
            result = self.db.table('registration_sessions').update(
                update_data
            ).eq('id', session_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating session step: {str(e)}")
            return False
    
    def cancel_session(self, session_id: str) -> bool:
        """Cancel and delete registration session"""
        try:
            result = self.db.table('registration_sessions').delete().eq(
                'id', session_id
            ).execute()
            
            log_info(f"Registration session {session_id} cancelled")
            return True
            
        except Exception as e:
            log_error(f"Error cancelling session: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired registration sessions"""
        try:
            cutoff_time = datetime.now(self.sa_tz) - timedelta(minutes=self.session_timeout)
            
            # Get expired sessions
            expired = self.db.table('registration_sessions').select('id').lt(
                'created_at', cutoff_time.isoformat()
            ).execute()
            
            if expired.data:
                # Delete expired sessions
                for session in expired.data:
                    self.db.table('registration_sessions').delete().eq(
                        'id', session['id']
                    ).execute()
                
                log_info(f"Cleaned up {len(expired.data)} expired registration sessions")
                return len(expired.data)
            
            return 0
            
        except Exception as e:
            log_error(f"Error cleaning up sessions: {str(e)}")
            return 0
    
    def is_registration_in_progress(self, phone: str) -> bool:
        """Check if registration is in progress for phone number"""
        session = self.get_active_session(phone)
        return session is not None
    
    def get_session_progress(self, session_id: str) -> Dict:
        """Get registration progress for session"""
        try:
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {'exists': False}
            
            # Calculate progress based on user type and step
            if session.data['user_type'] == 'trainer':
                steps = ['name', 'email', 'business_name', 'location', 'pricing', 'specialties', 'confirm']
            else:
                steps = ['name', 'email', 'emergency_contact', 'goals', 'fitness_level', 'medical_conditions', 'confirm']
            
            current_step_index = steps.index(session.data['step']) if session.data['step'] in steps else 0
            progress_percentage = (current_step_index / len(steps)) * 100
            
            return {
                'exists': True,
                'user_type': session.data['user_type'],
                'current_step': session.data['step'],
                'progress': progress_percentage,
                'data': session.data.get('data', {}),
                'created_at': session.data['created_at']
            }
            
        except Exception as e:
            log_error(f"Error getting session progress: {str(e)}")
            return {'exists': False}