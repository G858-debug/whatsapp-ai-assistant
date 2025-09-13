"""Refiloe AI service - Main conversation handler"""
from typing import Dict, Optional, List
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class RefiloeService:
    """Main Refiloe AI conversation service"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Conversation states
        self.STATES = {
            'IDLE': 'idle',
            'AWAITING_RESPONSE': 'awaiting_response',
            'REGISTRATION': 'registration',
            'BOOKING': 'booking',
            'ASSESSMENT': 'assessment',
            'HABIT_TRACKING': 'habit_tracking'
        }
    
    def get_conversation_state(self, phone: str) -> Dict:
        """Get current conversation state for user"""
        try:
            result = self.db.table('conversation_states').select('*').eq(
                'phone_number', phone
            ).single().execute()
            
            if result.data:
                return result.data
            
            # Create new state
            return self.create_conversation_state(phone)
            
        except Exception as e:
            log_error(f"Error getting conversation state: {str(e)}")
            return {'state': self.STATES['IDLE']}
    
    def create_conversation_state(self, phone: str) -> Dict:
        """Create new conversation state"""
        try:
            state_data = {
                'phone_number': phone,
                'state': self.STATES['IDLE'],
                'context': {},
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('conversation_states').insert(
                state_data
            ).execute()
            
            return result.data[0] if result.data else state_data
            
        except Exception as e:
            log_error(f"Error creating conversation state: {str(e)}")
            return {'state': self.STATES['IDLE']}
    
    def update_conversation_state(self, phone: str, state: str, 
                                 context: Dict = None) -> bool:
        """Update conversation state"""
        try:
            update_data = {
                'state': state,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if context:
                update_data['context'] = context
            
            result = self.db.table('conversation_states').update(
                update_data
            ).eq('phone_number', phone).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating conversation state: {str(e)}")
            return False
    
    def get_conversation_history(self, phone: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        try:
            result = self.db.table('message_history').select('*').eq(
                'phone_number', phone
            ).order('created_at', desc=True).limit(limit).execute()
            
            # Reverse to get chronological order
            return list(reversed(result.data)) if result.data else []
            
        except Exception as e:
            log_error(f"Error getting conversation history: {str(e)}")
            return []
    
    def save_message(self, phone: str, message: str, sender: str, 
                    intent: str = None) -> bool:
        """Save message to history"""
        try:
            message_data = {
                'phone_number': phone,
                'message': message,
                'sender': sender,  # 'user' or 'bot'
                'intent': intent,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('message_history').insert(
                message_data
            ).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error saving message: {str(e)}")
            return False
    
    def clear_conversation_state(self, phone: str) -> bool:
        """Clear conversation state (reset to idle)"""
        try:
            return self.update_conversation_state(phone, self.STATES['IDLE'], {})
            
        except Exception as e:
            log_error(f"Error clearing conversation state: {str(e)}")
            return False
    
    def get_user_context(self, phone: str) -> Dict:
        """Get complete user context including trainer/client info"""
        try:
            context = {}
            
            # Check if trainer
            trainer = self.db.table('trainers').select('*').eq(
                'whatsapp', phone
            ).single().execute()
            
            if trainer.data:
                context['user_type'] = 'trainer'
                context['user_data'] = trainer.data
                
                # Get active clients count
                clients = self.db.table('clients').select('id').eq(
                    'trainer_id', trainer.data['id']
                ).eq('status', 'active').execute()
                
                context['active_clients'] = len(clients.data) if clients.data else 0
            else:
                # Check if client
                client = self.db.table('clients').select(
                    '*, trainers(name, business_name)'
                ).eq('whatsapp', phone).single().execute()
                
                if client.data:
                    context['user_type'] = 'client'
                    context['user_data'] = client.data
                    
                    if client.data.get('trainers'):
                        context['trainer_name'] = (
                            client.data['trainers'].get('business_name') or 
                            client.data['trainers'].get('name')
                        )
                else:
                    context['user_type'] = 'unknown'
                    context['user_data'] = None
            
            return context
            
        except Exception as e:
            log_error(f"Error getting user context: {str(e)}")
            return {'user_type': 'unknown', 'user_data': None}