"""
Invitation Manager - Invitation operations
Handles invitation creation, sending, and tracking operations
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
import pytz
import secrets
from utils.logger import log_info, log_error, log_warning
from config import Config


class InvitationManager:
    """Manages invitation operations"""
    
    def __init__(self, supabase_client, whatsapp_service, relationship_manager=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.relationship_manager = relationship_manager
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def generate_invitation_token(self) -> str:
        """Generate unique invitation token"""
        return secrets.token_urlsafe(16)
    
    def send_trainer_to_client_invitation(self, trainer_id: str, client_id: str, 
                                         client_phone: str) -> Tuple[bool, str]:
        """Send invitation from trainer to client"""
        try:
            # Get trainer info
            trainer_result = self.db.table('trainers').select('*').eq(
                'trainer_id', trainer_id
            ).execute()
            
            if not trainer_result.data:
                return False, "Trainer not found"
            
            trainer = trainer_result.data[0]
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()
            
            # Create invitation message
            message = (
                f"🎯 *Training Invitation*\n\n"
                f"*{trainer_name}* (ID: {trainer_id}) has invited you to join as their client!\n\n"
                f"*Trainer Info:*\n"
            )
            
            if trainer.get('specialization'):
                message += f"• Specialization: {trainer['specialization']}\n"
            if trainer.get('experience_years'):
                message += f"• Experience: {trainer['experience_years']}\n"
            if trainer.get('city'):
                message += f"• Location: {trainer['city']}\n"
            
            message += f"\nWould you like to accept this invitation?"
            
            # Send with buttons
            buttons = [
                {'id': f'accept_trainer_{trainer_id}', 'title': '✅ Accept'},
                {'id': f'decline_trainer_{trainer_id}', 'title': '❌ Decline'}
            ]
            
            # Create initial pending relationship
            relationship_success, relationship_msg = self.create_relationship(
                trainer_id, client_id, 'trainer'
            )
            
            if not relationship_success:
                log_error(f"Failed to create relationship: {relationship_msg}")
                return False, f"Failed to create relationship: {relationship_msg}"
            
            self.whatsapp.send_button_message(client_phone, message, buttons)
            
            log_info(f"Sent trainer invitation from {trainer_id} to client {client_id}")
            return True, "Invitation sent"
            
        except Exception as e:
            log_error(f"Error sending trainer invitation: {str(e)}")
            return False, str(e)
    
    def send_client_to_trainer_invitation(self, client_id: str, trainer_id: str,
                                         trainer_phone: str) -> Tuple[bool, str]:
        """Send invitation from client to trainer"""
        try:
            # Get client info
            client_result = self.db.table('clients').select('*').eq(
                'client_id', client_id
            ).execute()
            
            if not client_result.data:
                return False, "Client not found"
            
            client = client_result.data[0]
            client_name = client.get('name', 'A client')
            
            # Create invitation message
            message = (
                f"👤 *Client Request*\n\n"
                f"*{client_name}* (ID: {client_id}) wants to train with you!\n\n"
                f"*Client Info:*\n"
            )
            
            if client.get('fitness_goals'):
                message += f"• Goals: {client['fitness_goals']}\n"
            if client.get('experience_level'):
                message += f"• Experience: {client['experience_level']}\n"
            
            message += f"\nWould you like to accept this client?"
            
            # Send with buttons
            buttons = [
                {'id': f'accept_client_{client_id}', 'title': '✅ Accept'},
                {'id': f'decline_client_{client_id}', 'title': '❌ Decline'}
            ]
            
            # Create initial pending relationship
            relationship_success, relationship_msg = self.create_relationship(
                trainer_id, client_id, 'client'
            )
            
            if not relationship_success:
                log_error(f"Failed to create relationship: {relationship_msg}")
                return False, f"Failed to create relationship: {relationship_msg}"
            
            self.whatsapp.send_button_message(trainer_phone, message, buttons)
            
            log_info(f"Sent client invitation from {client_id} to trainer {trainer_id}")
            return True, "Invitation sent"
            
        except Exception as e:
            log_error(f"Error sending client invitation: {str(e)}")
            return False, str(e)    
  
    def send_new_client_invitation(self, trainer_id: str, client_data: Dict,client_phone: str) -> Tuple[bool, str]:
        """Send invitation to new client with prefilled data"""
        try:
            # Get trainer info
            trainer_result = self.db.table('trainers').select('*').eq(
                'id', trainer_id
            ).execute()

            if not trainer_result.data:
                return False, "Trainer not found"

            trainer = trainer_result.data[0]
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()

            # Generate invitation token
            invitation_token = self.generate_invitation_token()

            # Store invitation in database with complete prefilled data
            invitation_data = {
                'trainer_id': trainer['id'],  # Use UUID from trainer record
                'client_phone': client_phone,
                'client_name': client_data.get('name') or client_data.get('full_name'),
                'client_email': client_data.get('email') if client_data.get('email') and client_data.get('email').lower() not in ['skip', 'none'] else None,
                'invitation_token': invitation_token,
                'prefilled_data': client_data,  # Store complete client data as JSONB
                'status': 'pending',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }

            # Insert or update invitation
            existing = self.db.table('client_invitations').select('id').eq(
                'client_phone', client_phone
            ).eq('trainer_id', trainer['id']).eq('status', 'pending').execute()

            if existing.data:
                # Update existing invitation
                self.db.table('client_invitations').update(invitation_data).eq(
                    'id', existing.data[0]['id']
                ).execute()
            else:
                # Create new invitation
                self.db.table('client_invitations').insert(invitation_data).execute()

            # Create invitation message with prefilled data
            client_name = client_data.get('name') or client_data.get('full_name', 'there')

            message = (
                f"🎯 *Training Invitation*\n\n"
                f"Hi {client_name}! 👋\n\n"
                f"*{trainer_name}* has created a fitness profile for you and invited you to train together!\n\n"
                f"📋 *Your Profile:*\n"
                f"• Name: {client_name}\n"
            )

            if client_data.get('email') and client_data['email'].lower() not in ['skip', 'none']:
                message += f"• Email: {client_data['email']}\n"
            if client_data.get('fitness_goals'):
                message += f"• Goals: {client_data['fitness_goals']}\n"
            if client_data.get('experience_level'):
                message += f"• Experience: {client_data['experience_level']}\n"

            message += (
                f"\n👨‍🏫 *Your Trainer:*\n"
                f"• Name: {trainer_name}\n"
                f"• ID: {trainer_id}\n"
            )

            if trainer.get('specialization'):
                message += f"• Specialization: {trainer['specialization']}\n"

            message += f"\n✅ Do you accept this invitation and want to train with {trainer_name}?"

            # Send with buttons (use trainer_id string, not UUID)
            trainer_string_id = trainer.get('trainer_id')
            buttons = [
                {'id': f'approve_new_client_{trainer_string_id}', 'title': '✅ Accept'},
                {'id': f'reject_new_client_{trainer_string_id}', 'title': '❌ Decline'}
            ]

            self.whatsapp.send_button_message(client_phone, message, buttons)

            log_info(f"Sent new client invitation from trainer {trainer_id} to {client_phone}")
            return True, "Invitation sent"

        except Exception as e:
            log_error(f"Error sending new client invitation: {str(e)}")
            return False, str(e)

    def send_client_fills_invitation(self, trainer_id: str, client_phone: str,
                                     client_name: str, selected_price: Optional[int] = None) -> Tuple[bool, str]:
        """Send invitation to client who will fill their own profile

        Args:
            trainer_id: UUID of the trainer
            client_phone: Client's phone number
            client_name: Client's name
            selected_price: Price per session as integer (None if "discuss later")

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Get trainer info
            trainer_result = self.db.table('trainers').select('*').eq(
                'id', trainer_id
            ).execute()

            if not trainer_result.data:
                return False, "Trainer not found"

            trainer = trainer_result.data[0]
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()

            # Generate invitation token
            invitation_token = self.generate_invitation_token()

            # Store invitation in database
            invitation_data = {
                'trainer_id': trainer['id'],  # Use UUID from trainer record
                'client_phone': client_phone,
                'client_name': client_name,
                'invitation_token': invitation_token,
                'status': 'pending_client_completion',
                'profile_completion_method': 'client_fills',
                'custom_price': selected_price,  # Can be None
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }

            # Insert or update invitation
            existing = self.db.table('client_invitations').select('id').eq(
                'client_phone', client_phone
            ).eq('trainer_id', trainer['id']).eq('status', 'pending_client_completion').execute()

            if existing.data:
                # Update existing invitation
                invitation_result = self.db.table('client_invitations').update(invitation_data).eq(
                    'id', existing.data[0]['id']
                ).execute()
                invitation_id = existing.data[0]['id']
            else:
                # Create new invitation
                invitation_result = self.db.table('client_invitations').insert(invitation_data).execute()
                invitation_id = invitation_result.data[0]['id']

            # Get invitation ID for button payloads
            invitation_query = self.db.table('client_invitations').select('id').eq(
                'client_phone', client_phone
            ).eq('trainer_id', trainer['id']).eq('status', 'pending_client_completion').execute()

            if not invitation_query.data:
                log_error(f"Could not find invitation for buttons: {client_phone}")
                return False, "Invitation created but missing ID"

            invitation_id = invitation_query.data[0]['id']

            # Generate flow token
            flow_token = f"client_onboarding_invitation_{invitation_id}_{client_phone}_{int(datetime.now().timestamp())}"

            # Store flow token with trainer data
            try:
                from datetime import timedelta
                self.db.table('flow_tokens').insert({
                    'flow_token': flow_token,
                    'phone_number': client_phone,
                    'flow_type': 'client_onboarding',
                    'flow_data': {
                        'invitation_id': str(invitation_id),
                        'trainer_id': str(trainer_id),
                        'trainer_name': trainer_name,
                        'selected_price': str(selected_price) if selected_price else None
                    },
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'expires_at': (datetime.now(self.sa_tz) + timedelta(days=7)).isoformat()
                }).execute()
                log_info(f"Stored flow token: {flow_token}")
            except Exception as e:
                log_warning(f"Could not store flow token: {str(e)}")

            # Use configured client onboarding flow ID
            flow_id = Config.CLIENT_ONBOARDING_FLOW_ID

            # Create interactive flow message (NOT template)
            flow_message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": client_phone,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": f"Training invitation!\n"
                    },
                    "body": {
                        "text": f"Hi {client_name or 'there'}! 👋\n\n*{trainer_name}* has invited you to start training together!\n\n📋 *Next steps:*\n - Accept the invitation below\n - Complete your fitness profile (2 minutes)\n - Start yoru fitness journey!\n\n💰 *Pricing*: R{int(selected_price) if selected_price else 'TBD'} per session\n\nReady to get started?"
                    },
                    "footer": {
                        "text": "Powered by Refiloe"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": flow_id,
                            "flow_cta": "Complete profile",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "welcome",
                                "data": {
                                    "flow_token": flow_token,
                                    "trainer_name": trainer_name,
                                    "selected_price": str(selected_price) if selected_price else "500"
                                }
                            }
                        }
                    }
                }
            }

            # Send interactive flow message
            success = self.whatsapp.send_flow_message(flow_message)

            if not success:
                log_error(f"Failed to send flow message to {client_phone}")
                return False, "Failed to send flow message"

            log_info(f"Sent client_fills invitation from trainer {trainer_id} to {client_phone}")
            return True, "Invitation sent successfully"

        except Exception as e:
            log_error(f"Error sending client_fills invitation: {str(e)}")
            return False, str(e) 
   
    def create_relationship(self, trainer_id: str, client_id: str, 
                          invited_by: str, invitation_token: str = None) -> Tuple[bool, str]:
        """Create or update bidirectional trainer-client relationship"""
        try:
            now = datetime.now(self.sa_tz).isoformat()
            
            # Check if any relationship already exists (including declined ones)
            existing = None
            if self.relationship_manager:
                existing = self.relationship_manager.check_any_relationship(trainer_id, client_id)
            
            relationship_data = {
                'connection_status': 'pending',
                'invited_by': invited_by,
                'invitation_token': invitation_token,
                'invited_at': now,
                'updated_at': now
            }
            
            if existing:
                # Update existing relationship
                self.db.table('trainer_client_list').update(relationship_data).eq(
                    'trainer_id', trainer_id
                ).eq('client_id', client_id).execute()
                
                self.db.table('client_trainer_list').update(relationship_data).eq(
                    'client_id', client_id
                ).eq('trainer_id', trainer_id).execute()
                
                log_info(f"Updated existing relationship: trainer {trainer_id} <-> client {client_id}")
                return True, "Relationship updated successfully"
            else:
                # Create new relationship
                trainer_list_data = {
                    'trainer_id': trainer_id,
                    'client_id': client_id,
                    'created_at': now,
                    **relationship_data
                }
                
                self.db.table('trainer_client_list').insert(trainer_list_data).execute()
                
                client_list_data = {
                    'client_id': client_id,
                    'trainer_id': trainer_id,
                    'created_at': now,
                    **relationship_data
                }
                
                self.db.table('client_trainer_list').insert(client_list_data).execute()
                
                log_info(f"Created new relationship: trainer {trainer_id} <-> client {client_id}")
                return True, "Relationship created successfully"
            
        except Exception as e:
            log_error(f"Error creating/updating relationship: {str(e)}")
            return False, str(e)
