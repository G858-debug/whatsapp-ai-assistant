"""
 Handle Clients Command
Handle /clients command - show trainer's clients
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_clients_command(self, phone: str, user_data: dict) -> Dict:
    """Handle /clients command - show trainer's clients"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        trainer_id = user_data.get('id')
        if not trainer_id:
            response = "❌ Unable to find your trainer profile. Please contact support."
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        # Get trainer's clients
        clients = self.db.table('clients').select('*').eq('trainer_id', trainer_id).eq('status', 'active').execute()
        
        if not clients.data:
            response = (
                "👥 *Your Clients*\n\n"
                "You don't have any active clients yet.\n\n"
                "🚀 *Get Started:*\n"
                "• Type `/add_client` to add your first client\n"
                "• Share your WhatsApp number with potential clients\n"
                "• They can message you to get started!\n\n"
                "💡 *Tip:* Clients can find you by saying 'I need a trainer'"
            )
        else:
            client_list = []
            for i, client in enumerate(clients.data, 1):
                name = client.get('name', 'Unknown')
                sessions = client.get('sessions_remaining', 0)
                client_list.append(f"{i}. {name} ({sessions} sessions left)")
            
            clients_text = '\n'.join(client_list)
            response = (
                f"👥 *Your Clients ({len(clients.data)})*\n\n"
                f"{clients_text}\n\n"
                f"📱 *Actions:*\n"
                f"• Type `/add_client` to add a new client\n"
                f"• Message me about specific client needs"
            )
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling clients command: {str(e)}")
        return {'success': False, 'error': str(e)}
