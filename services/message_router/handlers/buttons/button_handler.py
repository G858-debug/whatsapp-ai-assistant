"""
Main Button Handler
Coordinates button responses and delegates to specific handlers
"""
from typing import Dict
from utils.logger import log_info, log_error

from .relationship_buttons import RelationshipButtonHandler
from .registration_buttons import RegistrationButtonHandler
from .client_creation_buttons import ClientCreationButtonHandler
from .contact_confirmation_buttons import ContactConfirmationButtonHandler
from .timeout_buttons import TimeoutButtonHandler


class ButtonHandler:
    """Main button handler that delegates to specific button handlers"""

    def __init__(self, supabase_client, whatsapp_service, auth_service, reg_service=None, task_service=None, timeout_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.reg_service = reg_service
        self.task_service = task_service
        self.timeout_service = timeout_service

        # Initialize sub-handlers
        self.relationship_handler = RelationshipButtonHandler(
            self.db, self.whatsapp, self.auth_service
        )
        self.registration_handler = RegistrationButtonHandler(
            self.db, self.whatsapp, self.auth_service, self.reg_service, self.task_service
        )
        self.client_creation_handler = ClientCreationButtonHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service
        )
        self.contact_confirmation_handler = ContactConfirmationButtonHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service
        )

        # Initialize timeout handler if timeout service is available
        if self.timeout_service and self.task_service:
            self.timeout_handler = TimeoutButtonHandler(
                self.db, self.whatsapp, self.task_service, self.timeout_service
            )
        else:
            self.timeout_handler = None
    
    def handle_button_response(self, phone: str, button_id: str) -> Dict:
        """Handle button responses by delegating to appropriate handler"""
        try:
            log_info(f"Handling button response: {button_id} from {phone}")
            
            # Check if button_id is a command (starts with /)
            if button_id.startswith('/'):
                log_info(f"Button is a command: {button_id} - routing through command processing")
                # Route command buttons through the normal message processing flow
                # Import here to avoid circular imports
                from services.message_router.message_router import MessageRouter
                router = MessageRouter(self.db, self.whatsapp)
                # Process as a regular message (no button_id to avoid infinite loop)
                return router.route_message(phone, button_id, button_id=None)
            
            # Delegate to appropriate handler based on button type
            if button_id.startswith(('accept_trainer_', 'decline_trainer_', 'accept_client_', 'decline_client_', 'send_invitation_', 'cancel_invitation_', 'resend_invite_', 'cancel_invite_', 'contact_client_')):
                return self.relationship_handler.handle_relationship_button(phone, button_id)

            elif button_id.startswith(('approve_new_client_', 'reject_new_client_')) or button_id == 'share_contact_instructions':
                return self.client_creation_handler.handle_client_creation_button(phone, button_id)

            elif button_id.startswith(('accept_invitation_', 'decline_invitation_')):
                return self.client_creation_handler.handle_invitation_button(phone, button_id)

            elif button_id in ['register_trainer', 'register_client', 'login_trainer', 'login_client']:
                return self.registration_handler.handle_registration_button(phone, button_id)

            elif button_id.startswith('confirm_contact_'):
                return self.contact_confirmation_handler.handle_contact_confirmation_button(phone, button_id)

            elif button_id in ['client_fills_profile', 'trainer_fills_profile', 'send_secondary_invitation', 'cancel_add_client', 'add_client_type', 'add_client_share']:
                return self.client_creation_handler.handle_add_client_button(phone, button_id)

            elif button_id in ['continue_task', 'start_over', 'resume_add_client', 'start_fresh_add_client']:
                if self.timeout_handler:
                    return self.timeout_handler.handle_timeout_button(phone, button_id)
                else:
                    log_error("Timeout handler not initialized")
                    return {'success': False, 'response': 'Service unavailable', 'handler': 'timeout_handler_unavailable'}

            else:
                log_error(f"Unknown button ID: {button_id}")
                return {'success': False, 'response': 'Unknown button action', 'handler': 'button_unknown'}
                
        except Exception as e:
            log_error(f"Error handling button response: {str(e)}")
            return {'success': False, 'response': 'Error processing button', 'handler': 'button_error'}