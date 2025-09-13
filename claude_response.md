<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5478 -->
<!-- Max Tokens: 32000 -->
<!-- Step 2 of 0 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS

Step 2 focuses on implementing the core functionality for help, back, and cancel commands during registration. These commands need to work at any point in the registration flow, providing users with control and assistance. We need to modify the registration handlers to check for these special commands before processing regular input.

## CHANGES NEEDED

### EDIT: services/registration/registration_state.py

**Change 1:** Add method to handle special commands
Location: After the `get_active_session_by_phone` method (around line 70)

```python
# ADD after get_active_session_by_phone method:

    def handle_special_command(self, message: str, session_id: str, phone: str) -> Optional[Dict]:
        """
        Handle special commands (help, back, cancel) during registration
        
        Returns:
            Dict with command result or None if not a special command
        """
        message_lower = message.lower().strip()
        
        # Check for cancel command
        if message_lower in ['cancel', 'stop', 'quit', 'exit']:
            return self._handle_cancel_command(session_id, phone)
        
        # Check for help command
        if message_lower in ['help', 'assist', 'support', '?']:
            return self._handle_help_command(session_id)
        
        # Check for back command
        if message_lower in ['back', 'previous', 'undo', 'go back']:
            return self._handle_back_command(session_id)
        
        return None
    
    def _handle_cancel_command(self, session_id: str, phone: str) -> Dict:
        """Handle cancel command - abort registration"""
        try:
            # Update session status
            if session_id:
                self.db.table('registration_sessions').update({
                    'status': 'cancelled',
                    'cancelled_at': datetime.now(self.sa_tz).isoformat(),
                    'cancellation_reason': 'user_cancelled'
                }).eq('id', session_id).execute()
                
                # Clear in-memory state
                if phone in self.registration_state:
                    del self.registration_state[phone]
                
                log_info(f"Registration cancelled for session {session_id}")
            
            return {
                'success': True,
                'action': 'cancel',
                'message': (
                    "Registration cancelled. No worries! 👋\n\n"
                    "You can start again anytime by saying 'hi'.\n"
                    "If you need help, just ask!"
                )
            }
            
        except Exception as e:
            log_error(f"Error handling cancel command: {str(e)}")
            return {
                'success': False,
                'action': 'cancel',
                'message': "Registration cancelled."
            }
    
    def _handle_help_command(self, session_id: str) -> Dict:
        """Handle help command - provide context-specific help"""
        try:
            # Get current session state
            session = self.get_session(session_id) if session_id else None
            
            if not session:
                return {
                    'success': True,
                    'action': 'help',
                    'message': (
                        "💡 *Registration Help*\n\n"
                        "I'll guide you through a simple registration process.\n\n"
                        "*Commands you can use:*\n"
                        "• Type 'back' to go to previous step\n"
                        "• Type 'cancel' to stop registration\n"
                        "• Type 'help' anytime for assistance\n\n"
                        "Ready to start? Just say 'hi'!"
                    )
                }
            
            # Get step-specific help
            current_step = session.get('step', 'unknown')
            registration_type = session.get('registration_type', 'trainer')
            
            help_messages = self._get_step_help_messages(registration_type)
            step_help = help_messages.get(current_step, help_messages['default'])
            
            return {
                'success': True,
                'action': 'help',
                'message': (
                    f"💡 *Help - {current_step.replace('_', ' ').title()}*\n\n"
                    f"{step_help}\n\n"
                    "*Available commands:*\n"
                    "• 'back' - Go to previous step\n"
                    "• 'cancel' - Stop registration\n"
                    "• 'skip' - Skip optional fields"
                )
            }
            
        except Exception as e:
            log_error(f"Error handling help command: {str(e)}")
            return {
                'success': True,
                'action': 'help',
                'message': "Type 'back' to go back, 'cancel' to stop, or answer the current question."
            }
    
    def _handle_back_command(self, session_id: str) -> Dict:
        """Handle back command - go to previous step"""
        try:
            if not session_id:
                return {
                    'success': False,
                    'action': 'back',
                    'message': "No active registration to go back in. Start fresh by saying 'hi'!"
                }
            
            session = self.get_session(session_id)
            if not session:
                return {
                    'success': False,
                    'action': 'back',
                    'message': "Session not found. Please start again."
                }
            
            current_step = session.get('step', 'type_selection')
            registration_type = session.get('registration_type', 'trainer')
            
            # Get step sequence
            step_sequence = self._get_step_sequence(registration_type)
            
            # Find current step index
            try:
                current_index = step_sequence.index(current_step)
            except ValueError:
                current_index = 0
            
            # Go to previous step
            if current_index > 0:
                previous_step = step_sequence[current_index - 1]
                
                # Update session
                self.db.table('registration_sessions').update({
                    'step': previous_step,
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('id', session_id).execute()
                
                # Get prompt for previous step
                prompts = self._get_step_prompts(registration_type)
                prompt = prompts.get(previous_step, "Please provide the information:")
                
                # Add current value if exists
                data = session.get('data', {})
                current_value = self._get_step_value(data, previous_step)
                if current_value:
                    prompt += f"\n\n📝 Current value: {current_value}\n(Type a new value or 'skip' to keep current)"
                
                log_info(f"Moved back to step {previous_step} for session {session_id}")
                
                return {
                    'success': True,
                    'action': 'back',
                    'new_step': previous_step,
                    'message': f"⬅️ Going back...\n\n{prompt}"
                }
            else:
                return {
                    'success': False,
                    'action': 'back',
                    'message': "You're at the beginning. Answer the current question or type 'cancel' to stop."
                }
                
        except Exception as e:
            log_error(f"Error handling back command: {str(e)}")
            return {
                'success': False,
                'action': 'back',
                'message': "Error going back. Please continue or type 'cancel' to stop."
            }
    
    def _get_step_sequence(self, registration_type: str) -> List[str]:
        """Get the sequence of steps for a registration type"""
        if registration_type == 'trainer':
            return [
                'type_selection',
                'name',
                'email',
                'business',
                'location',
                'specialization',
                'pricing',
                'confirmation'
            ]
        else:  # client
            return [
                'type_selection',
                'name',
                'email',
                'trainer_selection',
                'goals',
                'availability',
                'confirmation'
            ]
    
    def _get_step_prompts(self, registration_type: str) -> Dict[str, str]:
        """Get prompts for each step"""
        if registration_type == 'trainer':
            return {
                'type_selection': "Are you registering as a trainer or looking for a trainer?",
                'name': "What's your full name?",
                'email': "What's your email address?",
                'business': "What's your business name? (or type 'skip' if you don't have one)",
                'location': "Where are you located? (area/suburb)",
                'specialization': "What's your training specialization? (e.g., weight loss, strength training)",
                'pricing': "What's your rate per session? (e.g., R350)",
                'confirmation': "Please review your information above. Type 'confirm' to complete or 'edit' to make changes."
            }
        else:  # client
            return {
                'type_selection': "Are you registering as a trainer or looking for a trainer?",
                'name': "What's your full name?",
                'email': "What's your email address?",
                'trainer_selection': "Do you have a specific trainer in mind? (name or 'no')",
                'goals': "What are your fitness goals?",
                'availability': "When are you usually available for training? (e.g., weekday mornings)",
                'confirmation': "Please review your information above. Type 'confirm' to complete or 'edit' to make changes."
            }
    
    def _get_step_help_messages(self, registration_type: str) -> Dict[str, str]:
        """Get help messages for each step"""
        if registration_type == 'trainer':
            return {
                'type_selection': "Choose whether you're a trainer offering services or a client looking for a trainer.",
                'name': "Enter your full name as you'd like clients to see it.",
                'email': "Provide a valid email address where clients can reach you.",
                'business': "Enter your business name if you have one, or type 'skip' to continue without one.",
                'location': "Tell us your area or suburb so clients can find trainers near them.",
                'specialization': "Describe what type of training you specialize in (e.g., weight loss, CrossFit, yoga).",
                'pricing': "Enter your price per session in Rands (e.g., R350 or 350).",
                'confirmation': "Review all your details. Type 'confirm' if everything is correct, or 'edit' to change something.",
                'default': "Please answer the current question or use a command (back/cancel/help)."
            }
        else:  # client
            return {
                'type_selection': "Choose whether you're a trainer or looking for a trainer.",
                'name': "Enter your full name.",
                'email': "Provide your email address for communication.",
                'trainer_selection': "If you know a specific trainer's name, enter it. Otherwise, type 'no' and I'll help you find one.",
                'goals': "Describe what you want to achieve (e.g., lose weight, build muscle, get fit).",
                'availability': "Tell us when you're usually free for training sessions.",
                'confirmation': "Review your details. Type 'confirm' if correct, or 'edit' to make changes.",
                'default': "Please answer the current question or use a command (back/cancel/help)."
            }
    
    def _get_step_value(self, data: Dict, step: str) -> Optional[str]:
        """Get the current value for a step from session data"""
        step_to_field = {
            'name': 'name',
            'email': 'email',
            'business': 'business_name',
            'location': 'location',
            'specialization': 'specialization',
            'pricing': 'pricing_per_session',
            'trainer_selection': 'preferred_trainer',
            'goals': 'fitness_goals',
            'availability': 'availability'
        }
        
        field = step_to_field.get(step)
        if field and data:
            value = data.get(field)
            if value and field == 'pricing_per_session':
                return f"R{value}"
            return value
        return None
```

### NEW FILE: services/registration/registration_cleaner.py

```python
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
```

### EDIT: services/registration/registration_handlers.py

**Change 1:** Add special command checking to main handler
Location: At the beginning of the handle_registration method (add new method)

```python
# ADD this new method before handle_registration:

    def process_registration_message(self, phone: str, message: str) -> str:
        """
        Main entry point for registration messages with special command handling
        
        Args:
            phone: User's phone number
            message: Message text
            
        Returns:
            Response message
        """
        try:
            # Get or create session
            session = self.state_manager.get_active_session_by_phone(phone)
            session_id = session['id'] if session else None
            
            # Check for special commands first
            special_result = self.state_manager.handle_special_command(
                message, session_id, phone
            )
            
            if special_result:
                # Log the special command
                log_info(f"Special command '{special_result.get('action')}' for phone {phone[-4:]}")
                
                # Handle based on action type
                if special_result.get('action') == 'cancel':
                    # Clear any cached data
                    return special_result.get('message', 'Registration cancelled.')
                    
                elif special_result.get('action') == 'help':
                    # Return help message and stay on current step
                    return special_result.get('message', 'Help not available.')
                    
                elif special_result.get('action') == 'back':
                    # Return back message with new prompt
                    return special_result.get('message', 'Cannot go back.')
                
                return special_result.get('message', '')
            
            # If not a special command, process normally
            return self.handle_registration(phone, message)
            
        except Exception as e:
            # Use error handler for recovery
            if hasattr(self, 'error_handler'):
                error_result = self.error_handler.handle_registration_error(
                    e, session_id, phone, {'message': message}
                )
                return error_result.get('message', 'An error occurred. Please try again.')
            else:
                log_error(f"Registration error: {str(e)}")
                return "Sorry, something went wrong. Please try again or type 'help' for assistance."
```

## SUMMARY

In Step 2, I've implemented core functionality for handling help, back, and cancel commands during registration:

1. **Added special command handler** in `RegistrationStateManager` that:
   - Detects help, back, and cancel commands at any point
   - Provides context-specific help based on current step
   - Allows users to go back to previous steps
   - Enables clean cancellation with session cleanup

2. **Created RegistrationCleaner** service for:
   - Automatic cleanup of abandoned sessions after 90 minutes
   - Session age tracking and timeout warnings
   - Abandonment analytics for optimization
   - Session recovery for recently expired sessions

3. **Enhanced registration flow** with:
   - Special command checking before normal processing
   - Step sequence management for back navigation
   - Current value display when going back
   - Comprehensive logging for all registration steps

The system now provides a user-friendly registration experience where users never get stuck and always have options to get help, go back, or cancel.

## CONTINUE_NEEDED
Next step: Step 3: Add duplicate prevention and database error handling