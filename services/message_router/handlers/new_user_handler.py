"""
New User Handler
Handles messages from users who are not yet in the database
"""
from typing import Dict
from utils.logger import log_error


class NewUserHandler:
    """Handles messages from new users (not in database)"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service, reg_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.reg_service = reg_service
        self.task_service = task_service
    
    def handle_new_user(self, phone: str, message: str) -> Dict:
        """Handle messages from new users (not in database)"""
        try:
            from services.flows import RegistrationFlowHandler
            
            flow_handler = RegistrationFlowHandler(
                self.db, self.whatsapp, self.auth_service, 
                self.reg_service, self.task_service
            )
            
            return flow_handler.handle_new_user(phone, message)
            
        except Exception as e:
            log_error(f"Error handling new user: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error during registration. Please try again.",
                'handler': 'new_user_error'
            }