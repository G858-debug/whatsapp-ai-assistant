"""
Switch Role Command Handler - Phase 1
Handles role switching for users with multiple roles
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_switch_role(phone: str, auth_service, task_service, whatsapp) -> Dict:
    """Handle switch role command"""
    try:
        # Check if user has both roles
        roles = auth_service.get_user_roles(phone)
        
        if not (roles['trainer'] and roles['client']):
            msg = (
                "❌ You only have one role registered.\n\n"
                "You can't switch roles unless you're registered as both a trainer and a client.\n\n"
                "Type /register to register for another role."
            )
            whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'switch_role_single_role'
            }
        
        # Get current login status
        current_status = auth_service.get_login_status(phone)
        
        if not current_status:
            msg = (
                "You're not currently logged in.\n\n"
                "Please login first by sending me a message."
            )
            whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'switch_role_not_logged_in'
            }
        
        # Determine new role
        new_role = 'client' if current_status == 'trainer' else 'trainer'
        
        # Get current user ID to stop tasks
        current_user_id = auth_service.get_user_id_by_role(phone, current_status)
        
        if current_user_id:
            # Stop all running tasks for current role
            task_service.stop_all_running_tasks(current_user_id, current_status)
        
        # Switch role
        success = auth_service.set_login_status(phone, new_role)
        
        if success:
            msg = (
                f"✅ *Switched to {new_role.title()} mode!*\n\n"
                f"You're now using Refiloe as a {new_role}.\n\n"
                f"Type /help to see what you can do, or just tell me what you need!"
            )
            whatsapp.send_message(phone, msg)
            
            log_info(f"User {phone} switched from {current_status} to {new_role}")
            
            return {
                'success': True,
                'response': msg,
                'handler': 'switch_role_success'
            }
        else:
            msg = "❌ Role switch failed. Please try again."
            whatsapp.send_message(phone, msg)
            
            return {
                'success': False,
                'response': msg,
                'handler': 'switch_role_failed'
            }
            
    except Exception as e:
        log_error(f"Error in switch role command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error switching roles.",
            'handler': 'switch_role_error'
        }
