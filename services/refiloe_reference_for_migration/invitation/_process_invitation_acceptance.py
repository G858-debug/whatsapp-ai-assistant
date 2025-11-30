"""
 Process Invitation Acceptance
Process client acceptance of trainer invitation
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _process_invitation_acceptance(self, invitation: Dict, client_phone: str) -> Dict:
    """Process client acceptance of trainer invitation"""
    try:
        invitation_id = invitation['id']
        trainer_id = invitation['trainer_id']
        client_name = invitation['client_name']
        
        # Update invitation status
        self.db.table('client_invitations').update({
            'status': 'accepted',
            'updated_at': datetime.now().isoformat()
        }).eq('id', invitation_id).execute()
        
        # Get trainer info
        trainer_result = self.db.table('trainers').select('name, business_name').eq('id', trainer_id).execute()
        trainer_name = 'Your trainer'
        business_name = 'the training program'
        
        if trainer_result.data:
            trainer_info = trainer_result.data[0]
            trainer_name = trainer_info.get('name', 'Your trainer')
            business_name = trainer_info.get('business_name') or f"{trainer_name}'s training program"
        
        # Start client registration process
        from services.registration.client_registration import ClientRegistrationHandler
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        client_reg_handler = ClientRegistrationHandler(self.db, whatsapp_service)
        
        # Set conversation state for registration
        self.update_conversation_state(client_phone, 'REGISTRATION', {
            'type': 'client',
            'current_step': 0,
            'trainer_id': trainer_id,
            'invitation_accepted': True
        })
        
        # Start registration with trainer context
        welcome_message = client_reg_handler.start_registration(client_phone, trainer_id)
        
        # Notify trainer of acceptance
        try:
            trainer_phone = self.db.table('trainers').select('whatsapp').eq('id', trainer_id).execute()
            if trainer_phone.data:
                trainer_notification = (
                    f"🎉 *Great News!*\n\n"
                    f"{client_name} accepted your invitation and is now registering!\n\n"
                    f"I'm guiding them through the setup process. You'll be notified when they complete registration."
                )
                
                from app import app
                whatsapp_service = app.config['services']['whatsapp']
                whatsapp_service.send_message(trainer_phone.data[0]['whatsapp'], trainer_notification)
                
        except Exception as e:
            log_warning(f"Could not notify trainer of invitation acceptance: {str(e)}")
        
        return {
            'handled': True,
            'message': welcome_message
        }
        
    except Exception as e:
        log_error(f"Error processing invitation acceptance: {str(e)}")
        return {
            'handled': True,
            'message': "❌ Sorry, there was an error processing your acceptance. Please contact your trainer directly."
        }
