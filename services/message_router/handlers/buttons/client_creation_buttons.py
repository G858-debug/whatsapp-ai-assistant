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
            client_insert_result = self.db.table('clients').insert(client_data).execute()

            # Get the UUID 'id' that was auto-generated
            if client_insert_result.data:
                client_uuid = client_insert_result.data[0]['id']

                # Create user entry using the UUID 'id', not the VARCHAR 'client_id'
                user_data = {
                    'phone_number': phone,
                    'client_id': str(client_uuid),  # Use the UUID 'id' from the insert result
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

    def _ensure_trainer_record_exists(self, phone: str, trainer_id: str):
        """
        Ensure a trainer record exists in the trainers table.
        If not, create one with basic information from the users table.

        Args:
            phone: Trainer's WhatsApp phone number
            trainer_id: Trainer's string ID (e.g., 'TR001')

        Returns:
            tuple: (trainer_uuid, error_message) - trainer_uuid is the UUID from trainers table,
                   error_message is None if successful, otherwise contains the error description
        """
        try:
            log_info(f"Ensuring trainer record exists for: {trainer_id}")

            # First, verify trainer exists in users table
            user_result = self.db.table('users').select('id, trainer_id').eq(
                'trainer_id', trainer_id
            ).execute()

            if not user_result.data:
                log_error(f"Trainer not found in users table: {trainer_id}")
                return None, "Trainer not found in users table"

            trainer_user_uuid = user_result.data[0]['id']
            log_info(f"Found trainer in users table with UUID: {trainer_user_uuid}")

            # Check if trainer has a corresponding trainers table entry
            trainer_result = self.db.table('trainers').select('id, trainer_id').eq(
                'trainer_id', trainer_id
            ).execute()

            if trainer_result.data:
                # Trainer already exists
                trainer_uuid = trainer_result.data[0]['id']
                log_info(f"Trainer already exists in trainers table with UUID: {trainer_uuid}")
                return trainer_uuid, None

            # Trainer doesn't exist in trainers table - create a record
            log_info(f"Trainer {trainer_id} not found in trainers table, creating basic record")

            try:
                from datetime import datetime
                import pytz
                sa_tz = pytz.timezone('Africa/Johannesburg')

                # Get any additional info from users table if available
                user_full_result = self.db.table('users').select('*').eq(
                    'trainer_id', trainer_id
                ).execute()

                user_data = user_full_result.data[0] if user_full_result.data else {}

                # Prepare trainer record with available data
                trainer_insert_data = {
                    'trainer_id': trainer_id,
                    'whatsapp': phone,
                    'created_at': datetime.now(sa_tz).isoformat(),
                    'updated_at': datetime.now(sa_tz).isoformat()
                }

                # Add optional fields if available from users table
                if user_data.get('name'):
                    trainer_insert_data['name'] = user_data['name']
                if user_data.get('email'):
                    trainer_insert_data['email'] = user_data['email']

                # Create the trainer record
                trainer_create_result = self.db.table('trainers').insert(trainer_insert_data).execute()

                if trainer_create_result.data:
                    trainer_uuid = trainer_create_result.data[0]['id']
                    log_info(f"Successfully created trainer record with UUID: {trainer_uuid}")
                    return trainer_uuid, None
                else:
                    log_error(f"Failed to create trainer record for {trainer_id} - no data returned")
                    return None, "Failed to create trainer record"

            except Exception as e:
                log_error(f"Error creating trainer record: {str(e)}")
                return None, f"Error creating trainer record: {str(e)}"

        except Exception as e:
            log_error(f"Error in _ensure_trainer_record_exists: {str(e)}")
            return None, f"Unexpected error: {str(e)}"

    def handle_add_client_button(self, phone: str, button_id: str) -> Dict:
        """
        Handle add client flow buttons (profile filling and secondary invitation)

        Buttons:
        - add_client_type: Launch WhatsApp Flow for trainer to type client details
        - add_client_share: Prompt trainer to share a contact
        - client_fills_profile: Send invitation for client to fill their own profile
        - trainer_fills_profile: Launch WhatsApp Flow for trainer to fill profile
        - send_secondary_invitation: Send invitation for multi-trainer scenario
        - cancel_add_client: Cancel the add client process
        """
        try:
            if not self.task_service:
                log_error("Task service not available")
                return {'success': False, 'response': 'Service unavailable', 'handler': 'add_client_no_task_service'}

            if button_id == 'add_client_type':
                return self._handle_add_client_type(phone)
            elif button_id == 'add_client_share':
                return self._handle_add_client_share(phone)
            elif button_id == 'client_fills_profile':
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

    def handle_pricing_button(self, phone: str, button_id: str) -> Dict:
        """
        Handle pricing buttons for client creation flow

        Buttons:
        - use_standard: Use trainer's default price per session
        - set_custom: Ask for custom price input
        - discuss_later: Skip pricing, to be discussed with client
        """
        try:
            if not self.task_service:
                log_error("Task service not available")
                return {'success': False, 'response': 'Service unavailable', 'handler': 'pricing_no_task_service'}

            if button_id == 'use_standard':
                return self._handle_use_standard_price(phone)
            elif button_id == 'set_custom':
                return self._handle_set_custom_price(phone)
            elif button_id == 'discuss_later':
                return self._handle_discuss_later(phone)
            else:
                return {'success': False, 'response': 'Unknown pricing button', 'handler': 'unknown_pricing_button'}

        except Exception as e:
            log_error(f"Error handling pricing button: {str(e)}")
            return {'success': False, 'response': 'Error processing button', 'handler': 'pricing_button_error'}

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

            # Handle both contact_data (from contact share) and basic_contact_data (from typed input)
            contact_data = task_data.get('contact_data')
            basic_contact_data = task_data.get('basic_contact_data')

            if contact_data:
                # From shared contact
                client_name = contact_data.get('name', 'Unknown')
                client_phone = contact_data.get('phone')
                # Extract email from emails array
                emails = contact_data.get('emails', [])
                client_email = emails[0] if emails else None
            elif basic_contact_data:
                # From typed input
                client_name = basic_contact_data.get('name', 'Unknown')
                client_phone = basic_contact_data.get('phone')
                client_email = basic_contact_data.get('email')
            else:
                msg = "❌ Missing contact information. Please try again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'client_fills_no_contact_data'}

            if not client_phone:
                msg = "❌ Missing phone number. Please share the contact again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'client_fills_no_phone'}

            # Get pricing from task data
            selected_price = task_data.get('selected_price')

            # If no price set yet, ask for it first
            if selected_price is None and not task_data.get('pricing_to_discuss'):
                # Ask for pricing before sending invitation
                return self._ask_pricing_for_client(phone, client_name, task_id, task_data, user_id)

            # Ensure trainer record exists in trainers table (create if needed)
            trainer_uuid, error_msg = self._ensure_trainer_record_exists(phone, user_id)

            if not trainer_uuid:
                log_error(f"Failed to ensure trainer record exists: {error_msg}")
                msg = "❌ Error setting up trainer profile. Please contact support."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'client_fills_trainer_record_error'}

            # Send invitation using template
            from services.relationships.invitations.invitation_service import InvitationService

            invitation_service = InvitationService(self.db, self.whatsapp)

            success, msg = invitation_service.send_client_fills_invitation(
                trainer_id=trainer_uuid,
                client_phone=client_phone,
                client_name=client_name,
                selected_price=selected_price
            )

            if success:
                # Build pricing text for notification
                if task_data.get('pricing_to_discuss'):
                    pricing_text = "To be discussed"
                elif selected_price:
                    pricing_text = f"R{selected_price} per session"
                else:
                    pricing_text = "Not specified"

                # Notify trainer
                trainer_msg = (
                    f"✅ *Invitation sent!*\n\n"
                    f"I've sent {client_name} a training invitation.\n\n"
                    f"💰 Rate: {pricing_text}\n\n"
                    f"They'll receive a message with options to accept or decline."
                )
                self.whatsapp.send_message(phone, trainer_msg)
                self.task_service.complete_task(task_id, role)

                log_info(f"Sent client-fills invitation from trainer {user_id} to {client_name} ({client_phone}) with price: {selected_price}")
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

    def _ask_pricing_for_client(self, phone: str, client_name: str, task_id: str, task_data: Dict, trainer_id: str) -> Dict:
        """
        Ask trainer for pricing before sending client invitation
        """
        try:
            # Get trainer's default price from database
            trainer_result = self.db.table('trainers').select('pricing_per_session').eq(
                'trainer_id', trainer_id
            ).execute()

            default_price = None
            if trainer_result.data and trainer_result.data[0].get('pricing_per_session'):
                default_price = trainer_result.data[0]['pricing_per_session']

            # Build pricing message
            if default_price:
                msg = (
                    f"💰 *Pricing setup*\n\n"
                    f"What rate would you like to set for {client_name}?\n\n"
                    f"Your standard rate: R{default_price} per session\n\n"
                    f"Choose an option below:"
                )
            else:
                msg = (
                    f"💰 *Pricing setup*\n\n"
                    f"What rate would you like to set for {client_name}?\n\n"
                    f"Choose an option below:"
                )

            # Create pricing buttons
            buttons = [
                {'id': 'use_standard', 'title': f'Use standard (R{default_price})' if default_price else 'Set standard rate'},
                {'id': 'set_custom', 'title': 'Set custom rate'},
                {'id': 'discuss_later', 'title': 'Discuss with client'}
            ]

            self.whatsapp.send_button_message(phone, msg, buttons)

            # Update task to track we're waiting for pricing choice
            task_data['profile_completion_by'] = 'client'
            task_data['trainer_default_price'] = default_price
            self.task_service.update_task(task_id, 'trainer', task_data=task_data)

            log_info(f"Asked trainer {trainer_id} for pricing for client {client_name}")
            return {'success': True, 'response': msg, 'handler': 'ask_pricing_for_client'}

        except Exception as e:
            log_error(f"Error asking pricing for client: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'ask_pricing_error'}

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

            # Handle both contact_data (from contact share) and basic_contact_data (from typed input)
            contact_data = task_data.get('contact_data')
            basic_contact_data = task_data.get('basic_contact_data')

            if contact_data:
                # From shared contact
                client_name = contact_data.get('name', 'Unknown')
                client_phone = contact_data.get('phone')
                # Extract email from emails array
                emails = contact_data.get('emails', [])
                client_email = emails[0] if emails and len(emails) > 0 else ''
            elif basic_contact_data:
                # From typed input
                client_name = basic_contact_data.get('name', 'Unknown')
                client_phone = basic_contact_data.get('phone')
                client_email = basic_contact_data.get('email') or ''
            else:
                msg = "❌ Missing contact information. Please try again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'trainer_fills_no_contact_data'}

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
                # Update task to track that flow was sent (preserve original data source)
                updated_task_data = {
                    'step': 'flow_sent',
                    'trainer_id': user_id,
                    'flow_token': flow_result.get('flow_token')
                }
                if contact_data:
                    updated_task_data['contact_data'] = contact_data
                if basic_contact_data:
                    updated_task_data['basic_contact_data'] = basic_contact_data

                self.task_service.update_task(
                    task_id,
                    role,
                    task_data=updated_task_data
                )

                # Note: The flow will be pre-filled with name and phone in the flow handler
                # The task will be completed when the flow response is received

                log_info(f"Launched trainer add client flow for {user_id} to add {client_name} ({client_phone})")
                return {'success': True, 'response': 'Flow launched successfully', 'handler': 'trainer_fills_flow_launched'}
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

    def _handle_add_client_type(self, phone: str) -> Dict:
        """
        Handle 'Type details' button (add_client_type)
        Start text-based collection for client details
        """
        try:
            # Get trainer info
            role = 'trainer'
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'add_client_type_no_user'}

            # Get running task
            task = self.task_service.get_running_task(phone, role)

            if not task or task.get('task_type') != 'add_client_choice':
                msg = "❌ No add client task in progress. Please use /add-client to start."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'add_client_type_no_task'}

            task_id = task.get('id')

            # Update task to track we're collecting basic contact info
            task_data = {
                'step': 'collecting_name',
                'trainer_id': user_id,
                'basic_contact_data': {}
            }

            self.task_service.update_task(
                task_id,
                role,
                task_data=task_data
            )

            # Send message asking for client's name
            msg = (
                "Great! Let's get started. ✍️\n\n"
                "What is your client's full name?"
            )
            self.whatsapp.send_message(phone, msg)

            log_info(f"Started text-based client collection for trainer {user_id}")
            return {'success': True, 'response': msg, 'handler': 'add_client_type_name_requested'}

        except Exception as e:
            log_error(f"Error handling add client type: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'add_client_type_error'}

    def _handle_add_client_share(self, phone: str) -> Dict:
        """
        Handle 'Share contact' button (add_client_share)
        Prompt trainer to share a contact card
        """
        try:
            # Get trainer info
            role = 'trainer'
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'add_client_share_no_user'}

            # Get running task
            task = self.task_service.get_running_task(phone, role)

            if not task or task.get('task_type') != 'add_client_choice':
                msg = "❌ No add client task in progress. Please use /add-client to start."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'add_client_share_no_task'}

            task_id = task.get('id')
            task_data = task.get('task_data', {})

            # Update task to wait for contact share
            self.task_service.update_task(
                task_id,
                role,
                task_data={
                    'step': 'waiting_for_contact',
                    'trainer_id': user_id,
                    'pre_collected_data': task_data.get('pre_collected_data', {})
                }
            )

            # Send detailed instructions immediately
            msg = (
                "📱 *How to share a contact*\n\n"
                "Here's how to share your client's contact with me:\n\n"
                "1️⃣ Tap the 📎 or ➕ icon in WhatsApp\n"
                "2️⃣ Select 'Contact'\n"
                "3️⃣ Choose your client from your phone contacts\n"
                "4️⃣ Send the contact to me\n\n"
                "Once I receive their contact card, I'll extract their details and help you create their profile!"
            )

            self.whatsapp.send_message(phone, msg)

            log_info(f"Prompted trainer {user_id} to share contact for add client flow")
            return {'success': True, 'response': msg, 'handler': 'add_client_share_prompted'}

        except Exception as e:
            log_error(f"Error handling add client share: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'add_client_share_error'}

    def _handle_use_standard_price(self, phone: str) -> Dict:
        """
        Handle 'Use Standard Rate' button
        Get trainer's default_price_per_session and proceed with invitation
        """
        try:
            # Get trainer info
            role = 'trainer'
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'use_standard_no_user'}

            # Get running task
            task = self.task_service.get_running_task(phone, role)

            if not task:
                msg = "❌ No client creation task in progress."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'use_standard_no_task'}

            task_id = task.get('id')
            task_data = task.get('task_data', {})

            # Get trainer's default price from database
            trainer_result = self.db.table('trainers').select('pricing_per_session').eq(
                'trainer_id', user_id
            ).execute()

            if not trainer_result.data:
                msg = "❌ Trainer not found in database."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'use_standard_trainer_not_found'}

            default_price = trainer_result.data[0].get('pricing_per_session')

            if not default_price:
                # No standard rate set, ask them to type their standard rate
                msg = (
                    "ℹ️ You don't have a standard rate set yet.\n\n"
                    "Please type your standard rate per session:\n"
                    "(Example: 450 for R450)"
                )
                self.whatsapp.send_message(phone, msg)

                # Update task to wait for custom price input
                task_data['new_client_step'] = 'await_custom_price'
                self.task_service.update_task(task_id, role, task_data=task_data)

                return {'success': True, 'response': msg, 'handler': 'use_standard_no_default_set'}

            # Store the standard price in task_data
            task_data['selected_price'] = default_price
            self.task_service.update_task(task_id, role, task_data=task_data)

            # Proceed to send invitation with pricing info
            return self._send_client_fills_invitation(phone, user_id, task, task_data)

        except Exception as e:
            log_error(f"Error handling use standard price: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'use_standard_error'}

    def _handle_set_custom_price(self, phone: str) -> Dict:
        """
        Handle 'Set Custom Rate' button
        Ask trainer to input custom price for this client
        """
        try:
            # Get trainer info
            role = 'trainer'
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'set_custom_no_user'}

            # Get running task
            task = self.task_service.get_running_task(phone, role)

            if not task:
                msg = "❌ No client creation task in progress."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'set_custom_no_task'}

            task_id = task.get('id')
            task_data = task.get('task_data', {})

            # Get client name from task data
            contact_data = task_data.get('contact_data')
            basic_contact_data = task_data.get('basic_contact_data')
            client_data = task_data.get('client_data', {})

            if contact_data:
                client_name = contact_data.get('name', 'this client')
            elif basic_contact_data:
                client_name = basic_contact_data.get('name', 'this client')
            elif client_data:
                client_name = client_data.get('name', 'this client')
            else:
                client_name = 'this client'

            # Send message asking for custom price
            msg = (
                f"💵 *Custom rate*\n\n"
                f"Enter the price per session for {client_name}:\n"
                f"(Example: 450 for R450)"
            )
            self.whatsapp.send_message(phone, msg)

            # Update task to wait for custom price input
            task_data['step'] = 'awaiting_custom_price'
            self.task_service.update_task(task_id, role, task_data=task_data)

            log_info(f"Trainer {user_id} setting custom price for client {client_name}")
            return {'success': True, 'response': msg, 'handler': 'set_custom_price_requested'}

        except Exception as e:
            log_error(f"Error handling set custom price: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'set_custom_error'}

    def _handle_discuss_later(self, phone: str) -> Dict:
        """
        Handle 'Discuss with Client' button
        Skip pricing for now and send invitation
        """
        try:
            # Get trainer info
            role = 'trainer'
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'discuss_later_no_user'}

            # Get running task
            task = self.task_service.get_running_task(phone, role)

            if not task:
                msg = "❌ No client creation task in progress."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'discuss_later_no_task'}

            task_id = task.get('id')
            task_data = task.get('task_data', {})

            # Set price to None and mark for discussion
            task_data['selected_price'] = None
            task_data['pricing_to_discuss'] = True
            self.task_service.update_task(task_id, role, task_data=task_data)

            # Proceed to send invitation without specific pricing
            return self._send_client_fills_invitation(phone, user_id, task, task_data)

        except Exception as e:
            log_error(f"Error handling discuss later: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'discuss_later_error'}

    def _send_client_fills_invitation(self, phone: str, trainer_id: str, task: Dict, task_data: Dict) -> Dict:
        """
        Send invitation to client after pricing has been set for client_fills flow

        Args:
            phone: Trainer's WhatsApp number
            trainer_id: Trainer's ID (string ID like 'TR001')
            task: Current task data
            task_data: Task data dictionary

        Returns:
            Dict with success status and response details
        """
        try:
            # Get client data from task_data
            contact_data = task_data.get('contact_data')
            basic_contact_data = task_data.get('basic_contact_data')

            if contact_data:
                # From shared contact
                client_name = contact_data.get('name', 'Unknown')
                client_phone = contact_data.get('phone')
            elif basic_contact_data:
                # From typed input
                client_name = basic_contact_data.get('name', 'Unknown')
                client_phone = basic_contact_data.get('phone')
            else:
                msg = "❌ Missing contact information. Please try again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task.get('id'), 'trainer')
                return {'success': False, 'response': msg, 'handler': 'send_invitation_no_contact_data'}

            if not client_phone:
                msg = "❌ Missing phone number. Please share the contact again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task.get('id'), 'trainer')
                return {'success': False, 'response': msg, 'handler': 'send_invitation_no_phone'}

            # Get pricing from task data
            selected_price = task_data.get('selected_price')
            pricing_to_discuss = task_data.get('pricing_to_discuss', False)

            # Ensure trainer record exists in trainers table (create if needed)
            trainer_uuid, error_msg = self._ensure_trainer_record_exists(phone, trainer_id)

            if not trainer_uuid:
                log_error(f"Failed to ensure trainer record exists: {error_msg}")
                msg = "❌ Error setting up trainer profile. Please contact support."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task.get('id'), 'trainer')
                return {'success': False, 'response': msg, 'handler': 'send_invitation_trainer_record_error'}

            # Send invitation using InvitationService
            from services.relationships.invitations.invitation_service import InvitationService

            invitation_service = InvitationService(self.db, self.whatsapp)

            success, error_msg = invitation_service.send_client_fills_invitation(
                trainer_id=trainer_uuid,
                client_phone=client_phone,
                client_name=client_name,
                selected_price=selected_price
            )

            if success:
                # Build success message
                if pricing_to_discuss:
                    pricing_text = "To be discussed"
                elif selected_price:
                    pricing_text = f"R{selected_price} per session"
                else:
                    pricing_text = "Not specified"

                msg = (
                    f"✅ *Invitation sent!*\n\n"
                    f"I've sent {client_name} a training invitation.\n\n"
                    f"💰 Rate: {pricing_text}\n\n"
                    f"They'll receive a message with options to accept or decline."
                )
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task.get('id'), 'trainer')

                log_info(f"Sent client-fills invitation from trainer {trainer_id} to {client_name} ({client_phone}) with price: {selected_price}")
                return {'success': True, 'response': msg, 'handler': 'send_invitation_success'}
            else:
                error_msg_text = f"❌ Failed to send invitation: {error_msg}"
                self.whatsapp.send_message(phone, error_msg_text)
                self.task_service.complete_task(task.get('id'), 'trainer')
                return {'success': False, 'response': error_msg_text, 'handler': 'send_invitation_failed'}

        except Exception as e:
            log_error(f"Error sending client fills invitation: {str(e)}")
            msg = "❌ Sorry, I encountered an error sending the invitation. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'send_invitation_error'}
