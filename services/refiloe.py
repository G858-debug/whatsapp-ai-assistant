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

    def handle_message(self, phone: str, text: str) -> Dict:
        """Handle incoming WhatsApp message - main entry point"""
        try:
            # Import services we need
            from app import app
            ai_handler = app.config['services']['ai_handler']
            whatsapp_service = app.config['services']['whatsapp']
            
            # Get user context using existing method
            context = self.get_user_context(phone)
            
            # Determine sender type and data from context
            if context['user_type'] == 'trainer':
                sender_type = 'trainer'
                sender_data = context['user_data']
            elif context['user_type'] == 'client':
                sender_type = 'client'
                sender_data = context['user_data']
            else:
                sender_type = 'unknown'
                sender_data = {'name': 'there', 'whatsapp': phone}
            
            # Get conversation history using existing method
            history = self.get_conversation_history(phone)
            history_text = [h['message'] for h in history] if history else []
            
            # Save incoming message using existing method
            self.save_message(phone, text, 'user')
            
            # Process with AI to understand intent
            intent = ai_handler.understand_message(
                text,
                sender_type,
                sender_data,
                history_text
            )
            
            # Generate smart response using the EXISTING method in AIIntentHandler
            response_text = ai_handler.generate_smart_response(
                intent,
                sender_type,
                sender_data
            )
            
            # Send the response
            whatsapp_service.send_message(phone, response_text)
            
            # Save bot response
            self.save_message(phone, response_text, 'bot', intent.get('primary_intent'))
            
            # Check if we should start registration flow
            if sender_type == 'unknown':
                if intent.get('primary_intent') == 'registration_trainer':
                    # Check if registration manager exists
                    try:
                        from services.registration.trainer_registration import TrainerRegistration
                        reg = TrainerRegistration(self.db)
                        reg_result = reg.start_registration(phone)
                        if reg_result.get('buttons'):
                            whatsapp_service.send_button_message(
                                phone, 
                                reg_result['message'],
                                reg_result['buttons']
                            )
                    except ImportError:
                        pass  # Registration module not available
                
                elif intent.get('primary_intent') == 'registration_client':
                    # Similar for client registration
                    try:
                        from services.registration.client_registration import ClientRegistration
                        reg = ClientRegistration(self.db)
                        reg_result = reg.start_registration(phone)
                        if reg_result.get('buttons'):
                            whatsapp_service.send_button_message(
                                phone,
                                reg_result['message'], 
                                reg_result['buttons']
                            )
                    except ImportError:
                        pass
            
            return {'success': True, 'response': response_text}
            
        except Exception as e:
            log_error(f"Error handling message: {str(e)}")
            # Fallback to a friendly error message
            return {
                'success': False,
                'response': "Sorry, I'm having a bit of trouble right now. Please try again in a moment! 😊"
            }
    
