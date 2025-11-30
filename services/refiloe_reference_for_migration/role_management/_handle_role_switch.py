"""
 Handle Role Switch
Handle role switching for dual role users
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_role_switch(self, phone: str) -> Dict:
    """Handle role switching for dual role users"""
    try:
        # Get current context to check available roles
        context = self.get_user_context(phone)
        
        if not context.get('has_dual_roles'):
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            whatsapp_service.send_message(phone, "You only have one role available. No switching needed! 😊")
            return {'success': True, 'message': 'Single role user'}
        
        # Get current role preference
        current_role = context.get('active_role', 'trainer')
        new_role = 'client' if current_role == 'trainer' else 'trainer'
        
        # Switch the role
        return self.handle_role_selection(phone, new_role)
        
    except Exception as e:
        log_error(f"Error handling role switch: {str(e)}")
        return {'success': False, 'error': str(e)}
