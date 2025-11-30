"""
Send Role Selection Message
Send role selection buttons for dual role users
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def send_role_selection_message(self, phone: str, context: Dict) -> Dict:
    """Send role selection buttons for dual role users"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Get user's name from either role
        name = "there"
        if context.get('trainer_data'):
            trainer_name = context['trainer_data'].get('first_name') or context['trainer_data'].get('name', '').split()[0]
            if trainer_name:
                name = trainer_name
        elif context.get('client_data'):
            client_name = context['client_data'].get('first_name') or context['client_data'].get('name', '').split()[0]
            if client_name:
                name = client_name
        
        message = f"Hi {name}! 👋\n\nI see you're both a trainer and a client. Which role would you like to use today?"
        
        buttons = [
            {'id': 'role_trainer', 'title': '💪 Trainer'},
            {'id': 'role_client', 'title': '🏃‍♀️ Client'}
        ]
        
        return whatsapp_service.send_button_message(phone, message, buttons)
        
    except Exception as e:
        log_error(f"Error sending role selection message: {str(e)}")
        return {'success': False, 'error': str(e)}
