"""Trainer registration handling"""
from typing import Dict, Optional
from datetime import datetime
import pytz
import re
from utils.logger import log_info, log_error

class TrainerRegistrationHandler:
    """Handles trainer registration process"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def start_trainer_registration(self, phone: str) -> Dict:
        """Start the trainer registration process"""
        try:
            # Check if trainer already exists
            existing = self.db.table('trainers').select('*').eq(
                'whatsapp', phone
            ).execute()
            
            if existing.data:
                return {
                    'success': False,
                    'message': "You're already registered as a trainer! 👋\n\nHow can I help you today?",
                    'is_registered': True
                }
            
            # Create registration session
            session = self.db.table('registration_sessions').insert({
                'phone': phone,
                'user_type': 'trainer',
                'step': 'name',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            return {
                'success': True,
                'message': (
                    "Welcome to Refiloe! 🎉\n\n"
                    "Let's get you set up as a trainer.\n\n"
                    "First, what's your full name?"
                ),
                'session_id': session.data[0]['id'] if session.data else None
            }
            
        except Exception as e:
            log_error(f"Error starting trainer registration: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't start the registration. Please try again."
            }
    
    def process_trainer_step(self, session_id: str, step: str, value: str) -> Dict:
        """Process a trainer registration step"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': "Registration session not found. Please start over."
                }
            
            # Process based on step
            if step == 'name':
                return self._process_trainer_name(session_id, value)
            elif step == 'email':
                return self._process_trainer_email(session_id, value)
            elif step == 'business_name':
                return self._process_business_name(session_id, value)
            elif step == 'location':
                return self._process_location(session_id, value)
            elif step == 'pricing':
                return self._process_pricing(session_id, value)
            elif step == 'specialties':
                return self._process_specialties(session_id, value)
            elif step == 'confirm':
                return self._confirm_trainer_registration(session_id, value)
            else:
                return {
                    'success': False,
                    'message': "Unknown registration step."
                }
                
        except Exception as e:
            log_error(f"Error processing trainer step: {str(e)}")
            return {
                'success': False,
                'message': "Error processing registration. Please try again."
            }
    
    def _process_trainer_name(self, session_id: str, name: str) -> Dict:
        """Process trainer name"""
        if len(name.strip()) < 2:
            return {
                'success': False,
                'message': "Please enter a valid name (at least 2 characters)."
            }
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': {'name': name.strip()},
            'step': 'email'
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': f"Nice to meet you, {name}! 👋\n\nWhat's your email address?",
            'next_step': 'email'
        }
    
    def _process_trainer_email(self, session_id: str, email: str) -> Dict:
        """Process trainer email"""
        # Validate email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email.strip()):
            return {
                'success': False,
                'message': "Please enter a valid email address."
            }
        
        # Check if email already exists
        existing = self.db.table('trainers').select('id').eq(
            'email', email.strip()
        ).execute()
        
        if existing.data:
            return {
                'success': False,
                'message': "This email is already registered. Please use a different email."
            }
        
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        current_data['email'] = email.strip()
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'business_name'
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': "Great! 📧\n\nWhat's your business name? (or your name if you don't have one)",
            'next_step': 'business_name'
        }
    
    def _process_business_name(self, session_id: str, business_name: str) -> Dict:
        """Process business name"""
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        current_data['business_name'] = business_name.strip()
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'location'
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': "Perfect! 🏢\n\nWhere are you located? (City/Area)",
            'next_step': 'location'
        }
    
    def _process_location(self, session_id: str, location: str) -> Dict:
        """Process location"""
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        current_data['location'] = location.strip()
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'pricing'
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': "Got it! 📍\n\nWhat's your standard rate per session? (just the number, e.g., 500)",
            'next_step': 'pricing'
        }
    
    def _process_pricing(self, session_id: str, pricing: str) -> Dict:
        """Process pricing"""
        # Extract number from pricing
        import re
        numbers = re.findall(r'\d+', pricing)
        if not numbers:
            return {
                'success': False,
                'message': "Please enter a valid price (numbers only, e.g., 500)"
            }
        
        price = float(numbers[0])
        
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        current_data['pricing_per_session'] = price
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'specialties'
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': (
                f"R{price} per session, noted! 💰\n\n"
                "What are your specialties? (e.g., weight loss, strength training, yoga)\n"
                "You can list multiple, separated by commas."
            ),
            'next_step': 'specialties'
        }
    
    def _process_specialties(self, session_id: str, specialties: str) -> Dict:
        """Process specialties"""
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        
        # Parse specialties
        specialty_list = [s.strip() for s in specialties.split(',')]
        current_data['specialties'] = specialty_list
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'confirm'
        }).eq('id', session_id).execute()
        
        # Create confirmation message
        confirm_msg = (
            "Perfect! Let me confirm your details:\n\n"
            f"📝 Name: {current_data['name']}\n"
            f"📧 Email: {current_data['email']}\n"
            f"🏢 Business: {current_data['business_name']}\n"
            f"📍 Location: {current_data['location']}\n"
            f"💰 Rate: R{current_data['pricing_per_session']}/session\n"
            f"🎯 Specialties: {', '.join(specialty_list)}\n\n"
            "Is everything correct? (Yes/No)"
        )
        
        return {
            'success': True,
            'message': confirm_msg,
            'next_step': 'confirm'
        }
    
    def _confirm_trainer_registration(self, session_id: str, response: str) -> Dict:
        """Confirm and complete trainer registration"""
        response_lower = response.lower().strip()
        
        if response_lower not in ['yes', 'no']:
            return {
                'success': False,
                'message': "Please reply with Yes or No"
            }
        
        if response_lower == 'no':
            # Allow editing
            return {
                'success': True,
                'message': (
                    "What would you like to change?\n\n"
                    "1. Name\n"
                    "2. Email\n"
                    "3. Business Name\n"
                    "4. Location\n"
                    "5. Pricing\n"
                    "6. Specialties\n\n"
                    "Reply with the number of what you'd like to edit."
                ),
                'next_step': 'edit'
            }
        
        # Get session data
        session = self.db.table('registration_sessions').select('*').eq(
            'id', session_id
        ).single().execute()
        
        if not session.data:
            return {
                'success': False,
                'message': "Session not found. Please start registration again."
            }
        
        trainer_data = session.data['data']
        trainer_data['whatsapp'] = session.data['phone']
        trainer_data['status'] = 'active'
        trainer_data['created_at'] = datetime.now(self.sa_tz).isoformat()
        
        # Create trainer record
        result = self.db.table('trainers').insert(trainer_data).execute()
        
        if result.data:
            # Delete registration session
            self.db.table('registration_sessions').delete().eq(
                'id', session_id
            ).execute()
            
            log_info(f"Trainer registered: {trainer_data['name']}")
            
            return {
                'success': True,
                'message': (
                    "🎉 Welcome aboard! You're all set up!\n\n"
                    "Here's what you can do:\n"
                    "• Add clients: 'add client'\n"
                    "• Schedule sessions: 'book session'\n"
                    "• View your schedule: 'my schedule'\n"
                    "• Send workouts: 'send workout'\n"
                    "• Track payments: 'check payments'\n\n"
                    "Type 'help' anytime to see all commands.\n\n"
                    "Let's start by adding your first client! Type 'add client' to begin."
                ),
                'registration_complete': True,
                'trainer_id': result.data[0]['id']
            }
        else:
            return {
                'success': False,
                'message': "Failed to complete registration. Please try again."
            }