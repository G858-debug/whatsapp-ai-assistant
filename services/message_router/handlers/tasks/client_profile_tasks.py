"""
Client Profile Task Handler
Handles client profile-related tasks for contact-based onboarding flow
"""
from typing import Dict, Optional
from utils.logger import log_info, log_error, log_debug
from services.validation import get_validator


class ClientProfileTaskHandler:
    """Handles client profile-related tasks"""

    def __init__(self, db, whatsapp, auth_service, task_service):
        """
        Initialize the client profile task handler

        Args:
            db: Supabase database client
            whatsapp: WhatsApp service instance
            auth_service: Authentication service for user lookups
            task_service: Task service for task management
        """
        self.db = db
        self.whatsapp = whatsapp
        self.auth_service = auth_service
        self.task_service = task_service

    def handle_client_profile_task(self, phone: str, message: str, task: Dict, role: str) -> Dict:
        """
        Handle client profile tasks - specifically custom price input during onboarding

        Args:
            phone: User's phone number
            message: Message text from user
            task: Running task data
            role: User role ('trainer' or 'client')

        Returns:
            Dict with success status and response
        """
        try:
            task_type = task.get('task_type')
            task_id = task.get('id')
            task_data = task.get('task_data', {})
            step = task_data.get('step', '')

            log_info(f"Handling client profile task: {task_type}, step: {step}")

            # Handle add_client_profile_choice task with custom price step
            if task_type == 'add_client_profile_choice' and step == 'awaiting_custom_price':
                return self._handle_custom_price_input(phone, message, task_id, task_data, role)
            else:
                # Unknown step or task type
                log_error(f"Unknown client profile task step: {task_type}/{step}")
                msg = "Please select one of the buttons above to continue."
                self.whatsapp.send_message(phone, msg)
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'client_profile_unknown_step'
                }

        except Exception as e:
            log_error(f"Error handling client profile task: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Type /stop to cancel."
            self.whatsapp.send_message(phone, msg)
            return {
                'success': False,
                'response': msg,
                'handler': 'client_profile_error'
            }

    def _handle_custom_price_input(self, phone: str, message: str, task_id: str,
                                   task_data: Dict, role: str) -> Dict:
        """
        Handle custom price input from trainer

        Args:
            phone: Trainer's phone number
            message: Price input from trainer
            task_id: Current task ID
            task_data: Task data dictionary
            role: User role ('trainer')

        Returns:
            Dict with success status and response
        """
        try:
            # Check for cancel command
            if message.strip().lower() in ['/cancel', '/stop']:
                self.task_service.complete_task(task_id, role)
                msg = "❌ Cancelled. The client invitation was not sent."
                self.whatsapp.send_message(phone, msg)
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'custom_price_cancelled'
                }

            # Get trainer user ID for validation tracking
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                msg = "❌ Sorry, I couldn't find your account. Please log in again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {
                    'success': False,
                    'response': msg,
                    'handler': 'custom_price_no_user'
                }

            # Validate price input
            validator = get_validator()
            is_valid, error_msg, price_value = validator.validate_price(message.strip(), user_id)

            if not is_valid:
                # Send validation error to trainer
                self.whatsapp.send_message(phone, error_msg)
                return {
                    'success': True,
                    'response': error_msg,
                    'handler': 'custom_price_validation_error'
                }

            # Store validated price (rounded to 2 decimals)
            selected_price = round(price_value, 2)
            task_data['selected_price'] = selected_price
            log_info(f"Trainer {user_id} set custom price: R{selected_price}")

            # Get contact data (from either contact_data or basic_contact_data)
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
                self.task_service.complete_task(task_id, role)
                return {
                    'success': False,
                    'response': msg,
                    'handler': 'custom_price_no_contact_data'
                }

            if not client_phone:
                msg = "❌ Missing phone number. Please share the contact again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {
                    'success': False,
                    'response': msg,
                    'handler': 'custom_price_no_phone'
                }

            # Ensure trainer record exists in trainers table (get UUID)
            trainer_uuid, error_msg = self._ensure_trainer_record_exists(phone, user_id)

            if not trainer_uuid:
                log_error(f"Failed to ensure trainer record exists: {error_msg}")
                msg = "❌ Error setting up trainer profile. Please contact support."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {
                    'success': False,
                    'response': msg,
                    'handler': 'custom_price_trainer_record_error'
                }

            # Send invitation to client using InvitationService
            from services.relationships.invitations.invitation_service import InvitationService

            invitation_service = InvitationService(self.db, self.whatsapp)

            success, invitation_error = invitation_service.send_client_fills_invitation(
                trainer_id=trainer_uuid,
                client_phone=client_phone,
                client_name=client_name,
                selected_price=selected_price
            )

            if success:
                # Send success message to trainer
                msg = (
                    f"✅ *Invitation sent!*\n\n"
                    f"I've sent {client_name} a training invitation.\n\n"
                    f"💰 Rate: R{int(selected_price)} per session\n\n"
                    f"They'll receive a message to complete their fitness profile and review the details."
                )
                self.whatsapp.send_message(phone, msg)

                # Complete the task
                self.task_service.complete_task(task_id, role)

                log_info(f"Successfully sent client invitation from {user_id} to {client_phone} with price R{selected_price}")

                return {
                    'success': True,
                    'response': msg,
                    'handler': 'custom_price_invitation_sent'
                }
            else:
                # Invitation failed
                log_error(f"Failed to send invitation: {invitation_error}")
                msg = f"❌ Failed to send invitation: {invitation_error}\n\nPlease try again or contact support."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)

                return {
                    'success': False,
                    'response': msg,
                    'handler': 'custom_price_invitation_failed'
                }

        except Exception as e:
            log_error(f"Error handling custom price input: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {
                'success': False,
                'response': msg,
                'handler': 'custom_price_input_error'
            }

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
