"""
 Handle Accept Invitation Command
Handle /accept_invitation [token] command
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_accept_invitation_command(self, phone: str, command: str, user_data: dict) -> Dict:
    """Handle /accept_invitation [token] command"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Extract invitation token from command
        parts = command.split(' ', 1)
        if len(parts) < 2:
            response = (
                "❓ *Usage:* `/accept_invitation [token]`\n\n"
                "Example: `/accept_invitation abc12345`\n\n"
                "💡 Use `/invitations` to see all your invitations with tokens."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        token_partial = parts[1].strip()
        
        # Find invitation by partial token (first 8 characters)
        invitations = self.db.table('client_invitations').select('*').eq('client_phone', phone).eq('status', 'pending').execute()
        
        matching_invitation = None
        for invitation in invitations.data:
            if invitation['invitation_token'].startswith(token_partial):
                matching_invitation = invitation
                break
        
        if not matching_invitation:
            response = (
                f"❌ *Invitation Not Found*\n\n"
                f"I couldn't find a pending invitation with token '{token_partial}'.\n\n"
                f"💡 Use `/invitations` to see all your current invitations."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        # Check if invitation has expired
        from datetime import datetime
        import pytz
        
        sa_tz = pytz.timezone('Africa/Johannesburg')
        now = datetime.now(sa_tz)
        expires_at = datetime.fromisoformat(matching_invitation['expires_at'].replace('Z', '+00:00'))
        
        if now > expires_at:
            # Mark as expired
            self.db.table('client_invitations').update({'status': 'expired'}).eq('id', matching_invitation['id']).execute()
            
            response = (
                "⏰ *Invitation Expired*\n\n"
                "Sorry, this invitation has expired. Please contact the trainer for a new invitation.\n\n"
                "💡 Use `/find_trainer` to search for other trainers."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        # Accept the invitation - use existing invitation response handler
        invitation_response = self._process_invitation_acceptance(matching_invitation, phone)
        
        whatsapp_service.send_message(phone, invitation_response['message'])
        return {'success': True, 'response': invitation_response['message']}
        
    except Exception as e:
        log_error(f"Error handling accept invitation command: {str(e)}")
        return {'success': False, 'error': str(e)}
