"""
Flow Endpoint Handler
Handles WhatsApp Flow completion webhooks for client onboarding
"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error, log_warning


class FlowEndpointHandler:
    """Handles flow completion webhooks for client onboarding"""

    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')

    def handle_client_profile_completion(self, flow_data: Dict, phone_number: str) -> Dict:
        """
        Handle when client completes the profile flow

        Args:
            flow_data: The flow response data containing profile information
            phone_number: Client's phone number

        Returns:
            Dict with success status and message
        """
        try:
            log_info(f"Processing client profile completion for {phone_number}")
            log_info(f"Flow data: {flow_data}")

            # Step 1: Extract all profile data from the flow payload
            profile_data = self._extract_profile_data(flow_data)
            if not profile_data:
                log_error("Failed to extract profile data from flow")
                return {
                    'success': False,
                    'error': 'Failed to extract profile data'
                }

            log_info(f"Extracted profile data: {profile_data}")

            # Step 2: Find the invitation using the invitation_token passed to the flow
            invitation_id = profile_data.get('invitation_id')
            if not invitation_id:
                log_error("No invitation_id found in flow data")
                return {
                    'success': False,
                    'error': 'No invitation_id found in flow data'
                }

            invitation = self._get_invitation(invitation_id)
            if not invitation:
                log_error(f"Invitation {invitation_id} not found")
                return {
                    'success': False,
                    'error': 'Invitation not found'
                }

            log_info(f"Found invitation: {invitation}")

            # Verify the phone matches
            if invitation['client_phone'] != phone_number:
                log_error(f"Phone mismatch: {phone_number} vs {invitation['client_phone']}")
                return {
                    'success': False,
                    'error': 'Phone number mismatch'
                }

            # Step 3: Create or update the client record in the clients table
            client_result = self._create_or_update_client(
                invitation=invitation,
                profile_data=profile_data,
                phone_number=phone_number
            )

            if not client_result.get('success'):
                log_error(f"Failed to create/update client: {client_result.get('error')}")
                return client_result

            client_id = client_result['client_id']
            log_info(f"Created/updated client: {client_id}")

            # Step 4: Create the trainer_client_list relationship with the selected_price
            relationship_result = self._create_trainer_client_relationship(
                trainer_id=invitation['trainer_id'],
                client_id=client_id,
                selected_price=invitation.get('custom_price'),
                invitation_token=invitation.get('invitation_token')
            )

            if not relationship_result.get('success'):
                log_error(f"Failed to create relationship: {relationship_result.get('error')}")
                return relationship_result

            log_info(f"Created trainer-client relationship")

            # Step 5: Update invitation status to 'completed'
            self._update_invitation_status(invitation_id, 'completed')
            log_info(f"Updated invitation {invitation_id} to completed")

            # Step 6: Send confirmation to client
            trainer_name = self._get_trainer_name(invitation['trainer_id'])
            self._send_client_confirmation(phone_number, trainer_name)
            log_info(f"Sent confirmation to client {phone_number}")

            # Step 7: Notify trainer with client's details and next steps
            self._notify_trainer(
                trainer_id=invitation['trainer_id'],
                client_name=profile_data.get('name') or invitation.get('client_name'),
                profile_data=profile_data,
                selected_price=invitation.get('custom_price')
            )
            log_info(f"Sent notification to trainer {invitation['trainer_id']}")

            return {
                'success': True,
                'message': 'Client profile completed successfully',
                'client_id': client_id
            }

        except Exception as e:
            log_error(f"Error handling client profile completion: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _extract_profile_data(self, flow_data: Dict) -> Optional[Dict]:
        """Extract profile data from flow response"""
        try:
            # The flow_data should contain all the form fields
            # Extract invitation_id from flow_action_payload or flow_token
            invitation_id = None

            # Try to get from flow_action_payload
            if 'flow_action_payload' in flow_data:
                payload = flow_data['flow_action_payload']
                invitation_id = payload.get('invitation_id')

            # Try to get from flow_token
            if not invitation_id and 'flow_token' in flow_data:
                flow_token = flow_data['flow_token']
                # flow_token format: "client_onboarding_invitation_{uuid}_{phone}_{timestamp}"
                # After split: ["client", "onboarding", "invitation", "{uuid}", "{phone}", "{timestamp}"]
                if 'client_onboarding_invitation_' in flow_token:
                    parts = flow_token.split('_')
                    if len(parts) >= 6:  # Minimum: prefix parts (3) + uuid + phone + timestamp
                        try:
                            # UUID is at index 3 (already contains hyphens)
                            invitation_id = parts[3]
                            log_info(f"Extracted invitation_id (UUID): {invitation_id}")
                        except (ValueError, IndexError) as e:
                            log_warning(f"Failed to parse invitation_id UUID from flow_token: {flow_token}, error: {str(e)}")

            # If still no invitation_id, try to get from flow_tokens table
            if not invitation_id and 'flow_token' in flow_data:
                try:
                    flow_token_query = self.db.table('flow_tokens').select('data').eq(
                        'flow_token', flow_data['flow_token']
                    ).execute()

                    if flow_token_query.data and flow_token_query.data[0].get('data'):
                        token_data = flow_token_query.data[0]['data']
                        invitation_id = token_data.get('invitation_id')
                        log_info(f"Retrieved invitation_id from flow_tokens table: {invitation_id}")
                except Exception as e:
                    log_warning(f"Failed to retrieve invitation_id from flow_tokens table: {str(e)}")

            # Extract profile fields
            profile_data = {
                'invitation_id': invitation_id,
                'name': flow_data.get('name') or flow_data.get('full_name'),
                'email': flow_data.get('email'),
                'fitness_goals': flow_data.get('fitness_goals') or flow_data.get('goals'),
                'experience_level': flow_data.get('experience_level') or flow_data.get('experience'),
                'availability': flow_data.get('availability'),
                'injuries_conditions': flow_data.get('injuries_conditions') or flow_data.get('injuries'),
                'preferred_workout_type': flow_data.get('preferred_workout_type'),
                'additional_notes': flow_data.get('additional_notes') or flow_data.get('notes')
            }

            # Remove None values
            profile_data = {k: v for k, v in profile_data.items() if v is not None}

            return profile_data

        except Exception as e:
            log_error(f"Error extracting profile data: {str(e)}")
            return None

    def _get_invitation(self, invitation_id: str) -> Optional[Dict]:
        """Get invitation by ID (UUID string)"""
        try:
            log_info(f"Getting invitation with UUID: {invitation_id}")

            # Get invitation details - invitation_id is already a UUID string
            invitation_result = self.db.table('client_invitations').select('*').eq(
                'id', invitation_id
            ).execute()

            if not invitation_result.data:
                log_error(f"No invitation found with id {invitation_id}")
                return None

            invitation = invitation_result.data[0]
            log_info(f"Found invitation with UUID {invitation_id}")
            log_info(f"Invitation status: {invitation.get('status')}")
            log_info(f"Invitation trainer_id: {invitation.get('trainer_id')}")
            log_info(f"Invitation client_phone: {invitation.get('client_phone')}")

            return invitation

        except Exception as e:
            log_error(f"Error getting invitation {invitation_id}: {str(e)}")
            return None

    def _create_or_update_client(self, invitation: Dict, profile_data: Dict, phone_number: str) -> Dict:
        """Create or update client record"""
        try:
            trainer_id = invitation['trainer_id']
            log_info(f"Creating/updating client for phone {phone_number}, trainer_id: {trainer_id}")

            # Check if client already exists
            existing = self.db.table('clients').select('*').eq(
                'whatsapp', phone_number
            ).execute()

            # Prepare client data
            client_data = {
                'name': profile_data.get('name') or invitation.get('client_name'),
                'whatsapp': phone_number,
                'email': profile_data.get('email'),
                'fitness_goals': profile_data.get('fitness_goals'),
                'experience_level': profile_data.get('experience_level'),
                'availability': profile_data.get('availability'),
                'injuries_conditions': profile_data.get('injuries_conditions'),
                'preferred_workout_type': profile_data.get('preferred_workout_type'),
                'additional_notes': profile_data.get('additional_notes'),
                'status': 'active',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }

            if existing.data:
                # Update existing client
                client_id = existing.data[0]['id']
                log_info(f"Updating existing client {client_id} with new profile data")
                self.db.table('clients').update(client_data).eq('id', client_id).execute()
                log_info(f"Successfully updated client {client_id}")
            else:
                # Create new client
                log_info(f"Creating new client account for {phone_number}")
                client_data['created_at'] = datetime.now(self.sa_tz).isoformat()
                result = self.db.table('clients').insert(client_data).execute()

                if not result.data:
                    log_error(f"Failed to create client record for {phone_number}")
                    return {
                        'success': False,
                        'error': 'Failed to create client record'
                    }

                client_id = result.data[0]['id']
                log_info(f"Successfully created new client {client_id}")

            return {
                'success': True,
                'client_id': client_id
            }

        except Exception as e:
            log_error(f"Error creating/updating client: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _create_trainer_client_relationship(self, trainer_id: str, client_id: str,
                                           selected_price: Optional[float],
                                           invitation_token: Optional[str]) -> Dict:
        """Create bidirectional trainer-client relationship"""
        try:
            log_info(f"Creating trainer-client relationship: trainer_id={trainer_id}, client_id={client_id}")
            log_info(f"Relationship details: custom_price={selected_price}, invitation_token={invitation_token}")

            now = datetime.now(self.sa_tz).isoformat()

            # Check if relationship already exists
            existing_trainer = self.db.table('trainer_client_list').select('*').eq(
                'trainer_id', trainer_id
            ).eq('client_id', client_id).execute()

            relationship_data = {
                'connection_status': 'active',
                'custom_price': selected_price,
                'invitation_token': invitation_token,
                'updated_at': now
            }

            if existing_trainer.data:
                # Update existing relationship
                log_info(f"Updating existing trainer_client_list relationship")
                self.db.table('trainer_client_list').update(relationship_data).eq(
                    'trainer_id', trainer_id
                ).eq('client_id', client_id).execute()

                log_info(f"Successfully updated trainer_client_list relationship")
            else:
                # Create new relationship
                log_info(f"Creating new trainer_client_list relationship")
                trainer_list_data = {
                    'trainer_id': trainer_id,
                    'client_id': client_id,
                    'created_at': now,
                    **relationship_data
                }

                self.db.table('trainer_client_list').insert(trainer_list_data).execute()
                log_info(f"Successfully created trainer_client_list relationship")

            # Also create/update client_trainer_list (bidirectional)
            log_info(f"Creating/updating bidirectional client_trainer_list relationship")
            existing_client = self.db.table('client_trainer_list').select('*').eq(
                'client_id', client_id
            ).eq('trainer_id', trainer_id).execute()

            if existing_client.data:
                log_info(f"Updating existing client_trainer_list relationship")
                self.db.table('client_trainer_list').update(relationship_data).eq(
                    'client_id', client_id
                ).eq('trainer_id', trainer_id).execute()
                log_info(f"Successfully updated client_trainer_list relationship")
            else:
                log_info(f"Creating new client_trainer_list relationship")
                client_list_data = {
                    'client_id': client_id,
                    'trainer_id': trainer_id,
                    'created_at': now,
                    **relationship_data
                }

                self.db.table('client_trainer_list').insert(client_list_data).execute()
                log_info(f"Successfully created client_trainer_list relationship")

            return {
                'success': True,
                'message': 'Relationship created successfully'
            }

        except Exception as e:
            log_error(f"Error creating relationship: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _update_invitation_status(self, invitation_id: str, status: str):
        """Update invitation status (invitation_id is UUID string)"""
        try:
            log_info(f"Updating invitation {invitation_id} to status: {status}")
            self.db.table('client_invitations').update({
                'status': status,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', invitation_id).execute()
        except Exception as e:
            log_error(f"Error updating invitation {invitation_id} status: {str(e)}")

    def _get_trainer_name(self, trainer_id: str) -> str:
        """Get trainer name"""
        try:
            result = self.db.table('trainers').select('name, first_name, last_name').eq(
                'id', trainer_id
            ).execute()

            if result.data:
                trainer = result.data[0]
                return trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'your trainer'

            return 'your trainer'

        except Exception as e:
            log_error(f"Error getting trainer name: {str(e)}")
            return 'your trainer'

    def _send_client_confirmation(self, phone_number: str, trainer_name: str):
        """Send confirmation message to client"""
        try:
            message = f"✅ Profile complete! {trainer_name} will be in touch soon"
            self.whatsapp.send_message(phone_number, message)
        except Exception as e:
            log_error(f"Error sending client confirmation: {str(e)}")

    def _notify_trainer(self, trainer_id: str, client_name: str, profile_data: Dict,
                       selected_price: Optional[float]):
        """Notify trainer with client's details and next steps"""
        try:
            # Get trainer's phone number
            trainer_result = self.db.table('trainers').select('whatsapp, phone').eq(
                'id', trainer_id
            ).execute()

            if not trainer_result.data:
                log_error(f"Trainer {trainer_id} not found")
                return

            trainer = trainer_result.data[0]
            trainer_phone = trainer.get('whatsapp') or trainer.get('phone')

            if not trainer_phone:
                log_error(f"No phone number found for trainer {trainer_id}")
                return

            # Build notification message
            message = (
                f"🎉 *New Client Profile Complete!*\n\n"
                f"*{client_name}* has completed their fitness profile!\n\n"
                f"📋 *Profile Details:*\n"
            )

            if profile_data.get('fitness_goals'):
                message += f"• *Goals:* {profile_data['fitness_goals']}\n"

            if profile_data.get('experience_level'):
                message += f"• *Experience:* {profile_data['experience_level']}\n"

            if profile_data.get('availability'):
                message += f"• *Availability:* {profile_data['availability']}\n"

            if profile_data.get('injuries_conditions'):
                message += f"• *Injuries/Conditions:* {profile_data['injuries_conditions']}\n"

            if profile_data.get('preferred_workout_type'):
                message += f"• *Preferred Workout:* {profile_data['preferred_workout_type']}\n"

            if profile_data.get('additional_notes'):
                message += f"• *Notes:* {profile_data['additional_notes']}\n"

            # Add price information
            if selected_price is not None:
                message += f"\n💰 *Agreed Price:* R{selected_price:.2f} per session\n"
            else:
                message += f"\n💰 *Pricing:* To be discussed\n"

            # Add next steps
            message += (
                f"\n✨ *Next Steps:*\n"
                f"• Review their profile and goals\n"
                f"• Schedule your first session together\n"
                f"• Start planning their personalized program!\n\n"
                f"You can contact {client_name} at {profile_data.get('email', 'no email provided')}"
            )

            self.whatsapp.send_message(trainer_phone, message)
            log_info(f"Sent trainer notification to {trainer_phone}")

        except Exception as e:
            log_error(f"Error notifying trainer: {str(e)}")
