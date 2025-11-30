"""
 Process Text Client Invitation
Process client invitation from text flow
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _process_text_client_invitation(self, trainer_phone: str, client_data: Dict) -> Dict:
    """Process client invitation from text flow"""
    try:
        # Get trainer info
        user_context = self.get_user_context(trainer_phone)
        trainer_id = user_context.get('user_data', {}).get('id')
        
        if not trainer_id:
            return {
                'success': False,
                'message': "❌ Could not find your trainer profile. Please try again."
            }
        
        # Use the WhatsApp flow handler to create and send invitation
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        from services.whatsapp_flow_handler import WhatsAppFlowHandler
        
        flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
        result = flow_handler._create_and_send_invitation(trainer_id, client_data)
        
        if result.get('success'):
            return {
                'success': True,
                'completed': True,
                'message': result['message']
            }
        else:
            return {
                'success': False,
                'message': f"❌ Failed to send invitation: {result.get('error', 'Unknown error')}"
            }
            
    except Exception as e:
        log_error(f"Error processing text client invitation: {str(e)}")
        return {
            'success': False,
            'message': "❌ Sorry, there was an error sending the invitation. Please try again."
        }
