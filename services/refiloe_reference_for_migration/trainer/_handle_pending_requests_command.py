"""
 Handle Pending Requests Command
Handle /pending_requests command - show pending client requests
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_pending_requests_command(self, phone: str, user_data: dict) -> Dict:
    """Handle /pending_requests command - show pending client requests"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        trainer_id = user_data.get('id')
        
        # Get pending client requests
        pending_requests = self.db.table('clients').select('*').eq('trainer_id', trainer_id).eq('connection_status', 'pending').execute()
        
        if not pending_requests.data:
            response = (
                "📋 *No Pending Requests*\n\n"
                "You don't have any pending client requests at the moment.\n\n"
                "💡 *To get more clients:*\n"
                "• Use `/add_client` to invite clients directly\n"
                "• Share your email with potential clients\n"
                "• They can request you by saying 'trainer [your email]'\n\n"
                "Keep growing your business! 💪"
            )
        else:
            request_count = len(pending_requests.data)
            
            response = f"👋 *Pending Client Requests ({request_count})*\n\n"
            
            for i, request in enumerate(pending_requests.data, 1):
                client_phone = request['whatsapp']
                requested_date = request['created_at'][:10]
                
                response += f"{i}. 📱 {client_phone}\n"
                response += f"   📅 Requested: {requested_date}\n"
                response += f"   ✅ `/approve_client {client_phone}`\n"
                response += f"   ❌ `/decline_client {client_phone}`\n\n"
            
            response += "💡 *Quick Actions:*\n"
            response += "• Reply with the approve/decline commands above\n"
            response += "• Or just say 'approve [phone]' or 'decline [phone]'"
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling pending requests command: {str(e)}")
        return {'success': False, 'error': str(e)}
