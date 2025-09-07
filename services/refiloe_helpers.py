"""Helper methods for RefiloeService - utility functions and context management"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info

class RefiloeHelpers:
    """Helper utilities for RefiloeService"""
    
    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def get_user_context(self, phone: str) -> Tuple[str, Optional[Dict]]:
        """Get user context from phone number"""
        try:
            # Check if trainer
            trainer = self.db.table('trainers').select('*').eq(
                'whatsapp', phone
            ).execute()
            
            if trainer.data:
                return ('trainer', trainer.data[0])
            
            # Check if client
            client = self.db.table('clients').select('*, trainers(*)').eq(
                'whatsapp', phone
            ).execute()
            
            if client.data:
                client_data = client.data[0]
                # Add trainer info to client data
                if 'trainers' in client_data and client_data['trainers']:
                    client_data['trainer_name'] = client_data['trainers'].get('name', 'Your trainer')
                return ('client', client_data)
            
            return ('unknown', None)
            
        except Exception as e:
            log_error(f"Error getting user context: {str(e)}")
            return ('unknown', None)
    
    def log_interaction(self, phone: str, user_type: str, message_type: str, 
                       intent: str, response: str):
        """Log message interaction for analytics"""
        try:
            interaction_data = {
                'phone_number': phone,
                'user_type': user_type,
                'message_type': message_type,
                'intent': intent,
                'response_summary': response[:500] if response else None,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            self.db.table('message_logs').insert(interaction_data).execute()
            
        except Exception as e:
            log_error(f"Error logging interaction: {str(e)}")
    
    def get_conversation_history(self, phone: str, limit: int = 10) -> List[str]:
        """Get recent conversation history for context"""
        try:
            result = self.db.table('message_logs').select(
                'intent', 'response_summary'
            ).eq('phone_number', phone).order(
                'created_at', desc=True
            ).limit(limit).execute()
            
            if result.data:
                history = []
                for log in reversed(result.data):  # Reverse to get chronological order
                    if log.get('intent'):
                        history.append(f"User: {log['intent']}")
                    if log.get('response_summary'):
                        history.append(f"Bot: {log['response_summary'][:100]}")
                
                return history[-5:]  # Return last 5 messages
            
            return []
            
        except Exception as e:
            log_error(f"Error getting conversation history: {str(e)}")
            return []
    
    def check_session_state(self, phone: str) -> Optional[Dict]:
        """Check if user has an active session/context"""
        try:
            # Check for active assessment session
            assessment = self.db.table('assessment_sessions').select('*').eq(
                'phone_number', phone
            ).eq('status', 'in_progress').order(
                'created_at', desc=True
            ).limit(1).execute()
            
            if assessment.data:
                return {
                    'type': 'assessment',
                    'data': assessment.data[0],
                    'step': assessment.data[0].get('current_step', 1)
                }
            
            # Check for active booking session
            booking_session = self.db.table('booking_sessions').select('*').eq(
                'phone_number', phone
            ).eq('status', 'in_progress').order(
                'created_at', desc=True
            ).limit(1).execute()
            
            if booking_session.data:
                return {
                    'type': 'booking',
                    'data': booking_session.data[0],
                    'step': booking_session.data[0].get('current_step', 1)
                }
            
            return None
            
        except Exception as e:
            log_error(f"Error checking session state: {str(e)}")
            return None
    
    def update_session_state(self, phone: str, session_type: str, 
                           step: int, data: Dict) -> bool:
        """Update active session state"""
        try:
            table_name = f"{session_type}_sessions"
            
            # Check if session exists
            existing = self.db.table(table_name).select('id').eq(
                'phone_number', phone
            ).eq('status', 'in_progress').execute()
            
            if existing.data:
                # Update existing session
                self.db.table(table_name).update({
                    'current_step': step,
                    'session_data': data,
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('id', existing.data[0]['id']).execute()
            else:
                # Create new session
                self.db.table(table_name).insert({
                    'phone_number': phone,
                    'status': 'in_progress',
                    'current_step': step,
                    'session_data': data,
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
            
            return True
            
        except Exception as e:
            log_error(f"Error updating session state: {str(e)}")
            return False
    
    def format_currency(self, amount: float) -> str:
        """Format amount as South African Rand"""
        return f"R{amount:,.2f}"
    
    def format_phone_number(self, phone: str) -> str:
        """Format phone number to South African format"""
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Handle different formats
        if phone.startswith('27'):
            # Already in international format
            return f"+{phone}"
        elif phone.startswith('0'):
            # Local format - convert to international
            return f"+27{phone[1:]}"
        else:
            # Assume it's missing the leading 0
            return f"+27{phone}"
    
    def validate_south_african_phone(self, phone: str) -> bool:
        """Validate South African phone number"""
        phone = ''.join(filter(str.isdigit, phone))
        
        # Check valid SA mobile prefixes
        valid_prefixes = ['06', '07', '08']  # Mobile prefixes
        
        if phone.startswith('27'):
            phone = '0' + phone[2:]  # Convert to local format for checking
        elif not phone.startswith('0'):
            phone = '0' + phone
        
        if len(phone) != 10:
            return False
        
        return phone[:2] in valid_prefixes
    
    def get_greeting_by_time(self) -> str:
        """Get appropriate greeting based on time of day"""
        hour = datetime.now(self.sa_tz).hour
        
        if hour < 12:
            return "Good morning"
        elif hour < 17:
            return "Good afternoon"
        else:
            return "Good evening"
    
    def calculate_next_available_slot(self, trainer_id: str) -> Optional[Dict]:
        """Find the next available booking slot for a trainer"""
        try:
            from models.booking import BookingModel
            booking_model = BookingModel(self.db, self.config)
            
            # Check next 7 days
            for days_ahead in range(7):
                check_date = (datetime.now(self.sa_tz).date() + timedelta(days=days_ahead))
                available = booking_model.get_available_slots(trainer_id, check_date.isoformat())
                
                if available:
                    # Skip today if it's past the first available slot
                    if days_ahead == 0:
                        current_time = datetime.now(self.sa_tz).time()
                        available = [
                            slot for slot in available 
                            if datetime.strptime(slot, '%H:%M').time() > current_time
                        ]
                    
                    if available:
                        return {
                            'date': check_date,
                            'time': available[0],
                            'all_slots': available
                        }
            
            return None
            
        except Exception as e:
            log_error(f"Error calculating next available slot: {str(e)}")
            return None
    
    def get_motivational_message(self, context: str = 'general') -> str:
        """Get a motivational message based on context"""
        import random
        
        messages = {
            'general': [
                "💪 Keep pushing forward!",
                "🌟 You've got this!",
                "🎯 Stay focused on your goals!",
                "💯 Every step counts!",
                "🚀 Let's make it happen!"
            ],
            'workout': [
                "💪 Time to crush this workout!",
                "🔥 Feel the burn, love the results!",
                "⚡ Beast mode: ACTIVATED!",
                "🎯 Focus, execute, dominate!",
                "💯 Give it your all!"
            ],
            'progress': [
                "📈 Amazing progress! Keep it up!",
                "🌟 You're doing incredible!",
                "🎉 Look how far you've come!",
                "💪 Your hard work is paying off!",
                "🏆 You're a champion!"
            ],
            'booking': [
                "🎯 Great choice! See you there!",
                "💪 Can't wait for our session!",
                "🔥 Let's make it a great workout!",
                "⚡ Ready to level up?",
                "🌟 This is going to be awesome!"
            ]
        }
        
        return random.choice(messages.get(context, messages['general']))
    
    def parse_package_type(self, text: str) -> str:
        """Parse package type from text"""
        text_lower = text.lower()
        
        if 'single' in text_lower or '1' in text_lower:
            return 'single'
        elif 'weekly' in text_lower and '4' in text_lower:
            return 'weekly_4'
        elif 'weekly' in text_lower and '8' in text_lower:
            return 'weekly_8'
        elif 'monthly' in text_lower and '12' in text_lower:
            return 'monthly_12'
        elif 'monthly' in text_lower and '16' in text_lower:
            return 'monthly_16'
        else:
            return 'single'  # Default