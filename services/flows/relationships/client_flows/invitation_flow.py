"""
Client Trainer Invitation Flow
Handles client inviting trainers
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
    
    def continue_invite_trainer(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle invite trainer flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_trainer_id')
            
            if step == 'ask_trainer_id':
                # User provided trainer_id or phone number
                input_value = message.strip()
                
                # Try to find trainer by ID first (case-insensitive)
                trainer_result = self.db.table('trainers').select('*').ilike('trainer_id', input_value).execute()
                
                # If not found by ID, try by phone number
                if not trainer_result.data:
                    # Clean phone number (remove + and formatting)
                    clean_phone = input_value.replace('+', '').replace('-', '').replace(' ', '')
                    trainer_result = self.db.table('trainers').select('*').eq('whatsapp', clean_phone).execute()
                
                if not trainer_result.data:
                    msg = (
                        f"❌ Trainer with ID or phone number '{input_value}' not found.\n\n"
                        f"Please check the ID/phone number and try again, or type /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'invite_trainer_invalid_id'}
                
                trainer = trainer_result.data[0]
                trainer_id = trainer['trainer_id']  # Use actual trainer_id from database
                
                # Check if already connected
                if self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'this trainer'
                    msg = (
                        f"ℹ️ You're already connected with {trainer_name}!\n\n"
                        f"Type /view-trainers to see all your trainers."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': msg, 'handler': 'invite_trainer_already_connected'}
                
                # Send invitation
                trainer_phone = trainer.get('whatsapp')
                success, error_msg = self.invitation_service.send_client_to_trainer_invitation(
                    client_id, trainer_id, trainer_phone
                )
                
                if success:
                    trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'the trainer'
                    msg = (
                        f"✅ Invitation sent to {trainer_name}!\n\n"
                        f"I'll notify you when they respond."
                    )
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': msg, 'handler': 'invite_trainer_sent'}
                else:
                    msg = f"❌ Failed to send invitation: {error_msg}"
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': msg, 'handler': 'invite_trainer_failed'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'invite_trainer'}
            
        except Exception as e:
            log_error(f"Error in invite trainer flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'client')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while processing the invitation.\n\n"
                "The task has been cancelled. Please try again with /invite-trainer"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'invite_trainer_error'}