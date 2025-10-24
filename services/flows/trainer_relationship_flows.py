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
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error processing invitation', 'handler': 'invite_trainee_error'}

    def continue_create_trainee(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle create new client flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'start')
            collected_data = task_data.get('collected_data', {})
            
            # Load client registration fields
            if not task_data.get('fields'):
                with open('config/client_registration_inputs.json', 'r') as f:
                    config = json.load(f)
                    task_data['fields'] = config['fields']
                    task_data['current_field_index'] = 0
            
            fields = task_data['fields']
            current_index = task_data.get('current_field_index', 0)
            
            # Process current step
            if step != 'start':
                # Validate and store previous answer
                current_field = fields[current_index - 1]
                field_name = current_field['name']
                
                # Basic validation
                if not message.strip():
                    msg = f"Please provide a valid {current_field['label'].lower()}."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_invalid'}
                
                collected_data[field_name] = message.strip()
                task_data['collected_data'] = collected_data
            
            # Check if we have all fields
            if current_index >= len(fields):
                # All fields collected - check if phone exists
                phone_number = collected_data.get('phone_number')
                
                existing_client = self.db.table('clients').select('client_id, first_name, last_name').eq(
                    'phone_number', phone_number
                ).execute()
                
                if existing_client.data:
                    # Client exists - ask to invite instead
                    client = existing_client.data[0]
                    msg = (
                        f"ℹ️ This client already exists!\n\n"
                        f"*Name:* {client.get('first_name')} {client.get('last_name')}\n"
                        f"*Client ID:* {client.get('client_id')}\n\n"
                        f"Would you like to invite this existing client instead?\n\n"
                        f"Reply *YES* to send invitation, or *NO* to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    task_data['step'] = 'confirm_invite_existing'
                    task_data['existing_client_id'] = client.get('client_id')
                    self.task_service.update_task(task['id'], 'trainer', task_data)
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_exists'}
                
                # Client doesn't exist - send invitation with prefilled data
                success = self.invitation_service.send_new_client_invitation(
                    trainer_id, phone_number, collected_data
                )
                
                if success:
                    msg = (
                        f"✅ Invitation sent to {collected_data.get('first_name')}!\n\n"
                        f"They'll receive a message with all the prefilled information.\n"
                        f"I'll notify you when they respond."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_sent'}
                else:
                    msg = "❌ Failed to send invitation. Please try again later."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': msg, 'handler': 'create_trainee_failed'}
            
            # Handle confirmation for existing client
            if step == 'confirm_invite_existing':
                response = message.strip().upper()
                
                if response == 'YES':
                    existing_client_id = task_data.get('existing_client_id')
                    success = self.invitation_service.send_trainer_to_client_invitation(
                        trainer_id, existing_client_id
                    )
                    
                    if success:
                        msg = "✅ Invitation sent! I'll notify you when they respond."
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': True, 'response': msg, 'handler': 'create_trainee_invited_existing'}
                    else:
                        msg = "❌ Failed to send invitation."
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': False, 'response': msg, 'handler': 'create_trainee_invite_failed'}
                else:
                    msg = "Cancelled. Type /create-trainee to try again."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'create_trainee_cancelled'}
            
            # Ask next field
            next_field = fields[current_index]
            msg = f"*{next_field['label']}*\n\n{next_field.get('description', '')}"
            
            if next_field.get('options'):
                msg += f"\n\nOptions: {', '.join(next_field['options'])}"
            
            self.whatsapp.send_message(phone, msg)
            
            # Update task
            task_data['step'] = 'collecting'
            task_data['current_field_index'] = current_index + 1
            self.task_service.update_task(task['id'], 'trainer', task_data)
            
            return {'success': True, 'response': msg, 'handler': 'create_trainee'}
            
        except Exception as e:
            log_error(f"Error in create trainee flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error creating client', 'handler': 'create_trainee_error'}
    
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
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error removing client', 'handler': 'remove_trainee_error'}
