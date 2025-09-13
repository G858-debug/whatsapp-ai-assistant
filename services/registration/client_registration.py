"""Client registration handling"""
from typing import Dict, Optional
from datetime import datetime
import pytz
import re
from utils.logger import log_info, log_error

class ClientRegistrationHandler:
    """Handles client registration process"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def start_client_registration(self, phone: str, trainer_id: str = None) -> Dict:
        """Start the client registration process"""
        try:
            # Check if client already exists
            existing = self.db.table('clients').select('*, trainers(*)').eq(
                'whatsapp', phone
            ).execute()
            
            if existing.data:
                trainer_name = existing.data[0]['trainers']['name'] if existing.data[0].get('trainers') else 'your trainer'
                return {
                    'success': False,
                    'message': f"You're already registered as a client with {trainer_name}! 👋\n\nHow can I help you today?",
                    'is_registered': True
                }
            
            # Create registration session
            session_data = {
                'phone': phone,
                'user_type': 'client',
                'step': 'name',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if trainer_id:
                session_data['data'] = {'trainer_id': trainer_id}
            
            session = self.db.table('registration_sessions').insert(session_data).execute()
            
            return {
                'success': True,
                'message': (
                    "Welcome! 🎉\n\n"
                    "Let's get you registered as a client.\n\n"
                    "What's your full name?"
                ),
                'session_id': session.data[0]['id'] if session.data else None
            }
            
        except Exception as e:
            log_error(f"Error starting client registration: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't start the registration. Please try again."
            }
    
    def process_client_step(self, session_id: str, step: str, value: str) -> Dict:
        """Process a client registration step"""
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
                return self._process_client_name(session_id, value)
            elif step == 'email':
                return self._process_client_email(session_id, value)
            elif step == 'emergency_contact':
                return self._process_emergency_contact(session_id, value)
            elif step == 'goals':
                return self._process_goals(session_id, value)
            elif step == 'fitness_level':
                return self._process_fitness_level(session_id, value)
            elif step == 'medical_conditions':
                return self._process_medical_conditions(session_id, value)
            elif step == 'trainer_code':
                return self._process_trainer_code(session_id, value)
            elif step == 'confirm':
                return self._confirm_client_registration(session_id, value)
            else:
                return {
                    'success': False,
                    'message': "Unknown registration step."
                }
                
        except Exception as e:
            log_error(f"Error processing client step: {str(e)}")
            return {
                'success': False,
                'message': "Error processing registration. Please try again."
            }
    
    def _process_client_name(self, session_id: str, name: str) -> Dict:
        """Process client name"""
        if len(name.strip()) < 2:
            return {
                'success': False,
                'message': "Please enter a valid name (at least 2 characters)."
            }
        
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        current_data['name'] = name.strip()
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'email'
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': f"Nice to meet you, {name}! 👋\n\nWhat's your email address?",
            'next_step': 'email'
        }
    
    def _process_client_email(self, session_id: str, email: str) -> Dict:
        """Process client email"""
        # Allow skipping email
        if email.lower() in ['skip', 'none', 'no']:
            email = None
        else:
            # Validate email
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email.strip()):
                return {
                    'success': False,
                    'message': "Please enter a valid email address (or type 'skip' to skip)."
                }
            email = email.strip()
        
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        if email:
            current_data['email'] = email
        
        # Check if we have trainer_id already
        if current_data.get('trainer_id'):
            next_step = 'emergency_contact'
            message = "📞 Who should we contact in case of emergency?\n(Name and phone number)"
        else:
            next_step = 'trainer_code'
            message = "Do you have a trainer code? (If not, type 'skip')"
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': next_step
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': message,
            'next_step': next_step
        }
    
    def _process_trainer_code(self, session_id: str, code: str) -> Dict:
        """Process trainer code"""
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        
        if code.lower() not in ['skip', 'none', 'no']:
            # Try to find trainer by code
            trainer = self.db.table('trainers').select('id, name').eq(
                'trainer_code', code.upper()
            ).single().execute()
            
            if trainer.data:
                current_data['trainer_id'] = trainer.data['id']
                message = f"Great! You'll be training with {trainer.data['name']}! 🎯\n\n"
            else:
                return {
                    'success': False,
                    'message': "Invalid trainer code. Please check and try again (or type 'skip')."
                }
        else:
            message = ""
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'emergency_contact'
        }).eq('id', session_id).execute()
        
        message += "📞 Who should we contact in case of emergency?\n(Name and phone number)"
        
        return {
            'success': True,
            'message': message,
            'next_step': 'emergency_contact'
        }
    
    def _process_emergency_contact(self, session_id: str, contact: str) -> Dict:
        """Process emergency contact"""
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        current_data['emergency_contact'] = contact.strip()
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'goals'
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': (
                "Thank you! 🚨\n\n"
                "What are your fitness goals?\n"
                "(e.g., lose weight, build muscle, improve fitness)"
            ),
            'next_step': 'goals'
        }
    
    def _process_goals(self, session_id: str, goals: str) -> Dict:
        """Process fitness goals"""
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        current_data['fitness_goals'] = goals.strip()
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'fitness_level'
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': (
                "Excellent goals! 🎯\n\n"
                "How would you rate your current fitness level?\n\n"
                "1. Beginner\n"
                "2. Intermediate\n"
                "3. Advanced\n\n"
                "Reply with 1, 2, or 3"
            ),
            'next_step': 'fitness_level'
        }
    
    def _process_fitness_level(self, session_id: str, level: str) -> Dict:
        """Process fitness level"""
        # Map response to fitness level
        level_map = {
            '1': 'beginner',
            '2': 'intermediate',
            '3': 'advanced',
            'beginner': 'beginner',
            'intermediate': 'intermediate',
            'advanced': 'advanced'
        }
        
        fitness_level = level_map.get(level.lower().strip())
        
        if not fitness_level:
            return {
                'success': False,
                'message': "Please reply with 1 (Beginner), 2 (Intermediate), or 3 (Advanced)"
            }
        
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        current_data['fitness_level'] = fitness_level
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'medical_conditions'
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': (
                "Got it! 💪\n\n"
                "Do you have any medical conditions or injuries I should know about?\n"
                "(Type 'none' if you don't have any)"
            ),
            'next_step': 'medical_conditions'
        }
    
    def _process_medical_conditions(self, session_id: str, conditions: str) -> Dict:
        """Process medical conditions"""
        # Get current data
        session = self.db.table('registration_sessions').select('data').eq(
            'id', session_id
        ).single().execute()
        
        current_data = session.data.get('data', {})
        
        if conditions.lower().strip() in ['none', 'no', 'nothing']:
            current_data['medical_conditions'] = None
        else:
            current_data['medical_conditions'] = conditions.strip()
        
        # Update session
        self.db.table('registration_sessions').update({
            'data': current_data,
            'step': 'confirm'
        }).eq('id', session_id).execute()
        
        # Create confirmation message
        confirm_msg = (
            "Perfect! Let me confirm your details:\n\n"
            f"📝 Name: {current_data['name']}\n"
        )
        
        if current_data.get('email'):
            confirm_msg += f"📧 Email: {current_data['email']}\n"
        
        confirm_msg += (
            f"🚨 Emergency: {current_data['emergency_contact']}\n"
            f"🎯 Goals: {current_data['fitness_goals']}\n"
            f"💪 Level: {current_data['fitness_level'].title()}\n"
        )
        
        if current_data.get('medical_conditions'):
            confirm_msg += f"⚕️ Medical: {current_data['medical_conditions']}\n"
        
        confirm_msg += "\nIs everything correct? (Yes/No)"
        
        return {
            'success': True,
            'message': confirm_msg,
            'next_step': 'confirm'
        }
    
    def _confirm_client_registration(self, session_id: str, response: str) -> Dict:
        """Confirm and complete client registration"""
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
                    "3. Emergency Contact\n"
                    "4. Goals\n"
                    "5. Fitness Level\n"
                    "6. Medical Conditions\n\n"
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
        
        client_data = session.data['data']
        client_data['whatsapp'] = session.data['phone']
        client_data['status'] = 'active'
        client_data['sessions_remaining'] = 0
        client_data['created_at'] = datetime.now(self.sa_tz).isoformat()
        
        # Create client record
        result = self.db.table('clients').insert(client_data).execute()
        
        if result.data:
            # Delete registration session
            self.db.table('registration_sessions').delete().eq(
                'id', session_id
            ).execute()
            
            log_info(f"Client registered: {client_data['name']}")
            
            # Get trainer name if assigned
            trainer_msg = ""
            if client_data.get('trainer_id'):
                trainer = self.db.table('trainers').select('name').eq(
                    'id', client_data['trainer_id']
                ).single().execute()
                if trainer.data:
                    trainer_msg = f"Your trainer {trainer.data['name']} has been notified! "
            
            return {
                'success': True,
                'message': (
                    f"🎉 Welcome! You're all set!\n\n"
                    f"{trainer_msg}"
                    "Here's what you can do:\n"
                    "• View schedule: 'my schedule'\n"
                    "• Book sessions: 'book session'\n"
                    "• Log habits: 'log water 2L'\n"
                    "• Track progress: 'my progress'\n"
                    "• Get workouts: 'today's workout'\n\n"
                    "Type 'help' anytime to see all commands.\n\n"
                    "Ready to start your fitness journey! 💪"
                ),
                'registration_complete': True,
                'client_id': result.data[0]['id']
            }
        else:
            return {
                'success': False,
                'message': "Failed to complete registration. Please try again."
            }