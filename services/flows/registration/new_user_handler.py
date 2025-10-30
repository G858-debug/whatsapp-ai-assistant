"""
New User Handler
Handles welcome message and initial user interaction
"""
from typing import Dict
from utils.logger import log_error


class NewUserHandler:
    """Handles new user welcome and initial interaction"""
    
    def __init__(self, whatsapp_service, message_builder):
        self.whatsapp = whatsapp_service
        self.message_builder = message_builder
    
    def show_welcome_message(self, phone: str) -> Dict:
        """Show welcome message with registration options"""
        try:
            welcome_msg = (
                "👋 *Welcome to Refiloe!*\n\n"
                "I'm your AI fitness assistant. I can help you:\n\n"
                "🏋️ *As a Trainer:*\n"
                "• Manage clients\n"
                "• Track their progress\n"
                "• Assign fitness habits\n\n"
                "🏃 *As a Client:*\n"
                "• Find trainers\n"
                "• Track your fitness journey\n"
                "• Log your habits\n\n"
                "How would you like to register?"
            )
            
            # Send message with buttons
            buttons = [
                {'id': 'register_trainer', 'title': 'Register as Trainer'},
                {'id': 'register_client', 'title': 'Register as Trainee'}
            ]
            
            self.whatsapp.send_button_message(phone, welcome_msg, buttons)
            
            return {
                'success': True,
                'response': welcome_msg,
                'handler': 'new_user_welcome'
            }
            
        except Exception as e:
            log_error(f"Error showing welcome message: {str(e)}")
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error.\n\n"
                "Please try sending me a message again to start registration."
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'new_user_error'
            }