"""
 Handle Registration Command
Handle /registration command - start or restart registration
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_registration_command(self, phone: str, user_type: str) -> Dict:
    """Handle /registration command - start or restart registration"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        if user_type in ['trainer', 'client']:
            response = (
                f"✅ You're already registered as a {user_type}!\n\n"
                f"• Type `/profile` to view your info\n"
                f"• Type `/help` to see available commands\n\n"
                f"Need to register in a different role? Contact support."
            )
        else:
            response = (
                "🚀 *Start Your Registration*\n\n"
                "Choose how you'd like to register:\n\n"
                "👨‍💼 *As a Trainer:*\n"
                "• Say 'I want to be a trainer'\n"
                "• Or just say 'trainer'\n\n"
                "🏃‍♀️ *As a Client:*\n"
                "• Say 'I want to find a trainer'\n"
                "• Or just say 'client'\n\n"
                "💬 *Quick Start:*\n"
                "Just say 'Hi' and I'll guide you through the process!"
            )
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling registration command: {str(e)}")
        return {'success': False, 'error': str(e)}
