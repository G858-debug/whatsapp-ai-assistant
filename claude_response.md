<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5371 -->
<!-- Max Tokens: 16000 -->
<!-- Step 1 of 5 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS

Looking at the requirements and current state, I need to analyze what's missing and broken in the registration flow:

1. **Missing `services/refiloe.py`** - The main orchestration service is referenced in `app_core.py` but doesn't exist. This is critical as it handles message routing and session management.

2. **Text variation handling** - Current system likely fails on typos and variations (e.g., "yes", "yeah", "yep", "sure" should all work).

3. **Button title lengths** - WhatsApp has a 20-character limit for button titles that needs to be enforced.

4. **Validation helpers exist** but aren't fully integrated into the registration flow.

5. **Session timeout** - No automatic cleanup of expired sessions after 24 hours.

6. **Duplicate registration** - No checks to prevent users from registering multiple times.

7. **Text recognition** - Limited handling of yes/no variations and local South African terms.

8. **Error handling** - System breaks on unexpected inputs instead of providing helpful guidance.

## CHANGES NEEDED

### NEW FILE: services/refiloe.py
```python
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
                                'title': '💪 I'm a Trainer'  # 16 chars
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
                                'title': 'ℹ️ Learn More'  # 13 chars
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
    
    def _continue_registration(self, session: Dict, message: str) -> Dict:
        """Continue registration flow based on current step"""
        try:
            step = session.get('step', '')
            user_type = session.get('user_type', '')
            session_id = session['id']
            
            # Handle confirmation step with text variations
            if step in ['confirmation', 'confirm']:
                return self._handle_confirmation(session_id, message, session)
            
            # Handle edit mode
            if step.startswith('edit_'):
                return self._handle_edit(session_id, message, session)
            
            # Regular step processing
            if user_type == 'trainer':
                return self.trainer_handler.process_trainer_step(session_id, step, message)
            elif user_type == 'client':
                return self.client_handler.process_client_step(session_id, step, message)
            else:
                return {
                    'success': False,
                    'message': 'Invalid registration session. Please start over.'
                }
                
        except Exception as e:
            log_error(f"Error continuing registration: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, there was an error. Let's try that again.\n\nWhat would you like to enter?"
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
```

### NEW FILE: services/text_variation_handler.py
```python
"""Handler for text variations, typos, and local terms"""
from typing import Optional, List, Dict
import re
from difflib import SequenceMatcher
from utils.logger import log_info, log_warning

class TextVariationHandler:
    """Handles text variations, typos, and local South African terms"""
    
    def __init__(self):
        # Yes variations (including SA terms)
        self.yes_variations = [
            'yes', 'y', 'yeah', 'yep', 'ya', 'yah', 'yup', 'sure', 'ok', 'okay',
            'confirm', 'correct', 'right', 'affirmative', 'definitely', 'absolutely',
            'ja', 'jy', 'yebo', 'sharp', 'sho', 'hundred', '100', 'cool', 'kiff',
            'lekker', 'aweh', 'awe', '✅', '👍', '👌', 'good', 'great', 'perfect',
            'thats right', "that's right", 'thats correct', "that's correct",
            'all good', 'its good', "it's good", 'looks good', 'go ahead'
        ]
        
        # No variations (including SA terms)
        self.no_variations = [
            'no', 'n', 'nope', 'nah', 'negative', 'incorrect', 'wrong', 'cancel',
            'stop', 'exit', 'quit', 'nee', 'aikona', 'hayi', 'never', '❌', '👎',
            'not right', 'thats wrong', "that's wrong", 'mistake', 'error',
            'dont want', "don't want", 'not interested', 'no thanks', 'no thank you'
        ]
        
        # Edit variations
        self.edit_variations = [
            'edit', 'change', 'modify', 'update', 'fix', 'correct', 'alter',
            'revise', 'adjust', 'amend', 'redo', 'back', 'go back', 'previous',
            'mistake', 'wrong', 'incorrect', 'not right', 'let me change',
            'want to change', 'need to change', 'can i change', 'can i edit'
        ]
        
        # Registration intent variations
        self.trainer_variations = [
            'trainer', 'coach', 'instructor', 'fitness professional', 'pt',
            'personal trainer', 'i train', 'i coach', 'im a trainer',
            "i'm a trainer", 'fitness coach', 'gym instructor'
        ]
        
        self.client_variations = [
            'client', 'looking for trainer', 'need trainer', 'want trainer',
            'find trainer', 'get fit', 'need help', 'looking for pt',
            'need coach', 'want to train', 'fitness help', 'gym help',
            'looking for coach', 'need personal trainer'
        ]
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Convert to lowercase and remove extra spaces
        text = text.lower().strip()
        # Remove punctuation except apostrophes
        text = re.sub(r"[^\w\s']", '', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def fuzzy_match(self, text: str, variations: List[str], threshold: float = 0.8) -> bool:
        """Check if text fuzzy matches any variation"""
        normalized = self.normalize_text(text)
        
        for variation in variations:
            # Direct match
            if variation in normalized or normalized in variation:
                return True
            
            # Fuzzy match using SequenceMatcher
            similarity = SequenceMatcher(None, normalized, variation).ratio()
            if similarity >= threshold:
                return True
            
            # Word-level match
            words = normalized.split()
            var_words = variation.split()
            if any(word in var_words for word in words):
                if len(words) <= 3:  # Short responses
                    return True
        
        return False
    
    def understand_confirmation_response(self, text: str) -> str:
        """Understand user's response to confirmation prompt"""
        # Check for yes
        if self.fuzzy_match(text, self.yes_variations):
            return 'yes'
        
        # Check for no
        if self.fuzzy_match(text, self.no_variations):
            return 'no'
        
        # Check for edit
        if self.fuzzy_match(text, self.edit_variations):
            return 'edit'
        
        # Check for specific field mentions
        normalized = self.normalize_text(text)
        field_keywords = {
            'name': ['name', 'my name'],
            'email': ['email', 'mail', 'address'],
            'phone': ['phone', 'number', 'whatsapp'],
            'business': ['business', 'company', 'gym'],
            'location': ['location', 'area', 'where'],
            'price': ['price', 'rate', 'cost', 'fee'],
            'goals': ['goals', 'objectives', 'aims'],
            'emergency': ['emergency', 'contact']
        }
        
        for field, keywords in field_keywords.items():
            if any(keyword in normalized for keyword in keywords):
                return 'edit'
        
        return 'unclear'
    
    def normalize_registration_intent(self, text: str) -> Optional[str]:
        """Determine if user wants to register as trainer or client"""
        # Check for trainer intent
        if self.fuzzy_match(text, self.trainer_variations, threshold=0.7):
            return 'trainer'
        
        # Check for client intent
        if self.fuzzy_match(text, self.client_variations, threshold=0.7):
            return 'client'
        
        # Check for button responses
        normalized = self.normalize_text(text)
        if any(word in normalized for word in ['trainer', 'coach', 'pt']):
            return 'trainer'
        if any(word in normalized for word in ['client', 'find', 'looking', 'need']):
            return 'client'
        
        return None
    
    def extract_field_from_edit_request(self, text: str) -> Optional[str]:
        """Extract which field user wants to edit from their message"""
        normalized = self.normalize_text(text)
        
        # Field mappings
        field_patterns = {
            'name': r'\b(name|full name|my name)\b',
            'email': r'\b(email|mail|email address)\b',
            'phone': r'\b(phone|number|whatsapp|cell)\b',
            'business': r'\b(business|company|gym|studio)\b',
            'location': r'\b(location|area|address|where)\b',
            'price': r'\b(price|rate|cost|fee|charge)\b',
            'specialties': r'\b(specialt|skill|expertise|focus)\b',
            'goals': r'\b(goal|objective|aim|target)\b',
            'emergency': r'\b(emergency|contact person|emergency contact)\b',
            'fitness_level': r'\b(fitness level|level|experience)\b'
        }
        
        for field, pattern in field_patterns.items():
            if re.search(pattern, normalized):
                return field
        
        return None
    
    def is_skip_response(self, text: str) -> bool:
        """Check if user wants to skip a field"""
        skip_variations = [
            'skip', 'none', 'na', 'n/a', 'not applicable', 'dont have',
            "don't have", 'nothing', 'leave blank', 'blank', 'empty',
            'pass', 'next', 'no comment', '-', '--', 'nil'
        ]
        
        return self.fuzzy_match(text, skip_variations, threshold=0.85)
    
    def is_help_request(self, text: str) -> bool:
        """Check if user is asking for help"""
        help_variations = [
            'help', 'what', 'how', 'explain', 'dont understand',
            "don't understand", 'confused', 'not sure', 'what do you mean',
            'what should i', 'example', 'like what', 'such as', '?'
        ]
        
        return self.fuzzy_match(text, help_variations, threshold=0.7)
    
    def clean_price_input(self, text: str) -> Optional[float]:
        """Extract and clean price from various formats"""
        # Remove currency symbols and text
        text = re.sub(r'[Rr](?:and)?s?\.?', '', text)
        text = re.sub(r'per\s+(session|hour|class)', '', text, flags=re.IGNORECASE)
        
        # Find numbers (including decimals)
        numbers = re.findall(r'\d+(?:\.\d{2})?', text)
        
        if numbers:
            try:
                price = float(numbers[0])
                # Sanity check
                if 0 < price < 10000:
                    return price
            except ValueError:
                pass
        
        return None
    
    def clean_phone_input(self, text: str) -> Optional[str]:
        """Clean and validate phone number input"""
        # Remove all non-digits
        digits = re.sub(r'\D', '', text)
        
        # Handle different formats
        if len(digits) == 10 and digits.startswith('0'):
            # Local format: 0821234567
            return '27' + digits[1:]
        elif len(digits) == 11 and digits.startswith('27'):
            # International format: 27821234567
            return digits
        elif len(digits) == 9:
            # Missing leading 0: 821234567
            return '27' + digits
        
        return None
    
    def spell_check_common_words(self, text: str) -> str:
        """Fix common spelling mistakes in fitness context"""
        corrections = {
            'wieght': 'weight',
            'weigth': 'weight',
            'strenght': 'strength',
            'cardoi': 'cardio',
            'yogha': 'yoga',
            'pillates': 'pilates',
            'crosssfit': 'crossfit',
            'nutrtion': 'nutrition',
            'protien': 'protein',
            'suppliments': 'supplements'
        }
        
        normalized = text.lower()
        for wrong, correct in corrections.items():
            normalized = normalized.replace(wrong, correct)
        
        return normalized
```

## SUMMARY

In Step 1, I've analyzed the requirements and created two critical missing services:

1. **`services/refiloe.py`** - The main orchestration service that:
   - Routes messages and manages sessions
   - Handles session timeouts (24 hours)
   - Prevents duplicate registrations
   - Integrates with text variation handler
   - Provides graceful error handling

2. **`services/text_variation_handler.py`** - Comprehensive text handling that:
   - Recognizes yes/no/edit variations including South African terms
   - Handles typos and fuzzy matching
   - Cleans and validates input (phone, price)
   - Provides spell checking for fitness terms

These services address the core issues: missing orchestration, text variation handling, duplicate registration checks, timeout handling, and graceful error handling. Button titles are kept under 20 characters throughout.

## CONTINUE_NEEDED
Next step: Step 2: Implement validation integration and button fixes
Run @claude @continue to proceed with next step