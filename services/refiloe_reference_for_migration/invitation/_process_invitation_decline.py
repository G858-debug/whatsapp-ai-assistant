"""
 Process Invitation Decline
Process client decline of trainer invitation
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _process_invitation_decline(self, invitation: Dict, client_phone: str) -> Dict:
    """Process client decline of trainer invitation"""
    try:
        invitation_id = invitation['id']
        trainer_id = invitation['trainer_id']
        client_name = invitation['client_name']
        
        # Update invitation status
        self.db.table('client_invitations').update({
            'status': 'declined',
            'updated_at': datetime.now().isoformat()
        }).eq('id', invitation_id).execute()
        
        # Notify trainer of decline
        try:
            trainer_phone = self.db.table('trainers').select('whatsapp').eq('id', trainer_id).execute()
            if trainer_phone.data:
                trainer_notification = (
                    f"📋 *Invitation Update*\n\n"
                    f"{client_name} declined your training invitation.\n\n"
                    f"No worries! You can always send new invitations to other potential clients."
                )
                
                from app import app
                whatsapp_service = app.config['services']['whatsapp']
                whatsapp_service.send_message(trainer_phone.data[0]['whatsapp'], trainer_notification)
                
        except Exception as e:
            log_warning(f"Could not notify trainer of invitation decline: {str(e)}")
        
        return {
            'handled': True,
            'message': (
                "✅ I've noted that you're not interested in this training program.\n\n"
                "If you change your mind or want to find a different trainer, just say 'find a trainer' anytime! 🏃"
            )
        }
        
    except Exception as e:
        log_error(f"Error processing invitation decline: {str(e)}")
        return {
            'handled': True,
            'message': "✅ I've noted your response. If you want to find a trainer later, just say 'find a trainer'!"
        }
