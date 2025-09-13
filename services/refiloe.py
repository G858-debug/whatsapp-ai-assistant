"""Main orchestration service for Refiloe WhatsApp AI Assistant"""
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import pytz
import json
from utils.logger import log_info, log_error, log_warning
from services.registration import (
    TrainerRegistrationHandler,
    ClientRegistrationHandler,
    RegistrationStateManager
)
from services.text_variation_handler import TextVariationHandler
from services.ai_intent_handler import AIIntentHandler
from services.helpers.validation_helpers import ValidationHelpers
from services.helpers.whatsapp_helpers import WhatsAppHelpers
from services.refiloe_helpers import RefiloeHelpers

class RefiloeService:
    """Main orchestration service for message routing and session management"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize handlers
        from config import Config
        self.config = Config
        self.trainer_handler = TrainerRegistrationHandler(supabase_client, Config)
        self.client_handler = ClientRegistrationHandler(supabase_client, Config)
        self.state_manager = RegistrationStateManager(supabase_client, Config)
        self.text_handler = TextVariationHandler()
        self.ai_handler = AIIntentHandler(Config, supabase_client)
        self.validation = ValidationHelpers()
        self.whatsapp_helpers = WhatsAppHelpers()
        self.helpers = RefiloeHelpers(supabase_client, None, Config)
        
        # Session timeout (24 hours)
        self.SESSION_TIMEOUT_HOURS = 24
        
        # Cleanup expired sessions on init
        self._cleanup_expired_sessions()
    
    def process_message(self, message_data: Dict) -> Dict:
        """Main entry point for processing WhatsApp messages"""
        try:
            phone = message_data.get('from')
            message_type = message_data.get('type', 'text')
            
            # Extract message text based on type
            message_text = self._extract_message_text(message_data, message_type)
            
            if not message_text:
                return {
                    'success': True,
                    'message': "I couldn't understand that message. Please send a text message or voice note."
                }
            
            # Clean and normalize the message
            message_text = self.validation.sanitize_input(message_text)
            
            # Check for duplicate registration
            if self._is_duplicate_registration_attempt(phone, message_text):
                return {
                    'success': True,
                    'message': "You're already registered! 😊\n\nHow can I help you today?\n• Book a session\n• Check schedule\n• View progress"
                }
            
            # Check for active registration session
            session = self._get_or_create_session(phone)
            
            if session and session.get('status') == 'active':
                # Continue registration flow
                return self._continue_registration(session, message_text)
            
            # Check if user exists
            user_type, user_data = self._identify_user(phone)
            
            if user_type:
                # Process as existing user
                return self._process_user_message(user_type, user_data, message_text)
            else:
                # New user - start registration
                return self._start_registration(phone, message_text)
                
        except Exception as e:
            log_error(f"Error processing message: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, something went wrong. Please try again or type 'help' for assistance."
            }
    
    def _extract_message_text(self, message_data: Dict, message_type: str) -> Optional[str]:
        """Extract text from different message types"""
        if message_type == 'text':
            return message_data.get('text', {}).get('body', '')
        elif message_type == 'interactive':
            # Handle button responses
            interactive = message_data.get('interactive', {})
            if interactive.get('type') == 'button_reply':
                return interactive.get('button_reply', {}).get('title', '')
            elif interactive.get('type') == 'list_reply':
                return interactive.get('list_reply', {}).get('title', '')
        elif message_type == 'button':
            # Legacy button response
            return message_data.get('button', {}).get('text', '')
        
        return None
    
    def _cleanup_expired_sessions(self):
        """Clean up registration sessions older than 24 hours"""
        try:
            cutoff_time = datetime.now(self.sa_tz) - timedelta(hours=self.SESSION_TIMEOUT_HOURS)
            
            # Delete expired sessions
            result = self.db.table('registration_sessions').delete().lt(
                'updated_at', cutoff_time.isoformat()
            ).execute()
            
            if result.data:
                log_info(f"Cleaned up {len(result.data)} expired registration sessions")
                
        except Exception as e:
            log_error(f"Error cleaning up sessions: {str(e)}")
    
    def _is_duplicate_registration_attempt(self, phone: str, message: str) -> bool:
        """Check if user is trying to register again"""
        try:
            # Check for registration keywords
            registration_keywords = ['register', 'sign up', 'join', 'start']
            message_lower = message.lower()
            
            if not any(keyword in message_lower for keyword in registration_keywords):
                return False
            
            # Check if phone is already registered as trainer
            trainer = self.db.table('trainers').select('id').eq(
                'whatsapp', phone
            ).execute()
            
            if trainer.data:
                return True
            
            # Check if phone is already registered as client
            client = self.db.table('clients').select('id').eq(
                'whatsapp', phone
            ).execute()
            
            if client.data:
                return True
            
            return False
            
        except Exception as e:
            log_error(f"Error checking duplicate registration: {str(e)}")
            return False
    
    def _get_or_create_session(self, phone: str) -> Optional[Dict]:
        """Get or create registration session"""
        try:
            # Check for existing active session
            result = self.db.table('registration_sessions').select('*').eq(
                'phone', phone
            ).eq('status', 'active').execute()
            
            if result.data:
                session = result.data[0]
                
                # Check if session is expired
                updated_at = datetime.fromisoformat(session['updated_at'])
                if (datetime.now(self.sa_tz) - updated_at).total_seconds() > self.SESSION_TIMEOUT_HOURS * 3600:
                    # Session expired, mark as expired
                    self.db.table('registration_sessions').update({
                        'status': 'expired'
                    }).eq('id', session['id']).execute()
                    return None
                
                return session
            
            return None
            
        except Exception as e:
            log_error(f"Error getting session: {str(e)}")
            return None
    
    def _identify_user(self, phone: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Identify if user is trainer or client"""
        try:
            # Check trainers
            trainer = self.db.table('trainers').select('*').eq(
                'whatsapp', phone
            ).execute()
            
            if trainer.data:
                return 'trainer', trainer.data[0]
            
            # Check clients
            client = self.db.table('clients').select('*, trainers(*)').eq(
                'whatsapp', phone
            ).execute()
            
            if client.data:
                return 'client', client.data[0]
            
            return None, None
            
        except Exception as e:
            log_error(f"Error identifying user: {str(e)}")
            return None, None
    
    def _start_registration(self, phone: str, message: str) -> Dict:
        """Start registration flow for new user"""
        try:
            # Use text variation handler to understand intent
            normalized = self.text_handler.normalize_registration_intent(message)
            
            if normalized == 'trainer':
                # Start trainer registration
                result = self.trainer_handler.start_trainer_registration(phone)
            elif normalized == 'client':
                # Start client registration
                result = self.client_handler.start_client_registration(phone)
            else:
                # Ask what they want to do with buttons
                return {
                    'success': True,
                    'message': "Welcome to Refiloe! 👋\n\nI'm your AI fitness assistant. Are you a personal trainer or looking for one?",
                    'buttons': [
                        {
                            'type': 'reply',
                            'reply': {
                                'id': 'reg_trainer',
                                'title': '💪 I am a Trainer'  # 17 chars
                            }
                        },
                        {
                            'type': 'reply',
                            'reply': {
                                'id': 'reg_client',
                                'title': '🏃 Find a Trainer'  # 17 chars
                            }
                        },
                        {
                            'type': 'reply',
                            'reply': {
                                'id': 'info',
                                'title': 'ℹ️ Learn about me'  # 17 chars
                            }
                        }
                    ]
                }
            
            return result
            
        except Exception as e:
            log_error(f"Error starting registration: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't start the registration. Please try again."
            }
    
    def _handle_confirmation(self, session_id: str, message: str, session: Dict) -> Dict:
        """Handle confirmation step with text variations"""
        try:
            # Use text variation handler
            response_type = self.text_handler.understand_confirmation_response(message)
            user_type = session.get('user_type', '')
            
            if response_type == 'yes':
                # Complete registration
                if user_type == 'trainer':
                    return self.trainer_handler._confirm_trainer_registration(session_id, 'yes')
                else:
                    return self.client_handler._confirm_client_registration(session_id, 'yes')
            
            elif response_type == 'no':
                # Cancel registration
                self.db.table('registration_sessions').update({
                    'status': 'cancelled'
                }).eq('id', session_id).execute()
                
                return {
                    'success': True,
                    'message': "Registration cancelled. You can start over anytime by saying 'register'."
                }
            
            elif response_type == 'edit':
                # Show edit options
                return self._show_edit_options(session_id, session)
            
            else:
                # Unclear response - provide guidance
                return {
                    'success': True,
                    'message': "I didn't understand that. Please reply:\n\n✅ *YES* to confirm\n✏️ *EDIT* to make changes\n❌ *NO* to cancel",
                    'next_step': 'confirmation'
                }
                
        except Exception as e:
            log_error(f"Error handling confirmation: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing confirmation.'
            }
    
    def _show_edit_options(self, session_id: str, session: Dict) -> Dict:
        """Show editable fields with buttons"""
        try:
            user_type = session.get('user_type', '')
            data = session.get('data', {})
            
            if user_type == 'trainer':
                buttons = [
                    {'id': 'edit_name', 'title': '📝 Name'},
                    {'id': 'edit_email', 'title': '📧 Email'},
                    {'id': 'edit_business', 'title': '🏢 Business'}
                ]
            else:
                buttons = [
                    {'id': 'edit_name', 'title': '📝 Name'},
                    {'id': 'edit_emergency', 'title': '🚨 Emergency'},
                    {'id': 'edit_goals', 'title': '🎯 Goals'}
                ]
            
            # Update session to edit mode
            self.db.table('registration_sessions').update({
                'step': 'edit_selection',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            return {
                'success': True,
                'message': "What would you like to edit?",
                'buttons': [
                    {
                        'type': 'reply',
                        'reply': button
                    } for button in buttons[:3]  # WhatsApp limits to 3 buttons
                ]
            }
            
        except Exception as e:
            log_error(f"Error showing edit options: {str(e)}")
            return {
                'success': False,
                'message': 'Error showing edit options.'
            }
    
    def _handle_edit(self, session_id: str, message: str, session: Dict) -> Dict:
        """Handle field editing"""
        try:
            from services.registration.edit_handlers import EditHandlers
            edit_handler = EditHandlers(self.db, self.config)
            
            step = session.get('step', '')
            field_name = step.replace('edit_', '')
            
            # Process the edited value
            result = edit_handler.process_edit_value(session_id, field_name, message)
            
            if result.get('success'):
                # After successful edit, show confirmation again
                return self._show_updated_confirmation(session_id, session)
            
            return result
            
        except Exception as e:
            log_error(f"Error handling edit: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing edit.'
            }
    
    def _show_updated_confirmation(self, session_id: str, session: Dict) -> Dict:
        """Show updated confirmation after edit"""
        try:
            # Refresh session data
            result = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not result.data:
                return {
                    'success': False,
                    'message': 'Session not found.'
                }
            
            session = result.data
            user_type = session.get('user_type', '')
            
            # Build confirmation message
            if user_type == 'trainer':
                return self.trainer_handler._build_confirmation_message(session['data'])
            else:
                return self.client_handler._build_confirmation_message(session['data'])
                
        except Exception as e:
            log_error(f"Error showing updated confirmation: {str(e)}")
            return {
                'success': False,
                'message': 'Error showing confirmation.'
            }
    
    def _process_user_message(self, user_type: str, user_data: Dict, message: str) -> Dict:
        """Process message from existing user"""
        try:
            # Use AI to understand intent
            intent = self.ai_handler.understand_message(
                message=message,
                sender_type=user_type,
                sender_data=user_data
            )
            
            # Route based on intent
            primary_intent = intent.get('primary_intent', 'unclear')
            
            # For now, return a helpful response
            if primary_intent == 'greeting':
                name = user_data.get('name', 'there')
                return {
                    'success': True,
                    'message': f"Hey {name}! 👋\n\nHow can I help you today?"
                }
            else:
                return {
                    'success': True,
                    'message': "I'm here to help! You can:\n• Book a session\n• Check your schedule\n• Log your progress\n• View workouts\n\nWhat would you like to do?"
                }
                
        except Exception as e:
            log_error(f"Error processing user message: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process that. Please try again."
            }
