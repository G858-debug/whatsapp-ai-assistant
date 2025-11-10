"""
Trainer Client Creation Flow
Handles trainer creating new client accounts
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.relationships import RelationshipService, InvitationService
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
                    # Create new client - load fields (use trainer_add_client config)
                    with open('config/trainer_add_client_inputs.json', 'r') as f:
                        config = json.load(f)
                        task_data['fields'] = config['fields']
                        task_data['current_field_index'] = 0
                        task_data['step'] = 'collecting'
                        task_data['mode'] = 'create_new'
                    
                    fields = task_data['fields']
                    
                    # Send intro message
                    intro_msg = (
                        "✅ *Create New Client*\n\n"
                        f"I'll ask you *{len(fields)} questions* to create a client profile.\n\n"
                        f"📝 *Note:* You'll provide the client's information, then they'll receive an invitation to accept.\n\n"
                        f"💡 *Tip:* Type /stop at any time to cancel\n\n"
                        f"Let's start! 👇"
                    )
                    self.whatsapp.send_message(phone, intro_msg)
                    
                    # Send first field
                    first_field = fields[0]
                    self.whatsapp.send_message(phone, first_field['prompt'])
                    
                    task_data['current_field_index'] = 1
                    self.task_service.update_task(task['id'], 'trainer', task_data)
                    
                    return {'success': True, 'response': first_field['prompt'], 'handler': 'create_trainee_new'}
                
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
            
            # Step 2: Collect fields for new client
            if step == 'collecting':
                fields = task_data.get('fields', [])
                current_index = task_data.get('current_field_index', 0)
                
                # Validate and store previous answer
                if current_index > 0:
                    prev_field = fields[current_index - 1]
                    field_name = prev_field['name']
                    
                    # Use registration service for validation (with fallback)
                    if self.reg_service:
                        is_valid, error_msg = self.reg_service.validate_field_value(prev_field, message)
                        
                        if not is_valid:
                            error_response = f"❌ {error_msg}\n\n{prev_field['prompt']}"
                            self.whatsapp.send_message(phone, error_response)
                            return {'success': True, 'response': error_response, 'handler': 'create_trainee_validation_error'}
                        
                        # Parse and store value
                        parsed_value = self.reg_service.parse_field_value(prev_field, message)
                    else:
                        # Fallback validation when reg_service is not available
                        is_valid, error_msg = self._validate_field_value(prev_field, message)
                        
                        if not is_valid:
                            error_response = f"❌ {error_msg}\n\n{prev_field['prompt']}"
                            self.whatsapp.send_message(phone, error_response)
                            return {'success': True, 'response': error_response, 'handler': 'create_trainee_validation_error'}
                        
                        # Parse and store value
                        parsed_value = self._parse_field_value(prev_field, message)
                    
                    collected_data[field_name] = parsed_value
                    task_data['collected_data'] = collected_data
                    
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
                            # Client exists - ask to invite instead
                            client = existing_client.data[0]
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
                        # Client exists - ask to invite instead
                        client = existing_client.data[0]
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
                # Validate price input
                try:
                    # Remove 'R' and whitespace if present
                    price_str = message.strip().replace('R', '').replace('r', '').strip()
                    custom_price = float(price_str)

                    if custom_price <= 0:
                        msg = (
                            "❌ *Invalid Price*\n\n"
                            "Price must be a positive number.\n\n"
                            "Please enter the amount in Rands (e.g., 350)"
                        )
                        self.whatsapp.send_message(trainer_phone, msg)
                        return {'success': True, 'response': msg, 'handler': 'new_client_invalid_price'}

                    # Store custom price
                    task_data['selected_price'] = custom_price
                    task_data['new_client_step'] = 'ask_profile_completion'
                    self.task_service.update_task(task['id'], 'trainer', task_data)

                    # Proceed to profile completion choice
                    return self._ask_profile_completion(trainer_phone, task, task_data)

                except ValueError:
                    msg = (
                        "❌ *Invalid Format*\n\n"
                        "Please enter a valid number (e.g., 350)"
                    )
                    self.whatsapp.send_message(trainer_phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'new_client_invalid_format'}

            # Step 3: Handle profile completion choice
            elif step == 'await_profile_completion_choice':
                choice = message.strip()

                if choice == 'client_fills':
                    # Client fills details (Scenario 1A)
                    task_data['profile_completion_by'] = 'client'
                    task_data['new_client_step'] = 'scenario_1a'

                    # Add pricing to client_data for invitation
                    stored_client_data = task_data.get('client_data', client_data)
                    stored_client_data['custom_price_per_session'] = task_data.get('selected_price')
                    task_data['client_data'] = stored_client_data

                    self.task_service.update_task(task['id'], 'trainer', task_data)

                    # TODO: Branch to Scenario 1A handler
                    # This should send an invitation to the client with:
                    # - Basic info already collected (name, phone, email)
                    # - Custom price set
                    # - Request to complete fitness profile (goals, experience, etc.)
                    msg = (
                        "✅ *Great!*\n\n"
                        f"The client will receive an invitation to fill in their fitness details.\n\n"
                        f"📋 *Next Steps:*\n"
                        f"I'll send them an invitation with:\n"
                        f"• Pricing: R{task_data.get('selected_price', 0)} per session\n"
                        f"• Request to complete their profile\n\n"
                        f"_Coming soon: Scenario 1A implementation_"
                    )
                    self.whatsapp.send_message(trainer_phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')

                    return {'success': True, 'response': msg, 'handler': 'new_client_scenario_1a'}

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
                    # - Ask trainer to fill in fitness profile fields
                    # - Collect: fitness_goals, experience_level, health_conditions, etc.
                    # - Create complete client record with pricing
                    # - Send final invitation for client to accept
                    msg = (
                        "✅ *Great!*\n\n"
                        f"You'll fill in the client's fitness details now.\n\n"
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
        """Ask who should fill in the fitness profile details"""
        try:
            selected_price = task_data.get('selected_price', 0)

            msg = (
                f"✅ *Price Set: R{selected_price}*\n\n"
                f"👤 *Profile Completion*\n\n"
                f"Who should fill in the client's fitness details?\n\n"
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