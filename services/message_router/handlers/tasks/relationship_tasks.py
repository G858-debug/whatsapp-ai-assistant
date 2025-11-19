"""
Relationship Task Handler
Handles trainer-client relationship tasks (Phase 2)
"""
from typing import Dict
from utils.logger import log_info, log_error, log_debug


class RelationshipTaskHandler:
    """Handles relationship-related tasks"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service, reg_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
        self.reg_service = reg_service
    
    def handle_relationship_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle relationship tasks"""
        try:
            task_type = task.get('task_type')

            # Trainer relationship tasks
            if task_type in ['invite_trainee', 'create_trainee', 'remove_trainee']:
                return self._handle_trainer_relationship_task(phone, message, user_id, task)

            # Client relationship tasks
            elif task_type in ['search_trainer', 'invite_trainer', 'remove_trainer']:
                return self._handle_client_relationship_task(phone, message, user_id, task)

            # Add client tasks
            elif task_type in ['add_client_choice', 'add_client_profile_choice']:
                return self._handle_add_client_task(phone, message, user_id, task)

            # Invitation decline reason task
            elif task_type == 'decline_reason':
                return self._handle_decline_reason_task(phone, message, user_id, task)

            else:
                return {'success': False, 'response': 'Unknown relationship task', 'handler': 'unknown_relationship_task'}

        except Exception as e:
            log_error(f"Error handling relationship task: {str(e)}")
            return {'success': False, 'response': 'Error continuing relationship task', 'handler': 'relationship_task_error'}
    
    def _handle_trainer_relationship_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle trainer relationship tasks"""
        try:
            from services.flows import TrainerRelationshipFlows
            handler = TrainerRelationshipFlows(self.db, self.whatsapp, self.task_service, self.reg_service)
            
            task_type = task.get('task_type')
            if task_type == 'invite_trainee':
                return handler.continue_invite_trainee(phone, message, user_id, task)
            elif task_type == 'create_trainee':
                return handler.continue_create_trainee(phone, message, user_id, task)
            elif task_type == 'remove_trainee':
                return handler.continue_remove_trainee(phone, message, user_id, task)
            else:
                return {'success': False, 'response': 'Unknown trainer relationship task', 'handler': 'trainer_relationship_task_error'}
                
        except Exception as e:
            log_error(f"Error continuing trainer relationship task: {str(e)}")
            return {'success': False, 'response': 'Error continuing trainer task', 'handler': 'trainer_relationship_task_error'}
    
    def _handle_client_relationship_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle client relationship tasks"""
        try:
            from services.flows import ClientRelationshipFlows
            handler = ClientRelationshipFlows(self.db, self.whatsapp, self.task_service)

            task_type = task.get('task_type')
            if task_type == 'search_trainer':
                return handler.continue_search_trainer(phone, message, user_id, task)
            elif task_type == 'invite_trainer':
                return handler.continue_invite_trainer(phone, message, user_id, task)
            elif task_type == 'remove_trainer':
                return handler.continue_remove_trainer(phone, message, user_id, task)
            else:
                return {'success': False, 'response': 'Unknown client relationship task', 'handler': 'client_relationship_task_error'}

        except Exception as e:
            log_error(f"Error continuing client relationship task: {str(e)}")
            return {'success': False, 'response': 'Error continuing client task', 'handler': 'client_relationship_task_error'}

    def _handle_add_client_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle add client contact collection tasks"""
        try:
            task_type = task.get('task_type')
            task_id = task.get('id')
            task_data = task.get('task_data', {})
            step = task_data.get('step', '')
            role = 'trainer'

            # Handle add_client_choice task - text-based contact collection
            if task_type == 'add_client_choice':
                if step == 'collecting_name':
                    return self._handle_collecting_name(phone, message, user_id, task_id, task_data, role)
                elif step == 'collecting_phone':
                    return self._handle_collecting_phone(phone, message, user_id, task_id, task_data, role)
                elif step == 'collecting_email':
                    return self._handle_collecting_email(phone, message, user_id, task_id, task_data, role)
                else:
                    log_error(f"Unknown add_client_choice step: {step}")
                    return {'success': False, 'response': 'Unknown step', 'handler': 'add_client_unknown_step'}

            # Handle add_client_profile_choice task
            elif task_type == 'add_client_profile_choice':
                # Check if we're awaiting custom price input
                if step == 'awaiting_custom_price':
                    return self._handle_custom_price_input(phone, message, user_id, task_id, task_data, role)
                else:
                    # For other steps, this task type is handled by buttons
                    msg = "Please select one of the buttons above to continue."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'add_client_profile_awaiting_button'}

            else:
                return {'success': False, 'response': 'Unknown add client task type', 'handler': 'add_client_unknown_type'}

        except Exception as e:
            log_error(f"Error handling add client task: {str(e)}")
            return {'success': False, 'response': 'Error continuing add client task', 'handler': 'add_client_task_error'}

    def _handle_collecting_name(self, phone: str, message: str, user_id: str, task_id: str, task_data: Dict, role: str) -> Dict:
        """Handle collecting_name step"""
        try:
            name = message.strip()

            # Validate name (at least 2 characters)
            if len(name) < 2:
                msg = "❌ Name must be at least 2 characters. Please try again."
                self.whatsapp.send_message(phone, msg)
                return {'success': True, 'response': msg, 'handler': 'collecting_name_too_short'}

            # Store name in basic_contact_data
            if 'basic_contact_data' not in task_data:
                task_data['basic_contact_data'] = {}

            task_data['basic_contact_data']['name'] = name

            # Update step to collecting_phone
            task_data['step'] = 'collecting_phone'
            self.task_service.update_task(task_id, role, task_data)

            # Ask for phone number
            msg = (
                f"Perfect! 📱\n\n"
                f"What is {name}'s phone number?\n\n"
                f"(Include country code if outside South Africa, e.g., +27821234567)"
            )
            self.whatsapp.send_message(phone, msg)

            return {'success': True, 'response': msg, 'handler': 'collecting_name_success'}

        except Exception as e:
            log_error(f"Error handling collecting_name: {str(e)}")
            return {'success': False, 'response': 'Error collecting name', 'handler': 'collecting_name_error'}

    def _handle_collecting_phone(self, phone: str, message: str, user_id: str, task_id: str, task_data: Dict, role: str) -> Dict:
        """Handle collecting_phone step"""
        try:
            from utils.phone_utils import normalize_phone_number
            from services.relationships.client_checker import ClientChecker

            phone_input = message.strip()

            # Clean phone number
            if self.reg_service:
                cleaned_phone = self.reg_service.clean_phone_number(phone_input)
            else:
                # Basic cleaning
                cleaned_phone = ''.join(c for c in phone_input if c.isdigit() or c == '+')

            # Normalize phone number (add +27 if needed for SA numbers)
            normalized_phone = normalize_phone_number(cleaned_phone)

            if not normalized_phone:
                msg = "❌ Invalid phone number. Please try again with a valid phone number."
                self.whatsapp.send_message(phone, msg)
                return {'success': True, 'response': msg, 'handler': 'collecting_phone_invalid'}

            # Check if client already exists using ClientChecker
            client_checker = ClientChecker(self.db)
            check_result = client_checker.check_client_status(normalized_phone, user_id)

            scenario = check_result.get('scenario')
            client_name = task_data.get('basic_contact_data', {}).get('name', 'Unknown')

            # If client exists, route to appropriate scenario
            if scenario == 'available':
                # Client exists but no trainer - send invitation
                client_id = check_result.get('client_data', {}).get('client_id')
                msg = (
                    f"👤 *Existing Client Found!*\n\n"
                    f"{client_name} is already registered on Refiloe but doesn't have a trainer yet.\n\n"
                    f"I'll send them an invitation to connect with you!"
                )
                self.whatsapp.send_message(phone, msg)

                # Complete current task
                self.task_service.complete_task(task_id, role)

                # TODO: Integrate with invitation system for existing clients

                return {'success': True, 'response': msg, 'handler': 'collecting_phone_existing_available'}

            elif scenario == 'already_yours':
                # Already this trainer's client
                msg = (
                    f"ℹ️ *Already Your Client!*\n\n"
                    f"{client_name} is already one of your clients.\n\n"
                    f"You can view their details with /view-trainees"
                )
                self.whatsapp.send_message(phone, msg)

                # Complete current task
                self.task_service.complete_task(task_id, role)

                return {'success': True, 'response': msg, 'handler': 'collecting_phone_already_yours'}

            elif scenario == 'has_other_trainer':
                # Has another trainer - multi-trainer scenario
                msg = (
                    f"👥 *Client Has Another Trainer*\n\n"
                    f"{client_name} currently trains with another trainer.\n\n"
                    f"Would you like to send them an invitation to work with you as well?"
                )
                buttons = [
                    {'id': 'send_secondary_invitation', 'title': '✅ Yes, Invite'},
                    {'id': 'cancel_add_client', 'title': '❌ Cancel'}
                ]
                self.whatsapp.send_button_message(phone, msg, buttons)

                # Complete current task and create secondary invitation task
                self.task_service.complete_task(task_id, role)

                # Store for secondary invitation flow
                contact_data = {
                    'name': client_name,
                    'phone': normalized_phone
                }
                self.task_service.create_task(
                    user_id=phone,
                    role='trainer',
                    task_type='secondary_trainer_invitation',
                    task_data={
                        'step': 'confirm_secondary',
                        'trainer_id': user_id,
                        'contact_data': contact_data,
                        'client_id': check_result.get('client_data', {}).get('client_id')
                    }
                )

                return {'success': True, 'response': msg, 'handler': 'collecting_phone_has_trainer'}

            # Client is new - continue to collecting_email
            # Store normalized phone in basic_contact_data
            task_data['basic_contact_data']['phone'] = normalized_phone

            # Update step to collecting_email
            task_data['step'] = 'collecting_email'
            self.task_service.update_task(task_id, role, task_data)

            # Ask for email
            msg = (
                f"Great! 📧\n\n"
                f"What is {client_name}'s email address?\n\n"
                f"(Type 'skip' if they don't have one)"
            )
            self.whatsapp.send_message(phone, msg)

            return {'success': True, 'response': msg, 'handler': 'collecting_phone_success'}

        except Exception as e:
            log_error(f"Error handling collecting_phone: {str(e)}")
            return {'success': False, 'response': 'Error collecting phone', 'handler': 'collecting_phone_error'}

    def _handle_collecting_email(self, phone: str, message: str, user_id: str, task_id: str, task_data: Dict, role: str) -> Dict:
        """Handle collecting_email step"""
        try:
            email_input = message.strip()
            basic_contact_data = task_data.get('basic_contact_data', {})
            client_name = basic_contact_data.get('name', 'Unknown')
            client_phone = basic_contact_data.get('phone')

            # Check if user wants to skip
            if email_input.lower() == 'skip':
                basic_contact_data['email'] = None
            else:
                # Validate email format (contains @ and .)
                if '@' not in email_input or '.' not in email_input:
                    msg = "❌ Invalid email format. Please provide a valid email address or type 'skip'."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'collecting_email_invalid'}

                basic_contact_data['email'] = email_input

            # Show the "new client" message
            msg = (
                f"🎉 *New client!*\n\n"
                f"{client_name} ({client_phone}) is a new number on my database.\n\n"
                f"Who should populate their fitness profile?"
            )

            # Show buttons
            buttons = [
                {'id': 'client_fills_profile', 'title': '📱 Client populates'},
                {'id': 'trainer_fills_profile', 'title': '✏️ I\'ll populate'}
            ]

            self.whatsapp.send_button_message(phone, msg, buttons)

            # Complete current task
            self.task_service.complete_task(task_id, role)

            # Create new task type 'add_client_profile_choice' with step 'choose_profile_method'
            # Store basic_contact_data in the new task's contact_data
            contact_data = {
                'name': client_name,
                'phone': client_phone,
                'emails': [basic_contact_data['email']] if basic_contact_data.get('email') else []
            }

            self.task_service.create_task(
                user_id=phone,
                role='trainer',
                task_type='add_client_profile_choice',
                task_data={
                    'step': 'choose_profile_method',
                    'trainer_id': user_id,
                    'contact_data': contact_data
                }
            )

            return {'success': True, 'response': msg, 'handler': 'collecting_email_success'}

        except Exception as e:
            log_error(f"Error handling collecting_email: {str(e)}")
            return {'success': False, 'response': 'Error collecting email', 'handler': 'collecting_email_error'}

    def _handle_decline_reason_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """Handle client providing reason for declining invitation"""
        try:
            from datetime import datetime
            import pytz

            task_id = task.get('id')
            task_data = task.get('task_data', {})
            invitation_id = task_data.get('invitation_id')
            trainer_id = task_data.get('trainer_id')

            # Check if user wants to skip
            if message.strip().lower() in ['/skip', 'skip']:
                msg = "Thanks for letting me know. If you change your mind, feel free to reach out!"
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, 'client')
                return {'success': True, 'response': msg, 'handler': 'decline_reason_skipped'}

            # Store the reason in the invitation record
            sa_tz = pytz.timezone('Africa/Johannesburg')
            self.db.table('client_invitations').update({
                'decline_reason': message,
                'updated_at': datetime.now(sa_tz).isoformat()
            }).eq('id', invitation_id).execute()

            # Get trainer info to notify
            trainer_result = self.db.table('trainers').select('whatsapp, name, first_name, last_name').eq(
                'id', trainer_id
            ).execute()

            if trainer_result.data:
                trainer = trainer_result.data[0]
                trainer_phone = trainer.get('whatsapp') or trainer.get('phone')

                # Get invitation details for client name
                invitation_result = self.db.table('client_invitations').select('client_name').eq(
                    'id', invitation_id
                ).execute()

                client_name = invitation_result.data[0].get('client_name', 'The client') if invitation_result.data else 'The client'

                # Notify trainer with the reason
                if trainer_phone:
                    trainer_msg = (
                        f"ℹ️ {client_name} declined your invitation.\n\n"
                        f"*Reason:*\n{message}"
                    )
                    self.whatsapp.send_message(trainer_phone, trainer_msg)

            # Thank the client
            msg = "Thanks for sharing that feedback. If you change your mind about training, feel free to reach out!"
            self.whatsapp.send_message(phone, msg)

            # Complete the task
            self.task_service.complete_task(task_id, 'client')

            return {'success': True, 'response': msg, 'handler': 'decline_reason_provided'}

        except Exception as e:
            log_error(f"Error handling decline reason: {str(e)}")
            # Complete task even if there's an error
            self.task_service.complete_task(task.get('id'), 'client')
            return {'success': False, 'response': 'Error processing your response', 'handler': 'decline_reason_error'}

    def _handle_custom_price_input(self, phone: str, message: str, user_id: str, task_id: str, task_data: Dict, role: str) -> Dict:
        """Handle custom price input for client onboarding"""
        try:
            from services.validation.price_validator import get_validator

            # Validate the price
            validator = get_validator()
            is_valid, error_msg, validated_price = validator.validate_price(message, phone)

            if not is_valid:
                # Send validation error
                self.whatsapp.send_message(phone, error_msg)
                return {'success': True, 'response': error_msg, 'handler': 'custom_price_invalid'}

            # Store the price in task_data
            task_data['selected_price'] = validated_price
            task_data['step'] = 'price_confirmed'  # Update step

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

            # Send invitation to client with the custom price
            # Import here to avoid circular dependencies
            from services.flows.relationships.trainer_flows.creation_flow import TrainerClientCreationFlow

            creation_flow = TrainerClientCreationFlow(self.db, self.whatsapp, self.task_service)

            # Build task dict for the creation flow
            task_dict = {
                'id': task_id,
                'task_data': task_data
            }

            # Call the method to send invitation
            result = creation_flow._send_client_fills_invitation(
                trainer_phone=phone,
                trainer_id=user_id,  # user_id is the trainer's UUID
                task=task_dict,
                task_data=task_data
            )

            return result

        except Exception as e:
            log_error(f"Error handling custom price input: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'custom_price_input_error'}
