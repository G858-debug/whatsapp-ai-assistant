"""
Login Flow Handler - Phase 1
Handles login for existing users
"""
from typing import Dict
from utils.logger import log_info, log_error


class LoginFlowHandler:
    """Handles the login conversation flow"""
    
    def __init__(self, db, whatsapp, auth_service, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.auth = auth_service
        self.task = task_service
    
    def handle_login(self, phone: str, message: str) -> Dict:
        """Handle login for existing user"""
        try:
            # Check if user is responding to role selection
            msg_lower = message.lower().strip()
            
            if msg_lower in ['login_trainer', 'login as trainer', 'trainer', '💪 login as trainer']:
                return self._login_as_role(phone, 'trainer')
            
            elif msg_lower in ['login_client', 'login as client', 'client', '🏃 login as client']:
                return self._login_as_role(phone, 'client')
            
            # First time - check roles and auto-login or show selection
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
                return self._show_role_selection(phone)
            
            else:
                # No roles found - this shouldn't happen
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
            log_error(f"Error handling login: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error during login. Please try again.",
                'handler': 'login_error'
            }
    
    def _show_role_selection(self, phone: str) -> Dict:
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
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'role_selection_error'
            }
    
    def _login_as_role(self, phone: str, role: str) -> Dict:
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
                # Get user ID
                user_id = self.auth.get_user_id_by_role(phone, role)
                
                # Get user data for personalized message
                table = 'trainers' if role == 'trainer' else 'clients'
                id_column = 'trainer_id' if role == 'trainer' else 'client_id'
                
                user_data = self.db.table(table).select('*').eq(
                    id_column, user_id
                ).execute()
                
                name = "there"
                if user_data.data and len(user_data.data) > 0:
                    user_info = user_data.data[0]
                    name = user_info.get('first_name') or user_info.get('name', '').split()[0] or "there"
                
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
            return {
                'success': False,
                'response': "Sorry, I encountered an error during login. Please try again.",
                'handler': 'login_role_error'
            }
