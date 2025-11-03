"""
Client Creation Button Handler
Handles new client account creation approval/rejection buttons
"""
from typing import Dict
from utils.logger import log_error


class ClientCreationButtonHandler:
    """Handles new client account creation buttons"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
    
    def handle_client_creation_button(self, phone: str, button_id: str) -> Dict:
        """Handle client creation buttons"""
        try:
            if button_id.startswith('approve_new_client_'):
                return self._handle_approve_new_client(phone, button_id)
            elif button_id.startswith('reject_new_client_'):
                return self._handle_reject_new_client(phone, button_id)
            else:
                return {'success': False, 'response': 'Unknown client creation button', 'handler': 'unknown_client_creation_button'}
                
        except Exception as e:
            log_error(f"Error handling client creation button: {str(e)}")
            return {'success': False, 'response': 'Error processing client creation button', 'handler': 'client_creation_button_error'}
    
    def _handle_approve_new_client(self, phone: str, button_id: str) -> Dict:
        """New client approving account creation"""
        try:
            trainer_string_id = button_id.replace('approve_new_client_', '')
            
            # Get trainer UUID from string ID
            trainer_result = self.db.table('trainers').select('id, trainer_id').eq(
                'trainer_id', trainer_string_id
            ).execute()
            
            if not trainer_result.data:
                msg = "❌ Trainer not found. Please ask your trainer to send a new invitation."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'approve_new_client_trainer_not_found'}
            
            trainer_uuid = trainer_result.data[0]['id']
            
            # Check if there's a pending invitation for this phone and trainer
            invitation_result = self.db.table('client_invitations').select('*').eq(
                'client_phone', phone
            ).eq('trainer_id', trainer_uuid).eq('status', 'pending').execute()
            
            if not invitation_result.data:
                msg = "❌ Invitation not found or expired. Please ask your trainer to send a new invitation."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'approve_new_client_no_invitation'}
            
            invitation = invitation_result.data[0]
            
            # Get complete client data from prefilled_data JSONB column
            prefilled_data = invitation.get('prefilled_data', {})
            
            # Fallback to individual fields if prefilled_data is empty (for backward compatibility)
            if not prefilled_data:
                prefilled_data = {
                    'name': invitation.get('client_name'),
                    'email': invitation.get('client_email'),
                }
            
            client_data = prefilled_data
            
            # Create the client account
            client_id = self._create_client_account(phone, trainer_string_id, client_data, invitation['id'])
            
            if client_id:
                # Send success notifications
                return self._send_approval_notifications(phone, trainer_string_id, client_id, prefilled_data)
            else:
                msg = "❌ Error creating account. Please try again or contact your trainer."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'approve_new_client_error'}
            
        except Exception as e:
            log_error(f"Error creating new client account: {str(e)}")
            msg = "❌ Error creating account. Please try again or contact your trainer."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'approve_new_client_error'}
    
    def _handle_reject_new_client(self, phone: str, button_id: str) -> Dict:
        """New client rejecting account creation"""
        try:
            trainer_string_id = button_id.replace('reject_new_client_', '')
            
            # Get trainer UUID from string ID
            trainer_result = self.db.table('trainers').select('id, trainer_id').eq(
                'trainer_id', trainer_string_id
            ).execute()
            
            if not trainer_result.data:
                msg = "❌ Trainer not found."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'reject_new_client_trainer_not_found'}
            
            trainer_uuid = trainer_result.data[0]['id']
            
            # Update invitation status to declined
            from datetime import datetime
            import pytz
            sa_tz = pytz.timezone('Africa/Johannesburg')
            
            self.db.table('client_invitations').update({
                'status': 'declined',
                'updated_at': datetime.now(sa_tz).isoformat()
            }).eq('trainer_id', trainer_uuid).eq('client_phone', phone).eq('status', 'pending').execute()
            
            # Get trainer info and notify
            trainer_info_result = self.db.table('trainers').select('name, first_name, last_name, whatsapp').eq(
                'trainer_id', trainer_string_id
            ).execute()
            
            if trainer_info_result.data:
                trainer = trainer_info_result.data[0]
                trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'the trainer'
                
                # Notify user
                msg = f"You declined the invitation from {trainer_name}."
                self.whatsapp.send_message(phone, msg)
                
                # Notify trainer
                trainer_msg = f"ℹ️ The invitation you sent was declined."
                self.whatsapp.send_message(trainer['whatsapp'], trainer_msg)
                
                log_info(f"Client {phone} declined invitation from trainer {trainer_string_id}")
                return {'success': True, 'response': msg, 'handler': 'reject_new_client'}
            
            return {'success': False, 'response': 'Error processing rejection', 'handler': 'reject_new_client_error'}
            
        except Exception as e:
            log_error(f"Error rejecting new client: {str(e)}")
            return {'success': False, 'response': 'Error processing rejection', 'handler': 'reject_new_client_error'}
    
    def _create_client_account(self, phone: str, trainer_id: str, prefilled_data: dict, invitation_id: str) -> str:
        """Create a new client account with prefilled data"""
        try:
            # Generate client_id
            from services.auth.authentication_service import AuthenticationService
            auth_service = AuthenticationService(self.db)
            client_name = prefilled_data.get('name') or prefilled_data.get('full_name') or 'Client'
            client_id = auth_service.generate_unique_id(client_name, 'client')
            
            # Create client account
            from datetime import datetime
            import pytz
            sa_tz = pytz.timezone('Africa/Johannesburg')
            
            # Map the prefilled data to database fields with proper fallbacks
            client_name = (prefilled_data.get('name') or 
                          prefilled_data.get('full_name') or 
                          'New Client')  # Ensure name is never null
            
            client_data = {
                'client_id': client_id,
                'whatsapp': phone,
                'name': client_name,
                'email': prefilled_data.get('email') if prefilled_data.get('email') and prefilled_data.get('email').lower() not in ['skip', 'none'] else None,
                'fitness_goals': prefilled_data.get('fitness_goals') or 'To be determined',
                'experience_level': prefilled_data.get('experience_level') or 'Beginner',
                'health_conditions': prefilled_data.get('health_conditions') if prefilled_data.get('health_conditions') and prefilled_data.get('health_conditions').lower() not in ['skip', 'none'] else None,
                'availability': prefilled_data.get('availability') or 'Flexible',
                'preferred_training_times': prefilled_data.get('preferred_training_type') or 'To be discussed',
                'status': 'active',
                'created_at': datetime.now(sa_tz).isoformat(),
                'updated_at': datetime.now(sa_tz).isoformat()
            }
            
            # Insert into clients table
            self.db.table('clients').insert(client_data).execute()
            
            # Create user entry
            user_data = {
                'phone_number': phone,
                'client_id': client_id,
                'login_status': 'client',
                'created_at': datetime.now(sa_tz).isoformat()
            }
            self.db.table('users').insert(user_data).execute()
            
            # Create relationship and immediately approve it (since client accepted invitation)
            from services.relationships.invitations.invitation_manager import InvitationManager
            from services.relationships.core.relationship_manager import RelationshipManager
            
            invitation_manager = InvitationManager(self.db, self.whatsapp)
            relationship_manager = RelationshipManager(self.db)
            
            # Step 1: Create pending relationship
            success, error_msg = invitation_manager.create_relationship(trainer_id, client_id, 'trainer')
            
            if success:
                # Step 2: Immediately approve the relationship (since client accepted)
                approve_success, approve_error = relationship_manager.approve_relationship(trainer_id, client_id)
                if not approve_success:
                    log_error(f"Failed to approve relationship: {approve_error}")
            else:
                log_error(f"Failed to create relationship: {error_msg}")
                # Continue anyway - client account is created, relationship can be fixed later
            
            # Update invitation status
            self.db.table('client_invitations').update({
                'status': 'accepted',
                'accepted_at': datetime.now(sa_tz).isoformat(),  # Track when accepted
                'updated_at': datetime.now(sa_tz).isoformat()
            }).eq('id', invitation_id).execute()
            
            return client_id
            
        except Exception as e:
            log_error(f"Error creating client account: {str(e)}")
            return None
    
    def _send_approval_notifications(self, phone: str, trainer_id: str, client_id: str, prefilled_data: dict) -> Dict:
        """Send notifications after successful client account creation"""
        try:
            # Get client name from prefilled data
            client_name = prefilled_data.get('name') or prefilled_data.get('full_name') or 'there'
            
            # Notify new client
            msg = (
                f"✅ *Account Created Successfully!*\n\n"
                f"Welcome to Refiloe, {client_name}!\n\n"
                f"*Your Client ID:* {client_id}\n\n"
                f"You're now connected with your trainer.\n"
                f"Type /help to see what you can do!"
            )
            self.whatsapp.send_message(phone, msg)
            
            # Notify trainer
            trainer_result = self.db.table('trainers').select('name, first_name, last_name, whatsapp').eq(
                'trainer_id', trainer_id
            ).execute()
            
            if trainer_result.data:
                trainer = trainer_result.data[0]
                trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'the trainer'
                trainer_msg = (
                    f"✅ *New Client Added!*\n\n"
                    f"{client_name} approved your invitation!\n\n"
                    f"*Client ID:* {client_id}\n\n"
                    f"They're now in your client list."
                )
                self.whatsapp.send_message(trainer['whatsapp'], trainer_msg)
            
            return {'success': True, 'response': msg, 'handler': 'approve_new_client_success'}
            
        except Exception as e:
            log_error(f"Error sending approval notifications: {str(e)}")
            return {'success': False, 'response': 'Account created but error sending notifications', 'handler': 'approval_notification_error'}