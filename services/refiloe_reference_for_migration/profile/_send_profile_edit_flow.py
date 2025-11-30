"""
 Send Profile Edit Flow
Send WhatsApp Flow for profile editing
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _send_profile_edit_flow(self, phone: str, user_type: str, user_data: dict) -> Dict:
    """Send WhatsApp Flow for profile editing"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Determine which flow to use based on user type
        if user_type == 'trainer':
            flow_name = 'trainer_profile_edit_flow'
            flow_title = '✏️ Edit Trainer Profile'
            flow_description = 'Update your trainer profile information'
        elif user_type == 'client':
            flow_name = 'client_profile_edit_flow'
            flow_title = '✏️ Edit Client Profile'
            flow_description = 'Update your client profile information'
        else:
            return {'success': False, 'error': 'Invalid user type for profile editing'}
        
        # Generate flow token
        from datetime import datetime
        flow_token = f"profile_edit_{user_type}_{phone}_{int(datetime.now().timestamp())}"
        
        # Create flow message
        flow_message = {
            "recipient_type": "individual",
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "flow",
                "header": {
                    "type": "text",
                    "text": flow_title
                },
                "body": {
                    "text": f"{flow_description}. Only update the fields you want to change - leave others blank to keep current values."
                },
                "footer": {
                    "text": "Quick and easy profile updates"
                },
                "action": {
                    "name": "flow",
                    "parameters": {
                        "flow_message_version": "3",
                        "flow_token": flow_token,
                        "flow_name": flow_name,
                        "flow_cta": "Edit Profile",
                        "flow_action": "navigate",
                        "flow_action_payload": {
                            "screen": "welcome"
                        }
                    }
                }
            }
        }
        
        # Send the flow message
        result = whatsapp_service.send_flow_message(flow_message)
        
        if result.get('success'):
            # Store flow token for tracking
            self._store_profile_edit_token(phone, flow_token, user_type)
            
            log_info(f"Profile edit flow sent to {phone} ({user_type})")
            return {
                'success': True,
                'message': f'{flow_title} sent successfully',
                'flow_token': flow_token
            }
        else:
            return {
                'success': False,
                'error': f'Failed to send flow: {result.get("error")}',
                'fallback_required': True
            }
            
    except Exception as e:
        log_error(f"Error sending profile edit flow: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'fallback_required': True
        }
