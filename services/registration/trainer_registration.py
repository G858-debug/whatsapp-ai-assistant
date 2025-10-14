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
    

    def _parse_currency(self, value):
        """Parse currency value to numeric"""
        if isinstance(value, (int, float)):
            return value
        
        import re
        # Remove R, spaces, commas
        cleaned = re.sub(r'[Rr,\s]', '', str(value))
        # Remove any text like "per session"
        cleaned = re.sub(r'per.*', '', cleaned, flags=re.IGNORECASE)
        
        try:
            return float(cleaned) if cleaned else 400
        except:
            return 400  # Default value

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
            # Only return early if data actually exists
            if existing and hasattr(existing, 'data') and existing.data and len(existing.data) > 0:
                name = existing.data[0].get('first_name', 'there')
                self.track_registration_analytics(phone, 'already_registered')
                return f"Welcome back, {name}! You're already registered. How can I help you today?"
        except Exception as e:
            log_error(f"Error checking existing registration: {str(e)}")
        
        # Track registration start
        self.track_registration_analytics(phone, 'started', step=0)
        
        # Continue with registration for new users
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
                # Track validation error
                self.track_registration_analytics(phone, 'validation_error', step=current_step, 
                                                error_field=field, error_message=validated['error'])
                return {
                    'success': False,
                    'message': validated['error'],
                    'continue': True
                }
            
            # Track successful step completion
            self.track_registration_analytics(phone, 'step_completed', step=current_step)
            
            data[field] = validated['value']
            next_step = current_step + 1
            self.save_session(phone, data, next_step)
            
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
            self.track_registration_analytics(phone, 'system_error', step=current_step, 
                                            error_message=str(e))
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
            # Use the validator's email validation method
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
                # Extract just digits from the input
                digit_str = ''.join(filter(str.isdigit, value))
                if not digit_str:
                    return {
                        'valid': False,
                        'error': "Please enter just a number (e.g., 5)"
                    }
                years = int(digit_str)
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
            # Use the validator's extract_price method if available
            if hasattr(self.validator, 'extract_price'):
                price = self.validator.extract_price(value)
            else:
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
            if hasattr(self.validator, 'extract_price'):
                pricing = self.validator.extract_price(str(data.get('pricing', 300)))
            else:
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
                
                # Track successful completion
                self.track_registration_analytics(phone, 'completed')
                
                # Clear session
                if hasattr(self, '_sessions') and phone in self._sessions:
                    del self._sessions[phone]
                
                # Mark registration as complete in database
                try:
                    self.db.table('registration_states').update({
                        'completed': True,
                        'completed_at': datetime.now(self.sa_tz).isoformat()
                    }).eq('phone_number', phone).eq('user_type', 'trainer').execute()
                except Exception as e:
                    log_error(f"Error marking registration complete: {str(e)}")
                
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
            self.track_registration_analytics(phone, 'completion_error', error_message=str(e))
            return {
                'success': False,
                'message': "😅 Almost there! We hit a small snag. Please try again.",
                'continue': False
            }
    
    def track_registration_analytics(self, phone: str, event: str, step: int = None, 
                                   error_field: str = None, error_message: str = None):
        """Track registration analytics for optimization"""
        try:
            analytics_data = {
                'phone_number': phone,
                'event_type': event,  # 'started', 'step_completed', 'validation_error', 'completed', 'abandoned', 'system_error', 'already_registered'
                'step_number': step,
                'timestamp': datetime.now(self.sa_tz).isoformat(),
                'user_type': 'trainer'
            }
            
            # Add error details if applicable
            if error_field:
                analytics_data['error_field'] = error_field
            if error_message:
                analytics_data['error_message'] = error_message[:500]  # Limit length
            
            # Insert analytics data
            self.db.table('registration_analytics').insert(analytics_data).execute()
            
            log_info(f"Tracked registration analytics: {phone} - {event} - step {step}")
            
        except Exception as e:
            log_error(f"Error tracking registration analytics: {str(e)}")
            # Don't let analytics errors break the registration flow
    
    def get_registration_analytics_summary(self, days: int = 7) -> Dict:
        """Get registration analytics summary for the last N days"""
        try:
            from datetime import datetime, timedelta
            
            # Calculate date range
            end_date = datetime.now(self.sa_tz)
            start_date = end_date - timedelta(days=days)
            
            # Query analytics data
            result = self.db.table('registration_analytics').select('*').gte(
                'timestamp', start_date.isoformat()
            ).lte('timestamp', end_date.isoformat()).execute()
            
            analytics_data = result.data if result.data else []
            
            # Process analytics
            summary = {
                'period_days': days,
                'total_events': len(analytics_data),
                'registrations_started': 0,
                'registrations_completed': 0,
                'validation_errors': 0,
                'system_errors': 0,
                'already_registered': 0,
                'completion_rate': 0,
                'step_drop_off': {},
                'common_errors': {},
                'error_fields': {}
            }
            
            started_phones = set()
            completed_phones = set()
            
            for event in analytics_data:
                event_type = event.get('event_type')
                step = event.get('step_number')
                phone = event.get('phone_number')
                error_field = event.get('error_field')
                error_message = event.get('error_message', '')
                
                if event_type == 'started':
                    summary['registrations_started'] += 1
                    started_phones.add(phone)
                elif event_type == 'completed':
                    summary['registrations_completed'] += 1
                    completed_phones.add(phone)
                elif event_type == 'validation_error':
                    summary['validation_errors'] += 1
                    
                    # Track error fields
                    if error_field:
                        summary['error_fields'][error_field] = summary['error_fields'].get(error_field, 0) + 1
                    
                    # Track common error messages
                    if error_message:
                        summary['common_errors'][error_message] = summary['common_errors'].get(error_message, 0) + 1
                        
                elif event_type == 'system_error':
                    summary['system_errors'] += 1
                elif event_type == 'already_registered':
                    summary['already_registered'] += 1
                
                # Track step drop-off
                if step is not None:
                    summary['step_drop_off'][step] = summary['step_drop_off'].get(step, 0) + 1
            
            # Calculate completion rate
            unique_started = len(started_phones)
            unique_completed = len(completed_phones)
            
            if unique_started > 0:
                summary['completion_rate'] = round((unique_completed / unique_started) * 100, 2)
            
            summary['unique_registrations_started'] = unique_started
            summary['unique_registrations_completed'] = unique_completed
            
            log_info(f"Generated registration analytics summary: {summary['completion_rate']}% completion rate")
            
            return summary
            
        except Exception as e:
            log_error(f"Error generating registration analytics summary: {str(e)}")
            return {
                'error': str(e),
                'period_days': days,
                'total_events': 0
            }
