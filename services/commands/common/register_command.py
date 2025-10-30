"""
Register Command Handler - Phase 1
Handles registration command for adding new role
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_register(phone: str, auth_service, whatsapp) -> Dict:
    """Handle register command"""
    try:
        # Check current login status
        login_status = auth_service.get_login_status(phone)
        
        if login_status:
            msg = (
                "❌ You're currently logged in.\n\n"
                "Please logout first if you want to register for another role.\n\n"
                "Type /logout to logout."
            )
            whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'register_already_logged_in'
            }
        
        # Check which roles user already has
        roles = auth_service.get_user_roles(phone)
        
        if roles['trainer'] and roles['client']:
            msg = (
                "You're already registered as both a trainer and a client!\n\n"
                "Type /help to see what you can do."
            )
            whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'register_both_roles'
            }
        
        # Show registration options for missing role
        if roles['trainer'] and not roles['client']:
            msg = (
                "You're already registered as a trainer.\n\n"
                "Would you like to also register as a client?"
            )
            buttons = [
                {'id': 'register_client', 'title': 'Register as Trainee'}
            ]
        elif roles['client'] and not roles['trainer']:
            msg = (
                "You're already registered as a client.\n\n"
                "Would you like to also register as a trainer?"
            )
            buttons = [
                {'id': 'register_trainer', 'title': 'Register as Trainer'}
            ]
        else:
            # No roles - show both options
            msg = (
                "How would you like to register?"
            )
            buttons = [
                {'id': 'register_trainer', 'title': 'Register as Trainer'},
                {'id': 'register_client', 'title': 'Register as Trainee'}
            ]
        
        whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'register_show_options'
        }
        
    except Exception as e:
        log_error(f"Error in register command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'register_error'
        }