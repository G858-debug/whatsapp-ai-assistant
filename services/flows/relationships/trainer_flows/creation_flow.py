"""
Trainer Client Creation Flow
Handles trainer creating new client accounts
"""
from typing import Dict
from utils.logger import log_info, log_error, log_warning
from services.relationships import RelationshipService, InvitationService
from services.validation import get_validator
import json


class CreationFlow:
    """Handles client creation flows"""
    
    def __init__(self, db, whatsapp, task_service, reg_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.reg_service = reg_service
        self.relationship_service = RelationshipService(db)
        self.invitation_service = InvitationService(db, whatsapp)
    
    def continue_create_trainee(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle create new client flow - simplified to only handle new client creation"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_create_or_link')
            collected_data = task_data.get('collected_data', {})
            
            # Step 1: Ask if create new or link existing
            if step == 'ask_create_or_link':
                choice = message.strip()

                if choice == '1':
                    # Text-based client creation is deprecated - redirect to /add-client
                    msg = (
                        "ℹ️ *Text-Based Creation Deprecated*\n\n"
                        "The step-by-step text-based client creation has been replaced "
                        "with an improved WhatsApp Flow interface.\n\n"
                        "Please use the */add-client* command instead for a better experience!\n\n"
                        "🎯 *New Features:*\n"
                        "• Better form interface\n"
                        "• Easier to fill out\n"
                        "• Fewer errors\n\n"
                        "Type */add-client* to get started."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_deprecated'}
                
                elif choice == '2':
                    # Redirect to invitation flow with existing command button
                    msg = (
                        "🔗 *Link Existing Client*\n\n"
                        "Click the button below to start inviting an existing client:"
                    )
                    
                    # Use existing /invite-trainee command as button
                    buttons = [
                        {'id': '/invite-trainee', 'title': 'Invite Client'}
                    ]
                    self.whatsapp.send_button_message(phone, msg, buttons)
                    
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_redirect_invite'}
                
                else:
                    msg = "❌ Invalid choice. Please reply with *1* to create new or *2* to link existing."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_invalid_choice'}

            # ===== DEPRECATED: Text-based field collection =====
            # This entire section has been replaced by the /add-client WhatsApp Flow
            # Kept here for reference but should not be reached anymore
            """
            # Step 2: Collect fields for new client
            if step == 'collecting':
                fields = task_data.get('fields', [])
                current_index = task_data.get('current_field_index', 0)
                
                # Validate and store previous answer
                if current_index > 0:
                    prev_field = fields[current_index - 1]
                    field_name = prev_field['name']
                    field_type = prev_field.get('type', 'text')

                    # Use comprehensive validator for better validation and retry logic
                    validator = get_validator()
                    is_valid = False
                    error_msg = ""
                    parsed_value = message

                    # Field-specific validation with retry logic
                    if field_name == 'phone_number' or field_type == 'phone':
                        is_valid, error_msg, cleaned_phone = validator.validate_phone_number(message, phone)
                        if is_valid:
                            parsed_value = cleaned_phone

                        # Check for max retries
                        if not is_valid and validator.has_exceeded_max_retries(phone, 'phone'):
                            restart_msg = validator.get_restart_prompt('phone number')
                            self.whatsapp.send_message(phone, restart_msg)
                            return {'success': True, 'response': restart_msg, 'handler': 'create_trainee_max_retries'}

                    elif field_name == 'full_name' or field_name == 'name':
                        is_valid, error_msg = validator.validate_name(message, phone)
                        if is_valid:
                            parsed_value = message.strip()

                    elif field_name == 'email' or field_type == 'email':
                        is_optional = not prev_field.get('required', False)
                        is_valid, error_msg = validator.validate_email(message, not is_optional, phone)
                        if is_valid:
                            # Handle skip for optional fields
                            if message.strip().lower() in ['skip', 'none', 'n/a', 'na']:
                                parsed_value = None
                            else:
                                parsed_value = message.strip().lower()

                    elif field_name == 'custom_price_amount' or 'price' in field_name.lower():
                        is_valid, error_msg, price_value = validator.validate_price(message, phone)
                        if is_valid:
                            parsed_value = price_value

                        # Check for max retries
                        if not is_valid and validator.has_exceeded_max_retries(phone, 'price'):
                            restart_msg = validator.get_restart_prompt('price')
                            self.whatsapp.send_message(phone, restart_msg)
                            return {'success': True, 'response': restart_msg, 'handler': 'create_trainee_max_retries'}

                    else:
                        # Use registration service or fallback for other field types
                        if self.reg_service:
                            is_valid, error_msg = self.reg_service.validate_field_value(prev_field, message)
                            if is_valid:
                                parsed_value = self.reg_service.parse_field_value(prev_field, message)
                        else:
                            is_valid, error_msg = self._validate_field_value(prev_field, message)
                            if is_valid:
                                parsed_value = self._parse_field_value(prev_field, message)

                    # Handle validation failure
                    if not is_valid:
                        error_response = error_msg  # Already formatted with examples and tips
                        self.whatsapp.send_message(phone, error_response)
                        log_warning(f"Validation failed for {field_name}: {error_msg}")
                        return {'success': True, 'response': error_response, 'handler': 'create_trainee_validation_error'}

                    # Store validated value
                    collected_data[field_name] = parsed_value
                    task_data['collected_data'] = collected_data
                    log_info(f"Field {field_name} validated and stored: {parsed_value}")
                    
                    # Special handling for phone_number field - check if client exists immediately
                    if field_name == 'phone_number':
                        # Clean phone number
                        if self.reg_service:
                            clean_phone = self.reg_service.clean_phone_number(parsed_value)
                        else:
                            clean_phone = self._clean_phone_number(parsed_value)
                        
                        # Update the collected data with clean phone
                        collected_data['phone_number'] = clean_phone
                        task_data['collected_data'] = collected_data
                        
                        # Check if client already exists
                        existing_client = self.db.table('clients').select('client_id, name, whatsapp').eq(
                            'whatsapp', clean_phone
                        ).execute()
                        
                        if existing_client.data:
                            # Client exists - check if they have an active trainer
                            client = existing_client.data[0]
                            client_id = client.get('client_id')

                            # Check for existing active trainer relationships
                            existing_trainers = self.relationship_service.get_client_trainers(client_id, 'active')

                            if existing_trainers:
                                # Multi-trainer scenario - client has another trainer
                                current_trainer = existing_trainers[0]  # Get first active trainer
                                current_trainer_info = {
                                    'trainer_id': current_trainer.get('trainer_id'),
                                    'name': current_trainer.get('name') or f"{current_trainer.get('first_name', '')} {current_trainer.get('last_name', '')}".strip()
                                }

                                # Store in task data and redirect to multi-trainer handler
                                task_data['step'] = 'multi_trainer_scenario'
                                task_data['existing_client'] = client
                                task_data['current_trainer_info'] = current_trainer_info
                                task_data['multi_trainer_step'] = 'show_warning'
                                self.task_service.update_task(task['id'], 'trainer', task_data)

                                # Call the multi-trainer scenario handler
                                return self.handle_multi_trainer_scenario(
                                    phone, message, client, current_trainer_info, trainer_id, task
                                )
                            else:
                                # Client exists but no trainer - ask to invite instead
                                msg = (
                                    f"ℹ️ *Client Already Exists!*\n\n"
                                    f"A client with this phone number is already registered:\n\n"
                                    f"*Name:* {client.get('name')}\n"
                                    f"*Client ID:* {client.get('client_id')}\n\n"
                                    f"Would you like to send them an invitation instead?\n\n"
                                    f"Reply *YES* to send invitation, or *NO* to cancel."
                                )
                                self.whatsapp.send_message(phone, msg)
                                task_data['step'] = 'confirm_invite_existing'
                                task_data['existing_client_id'] = client.get('client_id')
                                task_data['existing_client_phone'] = client.get('whatsapp')
                                self.task_service.update_task(task['id'], 'trainer', task_data)
                                return {'success': True, 'response': msg, 'handler': 'create_trainee_exists_early'}
                
                # Check if we have all fields
                if current_index >= len(fields):
                    # All fields collected - clean and check if phone exists
                    phone_number = collected_data.get('phone_number')
                    
                    # Clean phone number (remove +, -, spaces, etc.)
                    if phone_number:
                        if self.reg_service:
                            phone_number = self.reg_service.clean_phone_number(phone_number)
                        else:
                            phone_number = self._clean_phone_number(phone_number)
                        collected_data['phone_number'] = phone_number
                    
                    existing_client = self.db.table('clients').select('client_id, name, whatsapp').eq(
                        'whatsapp', phone_number
                    ).execute()

                    if existing_client.data:
                        # Client exists - check if they have an active trainer
                        client = existing_client.data[0]
                        client_id = client.get('client_id')

                        # Check for existing active trainer relationships
                        existing_trainers = self.relationship_service.get_client_trainers(client_id, 'active')

                        if existing_trainers:
                            # Multi-trainer scenario - client has another trainer
                            current_trainer = existing_trainers[0]  # Get first active trainer
                            current_trainer_info = {
                                'trainer_id': current_trainer.get('trainer_id'),
                                'name': current_trainer.get('name') or f"{current_trainer.get('first_name', '')} {current_trainer.get('last_name', '')}".strip()
                            }

                            # Store in task data and redirect to multi-trainer handler
                            task_data['step'] = 'multi_trainer_scenario'
                            task_data['existing_client'] = client
                            task_data['current_trainer_info'] = current_trainer_info
                            task_data['multi_trainer_step'] = 'show_warning'
                            self.task_service.update_task(task['id'], 'trainer', task_data)

                            # Call the multi-trainer scenario handler
                            return self.handle_multi_trainer_scenario(
                                phone, message, client, current_trainer_info, trainer_id, task
                            )
                        else:
                            # Client exists but no trainer - ask to invite instead
                            msg = (
                                f"ℹ️ *Client Already Exists!*\n\n"
                                f"*Name:* {client.get('name')}\n"
                                f"*Client ID:* {client.get('client_id')}\n\n"
                                f"Would you like to send them an invitation instead?\n\n"
                                f"Reply *YES* to send invitation, or *NO* to cancel."
                            )
                            self.whatsapp.send_message(phone, msg)
                            task_data['step'] = 'confirm_invite_existing'
                            task_data['existing_client_id'] = client.get('client_id')
                            task_data['existing_client_phone'] = client.get('whatsapp')
                            self.task_service.update_task(task['id'], 'trainer', task_data)
                            return {'success': True, 'response': msg, 'handler': 'create_trainee_exists'}
                    
                    # Client doesn't exist - map data fields correctly and send invitation
                    # Map full_name to name for database compatibility
                    mapped_data = self._map_client_data_fields(collected_data)
                    
                    success, error_msg = self.invitation_service.send_new_client_invitation(
                        trainer_id, mapped_data, phone_number
                    )
                    
                    if success:
                        client_name = mapped_data.get('name', 'the client')
                        msg = (
                            f"✅ *Invitation Sent!*\n\n"
                            f"I've sent an invitation to *{client_name}* with all the information you provided.\n\n"
                            f"They'll receive a message to accept and complete their registration.\n\n"
                            f"I'll notify you when they respond. 🔔"
                        )
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': True, 'response': msg, 'handler': 'create_trainee_sent'}
                    else:
                        msg = f"❌ Failed to send invitation: {error_msg}"
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': False, 'response': msg, 'handler': 'create_trainee_failed'}
                
                # Ask next field with progress indicator
                next_field = fields[current_index]
                progress = f"✅ Got it! (*{current_index}/{len(fields)}*)\n\n"
                
                msg = progress + next_field['prompt']
                self.whatsapp.send_message(phone, msg)
                
                # Update task
                task_data['current_field_index'] = current_index + 1
                self.task_service.update_task(task['id'], 'trainer', task_data)

                return {'success': True, 'response': msg, 'handler': 'create_trainee'}
            """
            # ===== END OF DEPRECATED CODE =====

            # Handle confirmation for existing client
            if step == 'confirm_invite_existing':
                response = message.strip().upper()

                if response == 'YES':
                    existing_client_id = task_data.get('existing_client_id')
                    existing_client_phone = task_data.get('existing_client_phone')

                    success, error_msg = self.invitation_service.send_trainer_to_client_invitation(
                        trainer_id, existing_client_id, existing_client_phone
                    )

                    if success:
                        msg = "✅ Invitation sent! I'll notify you when they respond. 🔔"
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': True, 'response': msg, 'handler': 'create_trainee_invited_existing'}
                    else:
                        msg = f"❌ Failed to send invitation: {error_msg}"
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': False, 'response': msg, 'handler': 'create_trainee_invite_failed'}
                else:
                    msg = "❌ Cancelled. Type /create-trainee to try again."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_cancelled'}

            # Handle multi-trainer scenario steps
            if step == 'multi_trainer_scenario':
                return self.handle_multi_trainer_scenario(
                    phone, message,
                    task_data.get('client_data'),
                    task_data.get('current_trainer_info'),
                    trainer_id, task
                )
            
            return {'success': True, 'response': 'Processing...', 'handler': 'create_trainee'}
            
        except Exception as e:
            log_error(f"Error in create trainee flow: {str(e)}")
            
            # Complete the task (not stop) to ensure it's properly ended
            self.task_service.complete_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while creating the client.\n\n"
                "The task has been cancelled. Please try again with /create-trainee"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'create_trainee_error'}
    
    def _map_client_data_fields(self, collected_data: Dict) -> Dict:
        """Map config field names to database column names"""
        mapped_data = collected_data.copy()
        
        # Map full_name to name for database compatibility
        if 'full_name' in mapped_data:
            mapped_data['name'] = mapped_data.pop('full_name')
        
        # Ensure phone_number is mapped to whatsapp field
        if 'phone_number' in mapped_data:
            mapped_data['whatsapp'] = mapped_data['phone_number']
        
        return mapped_data
    
    def _validate_field_value(self, field: Dict, value: str) -> tuple:
        """Fallback validation when reg_service is not available"""
        try:
            field_type = field.get('type', 'text')
            field_name = field.get('name', 'field')
            validation = field.get('validation', {})
            
            # Basic validation
            if field.get('required', False) and not value.strip():
                return False, f"{field_name} is required"
            
            # Skip validation
            if value.lower().strip() in ['skip', 'none'] and not field.get('required', False):
                return True, ""
            
            # Phone validation
            if field_type == 'phone':
                clean_phone = value.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
                if not clean_phone.isdigit() or len(clean_phone) < 10:
                    return False, "Please enter a valid phone number with country code (e.g., 27730564882)"
            
            # Email validation
            elif field_type == 'email':
                if '@' not in value or '.' not in value.split('@')[-1]:
                    return False, "Please enter a valid email address"
            
            # Length validation
            if 'min_length' in validation and len(value) < validation['min_length']:
                return False, f"Must be at least {validation['min_length']} characters"
            
            if 'max_length' in validation and len(value) > validation['max_length']:
                return False, f"Must be no more than {validation['max_length']} characters"
            
            return True, ""
            
        except Exception as e:
            log_error(f"Error in fallback validation: {str(e)}")
            return True, ""  # Allow through if validation fails
    
    def _parse_field_value(self, field: Dict, value: str):
        """Fallback parsing when reg_service is not available"""
        try:
            field_type = field.get('type', 'text')
            
            # Skip values
            if value.lower().strip() in ['skip', 'none']:
                return None
            
            # Multi-choice fields
            if field_type in ['multi_choice', 'choice']:
                options = field.get('options', [])
                if field_type == 'multi_choice':
                    # Parse comma-separated numbers
                    try:
                        indices = [int(x.strip()) - 1 for x in value.split(',')]
                        selected = [options[i] for i in indices if 0 <= i < len(options)]
                        return ', '.join(selected) if selected else value
                    except:
                        return value
                else:
                    # Single choice
                    try:
                        index = int(value.strip()) - 1
                        return options[index] if 0 <= index < len(options) else value
                    except:
                        return value
            
            # Default: return as-is
            return value.strip()
            
        except Exception as e:
            log_error(f"Error in fallback parsing: {str(e)}")
            return value
    
    def _clean_phone_number(self, phone: str) -> str:
        """Fallback phone cleaning when reg_service is not available"""
        try:
            # Remove all non-digit characters
            clean = ''.join(filter(str.isdigit, phone))

            # Add country code if missing (assuming South Africa +27)
            if len(clean) == 10 and clean.startswith('0'):
                clean = '27' + clean[1:]
            elif len(clean) == 9:
                clean = '27' + clean

            return clean

        except Exception as e:
            log_error(f"Error cleaning phone number: {str(e)}")
            return phone

    def handle_new_client_scenario(self, trainer_phone: str, message: str,
                                   client_data: Dict, trainer_id: str, task: Dict) -> Dict:
        """
        Handle Scenario 1: Client doesn't exist in database

        Flow:
        1. Ask about pricing (default vs custom)
        2a. If default: Proceed to profile completion choice
        2b. If custom: Ask for custom price and validate
        3. Ask who fills profile (client or trainer)
        4. Store choices and branch to appropriate scenario

        Args:
            trainer_phone: Trainer's WhatsApp number
            message: User's message/button response
            client_data: Collected client information
            trainer_id: Trainer's ID
            task: Current task data

        Returns:
            Dict with success status and response details
        """
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('new_client_step', 'ask_pricing')

            # Store client_data and trainer_id in task_data for later use
            if not task_data.get('client_data'):
                task_data['client_data'] = client_data
                task_data['trainer_id'] = trainer_id

            # Step 1: Ask about pricing
            if step == 'ask_pricing':
                # Get trainer's default price
                trainer_result = self.db.table('trainers').select('pricing_per_session').eq(
                    'trainer_id', trainer_id
                ).execute()

                default_price = 300  # Fallback default
                if trainer_result.data and trainer_result.data[0].get('pricing_per_session'):
                    default_price = trainer_result.data[0]['pricing_per_session']

                # Store default price in task data
                task_data['default_price'] = default_price

                # Ask about pricing with buttons
                msg = (
                    f"💰 *Pricing Setup*\n\n"
                    f"What price per session would you like for this client?\n\n"
                    f"*Your default:* R{default_price}"
                )

                buttons = [
                    {'id': f'use_default_{default_price}', 'title': f'Use Default R{default_price}'},
                    {'id': 'custom_price', 'title': 'Custom Price'}
                ]

                self.whatsapp.send_button_message(trainer_phone, msg, buttons)

                # Update task to wait for pricing choice
                task_data['new_client_step'] = 'await_pricing_choice'
                self.task_service.update_task(task['id'], 'trainer', task_data)

                return {'success': True, 'response': msg, 'handler': 'new_client_pricing'}

            # Step 2a: Handle default price choice
            elif step == 'await_pricing_choice':
                choice = message.strip()

                if choice.startswith('use_default_'):
                    # Use default price
                    default_price = task_data.get('default_price', 300)
                    task_data['selected_price'] = default_price
                    task_data['new_client_step'] = 'ask_profile_completion'
                    self.task_service.update_task(task['id'], 'trainer', task_data)

                    # Proceed to profile completion choice
                    return self._ask_profile_completion(trainer_phone, task, task_data)

                elif choice == 'custom_price':
                    # Ask for custom price
                    msg = (
                        "💰 *Custom Price*\n\n"
                        "What's your price per session for this client?\n\n"
                        "Please enter the amount in Rands (e.g., 350)"
                    )
                    self.whatsapp.send_message(trainer_phone, msg)

                    task_data['new_client_step'] = 'await_custom_price'
                    self.task_service.update_task(task['id'], 'trainer', task_data)

                    return {'success': True, 'response': msg, 'handler': 'new_client_custom_price'}

                else:
                    # Invalid choice
                    msg = "❌ Invalid choice. Please use the buttons provided."
                    self.whatsapp.send_message(trainer_phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'new_client_invalid_choice'}

            # Step 2b: Handle custom price input
            elif step == 'await_custom_price':
                # Validate price input using comprehensive validator
                validator = get_validator()
                is_valid, error_msg, custom_price = validator.validate_price(message, trainer_phone)

                if not is_valid:
                    # Check for max retries
                    if validator.has_exceeded_max_retries(trainer_phone, 'price'):
                        restart_msg = validator.get_restart_prompt('price')
                        self.whatsapp.send_message(trainer_phone, restart_msg)
                        return {'success': True, 'response': restart_msg, 'handler': 'new_client_max_retries'}

                    # Send validation error
                    self.whatsapp.send_message(trainer_phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'new_client_invalid_price'}

                # Store custom price
                task_data['selected_price'] = custom_price
                task_data['new_client_step'] = 'ask_profile_completion'
                self.task_service.update_task(task['id'], 'trainer', task_data)

                # Proceed to profile completion choice
                return self._ask_profile_completion(trainer_phone, task, task_data)

            # Step 3: Handle profile completion choice
            elif step == 'await_profile_completion_choice':
                choice = message.strip()

                if choice == 'client_fills':
                    # Client fills details (Scenario 1A)
                    task_data['profile_completion_by'] = 'client'
                    task_data['new_client_step'] = 'scenario_1a'

                    # Add pricing to client_data for invitation
                    stored_client_data = task_data.get('client_data', client_data)
                    pricing_info = {
                        'custom_price': task_data.get('selected_price'),
                        'is_default': task_data.get('selected_price') == task_data.get('default_price')
                    }

                    self.task_service.update_task(task['id'], 'trainer', task_data)

                    # Send client completion invitation
                    success, error_msg = self.send_client_completion_invitation(
                        trainer_phone, trainer_id, stored_client_data, pricing_info
                    )

                    if success:
                        msg = (
                            "✅ *Invitation Sent!*\n\n"
                            f"I've sent an invitation to *{stored_client_data.get('name')}* to complete their fitness profile.\n\n"
                            f"📋 *What happens next:*\n"
                            f"• Client receives WhatsApp Flow to fill fitness details\n"
                            f"• Pricing: R{task_data.get('selected_price', 0)} per session\n"
                            f"• They can accept or decline the invitation\n\n"
                            f"I'll notify you when they respond. 🔔"
                        )
                        self.whatsapp.send_message(trainer_phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': True, 'response': msg, 'handler': 'new_client_scenario_1a_sent'}
                    else:
                        msg = f"❌ Failed to send invitation: {error_msg}"
                        self.whatsapp.send_message(trainer_phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': False, 'response': msg, 'handler': 'new_client_scenario_1a_failed'}

                elif choice == 'trainer_fills':
                    # Trainer fills details (Scenario 1B)
                    task_data['profile_completion_by'] = 'trainer'
                    task_data['new_client_step'] = 'scenario_1b'

                    # Add pricing to client_data for later use
                    stored_client_data = task_data.get('client_data', client_data)
                    stored_client_data['custom_price_per_session'] = task_data.get('selected_price')
                    task_data['client_data'] = stored_client_data

                    self.task_service.update_task(task['id'], 'trainer', task_data)

                    # TODO: Branch to Scenario 1B handler
                    # This should:
                    # - Ask trainer to populate fitness profile fields
                    # - Collect: fitness_goals, experience_level, health_conditions, etc.
                    # - Create complete client record with pricing
                    # - Send final invitation for client to accept
                    msg = (
                        "✅ *Great!*\n\n"
                        f"You'll populate the client's fitness details now.\n\n"
                        f"📋 *Next Steps:*\n"
                        f"I'll ask you questions about the client's:\n"
                        f"• Fitness goals\n"
                        f"• Experience level\n"
                        f"• Health conditions\n"
                        f"• And more...\n\n"
                        f"_Coming soon: Scenario 1B implementation_"
                    )
                    self.whatsapp.send_message(trainer_phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')

                    return {'success': True, 'response': msg, 'handler': 'new_client_scenario_1b'}

                else:
                    # Invalid choice
                    msg = "❌ Invalid choice. Please use the buttons provided."
                    self.whatsapp.send_message(trainer_phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'new_client_invalid_choice'}

            return {'success': True, 'response': 'Processing...', 'handler': 'new_client_scenario'}

        except Exception as e:
            log_error(f"Error in handle_new_client_scenario: {str(e)}")

            # Complete the task
            self.task_service.complete_task(task['id'], 'trainer')

            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while processing the new client setup.\n\n"
                "Please try again with /create-trainee"
            )
            self.whatsapp.send_message(trainer_phone, error_msg)

            return {'success': False, 'response': error_msg, 'handler': 'new_client_error'}

    def _ask_profile_completion(self, trainer_phone: str, task: Dict, task_data: Dict) -> Dict:
        """Ask who should populate the fitness profile details"""
        try:
            selected_price = task_data.get('selected_price', 0)

            msg = (
                f"✅ *Price Set: R{selected_price}*\n\n"
                f"👤 *Profile Completion*\n\n"
                f"Who should populate the client's fitness details?\n\n"
                f"• *Client Fills Details:* Client completes their own fitness profile\n"
                f"• *I'll Fill Details:* You complete the profile for them"
            )

            buttons = [
                {'id': 'client_fills', 'title': 'Client Fills Details'},
                {'id': 'trainer_fills', 'title': "I'll Fill Details"}
            ]

            self.whatsapp.send_button_message(trainer_phone, msg, buttons)

            # Update task to wait for profile completion choice
            task_data['new_client_step'] = 'await_profile_completion_choice'
            self.task_service.update_task(task['id'], 'trainer', task_data)

            return {'success': True, 'response': msg, 'handler': 'new_client_profile_completion'}

        except Exception as e:
            log_error(f"Error in _ask_profile_completion: {str(e)}")
            return {'success': False, 'response': str(e), 'handler': 'profile_completion_error'}

    def send_client_completion_invitation(self, trainer_phone: str, trainer_id: str,
                                         client_data: Dict, pricing_info: Dict) -> tuple:
        """
        Send invitation to client to complete their fitness profile via WhatsApp Flow (Scenario 1A)

        Args:
            trainer_phone: Trainer's WhatsApp number
            trainer_id: Trainer's ID
            client_data: Client's basic info (name, phone, email)
            pricing_info: Dict with custom_price and is_default flag

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            from datetime import datetime
            import pytz

            sa_tz = pytz.timezone('Africa/Johannesburg')

            # Get trainer info
            trainer_result = self.db.table('trainers').select('*').eq(
                'trainer_id', trainer_id
            ).execute()

            if not trainer_result.data:
                return False, "Trainer not found"

            trainer = trainer_result.data[0]
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()

            # Clean client phone number
            client_phone = client_data.get('phone_number')
            if self.reg_service:
                client_phone = self.reg_service.clean_phone_number(client_phone)
            else:
                client_phone = self._clean_phone_number(client_phone)

            # Generate invitation token
            invitation_token = self.invitation_service.generate_invitation_token()

            # Store invitation in database with pending_client_completion status
            invitation_data = {
                'trainer_id': trainer['id'],  # UUID
                'client_phone': client_phone,
                'client_name': client_data.get('name'),
                'client_email': client_data.get('email') if client_data.get('email') and client_data.get('email').lower() not in ['skip', 'none'] else None,
                'invitation_token': invitation_token,
                'status': 'pending_client_completion',
                'profile_completion_method': 'client_fills',
                'custom_price_per_session': pricing_info.get('custom_price'),
                'prefilled_data': client_data,  # Store complete client data as JSONB
                'created_at': datetime.now(sa_tz).isoformat(),
                'updated_at': datetime.now(sa_tz).isoformat()
            }

            # Insert or update invitation
            existing = self.db.table('client_invitations').select('id').eq(
                'client_phone', client_phone
            ).eq('trainer_id', trainer['id']).eq('status', 'pending_client_completion').execute()

            if existing.data:
                # Update existing invitation
                self.db.table('client_invitations').update(invitation_data).eq(
                    'id', existing.data[0]['id']
                ).execute()
                log_info(f"Updated existing invitation for {client_phone}")
            else:
                # Create new invitation
                result = self.db.table('client_invitations').insert(invitation_data).execute()
                log_info(f"Created new invitation for {client_phone}")

            # Send WhatsApp Flow invitation
            success = self._send_client_onboarding_flow(
                client_phone,
                client_data.get('name'),
                trainer_name,
                trainer_id,
                pricing_info.get('custom_price'),
                invitation_token
            )

            if success:
                log_info(f"Sent client completion invitation to {client_phone} from trainer {trainer_id}")
                return True, "Invitation sent successfully"
            else:
                return False, "Failed to send WhatsApp Flow invitation"

        except Exception as e:
            log_error(f"Error sending client completion invitation: {str(e)}")
            return False, str(e)

    def _send_client_onboarding_flow(self, client_phone: str, client_name: str,
                                    trainer_name: str, trainer_id: str,
                                    price_per_session: float, invitation_token: str) -> bool:
        """
        Send WhatsApp Flow invitation to client

        Args:
            client_phone: Client's WhatsApp number
            client_name: Client's name
            trainer_name: Trainer's name
            trainer_id: Trainer's ID
            price_per_session: Price per session
            invitation_token: Unique invitation token

        Returns:
            bool: Success status
        """
        try:
            import os
            from datetime import datetime

            # Create invitation message
            message_text = (
                f"🎯 *Training Invitation from {trainer_name}*\n\n"
                f"Hi {client_name}! 👋\n\n"
                f"{trainer_name} has invited you to start your fitness journey together!\n\n"
                f"📋 *Training Details:*\n"
                f"• Trainer: {trainer_name}\n"
                f"• Price per session: R{price_per_session}\n\n"
                f"Complete your fitness profile to get started, or decline if you're not interested."
            )

            # Get flow ID from environment or use placeholder
            # Note: This needs to be the actual Facebook-approved flow ID
            flow_id = os.getenv('CLIENT_ONBOARDING_FLOW_ID', '1234567890')  # TODO: Replace with actual flow ID

            # Generate flow token
            flow_token = f"client_invitation_{invitation_token}_{int(datetime.now().timestamp())}"

            # Create flow message payload
            flow_message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": client_phone,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": f"Invitation from {trainer_name}"
                    },
                    "body": {
                        "text": message_text
                    },
                    "footer": {
                        "text": "Powered by Refiloe AI"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": flow_id,
                            "flow_cta": "Complete Profile",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "WELCOME"
                            }
                        }
                    }
                }
            }

            # Try to send flow first
            result = self.whatsapp.send_flow_message(flow_message)

            if result.get('success'):
                log_info(f"Successfully sent flow invitation to {client_phone}")
                return True
            else:
                # Fallback to buttons if flow fails
                log_warning(f"Flow sending failed, using button fallback: {result.get('error')}")

                fallback_msg = (
                    f"🎯 *Training Invitation from {trainer_name}*\n\n"
                    f"Hi {client_name}! 👋\n\n"
                    f"{trainer_name} has invited you to start your fitness journey together!\n\n"
                    f"📋 *Training Details:*\n"
                    f"• Trainer: {trainer_name}\n"
                    f"• Price per session: R{price_per_session}\n\n"
                    f"Would you like to accept this invitation?"
                )

                buttons = [
                    {'id': f'accept_invitation_{trainer_id}', 'title': '✅ Accept'},
                    {'id': f'decline_invitation_{trainer_id}', 'title': '❌ Decline'}
                ]

                self.whatsapp.send_button_message(client_phone, fallback_msg, buttons)
                return True

        except Exception as e:
            log_error(f"Error sending client onboarding flow: {str(e)}")
            return False

    def handle_multi_trainer_scenario(self, trainer_phone: str, message: str,
                                      client_data: Dict, current_trainer_info: Dict,
                                      trainer_id: str, task: Dict) -> Dict:
        """
        Handle Scenario 4: Client exists and trains with a different trainer

        Flow:
        1. Show warning message with client and current trainer info (NO pricing)
        2. Buttons: [Send Invitation Anyway] [Cancel]
        3. If send anyway:
           - Ask about pricing (default vs custom)
           - Ask who fills profile details
           - Send invitation to client with note about multiple trainers
           - Create secondary trainer relationship (not primary)
           - Notify both trainers appropriately

        Args:
            trainer_phone: Trainer's WhatsApp number
            message: User's message/button response
            client_data: Existing client information
            current_trainer_info: Dict with current trainer's ID and name
            trainer_id: New trainer's ID
            task: Current task data

        Returns:
            Dict with success status and response details
        """
        try:
            task_data = task.get('task_data', {})
            multi_trainer_step = task_data.get('multi_trainer_step', 'show_warning')

            # Store necessary data in task_data
            if not task_data.get('client_data'):
                task_data['client_data'] = client_data
            if not task_data.get('current_trainer_info'):
                task_data['current_trainer_info'] = current_trainer_info
            if not task_data.get('trainer_id'):
                task_data['trainer_id'] = trainer_id

            # Step 1: Show warning message
            if multi_trainer_step == 'show_warning':
                client_name = client_data.get('name', 'Unknown')
                current_trainer_name = current_trainer_info.get('name', 'Unknown Trainer')

                msg = (
                    f"⚠️ *Client Has Another Trainer*\n\n"
                    f"*Client:* {client_name}\n"
                    f"*Current Trainer:* {current_trainer_name}\n\n"
                    f"ℹ️ *Good News:* Clients can train with multiple trainers on Refiloe!\n\n"
                    f"If you send an invitation, they'll be able to work with both of you.\n\n"
                    f"Would you like to proceed?"
                )

                buttons = [
                    {'id': 'send_invitation_anyway', 'title': 'Send Invitation Anyway'},
                    {'id': 'cancel_multi_trainer', 'title': 'Cancel'}
                ]

                self.whatsapp.send_button_message(trainer_phone, msg, buttons)

                # Update task to wait for choice
                task_data['multi_trainer_step'] = 'await_send_choice'
                self.task_service.update_task(task['id'], 'trainer', task_data)

                return {'success': True, 'response': msg, 'handler': 'multi_trainer_warning'}

            # Step 2: Handle send/cancel choice
            elif multi_trainer_step == 'await_send_choice':
                choice = message.strip()

                if choice == 'send_invitation_anyway':
                    # Proceed to pricing setup
                    task_data['multi_trainer_step'] = 'ask_pricing'
                    self.task_service.update_task(task['id'], 'trainer', task_data)

                    # Ask about pricing (reuse the same logic as new client scenario)
                    return self._ask_multi_trainer_pricing(trainer_phone, task, task_data, trainer_id)

                elif choice == 'cancel_multi_trainer':
                    msg = "❌ Cancelled. No invitation was sent."
                    self.whatsapp.send_message(trainer_phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'multi_trainer_cancelled'}

                else:
                    msg = "❌ Invalid choice. Please use the buttons provided."
                    self.whatsapp.send_message(trainer_phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'multi_trainer_invalid_choice'}

            # Step 3: Handle pricing choice
            elif multi_trainer_step == 'await_pricing_choice':
                choice = message.strip()

                if choice.startswith('use_default_'):
                    # Use default price
                    default_price = task_data.get('default_price', 300)
                    task_data['selected_price'] = default_price
                    task_data['multi_trainer_step'] = 'ask_profile_completion'
                    self.task_service.update_task(task['id'], 'trainer', task_data)

                    # Proceed to profile completion choice
                    return self._ask_multi_trainer_profile_completion(trainer_phone, task, task_data)

                elif choice == 'custom_price':
                    # Ask for custom price
                    msg = (
                        "💰 *Custom Price*\n\n"
                        "What's your price per session for this client?\n\n"
                        "Please enter the amount in Rands (e.g., 350)"
                    )
                    self.whatsapp.send_message(trainer_phone, msg)

                    task_data['multi_trainer_step'] = 'await_custom_price'
                    self.task_service.update_task(task['id'], 'trainer', task_data)

                    return {'success': True, 'response': msg, 'handler': 'multi_trainer_custom_price'}

                else:
                    msg = "❌ Invalid choice. Please use the buttons provided."
                    self.whatsapp.send_message(trainer_phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'multi_trainer_invalid_pricing'}

            # Step 4: Handle custom price input
            elif multi_trainer_step == 'await_custom_price':
                # Validate price input using comprehensive validator
                validator = get_validator()
                is_valid, error_msg, custom_price = validator.validate_price(message, trainer_phone)

                if not is_valid:
                    # Check for max retries
                    if validator.has_exceeded_max_retries(trainer_phone, 'price'):
                        restart_msg = validator.get_restart_prompt('price')
                        self.whatsapp.send_message(trainer_phone, restart_msg)
                        return {'success': True, 'response': restart_msg, 'handler': 'multi_trainer_max_retries'}

                    # Send validation error
                    self.whatsapp.send_message(trainer_phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'multi_trainer_invalid_price'}

                # Store custom price
                task_data['selected_price'] = custom_price
                task_data['multi_trainer_step'] = 'ask_profile_completion'
                self.task_service.update_task(task['id'], 'trainer', task_data)

                # Proceed to profile completion choice
                return self._ask_multi_trainer_profile_completion(trainer_phone, task, task_data)

            # Step 5: Handle profile completion choice
            elif multi_trainer_step == 'await_profile_completion_choice':
                choice = message.strip()

                if choice == 'client_fills':
                    # Client fills details - send invitation
                    return self._send_multi_trainer_invitation(
                        trainer_phone, task, task_data, 'client_fills'
                    )

                elif choice == 'trainer_fills':
                    # Trainer fills details
                    msg = (
                        "✅ *Great!*\n\n"
                        f"You'll populate additional training details for this client.\n\n"
                        f"📋 *Note:* The client already has a profile. "
                        f"You're setting up your own training plan with them.\n\n"
                        f"_This feature is coming soon. For now, sending invitation..._"
                    )
                    self.whatsapp.send_message(trainer_phone, msg)

                    # For now, just send the invitation
                    return self._send_multi_trainer_invitation(
                        trainer_phone, task, task_data, 'trainer_fills'
                    )

                else:
                    msg = "❌ Invalid choice. Please use the buttons provided."
                    self.whatsapp.send_message(trainer_phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'multi_trainer_invalid_profile_choice'}

            return {'success': True, 'response': 'Processing...', 'handler': 'multi_trainer_scenario'}

        except Exception as e:
            log_error(f"Error in handle_multi_trainer_scenario: {str(e)}")

            # Complete the task
            self.task_service.complete_task(task['id'], 'trainer')

            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while processing the multi-trainer setup.\n\n"
                "Please try again with /create-trainee"
            )
            self.whatsapp.send_message(trainer_phone, error_msg)

            return {'success': False, 'response': error_msg, 'handler': 'multi_trainer_error'}

    def _ask_multi_trainer_pricing(self, trainer_phone: str, task: Dict,
                                   task_data: Dict, trainer_id: str) -> Dict:
        """Ask about pricing for multi-trainer scenario"""
        try:
            # Get trainer's default price
            trainer_result = self.db.table('trainers').select('pricing_per_session').eq(
                'trainer_id', trainer_id
            ).execute()

            default_price = 300  # Fallback default
            if trainer_result.data and trainer_result.data[0].get('pricing_per_session'):
                default_price = trainer_result.data[0]['pricing_per_session']

            # Store default price in task data
            task_data['default_price'] = default_price

            # Ask about pricing with buttons
            msg = (
                f"💰 *Pricing Setup*\n\n"
                f"What price per session would you like for this client?\n\n"
                f"*Your default:* R{default_price}"
            )

            buttons = [
                {'id': f'use_default_{default_price}', 'title': f'Use Default R{default_price}'},
                {'id': 'custom_price', 'title': 'Custom Price'}
            ]

            self.whatsapp.send_button_message(trainer_phone, msg, buttons)

            # Update task to wait for pricing choice
            task_data['multi_trainer_step'] = 'await_pricing_choice'
            self.task_service.update_task(task['id'], 'trainer', task_data)

            return {'success': True, 'response': msg, 'handler': 'multi_trainer_pricing'}

        except Exception as e:
            log_error(f"Error in _ask_multi_trainer_pricing: {str(e)}")
            return {'success': False, 'response': str(e), 'handler': 'multi_trainer_pricing_error'}

    def _ask_multi_trainer_profile_completion(self, trainer_phone: str,
                                             task: Dict, task_data: Dict) -> Dict:
        """Ask who should populate the profile details for multi-trainer scenario"""
        try:
            selected_price = task_data.get('selected_price', 0)

            msg = (
                f"✅ *Price Set: R{selected_price}*\n\n"
                f"👤 *Profile Details*\n\n"
                f"The client already has a profile. Who should populate YOUR specific training details?\n\n"
                f"• *Client Fills Details:* Client completes training preferences for you\n"
                f"• *I'll Fill Details:* You set up your own training plan for them"
            )

            buttons = [
                {'id': 'client_fills', 'title': 'Client Fills Details'},
                {'id': 'trainer_fills', 'title': "I'll Fill Details"}
            ]

            self.whatsapp.send_button_message(trainer_phone, msg, buttons)

            # Update task to wait for profile completion choice
            task_data['multi_trainer_step'] = 'await_profile_completion_choice'
            self.task_service.update_task(task['id'], 'trainer', task_data)

            return {'success': True, 'response': msg, 'handler': 'multi_trainer_profile_completion'}

        except Exception as e:
            log_error(f"Error in _ask_multi_trainer_profile_completion: {str(e)}")
            return {'success': False, 'response': str(e), 'handler': 'multi_trainer_profile_error'}

    def _send_multi_trainer_invitation(self, trainer_phone: str, task: Dict,
                                      task_data: Dict, completion_method: str) -> Dict:
        """Send multi-trainer invitation and create secondary relationship"""
        try:
            from datetime import datetime
            import pytz

            sa_tz = pytz.timezone('Africa/Johannesburg')

            # Get stored data
            client_data = task_data.get('client_data', {})
            current_trainer_info = task_data.get('current_trainer_info', {})
            trainer_id = task_data.get('trainer_id')
            selected_price = task_data.get('selected_price', 300)

            # Get trainer info
            trainer_result = self.db.table('trainers').select('*').eq(
                'trainer_id', trainer_id
            ).execute()

            if not trainer_result.data:
                return False, "Trainer not found"

            trainer = trainer_result.data[0]
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()

            # Get client phone
            client_id = client_data.get('client_id')
            client_phone = client_data.get('whatsapp')
            client_name = client_data.get('name', 'there')

            # Generate invitation token
            invitation_token = self.invitation_service.generate_invitation_token()

            # Store invitation in database with multi-trainer flag
            invitation_data = {
                'trainer_id': trainer['id'],  # UUID
                'client_phone': client_phone,
                'client_name': client_name,
                'invitation_token': invitation_token,
                'status': 'pending',
                'profile_completion_method': completion_method,
                'custom_price_per_session': selected_price,
                'is_secondary_trainer': True,  # Mark as secondary trainer
                'created_at': datetime.now(sa_tz).isoformat(),
                'updated_at': datetime.now(sa_tz).isoformat()
            }

            # Insert invitation
            self.db.table('client_invitations').insert(invitation_data).execute()

            # Send invitation to client with multi-trainer note
            message = (
                f"🎯 *New Training Invitation*\n\n"
                f"Hi {client_name}! 👋\n\n"
                f"*{trainer_name}* has invited you to train together!\n\n"
                f"📋 *Training Details:*\n"
                f"• Trainer: {trainer_name}\n"
                f"• Price per session: R{selected_price}\n\n"
                f"✨ *Multi-Trainer Setup:*\n"
                f"You can accept this invitation and train with {trainer_name} "
                f"while continuing with your current trainer.\n\n"
                f"Would you like to accept?"
            )

            buttons = [
                {'id': f'accept_multi_trainer_{trainer_id}', 'title': '✅ Accept'},
                {'id': f'decline_multi_trainer_{trainer_id}', 'title': '❌ Decline'}
            ]

            self.whatsapp.send_button_message(client_phone, message, buttons)

            # Create secondary relationship (pending status, not primary)
            relationship_success, relationship_msg = self.invitation_service.create_relationship(
                trainer_id, client_id, 'trainer', invitation_token
            )

            if not relationship_success:
                log_error(f"Failed to create secondary relationship: {relationship_msg}")

            # Notify the new trainer
            msg_to_new_trainer = (
                f"✅ *Invitation Sent!*\n\n"
                f"I've sent a multi-trainer invitation to *{client_name}*.\n\n"
                f"📋 *Details:*\n"
                f"• Price per session: R{selected_price}\n"
                f"• Profile completion: {completion_method.replace('_', ' ').title()}\n"
                f"• Current trainer: {current_trainer_info.get('name')}\n\n"
                f"I'll notify you when they respond. 🔔"
            )
            self.whatsapp.send_message(trainer_phone, msg_to_new_trainer)

            # Notify the original trainer
            current_trainer_id = current_trainer_info.get('trainer_id')
            current_trainer_result = self.db.table('trainers').select('whatsapp').eq(
                'trainer_id', current_trainer_id
            ).execute()

            if current_trainer_result.data:
                current_trainer_phone = current_trainer_result.data[0].get('whatsapp')
                if current_trainer_phone:
                    msg_to_current_trainer = (
                        f"ℹ️ *Client Update*\n\n"
                        f"FYI: *{client_name}* is now also training with *{trainer_name}*.\n\n"
                        f"This doesn't affect your relationship with {client_name}. "
                        f"They can train with multiple trainers on Refiloe!"
                    )
                    self.whatsapp.send_message(current_trainer_phone, msg_to_current_trainer)
                    log_info(f"Notified current trainer {current_trainer_id} about multi-trainer setup")

            # Complete the task
            self.task_service.complete_task(task['id'], 'trainer')

            log_info(f"Sent multi-trainer invitation from {trainer_id} to {client_id}")
            return {'success': True, 'response': msg_to_new_trainer, 'handler': 'multi_trainer_sent'}

        except Exception as e:
            log_error(f"Error sending multi-trainer invitation: {str(e)}")

            # Complete the task
            self.task_service.complete_task(task['id'], 'trainer')

            error_msg = f"❌ Failed to send invitation: {str(e)}"
            self.whatsapp.send_message(trainer_phone, error_msg)

            return {'success': False, 'response': error_msg, 'handler': 'multi_trainer_send_failed'}
