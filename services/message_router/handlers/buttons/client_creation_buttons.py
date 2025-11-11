"""
Client Creation Button Handler
Handles new client account creation approval/rejection buttons
"""
from typing import Dict
from utils.logger import log_error, log_info


class ClientCreationButtonHandler:
    """Handles new client account creation buttons"""

    def __init__(self, supabase_client, whatsapp_service, auth_service, task_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.task_service = task_service
    
    def handle_client_creation_button(self, phone: str, button_id: str) -> Dict:
        """Handle client creation buttons"""
        try:
            if button_id.startswith('approve_new_client_'):
                return self._handle_approve_new_client(phone, button_id)
            elif button_id.startswith('reject_new_client_'):
                return self._handle_reject_new_client(phone, button_id)
            elif button_id == 'share_contact_instructions':
                return self._handle_share_contact_instructions(phone)
            else:
                return {'success': False, 'response': 'Unknown client creation button', 'handler': 'unknown_client_creation_button'}

        except Exception as e:
            log_error(f"Error handling client creation button: {str(e)}")
            return {'success': False, 'response': 'Error processing client creation button', 'handler': 'client_creation_button_error'}

    def handle_invitation_button(self, phone: str, button_id: str) -> Dict:
        """Handle client invitation buttons (Scenario 1A)"""
        try:
            if button_id.startswith('accept_invitation_'):
                return self._handle_accept_invitation(phone, button_id)
            elif button_id.startswith('decline_invitation_'):
                return self._handle_decline_invitation(phone, button_id)
            else:
                return {'success': False, 'response': 'Unknown invitation button', 'handler': 'unknown_invitation_button'}

        except Exception as e:
            log_error(f"Error handling invitation button: {str(e)}")
            return {'success': False, 'response': 'Error processing invitation button', 'handler': 'invitation_button_error'}
    
    def _handle_approve_new_client(self, phone: str, button_id: str) -> Dict:
        """New client approving account creation"""
        try:
            trainer_string_id = button_id.replace('approve_new_client_', '')
            
            # Get trainer UUID from string ID (case-insensitive)
            trainer_result = self.db.table('trainers').select('id, trainer_id').ilike(
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
            
            # Get trainer UUID from string ID (case-insensitive)
            trainer_result = self.db.table('trainers').select('id, trainer_id').ilike(
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

    def _handle_share_contact_instructions(self, phone: str) -> Dict:
        """Handle share contact instructions button"""
        try:
            msg = (
                "📱 *How to Share a Contact*\n\n"
                "Here's how to share your client's contact with me:\n\n"
                "1️⃣ Tap the 📎 or ➕ icon in WhatsApp\n"
                "2️⃣ Select 'Contact' \n"
                "3️⃣ Choose your client from your phone contacts\n"
                "4️⃣ Send the contact to me\n\n"
                "Once I receive their contact card, I'll extract their details and help you create their profile!"
            )
            self.whatsapp.send_message(phone, msg)

            log_info(f"Sent contact sharing instructions to {phone}")
            return {
                'success': True,
                'response': msg,
                'handler': 'share_contact_instructions'
            }

        except Exception as e:
            log_error(f"Error sending contact sharing instructions: {str(e)}")
            return {
                'success': False,
                'response': 'Error sending instructions',
                'handler': 'share_contact_instructions_error'
            }

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
            
            relationship_manager = RelationshipManager(self.db)
            invitation_manager = InvitationManager(self.db, self.whatsapp, relationship_manager)
            
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
            trainer_result = self.db.table('trainers').select('name, first_name, last_name, whatsapp').ilike(
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

    def _handle_accept_invitation(self, phone: str, button_id: str) -> Dict:
        """Handle client accepting invitation via button (Scenario 1A fallback)"""
        try:
            # Extract trainer_id from button_id
            trainer_string_id = button_id.replace('accept_invitation_', '')

            # Send message asking client to complete profile via text
            msg = (
                f"✅ *Great! Let's complete your profile.*\n\n"
                f"Please answer these questions to set up your fitness journey:\n\n"
                f"*1. What are your fitness goals?*\n"
                f"(e.g., lose weight, build muscle, improve fitness)"
            )
            self.whatsapp.send_message(phone, msg)

            # Store state for text-based profile completion
            # This could be implemented with a task or conversation state
            # For now, just send the message
            log_info(f"Client {phone} accepted invitation from trainer {trainer_string_id}")
            return {'success': True, 'response': msg, 'handler': 'accept_invitation_text_flow'}

        except Exception as e:
            log_error(f"Error handling accept invitation: {str(e)}")
            return {'success': False, 'response': 'Error accepting invitation', 'handler': 'accept_invitation_error'}

    def _handle_decline_invitation(self, phone: str, button_id: str) -> Dict:
        """Handle client declining invitation (Scenario 1A)"""
        try:
            from datetime import datetime
            import pytz

            sa_tz = pytz.timezone('Africa/Johannesburg')

            # Extract trainer_id from button_id
            trainer_string_id = button_id.replace('decline_invitation_', '')

            # Get trainer UUID from string ID
            trainer_result = self.db.table('trainers').select('id, trainer_id, name, first_name, last_name, whatsapp').ilike(
                'trainer_id', trainer_string_id
            ).execute()

            if not trainer_result.data:
                msg = "❌ Trainer not found."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'decline_invitation_trainer_not_found'}

            trainer = trainer_result.data[0]
            trainer_uuid = trainer['id']
            trainer_whatsapp = trainer['whatsapp']
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()

            # Update invitation status to declined
            update_result = self.db.table('client_invitations').update({
                'status': 'declined',
                'declined_at': datetime.now(sa_tz).isoformat(),
                'updated_at': datetime.now(sa_tz).isoformat()
            }).eq('trainer_id', trainer_uuid).eq('client_phone', phone).eq('status', 'pending_client_completion').execute()

            if update_result.data:
                # Notify client
                msg = f"You declined the training invitation from {trainer_name}."
                self.whatsapp.send_message(phone, msg)

                # Notify trainer
                trainer_msg = (
                    f"ℹ️ *Invitation Declined*\n\n"
                    f"The client declined your training invitation."
                )
                self.whatsapp.send_message(trainer_whatsapp, trainer_msg)

                log_info(f"Client {phone} declined invitation from trainer {trainer_string_id}")
                return {'success': True, 'response': msg, 'handler': 'decline_invitation_success'}
            else:
                msg = "❌ Invitation not found or already processed."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'decline_invitation_not_found'}

        except Exception as e:
            log_error(f"Error handling decline invitation: {str(e)}")
            return {'success': False, 'response': 'Error declining invitation', 'handler': 'decline_invitation_error'}

    def handle_add_client_button(self, phone: str, button_id: str) -> Dict:
        """
        Handle add client flow buttons (profile filling and secondary invitation)

        Buttons:
        - client_fills_profile: Send invitation for client to fill their own profile
        - trainer_fills_profile: Launch WhatsApp Flow for trainer to fill profile
        - send_secondary_invitation: Send invitation for multi-trainer scenario
        - cancel_add_client: Cancel the add client process
        """
        try:
            if not self.task_service:
                log_error("Task service not available")
                return {'success': False, 'response': 'Service unavailable', 'handler': 'add_client_no_task_service'}

            if button_id == 'client_fills_profile':
                return self._handle_client_fills_profile(phone)
            elif button_id == 'trainer_fills_profile':
                return self._handle_trainer_fills_profile(phone)
            elif button_id == 'send_secondary_invitation':
                return self._handle_send_secondary_invitation(phone)
            elif button_id == 'cancel_add_client':
                return self._handle_cancel_add_client(phone)
            else:
                return {'success': False, 'response': 'Unknown add client button', 'handler': 'unknown_add_client_button'}

        except Exception as e:
            log_error(f"Error handling add client button: {str(e)}")
            return {'success': False, 'response': 'Error processing button', 'handler': 'add_client_button_error'}

    def _handle_client_fills_profile(self, phone: str) -> Dict:
        """
        Handle 'Client Fills Profile' button
        Send invitation for client to fill their own profile (Scenario 1A)
        """
        try:
            # Get trainer info
            role = 'trainer'
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'client_fills_no_user'}

            # Get running task
            task = self.task_service.get_running_task(phone, role)

            if not task or task.get('task_type') != 'add_client_profile_choice':
                msg = "❌ No client profile task in progress. Please share a contact first."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'client_fills_no_task'}

            task_id = task.get('id')
            task_data = task.get('task_data', {})
            contact_data = task_data.get('contact_data', {})

            client_name = contact_data.get('name', 'Unknown')
            client_phone = contact_data.get('phone')

            if not client_phone:
                msg = "❌ Missing phone number. Please share the contact again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'client_fills_no_phone'}

            # Get trainer UUID (we have trainer_id string, need UUID)
            trainer_result = self.db.table('trainers').select('id').eq(
                'trainer_id', user_id
            ).execute()

            if not trainer_result.data:
                msg = "❌ Trainer not found."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'client_fills_trainer_not_found'}

            trainer_uuid = trainer_result.data[0]['id']

            # Send invitation to client using InvitationService
            from services.relationships.invitations.invitation_service import InvitationService

            invitation_service = InvitationService(self.db, self.whatsapp)

            # Prepare minimal client data for invitation
            client_data = {
                'name': client_name,
                'phone': client_phone
            }

            # Send invitation with type 'pending_client_completion' (client needs to fill profile)
            success, msg = invitation_service.send_new_client_invitation(
                trainer_id=trainer_uuid,
                client_data=client_data,
                client_phone=client_phone
            )

            if success:
                # Notify trainer
                trainer_msg = (
                    f"✅ *Invitation Sent!*\n\n"
                    f"I've sent {client_name} an invitation to fill out their fitness profile.\n\n"
                    f"They'll receive a message with buttons to accept or decline."
                )
                self.whatsapp.send_message(phone, trainer_msg)

                # Complete the task
                self.task_service.complete_task(task_id, role)

                log_info(f"Sent client-fills invitation from trainer {user_id} to {client_name} ({client_phone})")
                return {'success': True, 'response': trainer_msg, 'handler': 'client_fills_success'}
            else:
                error_msg = f"❌ Failed to send invitation: {msg}"
                self.whatsapp.send_message(phone, error_msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': error_msg, 'handler': 'client_fills_invitation_failed'}

        except Exception as e:
            log_error(f"Error handling client fills profile: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'client_fills_error'}

    def _handle_trainer_fills_profile(self, phone: str) -> Dict:
        """
        Handle 'Trainer Fills Profile' button
        Launch WhatsApp Flow for trainer to fill the client's profile (Scenario 1B)
        """
        try:
            # Get trainer info
            role = 'trainer'
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'trainer_fills_no_user'}

            # Get running task
            task = self.task_service.get_running_task(phone, role)

            if not task or task.get('task_type') != 'add_client_profile_choice':
                msg = "❌ No client profile task in progress. Please share a contact first."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'trainer_fills_no_task'}

            task_id = task.get('id')
            task_data = task.get('task_data', {})
            contact_data = task_data.get('contact_data', {})

            client_name = contact_data.get('name', 'Unknown')
            client_phone = contact_data.get('phone')

            # Extract email from contact_data if available
            client_email = ''
            if contact_data.get('emails'):
                emails = contact_data.get('emails', [])
                if emails and len(emails) > 0:
                    client_email = emails[0]

            if not client_phone:
                msg = "❌ Missing phone number. Please share the contact again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'trainer_fills_no_phone'}

            # Launch WhatsApp Flow for trainer to add client
            from services.whatsapp_flow_handler import WhatsAppFlowHandler

            flow_handler = WhatsAppFlowHandler(self.db, self.whatsapp)

            # Pre-fill the flow with contact data
            flow_result = flow_handler.send_trainer_add_client_flow(
                trainer_phone=phone,
                trainer_id=user_id,
                client_name=client_name,
                client_phone=client_phone,
                client_email=client_email
            )

            if flow_result.get('success'):
                # Update task to track that flow was sent
                self.task_service.update_task(
                    task_id,
                    role,
                    task_data={
                        'step': 'flow_sent',
                        'trainer_id': user_id,
                        'contact_data': contact_data,
                        'flow_token': flow_result.get('flow_token')
                    }
                )

                # Note: The flow will be pre-filled with name and phone in the flow handler
                # The task will be completed when the flow response is received

                msg = f"✏️ Please fill in {client_name}'s fitness profile in the form I just sent you."
                self.whatsapp.send_message(phone, msg)

                log_info(f"Launched trainer add client flow for {user_id} to add {client_name} ({client_phone})")
                return {'success': True, 'response': msg, 'handler': 'trainer_fills_flow_launched'}
            else:
                error_msg = f"❌ Failed to launch form: {flow_result.get('error', 'Unknown error')}"
                self.whatsapp.send_message(phone, error_msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': error_msg, 'handler': 'trainer_fills_flow_failed'}

        except Exception as e:
            log_error(f"Error handling trainer fills profile: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'trainer_fills_error'}

    def _handle_send_secondary_invitation(self, phone: str) -> Dict:
        """
        Handle 'Send Secondary Invitation' button
        Send invitation for multi-trainer scenario (Scenario 3)
        """
        try:
            # Get trainer info
            role = 'trainer'
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'secondary_inv_no_user'}

            # Get running task
            task = self.task_service.get_running_task(phone, role)

            if not task or task.get('task_type') != 'secondary_trainer_invitation':
                msg = "❌ No secondary invitation task in progress."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'secondary_inv_no_task'}

            task_id = task.get('id')
            task_data = task.get('task_data', {})
            contact_data = task_data.get('contact_data', {})
            client_id = task_data.get('client_id')

            client_name = contact_data.get('name', 'Unknown')
            client_phone = contact_data.get('phone')

            if not client_id or not client_phone:
                msg = "❌ Missing client information. Please try again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'secondary_inv_missing_data'}

            # Send invitation using InvitationService
            from services.relationships.invitations.invitation_service import InvitationService

            invitation_service = InvitationService(self.db, self.whatsapp)

            # Send trainer-to-client invitation (client already exists)
            success, msg = invitation_service.send_trainer_to_client_invitation(
                trainer_id=user_id,
                client_id=client_id,
                client_phone=client_phone
            )

            if success:
                trainer_msg = (
                    f"✅ *Invitation Sent!*\n\n"
                    f"I've sent {client_name} an invitation to train with you as well.\n\n"
                    f"They'll be able to accept or decline your invitation."
                )
                self.whatsapp.send_message(phone, trainer_msg)

                # Complete the task
                self.task_service.complete_task(task_id, role)

                log_info(f"Sent secondary trainer invitation from {user_id} to {client_name} ({client_id})")
                return {'success': True, 'response': trainer_msg, 'handler': 'secondary_inv_success'}
            else:
                error_msg = f"❌ Failed to send invitation: {msg}"
                self.whatsapp.send_message(phone, error_msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': error_msg, 'handler': 'secondary_inv_failed'}

        except Exception as e:
            log_error(f"Error handling secondary invitation: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'secondary_inv_error'}

    def _handle_cancel_add_client(self, phone: str) -> Dict:
        """
        Handle 'Cancel Add Client' button
        Simply complete the task and send confirmation
        """
        try:
            # Get trainer info
            role = 'trainer'
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'cancel_add_client_no_user'}

            # Get running task (could be either type)
            task = self.task_service.get_running_task(phone, role)

            if task:
                task_id = task.get('id')
                task_type = task.get('task_type')

                # Complete the task
                self.task_service.complete_task(task_id, role)

                log_info(f"Cancelled {task_type} for trainer {user_id}")

            # Send confirmation
            msg = "✅ Add client process cancelled. You can try again anytime!"
            self.whatsapp.send_message(phone, msg)

            return {'success': True, 'response': msg, 'handler': 'cancel_add_client_success'}

        except Exception as e:
            log_error(f"Error handling cancel add client: {str(e)}")
            msg = "✅ Process cancelled."
            self.whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'cancel_add_client_error'}
