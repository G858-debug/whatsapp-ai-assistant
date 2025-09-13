"""Trainer registration handler"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from services.helpers.validation_helpers import ValidationHelpers
from services.helpers.whatsapp_helpers import WhatsAppHelpers

class TrainerRegistrationHandler:
    """Handles trainer registration flow"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.validation = ValidationHelpers()
        self.whatsapp_helpers = WhatsAppHelpers()
        
        # Registration steps
        self.STEPS = ['name', 'email', 'business', 'location', 'price', 'specialties', 'confirmation']
    
    def start_trainer_registration(self, phone: str) -> Dict:
        """Start trainer registration process"""
        try:
            # Check if already registered
            existing = self.db.table('trainers').select('id').eq(
                'whatsapp', phone
            ).execute()
            
            if existing.data:
                return {
                    'success': True,
                    'message': "You're already registered as a trainer! 😊\n\nHow can I help you today?",
                    'already_registered': True
                }
            
            # Create registration session
            from services.registration.registration_state import RegistrationStateManager
            state_manager = RegistrationStateManager(self.db, self.config)
            result = state_manager.create_session(phone, 'trainer')
            
            if result['success']:
                return {
                    'success': True,
                    'message': "Welcome to Refiloe! 🎉\n\nLet's get you set up as a trainer.\n\nWhat's your full name?",
                    'session_id': result['session_id'],
                    'next_step': 'name'
                }
            
            return {
                'success': False,
                'message': "Sorry, I couldn't start the registration. Please try again."
            }
            
        except Exception as e:
            log_error(f"Error starting trainer registration: {str(e)}")
            return {
                'success': False,
                'message': "An error occurred. Please try again."
            }
    
    def process_trainer_step(self, session_id: str, step: str, input_text: str) -> Dict:
        """Process a registration step"""
        try:
            # Validate input
            validation_result = self._validate_step_input(step, input_text)
            if not validation_result['valid']:
                return {
                    'success': True,
                    'message': validation_result['message'],
                    'next_step': step  # Stay on same step
                }
            
            # Update session with validated data
            from services.registration.registration_state import RegistrationStateManager
            state_manager = RegistrationStateManager(self.db, self.config)
            
            # Get next step
            next_step = self._get_next_step(step)
            
            # Update session
            update_result = state_manager.update_session(
                session_id,
                step=next_step,
                data_update={step: validation_result['value']}
            )
            
            if not update_result['success']:
                return {
                    'success': False,
                    'message': "Session expired. Please start again by saying 'register'."
                }
            
            # Get appropriate response
            if next_step == 'confirmation':
                return self._build_confirmation_message(update_result['session']['data'])
            else:
                return self._get_step_prompt(next_step)
                
        except Exception as e:
            log_error(f"Error processing trainer step: {str(e)}")
            return {
                'success': False,
                'message': "An error occurred. Please try again."
            }
    
    def _validate_step_input(self, step: str, input_text: str) -> Dict:
        """Validate input for a specific step"""
        input_text = input_text.strip()
        
        if step == 'name':
            if len(input_text) < 2:
                return {'valid': False, 'message': "Please enter your full name."}
            return {'valid': True, 'value': input_text}
        
        elif step == 'email':
            if not self.validation.validate_email(input_text):
                return {'valid': False, 'message': "Please enter a valid email address (e.g., name@example.com)"}
            return {'valid': True, 'value': input_text.lower()}
        
        elif step == 'business':
            if len(input_text) < 2:
                return {'valid': False, 'message': "Please enter your business or gym name."}
            return {'valid': True, 'value': input_text}
        
        elif step == 'location':
            if len(input_text) < 2:
                return {'valid': False, 'message': "Please enter your location (e.g., Sandton, Cape Town)"}
            return {'valid': True, 'value': input_text}
        
        elif step == 'price':
            price = self.validation.extract_price(input_text)
            if not price:
                return {'valid': False, 'message': "Please enter a valid price (e.g., R500 or 500)"}
            if price < 50 or price > 5000:
                return {'valid': False, 'message': "Please enter a price between R50 and R5000"}
            return {'valid': True, 'value': price}
        
        elif step == 'specialties':
            if len(input_text) < 3:
                return {'valid': False, 'message': "Please describe your training specialties."}
            return {'valid': True, 'value': input_text}
        
        return {'valid': True, 'value': input_text}
    
    def _get_next_step(self, current_step: str) -> str:
        """Get the next registration step"""
        try:
            current_index = self.STEPS.index(current_step)
            if current_index < len(self.STEPS) - 1:
                return self.STEPS[current_index + 1]
            return 'confirmation'
        except ValueError:
            return 'confirmation'
    
    def _get_step_prompt(self, step: str) -> Dict:
        """Get prompt for a registration step"""
        prompts = {
            'email': {
                'message': "📧 Great! What's your email address?",
                'next_step': 'email'
            },
            'business': {
                'message': "🏢 What's your business or gym name?",
                'next_step': 'business'
            },
            'location': {
                'message': "📍 Where are you located? (City/Area)",
                'next_step': 'location'
            },
            'price': {
                'message': "💰 What's your standard rate per session?\n(e.g., R500)",
                'next_step': 'price'
            },
            'specialties': {
                'message': "💪 What are your training specialties?\n(e.g., Weight loss, Strength training, HIIT)",
                'next_step': 'specialties'
            }
        }
        
        result = prompts.get(step, {
            'message': "Please provide the required information.",
            'next_step': step
        })
        
        result['success'] = True
        return result
    
    def _build_confirmation_message(self, data: Dict) -> Dict:
        """Build confirmation message with buttons"""
        message = f"""✅ *Registration Summary*

*Name:* {data.get('name', 'Not provided')}
*Email:* {data.get('email', 'Not provided')}
*Business:* {data.get('business', 'Not provided')}
*Location:* {data.get('location', 'Not provided')}
*Rate:* R{data.get('price', 'Not provided')}/session
*Specialties:* {data.get('specialties', 'Not provided')}

Is this information correct?"""
        
        return {
            'success': True,
            'message': message,
            'buttons': [
                {
                    'type': 'reply',
                    'reply': {
                        'id': 'confirm_yes',
                        'title': '✅ Yes'  # 5 chars
                    }
                },
                {
                    'type': 'reply',
                    'reply': {
                        'id': 'confirm_edit',
                        'title': '✏️ Edit'  # 6 chars
                    }
                },
                {
                    'type': 'reply',
                    'reply': {
                        'id': 'confirm_no',
                        'title': '❌ Cancel'  # 8 chars
                    }
                }
            ],
            'next_step': 'confirmation'
        }
    
    def _confirm_trainer_registration(self, session_id: str, response: str) -> Dict:
        """Process confirmation response"""
        try:
            from services.registration.registration_state import RegistrationStateManager
            state_manager = RegistrationStateManager(self.db, self.config)
            
            # Get session
            session = state_manager.get_session(session_id)
            if not session:
                return {
                    'success': False,
                    'message': 'Session expired. Please start over.'
                }
            
            if response.lower() == 'yes':
                # Create trainer account
                trainer_data = {
                    'whatsapp': session['phone'],
                    'name': session['data'].get('name'),
                    'email': session['data'].get('email'),
                    'business_name': session['data'].get('business'),
                    'location': session['data'].get('location'),
                    'pricing_per_session': session['data'].get('price'),
                    'specialties': session['data'].get('specialties'),
                    'status': 'active',
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }
                
                result = self.db.table('trainers').insert(trainer_data).execute()
                
                if result.data:
                    # Mark session as completed
                    state_manager.update_session_status(session_id, 'completed')
                    
                    return {
                        'success': True,
                        'message': """🎉 *Welcome to Refiloe!*

Your trainer account is now active!

Here's what you can do:
• Add clients: "add client"
• Create workouts: "create workout"
• Schedule sessions: "book session"
• View dashboard: "my dashboard"

Type 'help' anytime for assistance."""
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Failed to create account. Please try again.'
                    }
            else:
                # User wants to edit or cancel
                state_manager.update_session_status(session_id, 'cancelled')
                return {
                    'success': True,
                    'message': "Registration cancelled. You can start over anytime by saying 'register'."
                }
                
        except Exception as e:
            log_error(f"Error confirming registration: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred. Please try again.'
            }