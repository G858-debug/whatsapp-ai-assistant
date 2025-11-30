"""
 Handle Registration Choice
Handle button clicks for registration choice
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_registration_choice(self, phone: str, message: str, whatsapp_service) -> Dict:
    """Handle button clicks for registration choice"""
    try:
        # Clear the awaiting state
        self.update_conversation_state(phone, 'IDLE')
        
        # Handle "I'm a Trainer" button
        if 'register_trainer' in message.lower() or "i'm a trainer" in message.lower() or "trainer" in message.lower():
            from services.registration.trainer_registration import TrainerRegistration
            reg = TrainerRegistration(self.db)
            reg_result = reg.start_registration(phone)
            if reg_result.get('buttons'):
                whatsapp_service.send_button_message(
                    phone,
                    reg_result['message'],
                    reg_result['buttons']
                )
            else:
                whatsapp_service.send_message(phone, reg_result['message'])
            
            self.update_conversation_state(phone, 'REGISTRATION', {'type': 'trainer'})
            return {'success': True}
        
        # Handle "Find a Trainer" button
        elif 'register_client' in message.lower() or "find a trainer" in message.lower() or "find trainer" in message.lower():
            from services.registration.client_registration import ClientRegistration
            reg = ClientRegistration(self.db)
            reg_result = reg.start_registration(phone)
            if reg_result.get('buttons'):
                whatsapp_service.send_button_message(
                    phone,
                    reg_result['message'],
                    reg_result['buttons']
                )
            else:
                whatsapp_service.send_message(phone, reg_result['message'])
            
            self.update_conversation_state(phone, 'REGISTRATION', {'type': 'client'})
            return {'success': True}
        
        # Handle "Learn about me" button
        elif 'learn_about_me' in message.lower() or "learn about me" in message.lower():
            info_message = (
                "🌟 *Hi! I'm Refiloe, your AI fitness assistant!*\n\n"
                "I was created to make fitness accessible and manageable for everyone passionate about health and wellness "
                "My name means 'we have been given' in Sesotho - and I'm here to give you the tools for success. 💪\n\n"
                "✨ *What I Can Do?*\n\n"
                "📱 *For Personal Trainers:*\n"
                "• Manage all your clients in one place\n"
                "• Schedule & track sessions\n"
                "• Share workouts instantly\n"
                "• Handle payments seamlessly\n"
                "• Track client progress\n\n"
                "🏃 *For Fitness Enthusiasts:*\n"
                "• Match you with qualified trainers\n"
                "• Book sessions easily\n"
                "• Track your fitness journey\n"
                "• Get personalized workouts\n"
                "• Monitor your progress\n\n"
                "I'm available 24/7 right here on WhatsApp! No apps to download, "
                "no complicated setups - just message me anytime! 🚀\n\n"
                "Ready to start? Let me know if you're a trainer or looking for one!"
            )
            
            # After learning about Refiloe, offer the registration options
            buttons = [
                {
                    'id': 'register_trainer',
                    'title': '💼 I\'m a Trainer'
                },
                {
                    'id': 'register_client',
                    'title': '🏃 Find a Trainer'
                }
            ]
            
            whatsapp_service.send_button_message(phone, info_message, buttons)
            
            # Keep state as awaiting choice for the follow-up buttons
            self.update_conversation_state(phone, 'AWAITING_REGISTRATION_CHOICE')
            
            return {'success': True}
        
        # If message doesn't match any button, treat as new message
        else:
            # Reset state and process as normal message
            self.update_conversation_state(phone, 'IDLE')
            return self.handle_message(phone, message)
            
    except Exception as e:
        log_error(f"Error handling registration choice: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, something went wrong. Please try again or just tell me if you're a trainer or looking for one!"
        }
