"""
 Handle Approve Client Command
Handle /approve_client [identifier] command
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_approve_client_command(self, phone: str, command: str, user_data: dict) -> Dict:
    """Handle /approve_client [identifier] command"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        trainer_id = user_data.get('id')
        
        # Extract client identifier from command
        parts = command.split(' ', 1)
        if len(parts) < 2:
            response = (
                "❓ *Usage:* `/approve_client [phone_number]`\n\n"
                "Example: `/approve_client +27821234567`\n\n"
                "💡 Use `/pending_requests` to see all pending requests."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        client_identifier = parts[1].strip()
        
        # Find pending client request
        pending_client = self.db.table('clients').select('*').eq('trainer_id', trainer_id).eq('whatsapp', client_identifier).eq('connection_status', 'pending').execute()
        
        if not pending_client.data:
            response = (
                f"❌ *No Pending Request Found*\n\n"
                f"I couldn't find a pending request from {client_identifier}.\n\n"
                f"💡 Use `/pending_requests` to see all current requests."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        client_record = pending_client.data[0]
        client_phone = client_record['whatsapp']
        
        # Approve the client - update status and start registration
        self.db.table('clients').update({
            'connection_status': 'approved',
            'approved_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }).eq('id', client_record['id']).execute()
        
        # Start client registration process
        from services.registration.client_registration import ClientRegistrationHandler
        
        client_reg_handler = ClientRegistrationHandler(self.db, whatsapp_service)
        
        # Set conversation state for registration
        self.update_conversation_state(client_phone, 'REGISTRATION', {
            'type': 'client',
            'current_step': 0,
            'trainer_id': trainer_id,
            'approved_by_trainer': True
        })
        
        # Start registration with trainer context
        welcome_message = client_reg_handler.start_registration(client_phone, trainer_id)
        
        # Send welcome message to client
        whatsapp_service.send_message(client_phone, welcome_message)
        
        # Confirm to trainer
        trainer_name = user_data.get('name', 'You')
        response = (
            f"✅ *Client Approved!*\n\n"
            f"Great! I've approved the client request from {client_phone}.\n\n"
            f"🚀 *What happens next:*\n"
            f"• They're now starting registration\n"
            f"• I'll guide them through the setup process\n"
            f"• You'll be notified when they complete registration\n\n"
            f"Welcome to your growing training business! 💪"
        )
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling approve client command: {str(e)}")
        return {'success': False, 'error': str(e)}
