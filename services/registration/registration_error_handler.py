"""Comprehensive error handling for registration flows"""
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info, log_warning
import traceback

class RegistrationErrorHandler:
    """Handles all registration errors and edge cases"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Error recovery strategies
        self.ERROR_STRATEGIES = {
            'database_error': self._handle_database_error,
            'validation_error': self._handle_validation_error,
            'timeout_error': self._handle_timeout_error,
            'duplicate_error': self._handle_duplicate_error,
            'unknown_step': self._handle_unknown_step,
            'invalid_input': self._handle_invalid_input
        }
        
        # User-friendly error messages
        self.ERROR_MESSAGES = {
            'database': "😔 Sorry, I'm having trouble saving your information. Please try again in a moment.",
            'timeout': "⏰ Your registration session expired. Let's start fresh! Just say 'hi' to begin.",
            'duplicate_phone': "📱 This phone number is already registered. Try 'help' to see your options.",
            'duplicate_email': "📧 This email is already in use. Please use a different email address.",
            'invalid_input': "🤔 I didn't understand that. Please check your input and try again.",
            'network': "📡 Connection issue detected. Please try again in a moment.",
            'unknown': "😅 Something went wrong. Don't worry, let's try again!"
        }
    
    def handle_registration_error(self, error: Exception, session_id: str = None, 
                                 phone: str = None, context: Dict = None) -> Dict:
        """
        Main error handler that gracefully recovers from any error state
        
        Args:
            error: The exception that occurred
            session_id: Current registration session ID
            phone: User's phone number
            context: Additional context about the error
            
        Returns:
            Dict with recovery message and actions
        """
        try:
            # Log the error with full context
            error_id = self._log_registration_error(error, session_id, phone, context)
            
            # Determine error type
            error_type = self._classify_error(error)
            
            # Get recovery strategy
            strategy = self.ERROR_STRATEGIES.get(error_type, self._handle_generic_error)
            
            # Execute recovery
            recovery_result = strategy(error, session_id, phone, context)
            
            # Add error ID for support reference
            recovery_result['error_id'] = error_id
            
            # Log recovery attempt
            log_info(f"Error recovery attempted for {error_id}: {error_type}")
            
            return recovery_result
            
        except Exception as recovery_error:
            # If recovery itself fails, provide failsafe response
            log_error(f"Recovery failed: {str(recovery_error)}")
            return self._failsafe_response(phone)
    
    def _classify_error(self, error: Exception) -> str:
        """Classify the type of error for appropriate handling"""
        error_str = str(error).lower()
        
        if 'database' in error_str or 'supabase' in error_str:
            return 'database_error'
        elif 'duplicate' in error_str or 'already exists' in error_str:
            return 'duplicate_error'
        elif 'timeout' in error_str or 'expired' in error_str:
            return 'timeout_error'
        elif 'validation' in error_str or 'invalid' in error_str:
            return 'validation_error'
        elif 'unknown step' in error_str:
            return 'unknown_step'
        else:
            return 'generic'
    
    def _log_registration_error(self, error: Exception, session_id: str, 
                               phone: str, context: Dict) -> str:
        """Log detailed error information for debugging"""
        import uuid
        error_id = str(uuid.uuid4())[:8]
        
        try:
            # Get full traceback
            tb = traceback.format_exc()
            
            # Log to database
            self.db.table('registration_errors').insert({
                'error_id': error_id,
                'session_id': session_id,
                'phone': phone,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': tb,
                'context': context or {},
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            # Log to file
            log_error(f"Registration Error {error_id}: {str(error)}", exc_info=True)
            
        except Exception as log_error:
            # If logging fails, at least try file logging
            log_error(f"Failed to log registration error: {str(log_error)}")
        
        return error_id
    
    def _handle_database_error(self, error: Exception, session_id: str, 
                              phone: str, context: Dict) -> Dict:
        """Handle database-related errors"""
        try:
            # Try to recover session from cache if available
            if session_id:
                # Mark session for retry
                self._mark_session_for_retry(session_id)
            
            return {
                'success': False,
                'message': self.ERROR_MESSAGES['database'],
                'retry_available': True,
                'actions': ['retry', 'help', 'cancel']
            }
        except:
            return self._failsafe_response(phone)
    
    def _handle_validation_error(self, error: Exception, session_id: str,
                                phone: str, context: Dict) -> Dict:
        """Handle validation errors"""
        field = context.get('field', 'input') if context else 'input'
        
        return {
            'success': False,
            'message': f"❌ Invalid {field}. {str(error)}\n\nType 'help' for examples or 'back' to go to previous step.",
            'retry_available': True,
            'actions': ['retry', 'help', 'back', 'cancel']
        }
    
    def _handle_timeout_error(self, error: Exception, session_id: str,
                             phone: str, context: Dict) -> Dict:
        """Handle session timeout errors"""
        try:
            # Clear the expired session
            if session_id:
                self.db.table('registration_sessions').update({
                    'status': 'expired',
                    'expired_at': datetime.now(self.sa_tz).isoformat()
                }).eq('id', session_id).execute()
            
            return {
                'success': False,
                'message': self.ERROR_MESSAGES['timeout'],
                'retry_available': True,
                'actions': ['start_over']
            }
        except:
            return self._failsafe_response(phone)
    
    def _handle_duplicate_error(self, error: Exception, session_id: str,
                               phone: str, context: Dict) -> Dict:
        """Handle duplicate registration attempts"""
        duplicate_field = context.get('field', 'phone') if context else 'phone'
        
        if duplicate_field == 'phone':
            message = self.ERROR_MESSAGES['duplicate_phone']
        elif duplicate_field == 'email':
            message = self.ERROR_MESSAGES['duplicate_email']
        else:
            message = f"This {duplicate_field} is already registered."
        
        return {
            'success': False,
            'message': message,
            'retry_available': False,
            'actions': ['login', 'help', 'use_different']
        }
    
    def _handle_unknown_step(self, error: Exception, session_id: str,
                            phone: str, context: Dict) -> Dict:
        """Handle unknown registration step errors"""
        try:
            # Try to recover by resetting to last known good step
            if session_id:
                session = self.db.table('registration_sessions').select('*').eq(
                    'id', session_id
                ).single().execute()
                
                if session.data:
                    last_step = session.data.get('last_completed_step', 'name')
                    
                    self.db.table('registration_sessions').update({
                        'step': last_step,
                        'updated_at': datetime.now(self.sa_tz).isoformat()
                    }).eq('id', session_id).execute()
                    
                    return {
                        'success': False,
                        'message': f"Let's continue from where we left off. Current step: {last_step}",
                        'retry_available': True,
                        'recovered': True,
                        'current_step': last_step
                    }
            
            return self._failsafe_response(phone)
            
        except:
            return self._failsafe_response(phone)
    
    def _handle_invalid_input(self, error: Exception, session_id: str,
                             phone: str, context: Dict) -> Dict:
        """Handle invalid input errors"""
        expected_format = context.get('expected_format', '') if context else ''
        
        message = self.ERROR_MESSAGES['invalid_input']
        if expected_format:
            message += f"\n\nExpected format: {expected_format}"
        
        return {
            'success': False,
            'message': message,
            'retry_available': True,
            'actions': ['retry', 'help', 'skip']
        }
    
    def _handle_generic_error(self, error: Exception, session_id: str,
                             phone: str, context: Dict) -> Dict:
        """Handle generic/unknown errors"""
        return {
            'success': False,
            'message': self.ERROR_MESSAGES['unknown'],
            'retry_available': True,
            'actions': ['retry', 'help', 'cancel']
        }
    
    def _failsafe_response(self, phone: str) -> Dict:
        """Ultimate failsafe response when everything else fails"""
        return {
            'success': False,
            'message': (
                "😔 I'm having technical difficulties right now.\n\n"
                "Please try again in a few minutes, or contact support if the problem persists.\n\n"
                "Your phone number has been saved, and we'll help you complete registration soon."
            ),
            'failsafe': True,
            'phone_saved': phone
        }
    
    def _mark_session_for_retry(self, session_id: str):
        """Mark a session for retry after error"""
        try:
            self.db.table('registration_sessions').update({
                'retry_count': self.db.rpc('increment', {'x': 1}),
                'last_error_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
        except:
            pass  # Non-critical operation
    
    def check_duplicate_registration(self, phone: str = None, email: str = None) -> Tuple[bool, str]:
        """
        Check if phone or email is already registered
        
        Returns:
            Tuple of (is_duplicate, duplicate_field)
        """
        try:
            # Check phone
            if phone:
                # Check trainers
                trainer = self.db.table('trainers').select('id').eq(
                    'whatsapp', phone
                ).execute()
                
                if trainer.data:
                    return True, 'phone_trainer'
                
                # Check clients
                client = self.db.table('clients').select('id').eq(
                    'whatsapp', phone
                ).execute()
                
                if client.data:
                    return True, 'phone_client'
            
            # Check email
            if email:
                # Check trainers
                trainer = self.db.table('trainers').select('id').eq(
                    'email', email
                ).execute()
                
                if trainer.data:
                    return True, 'email_trainer'
                
                # Check clients
                client = self.db.table('clients').select('id').eq(
                    'email', email
                ).execute()
                
                if client.data:
                    return True, 'email_client'
            
            return False, None
            
        except Exception as e:
            log_error(f"Error checking duplicates: {str(e)}")
            return False, None  # Fail open to avoid blocking registration
    
    def clear_expired_sessions(self, timeout_minutes: int = 90):
        """
        Clear registration sessions that have been abandoned
        
        Args:
            timeout_minutes: Minutes after which to consider session abandoned
        """
        try:
            cutoff = datetime.now(self.sa_tz) - timedelta(minutes=timeout_minutes)
            
            # Get sessions to expire
            expired = self.db.table('registration_sessions').select('id, phone').eq(
                'status', 'active'
            ).lt('updated_at', cutoff.isoformat()).execute()
            
            if expired.data:
                # Update to expired status
                session_ids = [s['id'] for s in expired.data]
                
                self.db.table('registration_sessions').update({
                    'status': 'expired',
                    'expired_at': datetime.now(self.sa_tz).isoformat(),
                    'expiry_reason': 'timeout'
                }).in_('id', session_ids).execute()
                
                log_info(f"Expired {len(session_ids)} abandoned registration sessions")
                
                return len(session_ids)
            
            return 0
            
        except Exception as e:
            log_error(f"Error clearing expired sessions: {str(e)}")
            return 0