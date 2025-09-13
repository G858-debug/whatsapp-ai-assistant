"""Client registration handler"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from services.helpers.validation_helpers import ValidationHelpers

class ClientRegistrationHandler:
    """Handles client registration flow"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.validation = ValidationHelpers()
        from services.refiloe_helpers import RefiloeHelpers
        self.helpers = RefiloeHelpers(supabase_client, None, config)
        
        # Registration steps
        self.STEPS = ['fitness_goal', 'training_preference', 'city', 'personal_info', 'confirmation']
    
    def start_client_registration(self, phone: str) -> Dict:
        """Start client registration process"""
        try:
            # Check if already registered
            existing = self.db.table('clients').select('id').eq(
                'whatsapp', phone
            ).execute()
            
            if existing.data:
                return {
                    'success': True,
                    'message': "You're already registered! 😊\n\nHow can I help you today?",
                    'already_registered': True
                }
            
            # Create registration session
            from services.registration.registration_state import RegistrationStateManager
            state_manager = RegistrationStateManager(self.db, self.config)
            session_id = state_manager.create_session(phone, 'client', initial_step='fitness_goal')
            
            if session_id:
                # Delegate to helpers for the first step
                return self.helpers._handle_client_registration_start(session_id)
            
            return {
                'success': False,
                'message': "Sorry, I couldn't start the registration. Please try again."
            }
    
    def process_client_step(self, session_id: str, step: str, input_text: str) -> Dict:
    """Process a registration step - delegates to RefiloeHelpers for special steps"""
    try:
        # Special handling for interactive steps
        if step == 'fitness_goal':
            return self.helpers._handle_client_goal_selection(session_id, input_text)
        elif step == 'training_preference':
            return self.helpers._handle_client_training_preference(session_id, input_text)
        elif step == 'city':
            return self.helpers._handle_client_city_input(session_id, input_text)
        elif step == 'personal_info':
            return self.helpers._handle_client_personal_info(session_id, input_text)
        elif step == 'confirmation':
            return self.helpers.confirm_client_registration(session_id, input_text)
        
            # Validate input
            validation_result = self._validate_step_input(step, input_text)
            if not validation_result['valid']:
                return {
                    'success': True,
                    'message': validation_result['message'],
                    'next_step': step
                }
            
            # Update session
            from services.registration.registration_state import RegistrationStateManager
            state_manager = RegistrationStateManager(self.db, self.config)
            
            next_step = self._get_next_step(step)
            
            update_result = state_manager.update_session(
                session_id,
                step=next_step,
                data_update={step: validation_result['value']}
            )
            
            if not update_result['success']:
                return {
                    'success': False,
                    'message': "Session expired. Please start again."
                }
            
            # Get appropriate response
            if next_step == 'confirmation':
                return self._build_confirmation_message(update_result['session']['data'])
            else:
                return self._get_step_prompt(next_step)
                
        except Exception as e:
            log_error(f"Error processing client step: {str(e)}")
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
        
        elif step == 'emergency_contact':
            if len(input_text) < 2:
                return {'valid': False, 'message': "Please enter the name of your emergency contact."}
            return {'valid': True, 'value': input_text}
        
        elif step == 'emergency_phone':
            phone = self.validation.format_phone_number(input_text)
            if not phone:
                return {'valid': False, 'message': "Please enter a valid phone number (e.g., 0821234567)"}
            return {'valid': True, 'value': phone}
        
        elif step == 'fitness_level':
            valid_levels = ['beginner', 'intermediate', 'advanced']
            level_lower = input_text.lower()
            
            # Map variations
            if any(word in level_lower for word in ['begin', 'new', 'start']):
                return {'valid': True, 'value': 'beginner'}
            elif any(word in level_lower for word in ['inter', 'medium', 'some']):
                return {'valid': True, 'value': 'intermediate'}
            elif any(word in level_lower for word in ['adv', 'expert', 'pro']):
                return {'valid': True, 'value': 'advanced'}
            else:
                return {
                    'valid': False, 
                    'message': "Please choose: Beginner, Intermediate, or Advanced"
                }
        
        elif step == 'goals':
            if len(input_text) < 5:
                return {'valid': False, 'message': "Please describe your fitness goals."}
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
            'emergency_contact': {
                'message': "🚨 Who should we contact in case of emergency?\n(Name of person)",
                'next_step': 'emergency_contact'
            },
            'emergency_phone': {
                'message': "📞 What's their phone number?",
                'next_step': 'emergency_phone'
            },
            'fitness_level': {
                'message': "💪 What's your current fitness level?",
                'buttons': [
                    {
                        'type': 'reply',
                        'reply': {
                            'id': 'level_beginner',
                            'title': '🌱 Beginner'  # 11 chars
                        }
                    },
                    {
                        'type': 'reply',
                        'reply': {
                            'id': 'level_intermediate',
                            'title': '🏃 Intermediate'  # 15 chars
                        }
                    },
                    {
                        'type': 'reply',
                        'reply': {
                            'id': 'level_advanced',
                            'title': '🔥 Advanced'  # 11 chars
                        }
                    }
                ],
                'next_step': 'fitness_level'
            },
            'goals': {
                'message': "🎯 What are your fitness goals?\n(e.g., Weight loss, Muscle gain, Better health)",
                'next_step': 'goals'
            }
        }
        
        result = prompts.get(step, {
            'message': "Please provide the required information.",
            'next_step': step
        })
        
        result['success'] = True
        return result
    
    def _build_confirmation_message(self, data: Dict) -> Dict:
        """Build confirmation message"""
        message = f"""✅ *Registration Summary*

*Name:* {data.get('name', 'Not provided')}
*Emergency Contact:* {data.get('emergency_contact', 'Not provided')}
*Emergency Phone:* {data.get('emergency_phone', 'Not provided')}
*Fitness Level:* {data.get('fitness_level', 'Not provided')}
*Goals:* {data.get('goals', 'Not provided')}

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
    
    def confirm_client_registration(self, session_id: str, response: str) -> Dict:
        """Process confirmation response"""
        try:
            from services.registration.registration_state import RegistrationStateManager
            state_manager = RegistrationStateManager(self.db, self.config)
            
            session = state_manager.get_session(session_id)
            if not session:
                return {
                    'success': False,
                    'message': 'Session expired. Please start over.'
                }
            
            if response.lower() == 'yes':
                # Create client account
                client_data = {
                    'whatsapp': session['phone'],
                    'name': session['data'].get('name'),
                    'emergency_contact_name': session['data'].get('emergency_contact'),
                    'emergency_contact_phone': session['data'].get('emergency_phone'),
                    'fitness_level': session['data'].get('fitness_level'),
                    'goals': session['data'].get('goals'),
                    'status': 'active',
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }
                
                # Note: We're not assigning a trainer yet - that happens separately
                result = self.db.table('clients').insert(client_data).execute()
                
                if result.data:
                    state_manager.update_session_status(session_id, 'completed')
                    
                    return {
                        'success': True,
                        'message': """🎉 *Welcome to your fitness journey!*

Your account is ready!

We'll help you find the perfect trainer.

What would you like to do?
• Browse trainers: "show trainers"
• Get matched: "find trainer for me"
• Learn more: "how it works"

Type 'help' anytime for assistance."""
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Failed to create account. Please try again.'
                    }
            else:
                state_manager.update_session_status(session_id, 'cancelled')
                return {
                    'success': True,
                    'message': "Registration cancelled. You can start over anytime."
                }
                
        except Exception as e:
            log_error(f"Error confirming registration: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred. Please try again.'
            }
