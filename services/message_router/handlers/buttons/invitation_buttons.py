"""
Invitation Button Handler
Handles client accepting/declining trainer invitations (client_fills flow)
"""
from typing import Dict, Optional
from datetime import datetime
import pytz

from utils.logger import log_info, log_error
from config import Config


class InvitationButtonHandler:
    """Handles invitation acceptance/decline buttons for client_fills flow"""

    def __init__(self, supabase_client, whatsapp_service, auth_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')

        # Button pattern routing
        self.button_patterns = {
            'accept_invitation_': self._handle_accept_client_invitation,
            'decline_invitation_': self._handle_decline_client_invitation,
            # Legacy patterns for backwards compatibility
            'accept_client_': self._handle_accept_client_invitation,
            'decline_client_': self._handle_decline_client_invitation,
        }

    def handle_invitation_button(self, phone: str, button_id: str) -> Dict:
        """Handle invitation buttons using pattern routing"""
        try:
            # Check button_patterns for matching prefix
            for pattern, handler in self.button_patterns.items():
                if button_id.startswith(pattern):
                    return handler(phone, button_id)

            # No matching pattern found
            return {'success': False, 'response': 'Unknown invitation button', 'handler': 'unknown_invitation_button'}

        except Exception as e:
            log_error(f"Error handling invitation button: {str(e)}")
            return {'success': False, 'response': 'Error processing invitation button', 'handler': 'invitation_button_error'}

    def _handle_accept_client_invitation(self, phone: str, button_id: str) -> Dict:
        """Client accepting trainer invitation"""
        try:
            # Extract invitation_id from button_id (support both new and legacy patterns)
            invitation_id = button_id.replace('accept_invitation_', '').replace('accept_client_', '')

            # invitation_id is already a UUID string from the button payload
            # No conversion needed
            log_info(f"Processing accept invitation for invitation_id: {invitation_id}")

            # Get invitation details
            invitation = self._get_invitation(invitation_id)
            if not invitation:
                return {'success': False, 'response': 'Invitation not found or expired', 'handler': 'accept_invitation_not_found'}

            # Verify invitation is valid
            if invitation['status'] not in ['pending_client_completion', 'pending']:
                return {'success': False, 'response': f"Invitation is no longer valid (status: {invitation['status']})", 'handler': 'accept_invitation_invalid_status'}

            # Verify the phone matches
            if invitation['client_phone'] != phone:
                log_error(f"Phone mismatch: {phone} vs {invitation['client_phone']}")
                return {'success': False, 'response': 'Invitation not found for this number', 'handler': 'accept_invitation_phone_mismatch'}

            # Update invitation status to 'accepted'
            self.db.table('client_invitations').update({
                'status': 'accepted',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', invitation_id).execute()

            log_info(f"Client {phone} accepted invitation {invitation_id}")

            # Get trainer details
            trainer = self._get_trainer(invitation['trainer_id'])
            if not trainer:
                return {'success': False, 'response': 'Trainer not found', 'handler': 'accept_invitation_trainer_not_found'}

            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'your trainer'

            # Launch WhatsApp Flow for client profile completion
            flow_result = self._launch_client_onboarding_flow(
                phone=phone,
                invitation_id=invitation_id,
                trainer_id=invitation['trainer_id'],
                trainer_name=trainer_name
            )

            if flow_result.get('success'):
                return {
                    'success': True,
                    'response': f"Great! Let's set up your fitness profile 📝\n\nThis helps {trainer_name} create the perfect program for you.",
                    'handler': 'accept_client_invitation'
                }
            else:
                return {
                    'success': False,
                    'response': 'Failed to launch onboarding flow',
                    'handler': 'accept_invitation_flow_failed',
                    'error': flow_result.get('error')
                }

        except Exception as e:
            log_error(f"Error accepting client invitation: {str(e)}")
            return {'success': False, 'response': 'Error accepting invitation', 'handler': 'accept_invitation_error'}

    def _handle_decline_client_invitation(self, phone: str, button_id: str) -> Dict:
        """Client declining trainer invitation"""
        try:
            # Extract invitation_id from button_id (support both new and legacy patterns)
            invitation_id = button_id.replace('decline_invitation_', '').replace('decline_client_', '')

            # invitation_id is already a UUID string from the button payload
            # No conversion needed
            log_info(f"Processing decline invitation for invitation_id: {invitation_id}")

            # Get invitation details
            invitation = self._get_invitation(invitation_id)
            if not invitation:
                return {'success': False, 'response': 'Invitation not found or expired', 'handler': 'decline_invitation_not_found'}

            # Verify the phone matches
            if invitation['client_phone'] != phone:
                log_error(f"Phone mismatch: {phone} vs {invitation['client_phone']}")
                return {'success': False, 'response': 'Invitation not found for this number', 'handler': 'decline_invitation_phone_mismatch'}

            # Update invitation status to 'declined'
            self.db.table('client_invitations').update({
                'status': 'declined',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', invitation_id).execute()

            log_info(f"Client {phone} declined invitation {invitation_id}")

            # Get trainer details for notification
            trainer = self._get_trainer(invitation['trainer_id'])
            if trainer:
                trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'the trainer'
                trainer_phone = trainer.get('whatsapp') or trainer.get('phone')

                # Notify trainer
                if trainer_phone:
                    client_name = invitation.get('client_name', 'The client')
                    trainer_msg = f"ℹ️ {client_name} has declined your training invitation."
                    self.whatsapp.send_message(trainer_phone, trainer_msg)

            # Ask for optional reason
            from services.tasks import TaskService
            task_service = TaskService(self.db)

            task_service.create_task(
                phone=phone,
                user_type='client',
                task_type='decline_reason',
                task_data={
                    'invitation_id': invitation_id,
                    'trainer_id': str(invitation['trainer_id'])
                }
            )

            msg = (
                "You've declined the training invitation.\n\n"
                "Would you like to share a reason? (optional)\n\n"
                "You can type your reason or type /skip to finish."
            )

            return {
                'success': True,
                'response': msg,
                'handler': 'decline_client_invitation'
            }

        except Exception as e:
            log_error(f"Error declining client invitation: {str(e)}")
            return {'success': False, 'response': 'Error declining invitation', 'handler': 'decline_invitation_error'}

    def _get_invitation(self, invitation_id: str) -> Optional[Dict]:
        """Get invitation by ID"""
        try:
            result = self.db.table('client_invitations').select('*').eq('id', invitation_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            log_error(f"Error getting invitation: {str(e)}")
            return None

    def _get_trainer(self, trainer_id: str) -> Optional[Dict]:
        """Get trainer by ID (UUID)"""
        try:
            result = self.db.table('trainers').select('*').eq('id', trainer_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            log_error(f"Error getting trainer: {str(e)}")
            return None

    def _launch_client_onboarding_flow(self, phone: str, invitation_id: str, trainer_id: str, trainer_name: str) -> Dict:
        """Launch WhatsApp Flow for client profile completion"""
        try:
            # Get invitation details to fetch selected_price
            invitation = self._get_invitation(invitation_id)
            selected_price = None
            if invitation:
                selected_price = invitation.get('custom_price') or invitation.get('custom_price_per_session')

            # Create flow token with invitation context
            flow_token = f"client_onboarding_invitation_{invitation_id}_{phone}_{int(datetime.now().timestamp())}"

            # Use the configured client onboarding flow ID
            flow_id = Config.CLIENT_ONBOARDING_FLOW_ID

            # Create flow message
            flow_message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "body": {
                        "text": f"Great! Let's set up your fitness profile 📝\n\nThis helps {trainer_name} create the perfect program for you."
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": flow_id,
                            "flow_cta": "Start Profile",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "welcome",
                                "data": {
                                    "flow_token": flow_token,
                                    "trainer_name": trainer_name,
                                    "selected_price": str(selected_price) if selected_price else "500"
                                }
                            }
                        }
                    }
                }
            }

            # Store flow token for tracking
            self._store_flow_token(phone, flow_token, invitation_id)

            # Send flow message
            result = self.whatsapp.send_flow_message(flow_message)

            if result.get('success'):
                log_info(f"Launched client onboarding flow for invitation {invitation_id}")
                return {'success': True, 'flow_token': flow_token}
            else:
                log_error(f"Failed to send flow message: {result.get('error')}")
                return {'success': False, 'error': result.get('error')}

        except Exception as e:
            log_error(f"Error launching client onboarding flow: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _store_flow_token(self, phone: str, flow_token: str, invitation_id: str):
        """Store flow token for tracking"""
        try:
            self.db.table('flow_tokens').insert({
                'phone_number': phone,
                'flow_token': flow_token,
                'flow_type': 'client_onboarding',
                'flow_data': {
                    'invitation_id': invitation_id
                },
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
        except Exception as e:
            log_error(f"Failed to store flow token: {str(e)}")
