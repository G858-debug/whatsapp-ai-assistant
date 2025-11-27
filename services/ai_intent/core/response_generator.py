"""
Response Generator
Generates appropriate responses based on detected intent
"""
from typing import Dict
from utils.logger import log_error
from ..handlers.trainer_intent_handler import TrainerIntentHandler
from ..handlers.client_intent_handler import ClientIntentHandler
from ..handlers.common_intent_handler import CommonIntentHandler


class ResponseGenerator:
    """Generates responses based on intent"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        
        # Initialize intent handlers
        self.trainer_handler = TrainerIntentHandler(self.db, self.whatsapp, task_service)
        self.client_handler = ClientIntentHandler(self.db, self.whatsapp)
        self.common_handler = CommonIntentHandler(self.db, self.whatsapp)
    
    def generate_response(self, phone: str, message: str, role: str, 
                         intent: Dict, context: Dict) -> Dict:
        """Generate response based on intent"""
        try:
            intent_type = intent.get('intent', 'unknown')
            confidence = intent.get('confidence', 0.5)
            
            # High confidence - provide action
            if confidence >= 0.7 and intent.get('needs_action'):
                return self._provide_action_response(phone, intent_type, intent, role, context)
            
            # Medium confidence - ask for clarification
            elif confidence >= 0.4:
                return self._provide_clarification_response(phone, intent_type, intent, role, context)
            
            # Low confidence - general conversation
            else:
                return self._provide_conversational_response(phone, message, role, context)
                
        except Exception as e:
            log_error(f"Error generating response: {str(e)}")
            return self._error_response(phone, message, role)
    
    def _provide_action_response(self, phone: str, intent_type: str, intent: Dict, 
                                role: str, context: Dict) -> Dict:
        """Provide actionable response with buttons"""
        try:
            # Route to appropriate handler
            if intent_type in self.common_handler.get_supported_intents():
                return self.common_handler.handle_intent(phone, intent_type, intent, context)
            elif role == 'trainer':
                return self.trainer_handler.handle_intent(phone, intent_type, intent, context)
            elif role == 'client':
                return self.client_handler.handle_intent(phone, intent_type, intent, context)
            else:
                return self._unknown_intent_response(phone, intent_type, role, context)
                
        except Exception as e:
            log_error(f"Error providing action response: {str(e)}")
            return self._error_response(phone, '', role)
    
    def _provide_clarification_response(self, phone: str, intent_type: str, intent: Dict,
                                       role: str, context: Dict) -> Dict:
        """Ask for clarification when confidence is medium"""
        try:
            name = context.get('name', 'there')
            
            # Check if asking about Phase 3 features
            if intent.get('is_asking_about_phase3'):
                msg = (
                    f"That's a great feature, {name}!\n\n"
                    f"Habit tracking is coming in Phase 3.\n\n"
                    f"For now, here's what you can do:"
                )
                buttons = [
                    {'id': '/view-profile', 'title': '👤 View Profile'},
                    {'id': '/help', 'title': '📚 Show Help'}
                ]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
            else:
                # General clarification
                msg = (
                    f"I'm not quite sure what you need, {name}.\n\n"
                    f"Here are some things I can help with:"
                )
                buttons = [
                    {'id': '/view-profile', 'title': '👤 View Profile'},
                    {'id': '/edit-profile', 'title': '✏️ Edit Profile'},
                    {'id': '/help', 'title': '📚 Show Help'}
                ]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'ai_intent_clarification'
            }
            
        except Exception as e:
            log_error(f"Error providing clarification: {str(e)}")
            return self._error_response(phone, '', role)
    
    def _provide_conversational_response(self, phone: str, message: str, 
                                        role: str, context: Dict) -> Dict:
        """Provide friendly conversational response"""
        try:
            name = context.get('name', 'there')
            msg_lower = message.lower().strip()
            
            # Greetings
            if any(word in msg_lower for word in ['hi', 'hello', 'hey', 'howzit']):
                msg = (
                    f"Hi {name}! 👋\n\n"
                    f"How can I help you today?"
                )
                
            # Thanks
            elif any(word in msg_lower for word in ['thanks', 'thank you', 'appreciate']):
                msg = (
                    f"You're welcome, {name}! 😊\n\n"
                    f"Is there anything else I can help with?"
                )
                
            # Status check
            elif any(phrase in msg_lower for phrase in ['are you there', 'you there', 'still there']):
                msg = (
                    f"Yes, I'm here {name}! 👍\n\n"
                    f"What can I do for you?"
                )
                
            # General
            else:
                msg = (
                    f"I'm here to help, {name}!\n\n"
                    f"You can ask me to:\n"
                    f"• Show your profile\n"
                    f"• Edit your information\n"
                    f"• Or type /help for all commands"
                )
            
            self.whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'ai_intent_conversation'
            }
            
        except Exception as e:
            log_error(f"Error providing conversational response: {str(e)}")
            return self._error_response(phone, message, role)
    
    def _unknown_intent_response(self, phone: str, intent_type: str, role: str, context: Dict) -> Dict:
        """Handle unknown intent"""
        name = context.get('name', 'there')
        msg = (
            f"I'm not sure how to help with that, {name}.\n\n"
            f"Here are some things I can do:"
        )
        buttons = [
            {'id': '/view-profile', 'title': '👤 View Profile'},
            {'id': '/help', 'title': '📚 Show Help'}
        ]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_unknown'
        }
    
    def _error_response(self, phone: str, message: str, role: str) -> Dict:
        """Handle error response"""
        msg = "Sorry, I encountered an error. Please try again."
        self.whatsapp.send_message(phone, msg)
        
        return {
            'success': False,
            'response': msg,
            'handler': 'ai_intent_error'
        }