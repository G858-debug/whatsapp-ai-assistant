"""
 Handle Decline Invitation Command
Handle /decline_invitation [token] command
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_decline_invitation_command(self, phone: str, command: str, user_data: dict) -> Dict:
    """Handle /decline_invitation [token] command"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Extract invitation token from command
        parts = command.split(' ', 1)
        if len(parts) < 2:
            response = (
                "❓ *Usage:* `/decline_invitation [token]`\n\n"
                "Example: `/decline_invitation abc12345`\n\n"
                "💡 Use `/invitations` to see all your invitations with tokens."
            )
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        token_partial = parts[1].strip()
        
        # Find invitation by partial token
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
        
        # Decline the invitation - use existing invitation response handler
        invitation_response = self._process_invitation_decline(matching_invitation, phone)
        
        whatsapp_service.send_message(phone, invitation_response['message'])
        return {'success': True, 'response': invitation_response['message']}
        
    except Exception as e:
        log_error(f"Error handling decline invitation command: {str(e)}")
        return {'success': False, 'error': str(e)}
