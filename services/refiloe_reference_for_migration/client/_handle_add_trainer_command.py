"""
 Handle Add Trainer Command
Handle /add_trainer [email/phone] command - directly add trainer
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_add_trainer_command(self, phone: str, command: str, user_data: dict) -> Dict:
    """Handle /add_trainer [email/phone] command - directly add trainer"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Extract trainer contact info from command
        parts = command.split(' ', 1)
        if len(parts) < 2:
            response = (
                "🚀 **Add Trainer Command**\n\n"
                "Usage: `/add_trainer [email or phone]`\n\n"
                "Examples:\n"
                "• `/add_trainer sarah@gym.com`\n"
                "• `/add_trainer 0829876543`\n\n"
                "This will try to add you directly to the trainer's program.\n"
                "Note: Only works if the trainer allows auto-approval."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        trainer_contact = parts[1].strip()
        
        # Use AI intent handler to process the direct addition
        ai_handler = app.config['services'].get('ai_intent_handler')
        if ai_handler:
            # Create intent data for the direct addition
            intent_data = {
                'primary_intent': 'add_trainer_direct',
                'extracted_data': {
                    'original_message': f"add me to trainer {trainer_contact}"
                }
            }
            
            # Check if it's email or phone and add to extracted data
            import re
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', trainer_contact):
                intent_data['extracted_data']['email'] = trainer_contact
            elif re.match(r'^(?:0|27|\+27)?[678]\d{8}$', trainer_contact):
                # Normalize phone number
                clean_phone = re.sub(r'^(?:27|\+27)', '0', trainer_contact)
                if not clean_phone.startswith('0'):
                    clean_phone = '0' + clean_phone
                intent_data['extracted_data']['phone_number'] = clean_phone
            
            result = ai_handler._handle_add_trainer_direct(phone, intent_data, 'client', user_data)
            whatsapp_service.send_message(phone, result)
            return {'success': True, 'response': result}
        else:
            # Fallback - try request instead
            response = (
                f"Direct trainer addition is not available right now.\n\n"
                f"Try using `/request_trainer {trainer_contact}` to send a request instead."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling add trainer command: {str(e)}")
        return {'success': False, 'error': str(e)}
