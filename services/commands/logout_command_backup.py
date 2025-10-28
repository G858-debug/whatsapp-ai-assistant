"""
Logout Command Handler - Phase 1
Handles user logout
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_logout(phone: str, auth_service, task_service, whatsapp) -> Dict:
    """Handle logout command"""
    try:
        # Get current login status
        current_status = auth_service.get_login_status(phone)
        
        if not current_status:
            msg = "You're not currently logged in."
            whatsapp.send_message(phone, msg)
            return {
                'success': True,
                'response': msg,
                'handler': 'logout_not_logged_in'
            }
        
        # Get user ID to stop tasks
        user_id = auth_service.get_user_id_by_role(phone, current_status)
        
        if user_id:
            # Stop all running tasks
            task_service.stop_all_running_tasks(user_id, current_status)
        
        # Logout
        success = auth_service.set_login_status(phone, None)
        
        if success:
            msg = (
                "✅ *Logged out successfully!*\n\n"
                "You can login again anytime by sending me a message.\n\n"
                "Type /help to see available commands."
            )
            whatsapp.send_message(phone, msg)
            
            log_info(f"User {phone} logged out from {current_status}")
            
            return {
                'success': True,
                'response': msg,
                'handler': 'logout_success'
            }
        else:
            msg = "❌ Logout failed. Please try again."
            whatsapp.send_message(phone, msg)
            
            return {
                'success': False,
                'response': msg,
                'handler': 'logout_failed'
            }
            
    except Exception as e:
        log_error(f"Error in logout command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error during logout.",
            'handler': 'logout_error'
        }
