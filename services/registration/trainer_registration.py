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
    
    def get_or_create_session(self, phone: str) -> Dict:
        """Get or create registration session data from database"""
        try:
            # Check if there's an existing incomplete registration in the database
            existing = self.db.table('registration_states').select('*').eq(
                'phone_number', phone
            ).eq('user_type', 'trainer').eq(
                'completed', False
            ).execute()
            
            if existing.data and len(existing.data) > 0:
                return existing.data[0].get('data', {})
            
            # Fall back to in-memory session if database not available
            if not hasattr(self, '_sessions'):
                self._sessions = {}
            
            if phone not in self._sessions:
                self._sessions[phone] = {}
            
            return self._sessions[phone]
            
        except Exception as e:
            log_error(f"Error getting session from database for {phone}: {str(e)}")
            # Fall back to in-memory storage
            if not hasattr(self, '_sessions'):
                self._sessions = {}
            
            if phone not in self._sessions:
                self._sessions[phone] = {}
            
            return self._sessions[phone]
    
    def save_session(self, phone: str, data: Dict, current_step: int = None):
        """Save session data to database and memory"""
        try:
            # Always save to memory as backup
            if not hasattr(self, '_sessions'):
                self._sessions = {}
            self._sessions[phone] = data
            
            # Try to save to database
            existing = self.db.table('registration_states').select('*').eq(
                'phone_number', phone
            ).eq('user_type', 'trainer').eq(
                'completed', False
            ).execute()
            
            session_data = {
                'phone_number': phone,
                'user_type': 'trainer',
                'current_step': current_step if current_step is not None else 0,
                'data': data,
                'completed': False,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if existing.data and len(existing.data) > 0:
                # Update existing session
                self.db.table('registration_states').update(
                    session_data
                ).eq('id', existing.data[0]['id']).execute()
            else:
                # Create new session
                session_data['created_at'] = datetime.now(self.sa_tz).isoformat()
                self.db.table('registration_states').insert(session_data).execute()
                
        except Exception as e:
            log_error(f"Error saving session to database for {phone}: {str(e)}")
            # Continue with in-memory storage even if database fails
    
    def start_registration(self, phone: str) -> str:
        """Start trainer registration with warm welcome"""

        # Check if already registered
        try:
            existing = self.db.table('trainers').select('id', 'first_name').eq('whatsapp', phone).execute()
            if existing.data and len(existing.data) > 0:
                name = existing.data[0].get('first_name', 'there')
                return f"Welcome back, {name}! You're already registered. How can I help you today?"
        except Exception as e:
            log_error(f"Error checking existing registration: {str(e)}")
            
        # Check for existing incomplete registration
        session_data = self.get_or_create_session(phone)
        
        if session_data and len(session_data) > 0:
            # They have some data from a previous attempt
            name = session_data.get('name', 'there')
            return (
                f"👋 Welcome back{', ' + name if name != 'there' else ''}! "
                "I see you started registering before.\n\n"
                "Would you like to:\n"
                "1️⃣ Continue where you left off\n"
                "2️⃣ Start fresh\n\n"
                "Just type 1 or 2"
            )
        
        # Normal welcome message for new registration
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
            # Handle continuation choice if they're resuming
            if message.strip() in ['1', '2'] and current_step == -1:
                if message.strip() == '1':
                    # Continue from where they left off
                    session_data = self.get_or_create_session(phone)
                    # Find the last completed step
                    last_step = len([k for k in ['name', 'business_name', 'email', 
                                                 'specialization', 'experience', 
                                                 'location', 'pricing'] 
                                    if k in session_data])
                    if last_step < len(self.STEPS):
                        next_prompt = self.STEPS[last_step]['prompt'](last_step + 1)
                        return {
                            'success': True,
                            'message': f"Great! Let's continue...\n\n{next_prompt}",
                            'next_step': last_step,
                            'data': session_data,
                            'continue': True
                        }
                else:
                    # Start fresh - clear old data
                    self.save_session(phone, {}, 0)
                    return {
                        'success': True,
                        'message': "No problem! Let's start fresh.\n\n📝 *Step 1 of 7*\n\nWhat's your name and surname? 😊",
                        'next_step': 0,
                        'data': {},
                        'continue': True
                    }
            
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
            
            # Save session after each successful step
            self.save_session(phone, data, current_step)
            
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
            "Great ✨\n\n"
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
            "Experience matters! 👍\n\n"
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
                'pricing_per_session': self._parse_currency(data.get('pricing', 300)),
                'status': 'active',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('trainers').insert(trainer_data).execute()
            
            if result.data:
                trainer_id = result.data[0]['id']
                log_info(f"Trainer registered: {full_name} ({trainer_id})")
                
                # Mark registration as complete in session
                try:
                    self.db.table('registration_states').update({
                        'completed': True,
                        'completed_at': datetime.now(self.sa_tz).isoformat()
                    }).eq('phone_number', phone).eq('user_type', 'trainer').execute()
                except Exception as e:
                    log_error(f"Error marking registration complete: {str(e)}")
                
                # Clear in-memory session
                if hasattr(self, '_sessions') and phone in self._sessions:
                    del self._sessions[phone]
                
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
                # Try to extract the price intelligently
                price = self.validator.extract_price(response)
                
                if price and 50 <= price <= 5000:
                    session['pricing'] = price
                    # Save session before attempting completion
                    self.save_session(phone, session, current_step)
                    
                    # Complete registration
                    result = self._complete_registration(phone, session)
                    
                    if result.get('success'):
                        return result
                    else:
                        # If completion failed, show the error but stay on pricing step
                        return {
                            'message': "😅 Almost there! There was an issue saving your info. Let's try your rate again (e.g., 350):",
                            'next_step': 6,  # Stay on pricing step
                            'complete': False
                        }
                else:
                    # Invalid price format or out of range
                    return {
                        'message': "💰 I couldn't understand that amount. Please enter your rate per session between R50 and R5000\n\nExamples: 350, R450, or 250 Rands",
                        'next_step': 6,  # Stay on pricing step
                        'complete': False
                    }
            else:
                # Unknown step - shouldn't happen but handle gracefully
                return {
                    'message': "I'm a bit confused. Let's continue with your registration. What's your name?",
                    'next_step': 0,
                    'complete': False
                }
            
            # Save session data after each successful step
            self.save_session(phone, session, next_step)
            
            # Return the next message
            return {
                'message': next_message,
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

    def _parse_currency(self, value):
        """Parse currency value to numeric"""
        if isinstance(value, (int, float)):
            return value
        
        import re
        # Handle string values like "R450", "450", "R 450"
        text = str(value).strip()
        # Remove R, commas, spaces
        text = re.sub(r'[Rr,\s]', '', text)
        # Remove "per session" etc
        text = re.sub(r'per.*', '', text, flags=re.IGNORECASE)
        
        try:
            return float(text) if text else 300
        except:
            return 300
