"""
Trainer Invitation Flow
Handles trainer inviting existing clients
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.relationships import RelationshipService, InvitationService


class InvitationFlow:
    """Handles trainer invitation flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.relationship_service = RelationshipService(db)
        self.invitation_service = InvitationService(db, whatsapp)
    
    def continue_invite_trainee(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle invite existing client flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_client_id')
            
            if step == 'ask_client_id':
                # User provided client_id or phone number
                input_value = message.strip()
                
                # Try to find client by ID first (case-insensitive)
                client_result = self.db.table('clients').select('*').ilike('client_id', input_value).execute()
                
                # If not found by ID, try by phone number
                if not client_result.data:
                    # Clean phone number (remove + and formatting)
                    clean_phone = input_value.replace('+', '').replace('-', '').replace(' ', '')
                    client_result = self.db.table('clients').select('*').eq('whatsapp', clean_phone).execute()
                
                if not client_result.data:
                    msg = (
                        f"❌ Client with ID or phone number '{input_value}' not found.\n\n"
                        f"Please check the ID/phone number and try again, or type /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    # Complete the task since the client doesn't exist
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'invite_trainee_invalid_id'}
                
                client = client_result.data[0]
                client_id = client['client_id']  # Use actual client_id from database
                
                # Check if already connected
                if self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    client_name = client.get('name') or 'this client'
                    msg = (
                        f"ℹ️ You're already connected with {client_name}!\n\n"
                        f"Type /view-trainees to see all your clients."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'invite_trainee_already_connected'}
                
                # Send invitation
                client_phone = client.get('whatsapp')
                success, error_msg = self.invitation_service.send_trainer_to_client_invitation(
                    trainer_id, client_id, client_phone
                )
                
                if success:
                    client_name = client.get('name') or 'the client'
                    msg = (
                        f"✅ Invitation sent to {client_name}!\n\n"
                        f"I'll notify you when they respond."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'invite_trainee_sent'}
                else:
                    msg = f"❌ Failed to send invitation: {error_msg}"
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': msg, 'handler': 'invite_trainee_failed'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'invite_trainee'}
            
        except Exception as e:
            log_error(f"Error in invite trainee flow: {str(e)}")
            
            # Complete the task (consistent with creation flow)
            self.task_service.complete_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while processing the invitation.\n\n"
                "The task has been cancelled. Please try again with /invite-trainee"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'invite_trainee_error'}