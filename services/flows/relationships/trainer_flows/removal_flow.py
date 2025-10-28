"""
Trainer Client Removal Flow
Handles trainer removing clients from their list
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.relationships import RelationshipService


class RemovalFlow:
    """Handles client removal flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.relationship_service = RelationshipService(db)
    
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