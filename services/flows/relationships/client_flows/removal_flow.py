"""
Client Trainer Removal Flow
Handles client removing trainers from their list
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.relationships import RelationshipService


class RemovalFlow:
    """Handles trainer removal flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.relationship_service = RelationshipService(db)
    
    def continue_remove_trainer(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle remove trainer flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_trainer_id')
            
            if step == 'ask_trainer_id':
                # User provided trainer_id
                input_value = message.strip()
                
                # Try to find trainer by ID (case-insensitive)
                trainer_result = self.db.table('trainers').select('*').ilike(
                    'trainer_id', input_value
                ).execute()
                
                if not trainer_result.data:
                    msg = (
                        f"❌ Trainer with ID '{input_value}' not found.\n\n"
                        f"Please check the ID and try again, or type /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    # Complete the task since the trainer doesn't exist
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': msg, 'handler': 'remove_trainer_not_found'}
                
                trainer = trainer_result.data[0]
                trainer_id = trainer['trainer_id']  # Use actual trainer_id from database
                
                # Verify trainer in client's list
                if not self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    msg = (
                        f"❌ Trainer ID '{input_value}' is not in your trainer list.\n\n"
                        f"Type /view-trainers to see your trainers, or /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    # Complete the task since the relationship doesn't exist
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': msg, 'handler': 'remove_trainer_not_found'}
                
                if not trainer_result.data:
                    msg = "❌ Error retrieving trainer information."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': msg, 'handler': 'remove_trainer_error'}
                
                trainer = trainer_result.data[0]
                
                # Ask confirmation
                trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'Unknown Trainer'
                msg = (
                    f"⚠️ *Confirm Removal*\n\n"
                    f"*Trainer:* {trainer_name}\n"
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
                task_data['trainer_name'] = trainer_name
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
                        trainer_result = self.db.table('trainers').select('whatsapp').eq(
                            'trainer_id', trainer_id
                        ).execute()
                        
                        if trainer_result.data:
                            trainer_phone = trainer_result.data[0].get('whatsapp')
                            
                            # Get client info
                            client_result = self.db.table('clients').select('name').eq(
                                'client_id', client_id
                            ).execute()
                            
                            if client_result.data:
                                client = client_result.data[0]
                                client_name = client.get('name', 'the client')
                                
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
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'client')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while removing the trainer.\n\n"
                "The task has been cancelled. Please try again with /remove-trainer"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'remove_trainer_error'}