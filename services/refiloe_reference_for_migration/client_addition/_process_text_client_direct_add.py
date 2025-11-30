"""
 Process Text Client Direct Add
Process direct client addition from text flow
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _process_text_client_direct_add(self, trainer_phone: str, client_data: Dict) -> Dict:
    """Process direct client addition from text flow"""
    try:
        # Get trainer info
        user_context = self.get_user_context(trainer_phone)
        trainer_id = user_context.get('user_data', {}).get('id')
        
        if not trainer_id:
            return {
                'success': False,
                'message': "❌ Could not find your trainer profile. Please try again."
            }
        
        # Use the WhatsApp flow handler to add client directly
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        from services.whatsapp_flow_handler import WhatsAppFlowHandler
        
        flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
        result = flow_handler._add_client_directly(trainer_id, client_data)
        
        if result.get('success'):
            return {
                'success': True,
                'completed': True,
                'message': result['message']
            }
        else:
            return {
                'success': False,
                'message': f"❌ Failed to add client: {result.get('error', 'Unknown error')}"
            }
            
    except Exception as e:
        log_error(f"Error processing text client direct add: {str(e)}")
        return {
            'success': False,
            'message': "❌ Sorry, there was an error adding the client. Please try again."
        }
