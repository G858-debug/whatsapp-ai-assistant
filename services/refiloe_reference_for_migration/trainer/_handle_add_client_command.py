"""
 Handle Add Client Command
Enhanced /add_client command with WhatsApp Flow integration
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_add_client_command(self, phone: str, user_data: dict) -> Dict:
    """Enhanced /add_client command with WhatsApp Flow integration"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Check trainer subscription limits first
        trainer_id = user_data.get('id')
        if trainer_id:
            try:
                from services.subscription_manager import SubscriptionManager
                subscription_manager = SubscriptionManager(self.db)
                
                if not subscription_manager.can_add_client(trainer_id):
                    limits = subscription_manager.get_client_limits(trainer_id)
                    current_clients = limits.get('current_clients', 0)
                    max_clients = limits.get('max_clients', 'unknown')
                    
                    response = (
                        f"⚠️ *Client Limit Reached*\n\n"
                        f"You currently have {current_clients}/{max_clients} clients.\n\n"
                        f"To add more clients, please upgrade your subscription:\n"
                        f"• Visit your dashboard\n"
                        f"• Choose a higher plan\n"
                        f"• Start adding unlimited clients!\n\n"
                        f"💡 *Need help?* Contact support for assistance."
                    )
                    
                    whatsapp_service.send_message(phone, response)
                    return {'success': True, 'response': response, 'limit_reached': True}
                    
            except Exception as e:
                log_warning(f"Could not check subscription limits: {str(e)}")
        
        # Try to send WhatsApp Flow for client addition
        try:
            from services.whatsapp_flow_handler import WhatsAppFlowHandler
            flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
            
            # Send client addition flow
            flow_result = self._send_client_addition_flow(phone, flow_handler)
            
            if flow_result.get('success'):
                return flow_result
            else:
                # Flow failed, use text-based fallback
                log_info(f"WhatsApp Flow failed for {phone}, using text fallback: {flow_result.get('error')}")
                return self._start_text_client_addition(phone, whatsapp_service)
                
        except Exception as e:
            log_warning(f"WhatsApp Flow not available for {phone}: {str(e)}")
            return self._start_text_client_addition(phone, whatsapp_service)
        
    except Exception as e:
        log_error(f"Error handling add client command: {str(e)}")
        return {'success': False, 'error': str(e)}
