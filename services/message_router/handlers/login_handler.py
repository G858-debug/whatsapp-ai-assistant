"""
Login Handler
Handles login flow for existing users who are not logged in
"""
from typing import Dict
from utils.logger import log_error


class LoginHandler:
    """Handles login flow for existing users"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.task_service = task_service
    
    def handle_login_flow(self, phone: str, message: str) -> Dict:
        """Handle login flow for existing users"""
        try:
            from services.flows import LoginFlowHandler
            
            flow_handler = LoginFlowHandler(
                self.db, self.whatsapp, self.auth_service, self.task_service
            )
            
            return flow_handler.handle_login(phone, message)
            
        except Exception as e:
            log_error(f"Error handling login flow: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error during login. Please try again.",
                'handler': 'login_flow_error'
            }