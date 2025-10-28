"""
Auto Login Handler
Handles automatic login for users with single roles
"""
from typing import Dict
from utils.logger import log_info, log_error


class AutoLoginHandler:
    """Handles automatic login logic"""
    
    def __init__(self, db, whatsapp, auth_service, message_builder):
        self.db = db
        self.whatsapp = whatsapp
        self.auth = auth_service
        self.message_builder = message_builder
    
    def handle_auto_login(self, phone: str) -> Dict:
        """Handle automatic login based on user roles"""
        try:
            # Check roles and auto-login or show selection
            success, role, result_msg = self.auth.auto_login_single_role(phone)
            
            if success:
                # Auto-logged in with single role
                self.whatsapp.send_message(phone, result_msg)
                
                return {
                    'success': True,
                    'response': result_msg,
                    'handler': 'auto_login'
                }
            
            elif result_msg == "multiple_roles":
                # User has both roles - show selection
                from .role_selector import RoleSelector
                role_selector = RoleSelector(self.db, self.whatsapp, self.auth, self.message_builder)
                return role_selector.show_role_selection(phone)
            
            else:
                # No roles found - this shouldn't happen in login flow
                error_msg = (
                    "❌ I couldn't find your account information.\n\n"
                    "Please contact support or try registering again."
                )
                self.whatsapp.send_message(phone, error_msg)
                
                return {
                    'success': False,
                    'response': error_msg,
                    'handler': 'login_no_roles'
                }
                
        except Exception as e:
            log_error(f"Error in auto login: {str(e)}")
            
            error_msg = self.message_builder.build_error_message(
                "login",
                "Please try again"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'auto_login_error'
            }