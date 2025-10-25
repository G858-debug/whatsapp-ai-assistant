"""
Trainer Relationship Flow Handlers - Phase 2
Handles multi-step flows for trainer relationship management
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.relationships import RelationshipService, InvitationService
import json


class TrainerRelationshipFlows:
    """Handles trainer relationship flows"""
    
    def __init__(self, db, whatsapp, task_service, reg_service=None):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.reg_service = reg_service
        self.relationship_service = RelationshipService(db)
        self.invitation_service = InvitationService(db, whatsapp)
    
    def continue_invite_trainee(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle invite existing client flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_client_id')
            
            if step == 'ask_client_id':
                # User provided client_id
                client_id = message.strip().upper()
                
                # Validate client exists
                client_result = self.db.table('clients').select('*').eq('client_id', client_id).execute()
                
                if not client_result.data:
                    msg = (
                        f"❌ Client ID '{client_id}' not found.\n\n"
                        f"Please check the ID and try again, or type /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'invite_trainee_invalid_id'}
                
                client = client_result.data[0]
                
                # Check if already connected
                if self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    msg = (
                        f"ℹ️ You're already connected with {client.get('first_name')} {client.get('last_name')}!\n\n"
                        f"Type /view-trainees to see all your clients."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'invite_trainee_already_connected'}
                
                # Send invitation
                success = self.invitation_service.send_trainer_to_client_invitation(
                    trainer_id, client_id
                )
                
                if success:
                    msg = (
                        f"✅ Invitation sent to {client.get('first_name')} {client.get('last_name')}!\n\n"
                        f"I'll notify you when they respond."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'invite_trainee_sent'}
                else:
                    msg = "❌ Failed to send invitation. Please try again later."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': msg, 'handler': 'invite_trainee_failed'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'invite_trainee'}
            
        except Exception as e:
            log_error(f"Error in invite trainee flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while processing the invitation.\n\n"
                "The task has been cancelled. Please try again with /invite-trainee"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'invite_trainee_error'}

    def continue_create_trainee(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle create new client flow with improved UX"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_create_or_link')
            collected_data = task_data.get('collected_data', {})
            
            # Step 1: Ask if create new or link existing
            if step == 'ask_create_or_link':
                choice = message.strip()
                
                if choice == '1':
                    # Create new client - load fields
                    with open('config/client_registration_inputs.json', 'r') as f:
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
                    # Link existing client
                    task_data['step'] = 'ask_client_id'
                    task_data['mode'] = 'link_existing'
                    self.task_service.update_task(task['id'], 'trainer', task_data)
                    
                    msg = (
                        "🔗 *Link Existing Client*\n\n"
                        "Please provide the *Client ID* of the client you want to link with.\n\n"
                        "💡 The client must already be registered in the system.\n\n"
                        "Type /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_link'}
                
                else:
                    msg = "❌ Invalid choice. Please reply with *1* to create new or *2* to link existing."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_invalid_choice'}
            
            # Step 2: Handle link existing client
            if step == 'ask_client_id':
                client_id = message.strip().upper()
                
                # Validate client exists
                client_result = self.db.table('clients').select('client_id, name, whatsapp').eq(
                    'client_id', client_id
                ).execute()
                
                if not client_result.data:
                    msg = (
                        f"❌ Client ID '{client_id}' not found.\n\n"
                        f"Please check the ID and try again, or type /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_invalid_id'}
                
                client = client_result.data[0]
                client_phone = client.get('whatsapp')
                
                # Check if already connected
                if self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    msg = (
                        f"ℹ️ You're already connected with {client.get('name')}!\n\n"
                        f"Type /view-trainees to see all your clients."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_already_connected'}
                
                # Send invitation
                success, error_msg = self.invitation_service.send_trainer_to_client_invitation(
                    trainer_id, client_id, client_phone
                )
                
                if success:
                    msg = (
                        f"✅ *Invitation Sent!*\n\n"
                        f"I've sent an invitation to *{client.get('name')}*.\n\n"
                        f"I'll notify you when they respond. 🔔"
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_link_sent'}
                else:
                    msg = f"❌ Failed to send invitation: {error_msg}"
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': msg, 'handler': 'create_trainee_link_failed'}
            
            # Step 3: Collect fields for new client
            if step == 'collecting':
                fields = task_data.get('fields', [])
                current_index = task_data.get('current_field_index', 0)
                
                # Validate and store previous answer
                if current_index > 0:
                    prev_field = fields[current_index - 1]
                    field_name = prev_field['name']
                    
                    # Use registration service for validation
                    is_valid, error_msg = self.reg_service.validate_field_value(prev_field, message)
                    
                    if not is_valid:
                        error_response = f"❌ {error_msg}\n\n{prev_field['prompt']}"
                        self.whatsapp.send_message(phone, error_response)
                        return {'success': True, 'response': error_response, 'handler': 'create_trainee_validation_error'}
                    
                    # Parse and store value
                    parsed_value = self.reg_service.parse_field_value(prev_field, message)
                    collected_data[field_name] = parsed_value
                    task_data['collected_data'] = collected_data
                
                # Check if we have all fields
                if current_index >= len(fields):
                    # All fields collected - check if phone exists
                    phone_number = collected_data.get('phone_number')
                    
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
                    
                    # Client doesn't exist - send invitation with prefilled data
                    success, error_msg = self.invitation_service.send_new_client_invitation(
                        trainer_id, collected_data, phone_number
                    )
                    
                    if success:
                        client_name = collected_data.get('full_name', 'the client')
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
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while creating the client.\n\n"
                "The task has been cancelled. Please try again with /create-trainee"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'create_trainee_error'}
    
    def continue_remove_trainee(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle remove client flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_client_id')
            
            if step == 'ask_client_id':
                # User provided client_id
                client_id = message.strip().upper()
                
                # Verify client in trainer's list
                if not self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    msg = (
                        f"❌ Client ID '{client_id}' is not in your client list.\n\n"
                        f"Type /view-trainees to see your clients, or /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'remove_trainee_not_found'}
                
                # Get client info
                client_result = self.db.table('clients').select('*').eq('client_id', client_id).execute()
                
                if not client_result.data:
                    msg = "❌ Error retrieving client information."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': msg, 'handler': 'remove_trainee_error'}
                
                client = client_result.data[0]
                
                # Ask confirmation
                msg = (
                    f"⚠️ *Confirm Removal*\n\n"
                    f"*Client:* {client.get('first_name')} {client.get('last_name')}\n"
                    f"*Client ID:* {client_id}\n\n"
                    f"Are you sure you want to remove this client?\n"
                    f"This will also remove any habit assignments.\n\n"
                    f"Reply *YES* to confirm, or *NO* to cancel."
                )
                self.whatsapp.send_message(phone, msg)
                
                # Update task
                task_data['step'] = 'confirm_removal'
                task_data['client_id'] = client_id
                task_data['client_name'] = f"{client.get('first_name')} {client.get('last_name')}"
                self.task_service.update_task(task['id'], 'trainer', task_data)
                
                return {'success': True, 'response': msg, 'handler': 'remove_trainee_confirm'}
            
            elif step == 'confirm_removal':
                response = message.strip().upper()
                
                if response == 'YES':
                    client_id = task_data.get('client_id')
                    client_name = task_data.get('client_name')
                    
                    # Remove relationship
                    success = self.relationship_service.remove_relationship(trainer_id, client_id)
                    
                    if success:
                        # Get client phone to notify
                        client_result = self.db.table('clients').select('phone_number').eq(
                            'client_id', client_id
                        ).execute()
                        
                        if client_result.data:
                            client_phone = client_result.data[0].get('phone_number')
                            
                            # Get trainer info
                            trainer_result = self.db.table('trainers').select('first_name, last_name').eq(
                                'trainer_id', trainer_id
                            ).execute()
                            
                            if trainer_result.data:
                                trainer = trainer_result.data[0]
                                trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                                
                                # Notify client
                                client_msg = (
                                    f"ℹ️ *Connection Removed*\n\n"
                                    f"Your trainer {trainer_name} has removed you from their client list.\n\n"
                                    f"You can search for and invite other trainers using /search-trainer"
                                )
                                self.whatsapp.send_message(client_phone, client_msg)
                        
                        # Notify trainer
                        msg = (
                            f"✅ {client_name} has been removed from your client list.\n\n"
                            f"All habit assignments have been removed."
                        )
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': True, 'response': msg, 'handler': 'remove_trainee_success'}
                    else:
                        msg = "❌ Failed to remove client. Please try again."
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': False, 'response': msg, 'handler': 'remove_trainee_failed'}
                else:
                    msg = "Cancelled. Client was not removed."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'remove_trainee_cancelled'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'remove_trainee'}
            
        except Exception as e:
            log_error(f"Error in remove trainee flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while removing the client.\n\n"
                "The task has been cancelled. Please try again with /remove-trainee"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'remove_trainee_error'}
