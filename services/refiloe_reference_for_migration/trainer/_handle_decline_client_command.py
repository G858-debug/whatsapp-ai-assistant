"""
 Handle Decline Client Command
Handle /decline_client [identifier] command
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_decline_client_command(self, phone: str, command: str, user_data: dict) -> Dict:
    """Handle /decline_client [identifier] command"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        trainer_id = user_data.get('id')
        
        # Extract client identifier from command
        parts = command.split(' ', 1)
        if len(parts) < 2:
            response = (
                "❓ *Usage:* `/decline_client [phone_number]`\n\n"
                "Example: `/decline_client +27821234567`\n\n"
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
        
        # Decline the client - update status
        self.db.table('clients').update({
            'connection_status': 'declined',
            'updated_at': datetime.now().isoformat()
        }).eq('id', client_record['id']).execute()
        
        # Notify client of decline
        decline_message = (
            f"📋 *Training Request Update*\n\n"
            f"Thank you for your interest in training! Unfortunately, your trainer request wasn't approved at this time.\n\n"
            f"💡 *Don't worry!* There are many great trainers available:\n"
            f"• Say 'find a trainer' to search for other trainers\n"
            f"• Ask friends for trainer recommendations\n"
            f"• Try reaching out to other trainers directly\n\n"
            f"Keep pursuing your fitness goals! 💪"
        )
        
        whatsapp_service.send_message(client_phone, decline_message)
        
        # Confirm to trainer
        response = (
            f"✅ *Client Request Declined*\n\n"
            f"I've declined the request from {client_phone} and notified them politely.\n\n"
            f"💡 *Remember:* You can always change your mind later if you have capacity for more clients.\n\n"
            f"Focus on providing great service to your current clients! 🌟"
        )
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling decline client command: {str(e)}")
        return {'success': False, 'error': str(e)}
