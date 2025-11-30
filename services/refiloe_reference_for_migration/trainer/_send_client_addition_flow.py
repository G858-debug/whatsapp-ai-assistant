"""
 Send Client Addition Flow
Send WhatsApp Flow for client addition
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _send_client_addition_flow(self, phone: str, flow_handler) -> Dict:
    """Send WhatsApp Flow for client addition"""
    try:
        # Create flow message for client addition
        flow_message = self._create_client_addition_flow_message(phone)
        
        if not flow_message:
            return {
                'success': False,
                'error': 'Failed to create client addition flow message'
            }
        
        # Send via WhatsApp service
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        result = whatsapp_service.send_flow_message(flow_message)
        
        if result.get('success'):
            return {
                'success': True,
                'method': 'whatsapp_flow',
                'message': '📋 I\'ve sent you a client addition form! Please fill it out to add your new client.',
                'flow_token': flow_message['interactive']['action']['parameters']['flow_token']
            }
        else:
            return {
                'success': False,
                'error': f'Failed to send flow: {result.get("error")}'
            }
            
    except Exception as e:
        log_error(f"Error sending client addition flow: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
