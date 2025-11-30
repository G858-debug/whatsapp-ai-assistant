"""
 Handle Invitation Response
Handle client's response to trainer invitation
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_invitation_response(self, client_phone: str, message: str) -> Dict:
    """Handle client's response to trainer invitation"""
    try:
        message_lower = message.strip().lower()
        
        # Check if this looks like an invitation acceptance
        acceptance_keywords = ['accept', 'yes', 'join', 'start', 'ok', 'sure', 'let\'s go', 'i accept']
        decline_keywords = ['decline', 'no', 'not interested', 'cancel', 'reject']
        
        is_acceptance = any(keyword in message_lower for keyword in acceptance_keywords)
        is_decline = any(keyword in message_lower for keyword in decline_keywords)
        
        if not (is_acceptance or is_decline):
            return {'handled': False}
        
        # Look for pending invitation for this phone number
        invitation_result = self.db.table('client_invitations').select('*').eq('client_phone', client_phone).eq('status', 'pending').execute()
        
        if not invitation_result.data:
            # No pending invitation found
            if is_acceptance:
                return {
                    'handled': True,
                    'message': "I don't see any pending trainer invitations for your number. If you're looking for a trainer, say 'find a trainer' and I'll help you get started! 🏃"
                }
            else:
                return {'handled': False}
        
        # Get the most recent invitation
        invitation = invitation_result.data[0]
        invitation_id = invitation['id']
        trainer_id = invitation['trainer_id']
        
        # Check if invitation has expired
        from datetime import datetime
        import pytz
        
        sa_tz = pytz.timezone('Africa/Johannesburg')
        now = datetime.now(sa_tz)
        expires_at = datetime.fromisoformat(invitation['expires_at'].replace('Z', '+00:00'))
        
        if now > expires_at:
            # Invitation expired
            self.db.table('client_invitations').update({'status': 'expired'}).eq('id', invitation_id).execute()
            
            return {
                'handled': True,
                'message': "⏰ Sorry, this invitation has expired. Please contact your trainer for a new invitation, or say 'find a trainer' to search for trainers."
            }
        
        if is_acceptance:
            # Accept the invitation
            return self._process_invitation_acceptance(invitation, client_phone)
        else:
            # Decline the invitation
            return self._process_invitation_decline(invitation, client_phone)
            
    except Exception as e:
        log_error(f"Error handling invitation response: {str(e)}")
        return {'handled': False}
