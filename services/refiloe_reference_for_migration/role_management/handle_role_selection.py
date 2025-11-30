"""
Handle Role Selection
Handle role selection for dual role users
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def handle_role_selection(self, phone: str, selected_role: str) -> Dict:
    """Handle role selection for dual role users"""
    try:
        # Store role preference
        self.db.table('conversation_states').upsert({
            'phone': phone,
            'role_preference': selected_role,
            'updated_at': datetime.now().isoformat()
        }, on_conflict='phone').execute()
        
        # Get context with selected role
        context = self.get_user_context(phone, selected_role)
        
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        if selected_role == 'trainer':
            message = f"Great! You're now using Refiloe as a trainer. 💪\n\nWhat can I help you with today?"
        else:
            message = f"Perfect! You're now using Refiloe as a client. 🏃‍♀️\n\nWhat can I help you with today?"
        
        # Add role switch button for easy switching
        buttons = [{
            'id': 'switch_role',
            'title': f'Switch to {("Client" if selected_role == "trainer" else "Trainer")}'
        }]
        
        whatsapp_service.send_button_message(phone, message, buttons)
        
        return {'success': True, 'role_selected': selected_role}
        
    except Exception as e:
        log_error(f"Error handling role selection: {str(e)}")
        return {'success': False, 'error': str(e)}
