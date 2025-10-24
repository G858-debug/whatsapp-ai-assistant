"""
Client Relationship Flow Handlers - Phase 2
Handles multi-step flows for client relationship management
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.relationships import RelationshipService, InvitationService


class ClientRelationshipFlows:
    """Handles client relationship flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.relationship_service = RelationshipService(db)
        self.invitation_service = InvitationService(db, whatsapp)
    
    def continue_search_trainer(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle search trainer flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_search_term')
            
            if step == 'ask_search_term':
                # User provided search term
                search_term = message.strip()
                
                if len(search_term) < 2:
                    msg = "Please provide at least 2 characters to search."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'search_trainer_invalid'}
                
                # Search trainers
                results = self.relationship_service.search_trainers(search_term, limit=5)
                
                if not results:
                    msg = (
                        f"❌ No trainers found matching '{search_term}'.\n\n"
                        f"Try a different search term or type /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'search_trainer_no_results'}
                
                # Format results
                msg = f"🔍 *Search Results for '{search_term}'*\n\n"
                
                for i, trainer in enumerate(results, 1):
                    msg += (
                        f"*{i}. {trainer.get('first_name')} {trainer.get('last_name')}*\n"
                        f"   ID: {trainer.get('trainer_id')}\n"
                        f"   Specialization: {trainer.get('specialization', 'N/A')}\n"
                        f"   Experience: {trainer.get('years_of_experience', 'N/A')} years\n"
                    )
                    
                    if trainer.get('business_name'):
                        msg += f"   Business: {trainer.get('business_name')}\n"
                    
                    msg += "\n"
                
                msg += (
                    f"💡 *To invite a trainer:*\n"
                    f"Copy their ID and type:\n"
                    f"/invite-trainer"
                )
                
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task['id'], 'client')
                
                return {'success': True, 'response': msg, 'handler': 'search_trainer_results'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'search_trainer'}
            
        except Exception as e:
            log_error(f"Error in search trainer flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error searching trainers', 'handler': 'search_trainer_error'}
    
    def continue_invite_trainer(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle invite trainer flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_trainer_id')
            
            if step == 'ask_trainer_id':
                # User provided trainer_id
                trainer_id = message.strip().upper()
                
                # Validate trainer exists
                trainer_result = self.db.table('trainers').select('*').eq('trainer_id', trainer_id).execute()
                
                if not trainer_result.data:
                    msg = (
                        f"❌ Trainer ID '{trainer_id}' not found.\n\n"
                        f"Please check the ID and try again, or type /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'invite_trainer_invalid_id'}
                
                trainer = trainer_result.data[0]
                
                # Check if already connected
                if self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    msg = (
                        f"ℹ️ You're already connected with {trainer.get('first_name')} {trainer.get('last_name')}!\n\n"
                        f"Type /view-trainers to see all your trainers."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': msg, 'handler': 'invite_trainer_already_connected'}
                
                # Send invitation
                success = self.invitation_service.send_client_to_trainer_invitation(
                    client_id, trainer_id
                )
                
                if success:
                    msg = (
                        f"✅ Invitation sent to {trainer.get('first_name')} {trainer.get('last_name')}!\n\n"
                        f"I'll notify you when they respond."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': msg, 'handler': 'invite_trainer_sent'}
                else:
                    msg = "❌ Failed to send invitation. Please try again later."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': msg, 'handler': 'invite_trainer_failed'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'invite_trainer'}
            
        except Exception as e:
            log_error(f"Error in invite trainer flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error processing invitation', 'handler': 'invite_trainer_error'}
    
    def continue_remove_trainer(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle remove trainer flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_trainer_id')
            
            if step == 'ask_trainer_id':
                # User provided trainer_id
                trainer_id = message.strip().upper()
                
                # Verify trainer in client's list
                if not self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    msg = (
                        f"❌ Trainer ID '{trainer_id}' is not in your trainer list.\n\n"
                        f"Type /view-trainers to see your trainers, or /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'remove_trainer_not_found'}
                
                # Get trainer info
                trainer_result = self.db.table('trainers').select('*').eq('trainer_id', trainer_id).execute()
                
                if not trainer_result.data:
                    msg = "❌ Error retrieving trainer information."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': msg, 'handler': 'remove_trainer_error'}
                
                trainer = trainer_result.data[0]
                
                # Ask confirmation
                msg = (
                    f"⚠️ *Confirm Removal*\n\n"
                    f"*Trainer:* {trainer.get('first_name')} {trainer.get('last_name')}\n"
                    f"*Trainer ID:* {trainer_id}\n"
                )
                
                if trainer.get('specialization'):
                    msg += f"*Specialization:* {trainer.get('specialization')}\n"
                
                msg += (
                    f"\nAre you sure you want to remove this trainer?\n"
                    f"This will also remove any habit assignments from them.\n\n"
                    f"Reply *YES* to confirm, or *NO* to cancel."
                )
                
                self.whatsapp.send_message(phone, msg)
                
                # Update task
                task_data['step'] = 'confirm_removal'
                task_data['trainer_id'] = trainer_id
                task_data['trainer_name'] = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                self.task_service.update_task(task['id'], 'client', task_data)
                
                return {'success': True, 'response': msg, 'handler': 'remove_trainer_confirm'}
            
            elif step == 'confirm_removal':
                response = message.strip().upper()
                
                if response == 'YES':
                    trainer_id = task_data.get('trainer_id')
                    trainer_name = task_data.get('trainer_name')
                    
                    # Remove relationship
                    success = self.relationship_service.remove_relationship(trainer_id, client_id)
                    
                    if success:
                        # Get trainer phone to notify
                        trainer_result = self.db.table('trainers').select('phone_number').eq(
                            'trainer_id', trainer_id
                        ).execute()
                        
                        if trainer_result.data:
                            trainer_phone = trainer_result.data[0].get('phone_number')
                            
                            # Get client info
                            client_result = self.db.table('clients').select('first_name, last_name').eq(
                                'client_id', client_id
                            ).execute()
                            
                            if client_result.data:
                                client = client_result.data[0]
                                client_name = f"{client.get('first_name')} {client.get('last_name')}"
                                
                                # Notify trainer
                                trainer_msg = (
                                    f"ℹ️ *Connection Removed*\n\n"
                                    f"Your client {client_name} has removed you from their trainer list."
                                )
                                self.whatsapp.send_message(trainer_phone, trainer_msg)
                        
                        # Notify client
                        msg = (
                            f"✅ {trainer_name} has been removed from your trainer list.\n\n"
                            f"All habit assignments from them have been removed."
                        )
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'client')
                        return {'success': True, 'response': msg, 'handler': 'remove_trainer_success'}
                    else:
                        msg = "❌ Failed to remove trainer. Please try again."
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'client')
                        return {'success': False, 'response': msg, 'handler': 'remove_trainer_failed'}
                else:
                    msg = "Cancelled. Trainer was not removed."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': msg, 'handler': 'remove_trainer_cancelled'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'remove_trainer'}
            
        except Exception as e:
            log_error(f"Error in remove trainer flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error removing trainer', 'handler': 'remove_trainer_error'}
