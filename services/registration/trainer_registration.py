"""Trainer registration handler with friendly UX"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from services.helpers.validation_helpers import ValidationHelpers

class TrainerRegistrationHandler:
    """Handle trainer registration with delightful experience"""
    
    def __init__(self, supabase_client, whatsapp_service=None):
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
            existing = self.db.table('registration_states').select('*').eq(
                'phone_number', phone
            ).eq('user_type', 'trainer').eq(
                'completed', False
            ).execute()
            
            if existing.data and len(existing.data) > 0:
                return existing.data[0].get('data', {})
            
            if not hasattr(self, '_sessions'):
                self._sessions = {}
            
            if phone not in self._sessions:
                self._sessions[phone] = {}
            
            return self._sessions[phone]
            
        except Exception as e:
            log_error(f"Error getting session from database for {phone}: {str(e)}")
            if not hasattr(self, '_sessions'):
                self._sessions = {}
            
            if phone not in self._sessions:
                self._sessions[phone] = {}
            
            return self._sessions[phone]
    
    def save_session(self, phone: str, data: Dict, current_step: int = None):
        """Save session data to database and memory"""
        try:
            if not hasattr(self, '_sessions'):
                self._sessions = {}
            self._sessions[phone] = data
            
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
                self.db.table('registration_states').update(
                    session_data
                ).eq('id', existing.data[0]['id']).execute()
            else:
                session_data['created_at'] = datetime.now(self.sa_tz).isoformat()
                self.db.table('registration_states').insert(session_data).execute()
                
        except Exception as e:
            log_error(f"Error saving session to database for {phone}: {str(e)}")
    
    def start_registration(self, phone: str) -> str:
        """Start trainer registration with warm welcome"""
        try:
            existing = self.db.table('trainers').select('id', 'first_name').eq('whatsapp', phone).execute()
            if existing.data and len(existing.data) > 0:
                name = existing.data[0].get('first_name', 'there')
                return f"Welcome back, {name}! You're already registered. How can I help you today?"
        except Exception as e:
            log_error(f"Error checking existing registration: {str(e)}")
        
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
            
            field = step_info['field']
            validated = self._validate_field(field, message)
            
            if not validated['valid']:
                return {
                    'success': False,
                    'message': validated['error'],
                    'continue': True
                }
            
            data[field] = validated['value']
            self.save_session(phone, data, current_step)
            
            next_step = current_step + 1
            
            if next_step >= len(self.STEPS):
                return self._complete_registration(phone, data)
            
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
        """Get name prompt"""
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
            # Check length limit
            if len(value) > 255:
                return {
                    'valid': False,
                    'error': "😊 That name is too long. Please enter a shorter name (max 255 characters)"
                }
            if len(value) < 2:
                return {
                    'valid': False,
                    'error': "😊 Please enter your full name (at least 2 characters)"
                }
            # Truncate if still somehow too long
            return {'valid': True, 'value': value[:255]}
        
        elif field == 'business_name':
            if value.lower() == 'skip':
                return {'valid': True, 'value': None}
            return {'valid': True, 'value': value}
        
        elif field == 'email':
            if '@' not in value or '.' not in value.split('@')[1] if '@' in value else False:
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
                years = int(''.join(filter(str.isdigit, value)))
                if 0 <= years <= 50:
                    return {'valid': True, 'value': years}
                else:
                    return {
                        'valid': False,
                        'error': "🤔 Please enter a valid number of years (0-50)"
                    }
            except (ValueError, AttributeError):
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
            # Parse price from various formats
            price = self._parse_pricing(value)
            if price and 50 <= price <= 5000:
                return {'valid': True, 'value': price}
            else:
                return {
                    'valid': False,
                    'error': "💰 Please enter a valid amount between R50 and R5000\nExample: 350"
                }
        
        return {'valid': True, 'value': value}
    
    def _parse_pricing(self, value):
        """Parse pricing from various formats"""
        import re
        
        if isinstance(value, (int, float)):
            return float(value)
        
        text = str(value).strip().lower()
        
        # Remove currency symbols and words
        text = re.sub(r'[rR$]', '', text)
        text = re.sub(r'rand[s]?', '', text)
        text = re.sub(r'buck[s]?', '', text)
        text = re.sub(r'zar', '', text)
        
        # Remove spaces, commas, and other separators
        text = re.sub(r'[\s,]', '', text)
        
        # Remove "per session" etc
        text = re.sub(r'per.*', '', text)
        text = re.sub(r'/.*', '', text)
        
        try:
            return float(text) if text else None
        except:
            return None
    
    def _complete_registration(self, phone: str, data: Dict) -> Dict:
        """Complete registration with celebration"""
        try:
            full_name = data['name']
            name_parts = full_name.strip().split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Ensure pricing is numeric
            pricing = self._parse_pricing(data.get('pricing', 300))
            if not pricing:
                pricing = 300
            
            trainer_data = {
                'name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'whatsapp': phone,
                'email': data['email'],
                'business_name': data.get('business_name'),
                'specialization': data.get('specialization'),
                'years_experience': data.get('experience', 0),
                'location': data.get('location'),
                'pricing_per_session': pricing,  # Always numeric
                'status': 'active',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('trainers').insert(trainer_data).execute()
            
            if result.data:
                trainer_id = result.data[0]['id']
                log_info(f"Trainer registered: {full_name} ({trainer_id})")
                
                if hasattr(self, '_sessions') and phone in self._sessions:
                    del self._sessions[phone]
                
                celebration = (
                    "🎊 *CONGRATULATIONS!* 🎊\n\n"
                    f"Welcome aboard, {first_name}! You're all set up and ready to grow "
                    "your training business with Refiloe! 🚀\n\n"
                    "Here's what you can do now:\n\n"
                    "💡 *Quick Actions:*"
                )
                
                return {
                    'success': True,
                    'message': celebration,
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
