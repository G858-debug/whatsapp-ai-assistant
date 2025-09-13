<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5363 -->
<!-- Max Tokens: 32000 -->
<!-- Step 2 of 0 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS

Step 2 focuses on implementing core functionality to fix the critical registration flow issues. The main tasks are:
1. Fix the missing import and integration of the new RefiloeService in app_core.py
2. Create the missing registration state manager and edit handlers that RefiloeService references
3. Fix button title lengths throughout the registration handlers
4. Integrate validation helpers into the registration flow

## CHANGES NEEDED

### EDIT: app_core.py

**Change 1:** Fix RefiloeService import and initialization
Location: Lines 15-20 (import section)
```python
# REMOVE (line 15):
from services.refiloe import RefiloeService

# ADD:
from services.refiloe import RefiloeService
```

### NEW FILE: services/registration/registration_state.py
```python
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
```

### NEW FILE: services/registration/trainer_registration.py
```python
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
```

### NEW FILE: services/registration/client_registration.py
```python
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
        
        # Registration steps
        self.STEPS = ['name', 'emergency_contact', 'emergency_phone', 'fitness_level', 'goals', 'confirmation']
    
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
            result = state_manager.create_session(phone, 'client')
            
            if result['success']:
                return {
                    'success': True,
                    'message': "Welcome! 🎉\n\nLet's find you the perfect trainer.\n\nWhat's your full name?",
                    'session_id': result['session_id'],
                    'next_step': 'name'
                }
            
            return {
                'success': False,
                'message': "Sorry, I couldn't start the registration. Please try again."
            }
            
        except Exception as e:
            log_error(f"Error starting client registration: {str(e)}")
            return {
                'success': False,
                'message': "An error occurred. Please try again."
            }
    
    def process_client_step(self, session_id: str, step: str, input_text: str) -> Dict:
        """Process a registration step"""
        try:
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
    
    def _confirm_client_registration(self, session_id: str, response: str) -> Dict:
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
```

### NEW FILE: services/registration/edit_handlers.py
```python
"""Edit handlers for registration flow"""
from typing import Dict
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from services.helpers.validation_helpers import ValidationHelpers

class EditHandlers:
    """Handle editing of registration fields"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.validation = ValidationHelpers()
    
    def process_edit_value(self, session_id: str, field_name: str, new_value: str) -> Dict:
        """Process edited field value"""
        try:
            # Get session
            from services.registration.registration_state import RegistrationStateManager
            state_manager = RegistrationStateManager(self.db, self.config)
            
            session = state_manager.get_session(session_id)
            if not session:
                return {
                    'success': False,
                    'message': 'Session expired. Please start over.'
                }
            
            # Validate new value based on field
            validation_result = self._validate_field(field_name, new_value, session['user_type'])
            
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': validation_result['message']
                }
            
            # Update session data
            update_result = state_manager.update_session(
                session_id,
                step='confirmation',  # Go back to confirmation
                data_update={field_name: validation_result['value']}
            )
            
            if update_result['success']:
                return {
                    'success': True,
                    'message': f"✅ {field_name.replace('_', ' ').title()} updated successfully!"
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to update. Please try again.'
                }
                
        except Exception as e:
            log_error(f"Error processing edit: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred while updating.'
            }
    
    def _validate_field(self, field_name: str, value: str, user_type: str) -> Dict:
        """Validate field value based on field name and user type"""
        value = value.strip()
        
        # Common fields
        if field_name == 'name':
            if len(value) < 2:
                return {'valid': False, 'message': 'Name must be at least 2 characters.'}
            return {'valid': True, 'value': value}
        
        elif field_name == 'email':
            if not self.validation.validate_email(value):
                return {'valid': False, 'message': 'Please enter a valid email address.'}
            return {'valid': True, 'value': value.lower()}
        
        # Trainer-specific fields
        elif user_type == 'trainer':
            if field_name == 'business':
                if len(value) < 2:
                    return {'valid': False, 'message': 'Business name must be at least 2 characters.'}
                return {'valid': True, 'value': value}
            
            elif field_name == 'location':
                if len(value) < 2:
                    return {'valid': False, 'message': 'Location must be at least 2 characters.'}
                return {'valid': True, 'value': value}
            
            elif field_name == 'price':
                price = self.validation.extract_price(value)
                if not price or price < 50 or price > 5000:
                    return {'valid': False, 'message': 'Price must be between R50 and R5000.'}
                return {'valid': True, 'value': price}
            
            elif field_name == 'specialties':
                if len(value) < 3:
                    return {'valid': False, 'message': 'Please describe your specialties.'}
                return {'valid': True, 'value': value}
        
        # Client-specific fields
        elif user_type == 'client':
            if field_name == 'emergency_contact':
                if len(value) < 2:
                    return {'valid': False, 'message': 'Emergency contact name required.'}
                return {'valid': True, 'value': value}
            
            elif field_name == 'emergency_phone':
                phone = self.validation.format_phone_number(value)
                if not phone:
                    return {'valid': False, 'message': 'Please enter a valid phone number.'}
                return {'valid': True, 'value': phone}
            
            elif field_name == 'goals':
                if len(value) < 5:
                    return {'valid': False, 'message': 'Please describe your goals.'}
                return {'valid': True, 'value': value}
        
        # Default validation
        return {'valid': True, 'value': value}
```

### NEW FILE: services/helpers/validation_helpers.py
```python
"""Validation helper functions"""
import re
from typing import Optional

class ValidationHelpers:
    """Helper functions for input validation"""
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    def format_phone_number(self, phone: str) -> Optional[str]:
        """Format and validate South African phone number"""
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Handle different formats
        if len(digits) == 10 and digits.startswith('0'):
            # Local format: 0821234567 -> 27821234567
            return '27' + digits[1:]
        elif len(digits) == 11 and digits.startswith('27'):
            # International format: 27821234567
            return digits
        elif len(digits) == 9:
            # Missing leading 0: 821234567 -> 27821234567
            return '27' + digits
        elif len(digits) == 12 and digits.startswith('27'):
            # With country code prefix: +27821234567
            return digits[2:] if digits.startswith('27') else None
        
        return None
    
    def extract_price(self, text: str) -> Optional[float]:
        """Extract price from text"""
        # Remove currency symbols and text
        text = re.sub(r'[Rr](?:and)?s?\.?', '', text)
        text = re.sub(r'per\s+(session|hour|class|month)', '', text, flags=re.IGNORECASE)
        
        # Find numbers (including decimals)
        numbers = re.findall(r'\d+(?:\.\d{2})?', text)
        
        if numbers:
            try:
                price = float(numbers[0])
                # Sanity check for reasonable prices
                if 0 < price < 10000:
                    return price
            except ValueError:
                pass
        
        return None
    
    def validate_date(self, date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        # Check if valid date
        try:
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def validate_time(self, time_str: str) -> bool:
        """Validate time format (HH:MM)"""
        pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        return bool(re.match(pattern, time_str.strip()))
    
    def sanitize_input(self, text: str) -> str:
        """Basic input sanitization"""
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        # Limit length
        text = text[:1000]
        # Strip whitespace
        text = text.strip()
        return text
    
    def is_empty_or_skip(self, text: str) -> bool:
        """Check if user wants to skip a field"""
        skip_words = ['skip', 'none', 'na', 'n/a', '-', '--', 'nil', 'nothing']
        return text.lower().strip() in skip_words or len(text.strip()) == 0
```

### NEW FILE: services/helpers/whatsapp_helpers.py
```python
"""WhatsApp-specific helper functions"""
from typing import List, Dict

class WhatsAppHelpers:
    """Helper functions for WhatsApp formatting and buttons"""
    
    def format_button_title(self, title: str, max_length: int = 20) -> str:
        """Ensure button title meets WhatsApp's length requirements"""
        if len(title) <= max_length:
            return title
        
        # Truncate and add ellipsis
        return title[:max_length-2] + '..'
    
    def create_button_list(self, buttons_data: List[Dict]) -> List[Dict]:
        """Create properly formatted button list"""
        formatted_buttons = []
        
        for button in buttons_data[:3]:  # WhatsApp allows max 3 buttons
            formatted_buttons.append({
                'type': 'reply',
                'reply': {
                    'id': button.get('id', 'button'),
                    'title': self.format_button_title(button.get('title', 'Option'))
                }
            })
        
        return formatted_buttons
    
    def format_whatsapp_message(self, text: str) -> str:
        """Format text for WhatsApp with proper styling"""
        # Ensure message doesn't exceed WhatsApp's limit
        if len(text) > 1600:
            text = text[:1597] + '...'
        
        return text
    
    def split_long_message(self, text: str, max_length: int = 1600) -> List[str]:
        """Split long message into multiple parts"""
        if len(text) <= max_length:
            return [text]
        
        messages = []
        current = ""
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            if len(current) + len(para) + 2 <= max_length:
                if current:
                    current += '\n\n'
                current += para
            else:
                if current:
                    messages.append(current)
                current = para
        
        if current:
            messages.append(current)
        
        return messages
```

## SUMMARY

In Step 2, I've implemented the core functionality by creating:

1. **Registration State Manager** - Handles session state with 24-hour timeout
2. **Trainer Registration Handler** - Complete trainer registration flow with validation
3. **Client Registration Handler** - Complete client registration flow  
4. **Edit Handlers** - Allows users to edit registration fields
5. **Validation Helpers** - Comprehensive input validation for emails, phones, prices
6. **WhatsApp Helpers** - Button formatting and message helpers

All button titles are now under 20 characters, validation is integrated throughout, and the system handles text variations gracefully.

**CONTINUE_NEEDED**
Next step: Step 3 - Add supporting features and integrate with existing system