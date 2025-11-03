"""
Invitation Manager - Invitation operations
Handles invitation creation, sending, and tracking operations
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
import pytz
import secrets
from utils.logger import log_info, log_error


class InvitationManager:
    """Manages invitation operations"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
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
                'trainer_id', trainer_id
            ).execute()
            
            if not trainer_result.data:
                return False, "Trainer not found"
            
            trainer = trainer_result.data[0]
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()
            
            # Generate invitation token
            invitation_token = self.generate_invitation_token()
            
            # Store invitation in database with prefilled data
            invitation_data = {
                'trainer_id': trainer['id'],  # Use UUID from trainer record
                'client_phone': client_phone,
                'client_name': client_data.get('name') or client_data.get('full_name'),
                'client_email': client_data.get('email') if client_data.get('email') and client_data.get('email').lower() not in ['skip', 'none'] else None,
                'invitation_token': invitation_token,
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
            
            # Send with buttons
            buttons = [
                {'id': f'approve_new_client_{trainer_id}', 'title': '✅ Accept'},
                {'id': f'reject_new_client_{trainer_id}', 'title': '❌ Decline'}
            ]
            
            self.whatsapp.send_button_message(client_phone, message, buttons)
            
            log_info(f"Sent new client invitation from trainer {trainer_id} to {client_phone}")
            return True, "Invitation sent"
            
        except Exception as e:
            log_error(f"Error sending new client invitation: {str(e)}")
            return False, str(e) 
   
    def create_relationship(self, trainer_id: str, client_id: str, 
                          invited_by: str, invitation_token: str = None) -> Tuple[bool, str]:
        """Create bidirectional trainer-client relationship"""
        try:
            now = datetime.now(self.sa_tz).isoformat()
            
            # Add to trainer_client_list
            trainer_list_data = {
                'trainer_id': trainer_id,
                'client_id': client_id,
                'connection_status': 'pending',
                'invited_by': invited_by,
                'invitation_token': invitation_token,
                'invited_at': now,
                'created_at': now,
                'updated_at': now
            }
            
            self.db.table('trainer_client_list').insert(trainer_list_data).execute()
            
            # Add to client_trainer_list
            client_list_data = {
                'client_id': client_id,
                'trainer_id': trainer_id,
                'connection_status': 'pending',
                'invited_by': invited_by,
                'invitation_token': invitation_token,
                'invited_at': now,
                'created_at': now,
                'updated_at': now
            }
            
            self.db.table('client_trainer_list').insert(client_list_data).execute()
            
            log_info(f"Created relationship: trainer {trainer_id} <-> client {client_id}")
            return True, "Relationship created successfully"
            
        except Exception as e:
            log_error(f"Error creating relationship: {str(e)}")
            return False, str(e)