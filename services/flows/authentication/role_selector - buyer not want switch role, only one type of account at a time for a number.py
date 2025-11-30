"""
Role Selector
Handles role selection and role-specific login
"""
from typing import Dict
from utils.logger import log_info, log_error


class RoleSelector:
    """Handles role selection for users with multiple roles"""
    
    def __init__(self, db, whatsapp, auth_service, message_builder):
        self.db = db
        self.whatsapp = whatsapp
        self.auth = auth_service
        self.message_builder = message_builder
    
    def show_role_selection(self, phone: str) -> Dict:
        """Show role selection for users with multiple roles"""
        try:
            message = (
                "👋 Welcome back!\n\n"
                "I see you're registered as both a *Trainer* and a *Client*.\n\n"
                "How would you like to login today?"
            )
            
            buttons = [
                {'id': 'login_trainer', 'title': 'Login as Trainer'},
                {'id': 'login_client', 'title': 'Login as Client'}
            ]
            
            self.whatsapp.send_button_message(phone, message, buttons)
            
            return {
                'success': True,
                'response': message,
                'handler': 'role_selection'
            }
            
        except Exception as e:
            log_error(f"Error showing role selection: {str(e)}")
            
            error_msg = self.message_builder.build_error_message(
                "role selection", 
                "Please try again"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'role_selection_error'
            }
    
    def login_as_role(self, phone: str, role: str) -> Dict:
        """Login user as specific role"""
        try:
            # Verify role exists
            if not self.auth.verify_role_exists(phone, role):
                error_msg = (
                    f"❌ You don't have a {role} account.\n\n"
                    f"Would you like to register as a {role}?"
                )
                self.whatsapp.send_message(phone, error_msg)
                
                return {
                    'success': False,
                    'response': error_msg,
                    'handler': 'role_not_found'
                }
            
            # Set login status
            success = self.auth.set_login_status(phone, role)
            
            if success:
                # Get user data for personalized message
                user_data = self._get_user_data(phone, role)
                name = user_data.get('first_name', 'there')
                
                success_msg = (
                    f"✅ Welcome back, *{name}*!\n\n"
                    f"You are now logged in as a *{role.title()}*.\n\n"
                    f"Type /help to see what you can do, or just tell me what you need!"
                )
                
                self.whatsapp.send_message(phone, success_msg)
                
                return {
                    'success': True,
                    'response': success_msg,
                    'handler': 'login_success'
                }
            else:
                error_msg = "❌ Login failed. Please try again."
                self.whatsapp.send_message(phone, error_msg)
                
                return {
                    'success': False,
                    'response': error_msg,
                    'handler': 'login_failed'
                }
                
        except Exception as e:
            log_error(f"Error logging in as {role}: {str(e)}")
            
            error_msg = self.message_builder.build_error_message(
                f"{role} login",
                "Please try again"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'login_role_error'
            }
    
    def _get_user_data(self, phone: str, role: str) -> Dict:
        """Get user data for personalized messages"""
        try:
            user_id = self.auth.get_user_id_by_role(phone, role)
            if not user_id:
                return {}
            
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            result = self.db.table(table).select('*').eq(id_column, user_id).execute()
            
            if result.data:
                return result.data[0]
            return {}
            
        except Exception as e:
            log_error(f"Error getting user data: {str(e)}")
            return {}