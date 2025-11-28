"""
New User Handler
Handles messages from users who are not yet in the database
"""
from typing import Dict
from utils.logger import log_info, log_error


class NewUserHandler:
    """Handles messages from new users (not in database)"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service, reg_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.reg_service = reg_service
        self.task_service = task_service
    
    def handle_new_user(self, phone: str, message: str) -> Dict:
        """
        Handle messages from new users (not in database)
        
        Simple flow:
        1. If user types "trainer" → Send WhatsApp Flow
        2. If user types "client" → Explain invitation system
        3. Otherwise → Show welcome message with buttons
        """
        try:
            msg_lower = message.lower().strip()
            
            # Check if user is selecting trainer role
            if any(keyword in msg_lower for keyword in ['trainer', '💪', 'register as trainer']):
                log_info(f"New user {phone} selecting trainer role - sending WhatsApp Flow")
                from .buttons.registration_buttons import RegistrationButtonHandler
                button_handler = RegistrationButtonHandler(
                    self.db, self.whatsapp, self.auth_service, 
                    self.reg_service, self.task_service
                )
                return button_handler.handle_registration_button(phone, 'register_trainer')
            
            # Check if user is selecting client role
            elif any(keyword in msg_lower for keyword in ['client', 'trainee', '🏃', 'register as trainee']):
                log_info(f"New user {phone} selecting client role")
                from .buttons.registration_buttons import RegistrationButtonHandler
                button_handler = RegistrationButtonHandler(
                    self.db, self.whatsapp, self.auth_service, 
                    self.reg_service, self.task_service
                )
                return button_handler.handle_registration_button(phone, 'register_client')
            
            # First time user - show welcome message with buttons
            log_info(f"New user {phone} - showing welcome message")
            return self._show_welcome_message(phone)
            
        except Exception as e:
            log_error(f"Error handling new user: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'new_user_error'
            }
    
    def _show_welcome_message(self, phone: str) -> Dict:
        """Show welcome message with registration options"""
        try:
            welcome_msg = (
                "👋 *Hi, I'm Refiloe!*\n\n"
                "I'm your AI fitness assistant and I can help you:\n\n"
                "🏋️ *As a Trainer:*\n"
                "• Manage clients\n"
                "• Track their progress\n"
                "• Assign fitness habits\n\n"
                "🏃 *As a Client:*\n"
                "• Find trainers\n"
                "• Track your fitness journey\n"
                "• Log your habits\n\n"
                "How would you like to proceed?"
            )
            
            # Send message with buttons
            buttons = [
                {'id': 'register_trainer', 'title': 'I\'m a Trainer'},
                {'id': 'register_client', 'title': 'I need a Trainer'}
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
                "Please try sending me a message again to start onboarding."
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'new_user_error'
            }