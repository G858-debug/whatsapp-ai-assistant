"""Clean up expired and abandoned registration sessions"""
from typing import Dict, List
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info

class RegistrationCleaner:
    """Handles cleanup of expired registration sessions"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.TIMEOUT_MINUTES = 90  # 90 minutes timeout
    
    def cleanup_expired_sessions(self) -> Dict:
        """
        Clean up registration sessions that have been abandoned
        This should be called periodically (e.g., every hour)
        
        Returns:
            Dict with cleanup statistics
        """
        try:
            cutoff = datetime.now(self.sa_tz) - timedelta(minutes=self.TIMEOUT_MINUTES)
            
            # Get expired sessions
            expired = self.db.table('registration_sessions').select(
                'id, phone, registration_type, step'
            ).eq('status', 'active').lt(
                'updated_at', cutoff.isoformat()
            ).execute()
            
            if not expired.data:
                return {
                    'success': True,
                    'expired_count': 0,
                    'message': 'No expired sessions found'
                }
            
            expired_count = len(expired.data)
            session_ids = [s['id'] for s in expired.data]
            
            # Update to expired status
            self.db.table('registration_sessions').update({
                'status': 'expired',
                'expired_at': datetime.now(self.sa_tz).isoformat(),
                'expiry_reason': 'timeout'
            }).in_('id', session_ids).execute()
            
            # Log details for monitoring
            for session in expired.data:
                log_info(
                    f"Expired session: {session['id'][:8]} | "
                    f"Type: {session.get('registration_type', 'unknown')} | "
                    f"Step: {session.get('step', 'unknown')} | "
                    f"Phone: {session.get('phone', 'unknown')[-4:]}"
                )
            
            log_info(f"Cleaned up {expired_count} expired registration sessions")
            
            return {
                'success': True,
                'expired_count': expired_count,
                'message': f'Expired {expired_count} abandoned sessions',
                'details': [
                    {
                        'id': s['id'],
                        'type': s.get('registration_type'),
                        'step': s.get('step')
                    } for s in expired.data
                ]
            }
            
        except Exception as e:
            log_error(f"Error cleaning up expired sessions: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to cleanup expired sessions'
            }
    
    def get_session_age(self, session_id: str) -> Optional[int]:
        """
        Get age of a session in minutes
        
        Args:
            session_id: Session ID to check
            
        Returns:
            Age in minutes or None if session not found
        """
        try:
            session = self.db.table('registration_sessions').select(
                'created_at, updated_at'
            ).eq('id', session_id).single().execute()
            
            if not session.data:
                return None
            
            # Use updated_at for last activity
            last_activity = session.data.get('updated_at', session.data.get('created_at'))
            if not last_activity:
                return None
            
            last_activity_dt = datetime.fromisoformat(last_activity)
            if last_activity_dt.tzinfo is None:
                last_activity_dt = self.sa_tz.localize(last_activity_dt)
            
            age = datetime.now(self.sa_tz) - last_activity_dt
            return int(age.total_seconds() / 60)  # Return minutes
            
        except Exception as e:
            log_error(f"Error getting session age: {str(e)}")
            return None
    
    def send_timeout_warning(self, phone: str, minutes_remaining: int = 15) -> bool:
        """
        Send a warning message before session timeout
        This could be called by a scheduler
        
        Args:
            phone: User's phone number
            minutes_remaining: Minutes until timeout
            
        Returns:
            True if warning sent successfully
        """
        try:
            # Check if there's an active session
            session = self.db.table('registration_sessions').select('id, step').eq(
                'phone', phone
            ).eq('status', 'active').single().execute()
            
            if not session.data:
                return False
            
            # Check session age
            age = self.get_session_age(session.data['id'])
            if not age:
                return False
            
            # Only send warning if close to timeout
            if age >= (self.TIMEOUT_MINUTES - minutes_remaining) and age < self.TIMEOUT_MINUTES:
                # This would integrate with WhatsApp service
                # For now, just log
                log_info(f"Timeout warning for session {session.data['id'][:8]}: {minutes_remaining} minutes remaining")
                
                # You would send WhatsApp message here:
                # message = f"⏰ Your registration session will expire in {minutes_remaining} minutes. Please complete your registration or type 'cancel' to stop."
                # whatsapp_service.send_message(phone, message)
                
                return True
            
            return False
            
        except Exception as e:
            log_error(f"Error sending timeout warning: {str(e)}")
            return False
    
    def get_abandoned_sessions_report(self, days: int = 7) -> Dict:
        """
        Get report of abandoned sessions for analysis
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dict with abandonment statistics
        """
        try:
            cutoff = datetime.now(self.sa_tz) - timedelta(days=days)
            
            # Get all expired sessions in timeframe
            expired = self.db.table('registration_sessions').select(
                'step, registration_type, expiry_reason'
            ).eq('status', 'expired').gte(
                'expired_at', cutoff.isoformat()
            ).execute()
            
            if not expired.data:
                return {
                    'total_abandoned': 0,
                    'by_step': {},
                    'by_type': {},
                    'by_reason': {}
                }
            
            # Analyze abandonment patterns
            by_step = {}
            by_type = {}
            by_reason = {}
            
            for session in expired.data:
                # Count by step
                step = session.get('step', 'unknown')
                by_step[step] = by_step.get(step, 0) + 1
                
                # Count by type
                reg_type = session.get('registration_type', 'unknown')
                by_type[reg_type] = by_type.get(reg_type, 0) + 1
                
                # Count by reason
                reason = session.get('expiry_reason', 'unknown')
                by_reason[reason] = by_reason.get(reason, 0) + 1
            
            return {
                'total_abandoned': len(expired.data),
                'by_step': by_step,
                'by_type': by_type,
                'by_reason': by_reason,
                'most_abandoned_step': max(by_step, key=by_step.get) if by_step else None
            }
            
        except Exception as e:
            log_error(f"Error getting abandonment report: {str(e)}")
            return {
                'total_abandoned': 0,
                'by_step': {},
                'by_type': {},
                'by_reason': {},
                'error': str(e)
            }
    
    def recover_expired_session(self, phone: str) -> Dict:
        """
        Attempt to recover an expired session for a user
        
        Args:
            phone: User's phone number
            
        Returns:
            Dict with recovery result
        """
        try:
            # Find most recent expired session
            expired = self.db.table('registration_sessions').select('*').eq(
                'phone', phone
            ).eq('status', 'expired').order(
                'expired_at', desc=True
            ).limit(1).execute()
            
            if not expired.data:
                return {
                    'success': False,
                    'message': 'No expired session found to recover'
                }
            
            session = expired.data[0]
            
            # Check if not too old (e.g., less than 24 hours)
            expired_at = datetime.fromisoformat(session['expired_at'])
            if expired_at.tzinfo is None:
                expired_at = self.sa_tz.localize(expired_at)
            
            age_hours = (datetime.now(self.sa_tz) - expired_at).total_seconds() / 3600
            
            if age_hours > 24:
                return {
                    'success': False,
                    'message': 'Session too old to recover. Please start fresh.'
                }
            
            # Reactivate session
            self.db.table('registration_sessions').update({
                'status': 'active',
                'updated_at': datetime.now(self.sa_tz).isoformat(),
                'recovered_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session['id']).execute()
            
            log_info(f"Recovered expired session {session['id'][:8]} for {phone[-4:]}")
            
            return {
                'success': True,
                'session_id': session['id'],
                'current_step': session.get('step'),
                'data': session.get('data', {}),
                'message': f"Welcome back! Let's continue from where you left off: {session.get('step', 'unknown').replace('_', ' ')}"
            }
            
        except Exception as e:
            log_error(f"Error recovering session: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to recover session. Please start fresh.',
                'error': str(e)
            }