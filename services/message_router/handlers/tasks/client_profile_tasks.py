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

    def _handle_custom_price_input(self, phone: str, message: str, task_id: str, task_data: Dict, role: str) -> Dict:
        """Handle custom price input for client onboarding"""
        try:
            from services.validation import get_validator

            # Get the trainer's UUID from the users table
            user_result = self.db.table('users').select('id, trainer_id').eq('phone_number', phone).execute()

            if not user_result.data or len(user_result.data) == 0:
                msg = "❌ Could not find your account. Please try again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'custom_price_no_user'}

            trainer_id = user_result.data[0].get('trainer_id')
            if not trainer_id:
                msg = "❌ Could not find your trainer account. Please contact support."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'custom_price_no_trainer_id'}

            # Validate the price
            validator = get_validator()
            is_valid, error_msg, validated_price = validator.validate_price(message, phone)

            if not is_valid:
                # Send validation error
                self.whatsapp.send_message(phone, error_msg)
                return {'success': True, 'response': error_msg, 'handler': 'custom_price_invalid'}

            # Store the price in task_data
            task_data['selected_price'] = validated_price
            task_data['step'] = 'price_confirmed'

            # Update the task
            self.task_service.update_task(task_id, role, task_data)

            # Get contact data
            contact_data = task_data.get('contact_data') or task_data.get('basic_contact_data')
            if not contact_data:
                msg = "❌ Missing contact information. Please try again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'custom_price_no_contact'}

            client_name = contact_data.get('name', 'the client')
            client_phone = contact_data.get('phone')

            if not client_phone:
                msg = "❌ Missing phone number. Please share the contact again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'custom_price_no_phone'}

            # Send invitation to client
            from services.flows.relationships.trainer_flows.creation_flow import TrainerClientCreationFlow

            creation_flow = TrainerClientCreationFlow(self.db, self.whatsapp, self.task_service)

            # Build task dict
            task_dict = {
                'id': task_id,
                'task_data': task_data
            }

            # Send the invitation
            result = creation_flow._send_client_fills_invitation(
                trainer_phone=phone,
                trainer_id=trainer_id,
                task=task_dict,
                task_data=task_data
            )

            return result

        except Exception as e:
            log_error(f"Error handling custom price input: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'custom_price_input_error'}

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
