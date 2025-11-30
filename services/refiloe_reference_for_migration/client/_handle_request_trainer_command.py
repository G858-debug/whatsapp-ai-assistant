"""
 Handle Request Trainer Command
Handle /request_trainer [email/phone] command - request specific trainer
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_request_trainer_command(self, phone: str, command: str, user_data: dict) -> Dict:
    """Handle /request_trainer [email/phone] command - request specific trainer"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Extract trainer contact info from command
        parts = command.split(' ', 1)
        if len(parts) < 2:
            response = (
                "📧 **Request Trainer Command**\n\n"
                "Usage: `/request_trainer [email or phone]`\n\n"
                "Examples:\n"
                "• `/request_trainer john@fitlife.com`\n"
                "• `/request_trainer 0821234567`\n\n"
                "This will send a request to the trainer for approval."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        trainer_contact = parts[1].strip()
        
        # Use AI intent handler to process the request
        ai_handler = app.config['services'].get('ai_intent_handler')
        if ai_handler:
            # Create intent data for the request
            intent_data = {
                'primary_intent': 'request_trainer',
                'extracted_data': {
                    'original_message': f"trainer {trainer_contact}"
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
            
            result = ai_handler._handle_request_trainer(phone, intent_data, 'client', user_data)
            whatsapp_service.send_message(phone, result)
            return {'success': True, 'response': result}
        else:
            # Fallback to existing trainer request handler
            result = self._handle_trainer_request_by_email(phone, f"trainer {trainer_contact}")
            if result.get('handled'):
                whatsapp_service.send_message(phone, result['message'])
                return {'success': True, 'response': result['message']}
            else:
                response = f"I couldn't process your trainer request for {trainer_contact}. Please check the contact details and try again."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling request trainer command: {str(e)}")
        return {'success': False, 'error': str(e)}
