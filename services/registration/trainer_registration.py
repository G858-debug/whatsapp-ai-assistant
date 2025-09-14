"""Trainer registration handler with friendly UX"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from services.helpers.validation_helpers import ValidationHelpers

class TrainerRegistrationHandler:
    """Handle trainer registration with delightful experience"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        self.validator = ValidationHelpers()
        
        self.STEPS = {
            0: {'field': 'name', 'prompt': self._get_name_prompt},
            1: {'field': 'business_name', 'prompt': self._get_business_prompt},
            2: {'field': 'email', 'prompt': self._get_email_prompt},
            3: {'field': 'specialization', 'prompt': self._get_specialization_prompt},
            4: {'field': 'experience', 'prompt': self._get_experience_prompt},
            5: {'field': 'location', 'prompt': self._get_location_prompt},
            6: {'field': 'pricing', 'prompt': self._get_pricing_prompt}
        }
    
    def start_registration(self, phone: str) -> str:
        """Start trainer registration with warm welcome"""
        return (
            "🎉 I'm so excited to help you grow your personal training business! "
            "Let's get you set up in just a few quick steps. Don't worry, this set up is free\n\n"
            "📝 *Step 1 of 7*\n\n"
            "First things first - what's your name and surname? 😊"
        )
    
    def handle_registration_response(self, phone: str, message: str, 
                                   current_step: int, data: Dict) -> Dict:
        """Handle registration step response"""
        try:
            step_info = self.STEPS.get(current_step)
            if not step_info:
                return self._complete_registration(phone, data)
            
            # Validate input
            field = step_info['field']
            validated = self._validate_field(field, message)
            
            if not validated['valid']:
                return {
                    'success': False,
                    'message': validated['error'],
                    'continue': True
                }
            
            # Store data
            data[field] = validated['value']
            
            # Move to next step
            next_step = current_step + 1
            
            if next_step >= len(self.STEPS):
                return self._complete_registration(phone, data)
            
            # Get next prompt
            next_prompt = self.STEPS[next_step]['prompt'](next_step + 1)
            
            return {
                'success': True,
                'message': next_prompt,
                'next_step': next_step,
                'data': data,
                'continue': True
            }
            
        except Exception as e:
            log_error(f"Error handling registration: {str(e)}")
            return {
                'success': False,
                'message': "😅 Oops! Something went wrong. Let's try that again.",
                'continue': True
            }
    
    def _get_name_prompt(self, step_num: int) -> str:
        """Get name prompt - already shown in start"""
        return ""
    
    def _get_business_prompt(self, step_num: int) -> str:
        return (
            "Perfect! 👍\n\n"
            f"📝 *Step {step_num} of 7*\n\n"
            "What's your business name? (or just type 'skip' if you don't have one yet)"
        )
    
    def _get_email_prompt(self, step_num: int) -> str:
        return (
            "Great! ✨\n\n"
            f"📝 *Step {step_num} of 7*\n\n"
            "What's your email address? 📧\n"
            "(We'll use this for important updates only)"
        )
    
    def _get_specialization_prompt(self, step_num: int) -> str:
        return (
            "Awesome! 💪\n\n"
            f"📝 *Step {step_num} of 7*\n\n"
            "What's your training specialization?\n\n"
            "Choose one or type your own:\n"
            "1️⃣ Weight Loss\n"
            "2️⃣ Muscle Building\n"
            "3️⃣ Sports Performance\n"
            "4️⃣ Functional Fitness\n"
            "5️⃣ Rehabilitation"
        )
    
    def _get_experience_prompt(self, step_num: int) -> str:
        return (
            "Nice specialization! 🎯\n\n"
            f"📝 *Step {step_num} of 7*\n\n"
            "How many years of experience do you have?\n\n"
            "Just type a number (e.g., 3)"
        )
    
    def _get_location_prompt(self, step_num: int) -> str:
        return (
            "Experience matters! 🌟\n\n"
            f"📝 *Step {step_num} of 7*\n\n"
            "Where are you based? (City/Area)\n"
            "Example: Cape Town, Sea Point"
        )
    
    def _get_pricing_prompt(self, step_num: int) -> str:
        return (
            "Almost done! 🏁\n\n"
            f"📝 *Step {step_num} of 7* (Last one!)\n\n"
            "What's your standard rate per session?\n"
            "Just type the amount (e.g., 350)"
        )
    
    def _validate_field(self, field: str, value: str) -> Dict:
        """Validate registration field with friendly errors"""
        value = value.strip()
        
        if field == 'name':
            if len(value) < 2:
                return {
                    'valid': False,
                    'error': "😊 Please enter your full name (at least 2 characters)"
                }
            return {'valid': True, 'value': value}
        
        elif field == 'business_name':
            if value.lower() == 'skip':
                return {'valid': True, 'value': None}
            return {'valid': True, 'value': value}
        
        elif field == 'email':
            if not self.validator.validate_email(value):
                return {
                    'valid': False,
                    'error': "📧 Hmm, that doesn't look like a valid email. Please try again!\nExample: john@gmail.com"
                }
            return {'valid': True, 'value': value.lower()}
        
        elif field == 'specialization':
            spec_map = {
                '1': 'Weight Loss',
                '2': 'Muscle Building',
                '3': 'Sports Performance',
                '4': 'Functional Fitness',
                '5': 'Rehabilitation'
            }
            
            if value in spec_map:
                return {'valid': True, 'value': spec_map[value]}
            elif len(value) >= 3:
                return {'valid': True, 'value': value}
            else:
                return {
                    'valid': False,
                    'error': "Please choose a number (1-5) or type your specialization"
                }
        
        elif field == 'experience':
            try:
                years = int(value)
                if 0 <= years <= 50:
                    return {'valid': True, 'value': years}
                else:
                    return {
                        'valid': False,
                        'error': "🤔 Please enter a valid number of years (0-50)"
                    }
            except ValueError:
                return {
                    'valid': False,
                    'error': "Please enter just a number (e.g., 5)"
                }
        
        elif field == 'location':
            if len(value) < 3:
                return {
                    'valid': False,
                    'error': "📍 Please enter your city or area"
                }
            return {'valid': True, 'value': value}
        
        elif field == 'pricing':
            price = self.validator.extract_price(value)
            if price and 50 <= price <= 5000:
                return {'valid': True, 'value': price}
            else:
                return {
                    'valid': False,
                    'error': "💰 Please enter a valid amount between R50 and R5000\nExample: 350"
                }
        
        return {'valid': True, 'value': value}
    
    def _complete_registration(self, phone: str, data: Dict) -> Dict:
        """Complete registration with celebration"""
        try:
            # Split the name into first and last
            full_name = data['name']
            name_parts = full_name.strip().split(' ', 1)  # Split on first space only
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Create trainer record
            trainer_data = {
                'name': full_name,  # Keep full name for compatibility
                'first_name': first_name,  # Store first name separately
                'last_name': last_name,    # Store last name separately
                'whatsapp': phone,
                'email': data['email'],
                'business_name': data.get('business_name'),
                'specialization': data.get('specialization'),
                'years_experience': data.get('experience', 0),
                'location': data.get('location'),
                'pricing_per_session': data.get('pricing', 300),
                'status': 'active',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('trainers').insert(trainer_data).execute()
            
            if result.data:
                trainer_id = result.data[0]['id']
                log_info(f"Trainer registered: {full_name} ({trainer_id})")
                
                # Create celebration message using first name only for friendliness
                celebration = (
                    "🎊 *CONGRATULATIONS!* 🎊\n\n"
                    f"Welcome aboard, {first_name}! You're all set up and ready to grow "
                    "your training business with Refiloe! 🚀\n\n"
                    "Here's what you can do now:\n\n"
                    "💡 *Quick Actions:*"
                )
                
                # Create buttons with <20 char titles
                buttons = [
                    {'id': 'add_client', 'title': '➕ Add First Client'},
                    {'id': 'view_dashboard', 'title': '📊 View Dashboard'},
                    {'id': 'help', 'title': '❓ Get Help'}
                ]
                
                return {
                    'success': True,
                    'message': celebration,
                    'buttons': buttons,
                    'continue': False,
                    'trainer_id': trainer_id
                }
            else:
                return {
                    'success': False,
                    'message': "😔 Registration failed. Please try again or contact support.",
                    'continue': False
                }
                
        except Exception as e:
            log_error(f"Error completing registration: {str(e)}")
            return {
                'success': False,
                'message': "😅 Almost there! We hit a small snag. Please try again.",
                'continue': False
            }

    def process_step(self, phone: str, response: str, current_step: int) -> Dict:
        """Process a registration step response"""
        try:
            # Get or create session data
            session = self.get_or_create_session(phone)
            
            # Handle the current step
            if current_step == 0:  # Name
                session['name'] = response
                next_message = self._get_business_prompt(2)  # Pass step 2 of 7
                next_step = 1
            elif current_step == 1:  # Business name
                if response.lower() != 'skip':
                    session['business_name'] = response
                next_message = self._get_email_prompt(3)  # Pass step 3 of 7
                next_step = 2
            elif current_step == 2:  # Email
                # Validate email
                if '@' not in response:
                    return {
                        'message': "🤔 That doesn't look like a valid email. Please enter a valid email address:",
                        'next_step': current_step,  # Stay on same step
                        'complete': False
                    }
                session['email'] = response
                next_message = self._get_specialization_prompt(4)  # Pass step 4 of 7
                next_step = 3
            elif current_step == 3:  # Specialization
                session['specialization'] = response
                next_message = self._get_experience_prompt(5)  # Pass step 5 of 7
                next_step = 4
            elif current_step == 4:  # Experience
                session['experience'] = response
                next_message = self._get_location_prompt(6)  # Pass step 6 of 7
                next_step = 5
            elif current_step == 5:  # Location
                session['location'] = response
                next_message = self._get_pricing_prompt(7)  # Pass step 7 of 7
                next_step = 6
            elif current_step == 6:  # Pricing
                session['pricing'] = response
                # Complete registration
                return self._complete_registration(phone, session)
            else:
                return {
                    'message': "I'm a bit confused. Let's start over. What's your name?",
                    'next_step': 0,
                    'complete': False
                }
            
            # Save session data
            self.save_session(phone, session)
            
            # Add step indicator with encouragement
            total_steps = 7
            step_message = next_message
            
            return {
                'message': step_message,
                'next_step': next_step,
                'complete': False
            }
            
        except Exception as e:
            log_error(f"Error processing step: {str(e)}")
            return {
                'message': "Sorry, I had trouble processing that. Could you please try again?",
                'next_step': current_step,
                'complete': False
            }
    
    def get_or_create_session(self, phone: str) -> Dict:
        """Get or create registration session data"""
        # This would retrieve from a database or cache
        # For now, using a simple in-memory approach
        if not hasattr(self, '_sessions'):
            self._sessions = {}
        
        if phone not in self._sessions:
            self._sessions[phone] = {}
        
        return self._sessions[phone]
    
    def save_session(self, phone: str, data: Dict):
        """Save session data"""
        if not hasattr(self, '_sessions'):
            self._sessions = {}
        self._sessions[phone] = data
