"""
 Start Text Client Addition
Text-based client addition fallback
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _start_text_client_addition(self, phone: str, whatsapp_service) -> Dict:
    """Text-based client addition fallback"""
    try:
        # Set conversation state for text-based client addition
        self.update_conversation_state(phone, 'TEXT_CLIENT_ADDITION', {
            'step': 'name',
            'client_data': {}
        })
        
        response = (
            "➕ *Add new client* (Text Mode)\n\n"
            "I'll help you add a client step by step.\n\n"
            "📝 *Step 1 of 4*\n\n"
            "What's your client's full name?"
        )
        
        whatsapp_service.send_message(phone, response)
        
        return {
            'success': True,
            'method': 'text_fallback',
            'message': response,
            'conversation_state_update': {
                'state': 'TEXT_CLIENT_ADDITION',
                'context': {
                    'step': 'name',
                    'client_data': {}
                }
            }
        }
        
    except Exception as e:
        log_error(f"Error starting text client addition: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
