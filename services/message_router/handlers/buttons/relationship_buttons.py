"""
Relationship Button Handler
Handles trainer-client relationship buttons (accept/decline invitations)
"""
from typing import Dict
from utils.logger import log_error


class RelationshipButtonHandler:
    """Handles relationship invitation buttons"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
    
    def handle_relationship_button(self, phone: str, button_id: str) -> Dict:
        """Handle relationship invitation buttons"""
        try:
            if button_id.startswith('accept_trainer_'):
                return self._handle_accept_trainer(phone, button_id)
            elif button_id.startswith('decline_trainer_'):
                return self._handle_decline_trainer(phone, button_id)
            elif button_id.startswith('accept_client_'):
                return self._handle_accept_client(phone, button_id)
            elif button_id.startswith('decline_client_'):
                return self._handle_decline_client(phone, button_id)
            elif button_id.startswith('send_invitation_'):
                return self._handle_send_invitation(phone, button_id)
            elif button_id.startswith('cancel_invitation_'):
                return self._handle_cancel_invitation(phone, button_id)
            elif button_id.startswith('resend_invite_'):
                return self._handle_resend_invite(phone, button_id)
            elif button_id.startswith('cancel_invite_'):
                return self._handle_cancel_invite(phone, button_id)
            elif button_id.startswith('contact_client_'):
                return self._handle_contact_client(phone, button_id)
            else:
                return {'success': False, 'response': 'Unknown relationship button', 'handler': 'unknown_relationship_button'}

        except Exception as e:
            log_error(f"Error handling relationship button: {str(e)}")
            return {'success': False, 'response': 'Error processing relationship button', 'handler': 'relationship_button_error'}
    
    def _handle_accept_trainer(self, phone: str, button_id: str) -> Dict:
        """Client accepting trainer invitation"""
        try:
            from services.relationships import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            trainer_id = button_id.replace('accept_trainer_', '')
            
            # Get client_id
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('client_id'):
                return {'success': False, 'response': 'Error: Client ID not found', 'handler': 'button_error'}
            
            client_id = user['client_id']
            
            # Approve relationship
            success, error_msg = relationship_service.approve_relationship(trainer_id, client_id)
            
            if success:
                return self._notify_relationship_accepted(phone, trainer_id, client_id, 'trainer')
            
            return {'success': False, 'response': 'Failed to accept invitation', 'handler': 'accept_trainer_failed'}
            
        except Exception as e:
            log_error(f"Error accepting trainer: {str(e)}")
            return {'success': False, 'response': 'Error accepting invitation', 'handler': 'accept_trainer_error'}
    
    def _handle_decline_trainer(self, phone: str, button_id: str) -> Dict:
        """Client declining trainer invitation"""
        try:
            from services.relationships import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            trainer_id = button_id.replace('decline_trainer_', '')
            
            # Get client_id
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('client_id'):
                return {'success': False, 'response': 'Error: Client ID not found', 'handler': 'button_error'}
            
            client_id = user['client_id']
            
            # Decline relationship
            success, error_msg = relationship_service.decline_relationship(trainer_id, client_id)
            
            if success:
                return self._notify_relationship_declined(phone, trainer_id, client_id, 'trainer')
            
            return {'success': False, 'response': 'Failed to decline invitation', 'handler': 'decline_trainer_failed'}
            
        except Exception as e:
            log_error(f"Error declining trainer: {str(e)}")
            return {'success': False, 'response': 'Error declining invitation', 'handler': 'decline_trainer_error'}
    
    def _handle_accept_client(self, phone: str, button_id: str) -> Dict:
        """Trainer accepting client invitation"""
        try:
            from services.relationships import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            client_id = button_id.replace('accept_client_', '')
            
            # Get trainer_id
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('trainer_id'):
                return {'success': False, 'response': 'Error: Trainer ID not found', 'handler': 'button_error'}
            
            trainer_id = user['trainer_id']
            
            # Approve relationship
            success, error_msg = relationship_service.approve_relationship(trainer_id, client_id)
            
            if success:
                return self._notify_relationship_accepted(phone, trainer_id, client_id, 'client')
            
            return {'success': False, 'response': 'Failed to accept invitation', 'handler': 'accept_client_failed'}
            
        except Exception as e:
            log_error(f"Error accepting client: {str(e)}")
            return {'success': False, 'response': 'Error accepting invitation', 'handler': 'accept_client_error'}
    
    def _handle_decline_client(self, phone: str, button_id: str) -> Dict:
        """Trainer declining client invitation"""
        try:
            from services.relationships import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            client_id = button_id.replace('decline_client_', '')
            
            # Get trainer_id
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('trainer_id'):
                return {'success': False, 'response': 'Error: Trainer ID not found', 'handler': 'button_error'}
            
            trainer_id = user['trainer_id']
            
            # Decline relationship
            success, error_msg = relationship_service.decline_relationship(trainer_id, client_id)
            
            if success:
                return self._notify_relationship_declined(phone, trainer_id, client_id, 'client')
            
            return {'success': False, 'response': 'Failed to decline invitation', 'handler': 'decline_client_failed'}
            
        except Exception as e:
            log_error(f"Error declining client: {str(e)}")
            return {'success': False, 'response': 'Error declining invitation', 'handler': 'decline_client_error'}
    
    def _notify_relationship_accepted(self, phone: str, trainer_id: str, client_id: str, accepted_role: str) -> Dict:
        """Notify both parties when relationship is accepted"""
        try:
            if accepted_role == 'trainer':
                # Client accepted trainer
                trainer_result = self.db.table('trainers').select('name, first_name, last_name, whatsapp').ilike(
                    'trainer_id', trainer_id
                ).execute()
                
                if trainer_result.data:
                    trainer = trainer_result.data[0]
                    trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'the trainer'
                    
                    # Notify client
                    msg = f"✅ You're now connected with {trainer_name}!"
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify trainer
                    client_result = self.db.table('clients').select('name').eq(
                        'client_id', client_id
                    ).execute()
                    
                    if client_result.data:
                        client = client_result.data[0]
                        client_name = client.get('name') or 'the client'
                        trainer_msg = f"✅ {client_name} accepted your invitation!"
                        self.whatsapp.send_message(trainer.get('whatsapp'), trainer_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'accept_trainer'}
            
            else:
                # Trainer accepted client
                client_result = self.db.table('clients').select('name, whatsapp').eq(
                    'client_id', client_id
                ).execute()
                
                if client_result.data:
                    client = client_result.data[0]
                    client_name = client.get('name') or 'the client'
                    
                    # Notify trainer
                    msg = f"✅ You're now connected with {client_name}!"
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify client
                    trainer_result = self.db.table('trainers').select('name, first_name, last_name').ilike(
                        'trainer_id', trainer_id
                    ).execute()
                    
                    if trainer_result.data:
                        trainer = trainer_result.data[0]
                        trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'the trainer'
                        client_msg = f"✅ {trainer_name} accepted your invitation!"
                        self.whatsapp.send_message(client.get('whatsapp'), client_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'accept_client'}
            
            return {'success': False, 'response': 'Error notifying parties', 'handler': 'notification_error'}
            
        except Exception as e:
            log_error(f"Error notifying relationship accepted: {str(e)}")
            return {'success': False, 'response': 'Error sending notifications', 'handler': 'notification_error'}
    
    def _notify_relationship_declined(self, phone: str, trainer_id: str, client_id: str, declined_role: str) -> Dict:
        """Notify both parties when relationship is declined"""
        try:
            if declined_role == 'trainer':
                # Client declined trainer
                trainer_result = self.db.table('trainers').select('name, first_name, last_name, whatsapp').ilike(
                    'trainer_id', trainer_id
                ).execute()
                
                if trainer_result.data:
                    trainer = trainer_result.data[0]
                    trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'the trainer'
                    
                    # Notify client
                    msg = f"You declined the invitation from {trainer_name}."
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify trainer
                    client_result = self.db.table('clients').select('name').eq(
                        'client_id', client_id
                    ).execute()
                    
                    if client_result.data:
                        client = client_result.data[0]
                        client_name = client.get('name') or 'the client'
                        trainer_msg = f"ℹ️ {client_name} declined your invitation."
                        self.whatsapp.send_message(trainer.get('whatsapp'), trainer_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'decline_trainer'}
            
            else:
                # Trainer declined client
                client_result = self.db.table('clients').select('name, whatsapp').eq(
                    'client_id', client_id
                ).execute()
                
                if client_result.data:
                    client = client_result.data[0]
                    client_name = client.get('name') or 'the client'
                    
                    # Notify trainer
                    msg = f"You declined the invitation from {client_name}."
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify client
                    trainer_result = self.db.table('trainers').select('name, first_name, last_name').ilike(
                        'trainer_id', trainer_id
                    ).execute()
                    
                    if trainer_result.data:
                        trainer = trainer_result.data[0]
                        trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'the trainer'
                        client_msg = f"ℹ️ {trainer_name} declined your invitation."
                        self.whatsapp.send_message(client.get('whatsapp'), client_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'decline_client'}
            
            return {'success': False, 'response': 'Error notifying parties', 'handler': 'notification_error'}
            
        except Exception as e:
            log_error(f"Error notifying relationship declined: {str(e)}")
            return {'success': False, 'response': 'Error sending notifications', 'handler': 'notification_error'}

    def _handle_send_invitation(self, phone: str, button_id: str) -> Dict:
        """Trainer sending invitation to available client"""
        try:
            from services.flows.relationships.trainer_flows.invitation_flow import InvitationFlow
            from services.tasks import TaskService

            client_id = button_id.replace('send_invitation_', '')

            # Get trainer_id
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('trainer_id'):
                return {'success': False, 'response': 'Error: Trainer ID not found', 'handler': 'button_error'}

            trainer_id = user['trainer_id']

            # Initialize invitation flow
            task_service = TaskService(self.db)
            invitation_flow = InvitationFlow(self.db, self.whatsapp, task_service)

            # Send invitation to available client
            result = invitation_flow.send_invitation_to_available_client(phone, trainer_id, client_id)

            return result

        except Exception as e:
            log_error(f"Error sending invitation to available client: {str(e)}")
            return {'success': False, 'response': 'Error sending invitation', 'handler': 'send_invitation_error'}

    def _handle_cancel_invitation(self, phone: str, button_id: str) -> Dict:
        """Trainer cancelling invitation to available client"""
        try:
            from services.flows.relationships.trainer_flows.invitation_flow import InvitationFlow
            from services.tasks import TaskService

            client_id = button_id.replace('cancel_invitation_', '')

            # Initialize invitation flow
            task_service = TaskService(self.db)
            invitation_flow = InvitationFlow(self.db, self.whatsapp, task_service)

            # Cancel invitation
            result = invitation_flow.cancel_invitation_to_available_client(phone, client_id)

            return result

        except Exception as e:
            log_error(f"Error cancelling invitation: {str(e)}")
            return {'success': False, 'response': 'Error cancelling invitation', 'handler': 'cancel_invitation_error'}

    def _handle_resend_invite(self, phone: str, button_id: str) -> Dict:
        """Trainer resending invitation (from 72h reminder)"""
        try:
            from services.scheduled.invitation_reminders import InvitationReminderService

            invitation_id = int(button_id.replace('resend_invite_', ''))

            # Verify trainer owns this invitation
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('trainer_id'):
                return {'success': False, 'response': 'Error: Trainer ID not found', 'handler': 'button_error'}

            # Get invitation and verify ownership
            invitation = self.db.table('client_invitations').select('trainer_id, client_name').eq(
                'id', invitation_id
            ).execute()

            if not invitation.data:
                return {'success': False, 'response': 'Invitation not found', 'handler': 'resend_invite_error'}

            # Initialize invitation reminder service
            invitation_reminder_service = InvitationReminderService(self.db, self.whatsapp)

            # Resend invitation
            result = invitation_reminder_service.resend_invitation(invitation_id)

            if result.get('success'):
                client_name = invitation.data[0].get('client_name', 'the client')
                msg = f"✅ Invitation resent to {client_name}!"
                return {'success': True, 'response': msg, 'handler': 'resend_invite'}
            else:
                return {'success': False, 'response': f"Failed to resend invitation: {result.get('error')}", 'handler': 'resend_invite_error'}

        except Exception as e:
            log_error(f"Error resending invitation: {str(e)}")
            return {'success': False, 'response': 'Error resending invitation', 'handler': 'resend_invite_error'}

    def _handle_cancel_invite(self, phone: str, button_id: str) -> Dict:
        """Trainer cancelling invitation (from 72h reminder)"""
        try:
            from services.scheduled.invitation_reminders import InvitationReminderService

            invitation_id = int(button_id.replace('cancel_invite_', ''))

            # Verify trainer owns this invitation
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('trainer_id'):
                return {'success': False, 'response': 'Error: Trainer ID not found', 'handler': 'button_error'}

            # Get invitation and verify ownership
            invitation = self.db.table('client_invitations').select('trainer_id, client_name').eq(
                'id', invitation_id
            ).execute()

            if not invitation.data:
                return {'success': False, 'response': 'Invitation not found', 'handler': 'cancel_invite_error'}

            # Initialize invitation reminder service
            invitation_reminder_service = InvitationReminderService(self.db, self.whatsapp)

            # Cancel invitation
            result = invitation_reminder_service.cancel_invitation(invitation_id)

            if result.get('success'):
                client_name = invitation.data[0].get('client_name', 'the client')
                msg = f"✅ Invitation to {client_name} has been cancelled."
                return {'success': True, 'response': msg, 'handler': 'cancel_invite'}
            else:
                return {'success': False, 'response': f"Failed to cancel invitation: {result.get('error')}", 'handler': 'cancel_invite_error'}

        except Exception as e:
            log_error(f"Error cancelling invitation: {str(e)}")
            return {'success': False, 'response': 'Error cancelling invitation', 'handler': 'cancel_invite_error'}

    def _handle_contact_client(self, phone: str, button_id: str) -> Dict:
        """Trainer requesting client contact info (from 72h reminder)"""
        try:
            invitation_id = int(button_id.replace('contact_client_', ''))

            # Get invitation details
            invitation = self.db.table('client_invitations').select(
                'client_name, client_phone, client_email'
            ).eq('id', invitation_id).execute()

            if not invitation.data:
                return {'success': False, 'response': 'Invitation not found', 'handler': 'contact_client_error'}

            client_data = invitation.data[0]
            client_name = client_data.get('client_name', 'the client')
            client_phone = client_data.get('client_phone')
            client_email = client_data.get('client_email')

            # Send contact info to trainer
            msg = f"📞 *Contact Information for {client_name}:*\n\n"

            if client_phone:
                msg += f"• Phone: {client_phone}\n"
            if client_email:
                msg += f"• Email: {client_email}\n"

            msg += f"\nYou can reach out to them directly to follow up on the invitation."

            result = self.whatsapp.send_message(phone, msg)

            if result.get('success'):
                return {'success': True, 'response': msg, 'handler': 'contact_client'}
            else:
                return {'success': False, 'response': 'Failed to send contact info', 'handler': 'contact_client_error'}

        except Exception as e:
            log_error(f"Error getting client contact info: {str(e)}")
            return {'success': False, 'response': 'Error getting contact information', 'handler': 'contact_client_error'}