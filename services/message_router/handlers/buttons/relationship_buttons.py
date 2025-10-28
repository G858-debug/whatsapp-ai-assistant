"""
Relationship Button Handler
Handles trainer-client relationship buttons (accept/decline invitations)
"""
from typing import Dict
from utils.logger import log_error


class RelationshipButtonHandler:
    """Handles relationship invitation buttons"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
    
    def handle_relationship_button(self, phone: str, button_id: str) -> Dict:
        """Handle relationship invitation buttons"""
        try:
            if button_id.startswith('accept_trainer_'):
                return self._handle_accept_trainer(phone, button_id)
            elif button_id.startswith('decline_trainer_'):
                return self._handle_decline_trainer(phone, button_id)
            elif button_id.startswith('accept_client_'):
                return self._handle_accept_client(phone, button_id)
            elif button_id.startswith('decline_client_'):
                return self._handle_decline_client(phone, button_id)
            else:
                return {'success': False, 'response': 'Unknown relationship button', 'handler': 'unknown_relationship_button'}
                
        except Exception as e:
            log_error(f"Error handling relationship button: {str(e)}")
            return {'success': False, 'response': 'Error processing relationship button', 'handler': 'relationship_button_error'}
    
    def _handle_accept_trainer(self, phone: str, button_id: str) -> Dict:
        """Client accepting trainer invitation"""
        try:
            from services.relationships import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            trainer_id = button_id.replace('accept_trainer_', '')
            
            # Get client_id
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('client_id'):
                return {'success': False, 'response': 'Error: Client ID not found', 'handler': 'button_error'}
            
            client_id = user['client_id']
            
            # Approve relationship
            success = relationship_service.approve_relationship(trainer_id, client_id)
            
            if success:
                return self._notify_relationship_accepted(phone, trainer_id, client_id, 'trainer')
            
            return {'success': False, 'response': 'Failed to accept invitation', 'handler': 'accept_trainer_failed'}
            
        except Exception as e:
            log_error(f"Error accepting trainer: {str(e)}")
            return {'success': False, 'response': 'Error accepting invitation', 'handler': 'accept_trainer_error'}
    
    def _handle_decline_trainer(self, phone: str, button_id: str) -> Dict:
        """Client declining trainer invitation"""
        try:
            from services.relationships import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            trainer_id = button_id.replace('decline_trainer_', '')
            
            # Get client_id
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('client_id'):
                return {'success': False, 'response': 'Error: Client ID not found', 'handler': 'button_error'}
            
            client_id = user['client_id']
            
            # Decline relationship
            success = relationship_service.decline_relationship(trainer_id, client_id)
            
            if success:
                return self._notify_relationship_declined(phone, trainer_id, client_id, 'trainer')
            
            return {'success': False, 'response': 'Failed to decline invitation', 'handler': 'decline_trainer_failed'}
            
        except Exception as e:
            log_error(f"Error declining trainer: {str(e)}")
            return {'success': False, 'response': 'Error declining invitation', 'handler': 'decline_trainer_error'}
    
    def _handle_accept_client(self, phone: str, button_id: str) -> Dict:
        """Trainer accepting client invitation"""
        try:
            from services.relationships import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            client_id = button_id.replace('accept_client_', '')
            
            # Get trainer_id
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('trainer_id'):
                return {'success': False, 'response': 'Error: Trainer ID not found', 'handler': 'button_error'}
            
            trainer_id = user['trainer_id']
            
            # Approve relationship
            success = relationship_service.approve_relationship(trainer_id, client_id)
            
            if success:
                return self._notify_relationship_accepted(phone, trainer_id, client_id, 'client')
            
            return {'success': False, 'response': 'Failed to accept invitation', 'handler': 'accept_client_failed'}
            
        except Exception as e:
            log_error(f"Error accepting client: {str(e)}")
            return {'success': False, 'response': 'Error accepting invitation', 'handler': 'accept_client_error'}
    
    def _handle_decline_client(self, phone: str, button_id: str) -> Dict:
        """Trainer declining client invitation"""
        try:
            from services.relationships import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            client_id = button_id.replace('decline_client_', '')
            
            # Get trainer_id
            user = self.auth_service.check_user_exists(phone)
            if not user or not user.get('trainer_id'):
                return {'success': False, 'response': 'Error: Trainer ID not found', 'handler': 'button_error'}
            
            trainer_id = user['trainer_id']
            
            # Decline relationship
            success = relationship_service.decline_relationship(trainer_id, client_id)
            
            if success:
                return self._notify_relationship_declined(phone, trainer_id, client_id, 'client')
            
            return {'success': False, 'response': 'Failed to decline invitation', 'handler': 'decline_client_failed'}
            
        except Exception as e:
            log_error(f"Error declining client: {str(e)}")
            return {'success': False, 'response': 'Error declining invitation', 'handler': 'decline_client_error'}
    
    def _notify_relationship_accepted(self, phone: str, trainer_id: str, client_id: str, accepted_role: str) -> Dict:
        """Notify both parties when relationship is accepted"""
        try:
            if accepted_role == 'trainer':
                # Client accepted trainer
                trainer_result = self.db.table('trainers').select('first_name, last_name, phone_number').eq(
                    'trainer_id', trainer_id
                ).execute()
                
                if trainer_result.data:
                    trainer = trainer_result.data[0]
                    trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                    
                    # Notify client
                    msg = f"✅ You're now connected with {trainer_name}!"
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify trainer
                    client_result = self.db.table('clients').select('first_name, last_name').eq(
                        'client_id', client_id
                    ).execute()
                    
                    if client_result.data:
                        client = client_result.data[0]
                        client_name = f"{client.get('first_name')} {client.get('last_name')}"
                        trainer_msg = f"✅ {client_name} accepted your invitation!"
                        self.whatsapp.send_message(trainer['phone_number'], trainer_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'accept_trainer'}
            
            else:
                # Trainer accepted client
                client_result = self.db.table('clients').select('first_name, last_name, phone_number').eq(
                    'client_id', client_id
                ).execute()
                
                if client_result.data:
                    client = client_result.data[0]
                    client_name = f"{client.get('first_name')} {client.get('last_name')}"
                    
                    # Notify trainer
                    msg = f"✅ You're now connected with {client_name}!"
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify client
                    trainer_result = self.db.table('trainers').select('first_name, last_name').eq(
                        'trainer_id', trainer_id
                    ).execute()
                    
                    if trainer_result.data:
                        trainer = trainer_result.data[0]
                        trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                        client_msg = f"✅ {trainer_name} accepted your invitation!"
                        self.whatsapp.send_message(client['phone_number'], client_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'accept_client'}
            
            return {'success': False, 'response': 'Error notifying parties', 'handler': 'notification_error'}
            
        except Exception as e:
            log_error(f"Error notifying relationship accepted: {str(e)}")
            return {'success': False, 'response': 'Error sending notifications', 'handler': 'notification_error'}
    
    def _notify_relationship_declined(self, phone: str, trainer_id: str, client_id: str, declined_role: str) -> Dict:
        """Notify both parties when relationship is declined"""
        try:
            if declined_role == 'trainer':
                # Client declined trainer
                trainer_result = self.db.table('trainers').select('first_name, last_name, phone_number').eq(
                    'trainer_id', trainer_id
                ).execute()
                
                if trainer_result.data:
                    trainer = trainer_result.data[0]
                    trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                    
                    # Notify client
                    msg = f"You declined the invitation from {trainer_name}."
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify trainer
                    client_result = self.db.table('clients').select('first_name, last_name').eq(
                        'client_id', client_id
                    ).execute()
                    
                    if client_result.data:
                        client = client_result.data[0]
                        client_name = f"{client.get('first_name')} {client.get('last_name')}"
                        trainer_msg = f"ℹ️ {client_name} declined your invitation."
                        self.whatsapp.send_message(trainer['phone_number'], trainer_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'decline_trainer'}
            
            else:
                # Trainer declined client
                client_result = self.db.table('clients').select('first_name, last_name, phone_number').eq(
                    'client_id', client_id
                ).execute()
                
                if client_result.data:
                    client = client_result.data[0]
                    client_name = f"{client.get('first_name')} {client.get('last_name')}"
                    
                    # Notify trainer
                    msg = f"You declined the invitation from {client_name}."
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify client
                    trainer_result = self.db.table('trainers').select('first_name, last_name').eq(
                        'trainer_id', trainer_id
                    ).execute()
                    
                    if trainer_result.data:
                        trainer = trainer_result.data[0]
                        trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                        client_msg = f"ℹ️ {trainer_name} declined your invitation."
                        self.whatsapp.send_message(client['phone_number'], client_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'decline_client'}
            
            return {'success': False, 'response': 'Error notifying parties', 'handler': 'notification_error'}
            
        except Exception as e:
            log_error(f"Error notifying relationship declined: {str(e)}")
            return {'success': False, 'response': 'Error sending notifications', 'handler': 'notification_error'}