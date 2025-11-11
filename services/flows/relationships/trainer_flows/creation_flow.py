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
                            # Client exists - check if relationship already exists
                            client = existing_client.data[0]
                            client_id = client.get('client_id')

                            # Check for existing relationship (Scenario 3)
                            existing_relationship = self.relationship_service.check_relationship_exists(trainer_id, client_id)

                            if existing_relationship:
                                # Scenario 3: Already this trainer's client
                                self.task_service.complete_task(task['id'], 'trainer')
                                return self.handle_existing_client_scenario(
                                    phone, client, trainer_id, existing_relationship
                                )

                            # Scenario 2: Client exists but not connected - ask to invite instead
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
                        # Client exists - check if relationship already exists
                        client = existing_client.data[0]
                        client_id = client.get('client_id')

                        # Check for existing relationship (Scenario 3)
                        existing_relationship = self.relationship_service.check_relationship_exists(trainer_id, client_id)

                        if existing_relationship:
                            # Scenario 3: Already this trainer's client
                            self.task_service.complete_task(task['id'], 'trainer')
                            return self.handle_existing_client_scenario(
                                phone, client, trainer_id, existing_relationship
                            )

                        # Scenario 2: Client exists but not connected - ask to invite instead
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

    def handle_existing_client_scenario(self, trainer_phone: str, client_data: Dict,
                                       trainer_id: str, relationship_data: Dict) -> Dict:
        """
        Handle Scenario 3: Client is already this trainer's active client

        Shows helpful information about the existing relationship and offers actions:
        - View Full Profile
        - Schedule Session
        - Nothing, Thanks

        Args:
            trainer_phone: Trainer's WhatsApp number
            client_data: Client information from database
            trainer_id: Trainer's ID
            relationship_data: Existing relationship data

        Returns:
            Dict with success status and response details
        """
        try:
            # Get client details
            client_name = client_data.get('name', 'Your Client')
            client_id = client_data.get('client_id')
            relationship_status = relationship_data.get('connection_status', 'active')

            # Get session statistics
            sessions_completed = self._get_completed_sessions_count(trainer_id, client_id)
            next_session = self._get_next_scheduled_session(trainer_id, client_id)

            # Build message
            msg = f"😊 *Already Your Client!*\n\n"
            msg += f"*Name:* {client_name}\n"
            msg += f"*Status:* {relationship_status.title()}\n"

            # Add session info if available
            if sessions_completed > 0:
                msg += f"*Sessions Completed:* {sessions_completed}\n"

            if next_session:
                session_date = next_session.get('session_date')
                session_time = next_session.get('session_time', 'TBD')
                msg += f"*Next Session:* {session_date} at {session_time}\n"

            msg += f"\n*What would you like to do?*"

            # Create action buttons
            buttons = [
                {'id': f'view_client_profile_{client_id}', 'title': 'View Full Profile'},
                {'id': f'schedule_session_{client_id}', 'title': 'Schedule Session'},
                {'id': 'nothing_thanks', 'title': 'Nothing, Thanks'}
            ]

            self.whatsapp.send_button_message(trainer_phone, msg, buttons)

            log_info(f"Showed existing client scenario for {client_id} to trainer {trainer_id}")
            return {'success': True, 'response': msg, 'handler': 'existing_client_scenario'}

        except Exception as e:
            log_error(f"Error in handle_existing_client_scenario: {str(e)}")

            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while retrieving the client information."
            )
            self.whatsapp.send_message(trainer_phone, error_msg)

            return {'success': False, 'response': error_msg, 'handler': 'existing_client_error'}

    def _get_completed_sessions_count(self, trainer_id: str, client_id: str) -> int:
        """
        Get count of completed sessions for a trainer-client relationship

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID

        Returns:
            int: Number of completed sessions
        """
        try:
            result = self.db.table('bookings').select('id').eq(
                'trainer_id', trainer_id
            ).eq('client_id', client_id).eq('status', 'completed').execute()

            return len(result.data) if result.data else 0

        except Exception as e:
            log_error(f"Error getting completed sessions count: {str(e)}")
            return 0

    def _get_next_scheduled_session(self, trainer_id: str, client_id: str) -> Dict:
        """
        Get the next scheduled session for a trainer-client relationship

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID

        Returns:
            Dict: Next session data or None if no upcoming sessions
        """
        try:
            from datetime import datetime
            import pytz

            sa_tz = pytz.timezone('Africa/Johannesburg')
            today = datetime.now(sa_tz).date().isoformat()

            # Get upcoming sessions ordered by date
            result = self.db.table('bookings').select('*').eq(
                'trainer_id', trainer_id
            ).eq('client_id', client_id).gte(
                'session_date', today
            ).in_('status', ['scheduled', 'confirmed']).order(
                'session_date', desc=False
            ).limit(1).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]

            return None

        except Exception as e:
            log_error(f"Error getting next scheduled session: {str(e)}")
            return None