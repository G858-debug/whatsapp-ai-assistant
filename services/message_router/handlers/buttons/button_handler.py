"""
Main Button Handler
Coordinates button responses and delegates to specific handlers
"""
from typing import Dict
from utils.logger import log_info, log_error

from .relationship_buttons import RelationshipButtonHandler
from .registration_buttons import RegistrationButtonHandler
from .client_creation_buttons import ClientCreationButtonHandler


class ButtonHandler:
    """Main button handler that delegates to specific button handlers"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        
        # Initialize sub-handlers
        self.relationship_handler = RelationshipButtonHandler(
            self.db, self.whatsapp, self.auth_service
        )
        self.registration_handler = RegistrationButtonHandler(
            self.db, self.whatsapp, self.auth_service
        )
        self.client_creation_handler = ClientCreationButtonHandler(
            self.db, self.whatsapp, self.auth_service
        )
    
    def handle_button_response(self, phone: str, button_id: str) -> Dict:
        """Handle button responses by delegating to appropriate handler"""
        try:
            log_info(f"Handling button response: {button_id} from {phone}")
            
            # Check if button_id is a command (starts with /)
            if button_id.startswith('/'):
                log_info(f"Button is a command: {button_id}")
                return {'success': True, 'response': 'Command button', 'handler': 'command_button'}
            
            # Delegate to appropriate handler based on button type
            if button_id.startswith(('accept_trainer_', 'decline_trainer_', 'accept_client_', 'decline_client_')):
                return self.relationship_handler.handle_relationship_button(phone, button_id)
            
            elif button_id.startswith(('approve_new_client_', 'reject_new_client_')):
                return self.client_creation_handler.handle_client_creation_button(phone, button_id)
            
            elif button_id in ['register_trainer', 'register_client', 'login_trainer', 'login_client']:
                return self.registration_handler.handle_registration_button(phone, button_id)
            
            else:
                log_error(f"Unknown button ID: {button_id}")
                return {'success': False, 'response': 'Unknown button action', 'handler': 'button_unknown'}
                
        except Exception as e:
            log_error(f"Error handling button response: {str(e)}")
            return {'success': False, 'response': 'Error processing button', 'handler': 'button_error'}