"""
Trainer Invitation Flow
Handles trainer inviting existing clients
"""
from typing import Dict
from datetime import datetime
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

    def handle_available_client_scenario(self, trainer_phone: str, client_data: Dict, trainer_id: str) -> Dict:
        """
        Handle Scenario 2: Client exists in database but has no current trainer.
        Shows client info to trainer and allows them to send invitation.

        Args:
            trainer_phone: Trainer's WhatsApp phone number
            client_data: Dictionary containing client information from database
            trainer_id: Trainer's ID

        Returns:
            Dict with success status and response message
        """
        try:
            log_info(f"Handling available client scenario for trainer {trainer_id}, client {client_data.get('client_id')}")

            # Extract client information
            client_name = client_data.get('name', 'Unknown')
            client_phone = client_data.get('whatsapp', 'N/A')
            client_id = client_data.get('client_id', 'N/A')
            created_at = client_data.get('created_at', '')

            # Format registration date
            registration_date = "Unknown"
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    registration_date = dt.strftime('%d %b %Y')
                except Exception as e:
                    log_error(f"Error parsing date: {str(e)}")
                    registration_date = "Unknown"

            # Build client info message
            message = (
                f"👤 *Client Found*\n\n"
                f"*Name:* {client_name}\n"
                f"*Phone:* {client_phone}\n"
                f"*Client ID:* {client_id}\n"
                f"*Registered:* {registration_date}\n"
                f"*Status:* Registered, no current trainer\n\n"
            )

            # Add optional client details if available
            if client_data.get('fitness_goals'):
                message += f"*Goals:* {client_data['fitness_goals']}\n"
            if client_data.get('experience_level'):
                message += f"*Experience:* {client_data['experience_level']}\n"
            if client_data.get('email'):
                message += f"*Email:* {client_data['email']}\n"

            message += f"\nWould you like to send a training invitation to {client_name}?"

            # Send message with buttons
            buttons = [
                {'id': f'send_invitation_{client_id}', 'title': '✉️ Send Invitation'},
                {'id': f'cancel_invitation_{client_id}', 'title': '❌ Cancel'}
            ]

            self.whatsapp.send_button_message(trainer_phone, message, buttons)

            log_info(f"Sent available client confirmation to trainer {trainer_id}")
            return {
                'success': True,
                'response': message,
                'handler': 'available_client_scenario',
                'client_id': client_id,
                'client_name': client_name
            }

        except Exception as e:
            log_error(f"Error in handle_available_client_scenario: {str(e)}")
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while processing the client information.\n\n"
                "Please try again."
            )
            self.whatsapp.send_message(trainer_phone, error_msg)
            return {'success': False, 'response': error_msg, 'handler': 'available_client_error'}

    def send_invitation_to_available_client(self, trainer_phone: str, trainer_id: str, client_id: str) -> Dict:
        """
        Send invitation to available client after trainer confirms.

        Args:
            trainer_phone: Trainer's WhatsApp phone number
            trainer_id: Trainer's ID
            client_id: Client's ID

        Returns:
            Dict with success status and response message
        """
        try:
            log_info(f"Sending invitation from trainer {trainer_id} to available client {client_id}")

            # Get client info
            client_result = self.db.table('clients').select('*').eq('client_id', client_id).execute()

            if not client_result.data:
                error_msg = f"❌ Client {client_id} not found."
                self.whatsapp.send_message(trainer_phone, error_msg)
                return {'success': False, 'response': error_msg, 'handler': 'client_not_found'}

            client = client_result.data[0]
            client_name = client.get('name', 'the client')
            client_phone = client.get('whatsapp')

            if not client_phone:
                error_msg = f"❌ Client phone number not found for {client_name}."
                self.whatsapp.send_message(trainer_phone, error_msg)
                return {'success': False, 'response': error_msg, 'handler': 'client_phone_missing'}

            # Send invitation using existing invitation service
            success, error_msg = self.invitation_service.send_trainer_to_client_invitation(
                trainer_id, client_id, client_phone
            )

            if success:
                msg = (
                    f"✅ *Invitation Sent!*\n\n"
                    f"Your training invitation has been sent to {client_name}.\n\n"
                    f"I'll notify you when they respond."
                )
                self.whatsapp.send_message(trainer_phone, msg)
                return {'success': True, 'response': msg, 'handler': 'invitation_sent'}
            else:
                msg = f"❌ Failed to send invitation: {error_msg}"
                self.whatsapp.send_message(trainer_phone, msg)
                return {'success': False, 'response': msg, 'handler': 'invitation_failed'}

        except Exception as e:
            log_error(f"Error sending invitation to available client: {str(e)}")
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while sending the invitation.\n\n"
                "Please try again."
            )
            self.whatsapp.send_message(trainer_phone, error_msg)
            return {'success': False, 'response': error_msg, 'handler': 'send_invitation_error'}

    def cancel_invitation_to_available_client(self, trainer_phone: str, client_id: str) -> Dict:
        """
        Handle cancellation of invitation to available client.

        Args:
            trainer_phone: Trainer's WhatsApp phone number
            client_id: Client's ID

        Returns:
            Dict with success status and response message
        """
        try:
            log_info(f"Cancelling invitation to client {client_id}")

            msg = (
                "✅ *Cancelled*\n\n"
                "Invitation cancelled. No invitation was sent to the client.\n\n"
                "You can search for other clients or add a new one anytime."
            )
            self.whatsapp.send_message(trainer_phone, msg)

            return {'success': True, 'response': msg, 'handler': 'invitation_cancelled'}

        except Exception as e:
            log_error(f"Error cancelling invitation: {str(e)}")
            error_msg = "❌ Error cancelling invitation."
            self.whatsapp.send_message(trainer_phone, error_msg)
            return {'success': False, 'response': error_msg, 'handler': 'cancel_invitation_error'}