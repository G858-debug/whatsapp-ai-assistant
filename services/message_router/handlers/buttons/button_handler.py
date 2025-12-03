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
from .invitation_buttons import InvitationButtonHandler


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
        # todo: will be deleted after client onboarding clean
        self.registration_handler = RegistrationButtonHandler(
            self.db, self.whatsapp, self.auth_service, self.reg_service, self.task_service
        )
        self.client_creation_handler = ClientCreationButtonHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service
        )
        self.contact_confirmation_handler = ContactConfirmationButtonHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service
        )
        self.invitation_handler = InvitationButtonHandler(
            self.db, self.whatsapp, self.auth_service
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
            log_info(f"Button pattern matching for button_id: {button_id}")

            # Check if button_id is a command (starts with /)
            if button_id.startswith('/'):
                log_info(f"Button is a command: {button_id} - routing to logged_in_user_handler")
                return self._handle_command_button(phone, button_id)

            # CRITICAL: Check for accept_invitation_/decline_invitation_ FIRST
            # These must be checked before accept_client_/decline_client_ to avoid conflicts
            if button_id.startswith(('accept_invitation_', 'decline_invitation_')):
                log_info(f"Routing {button_id} to InvitationButtonHandler for WhatsApp Flow launch")
                return self.invitation_handler.handle_invitation_button(phone, button_id)

            # Delegate to appropriate handler based on button type
            # Check for client relationship buttons (accept_client_{invitation_id} / decline_client_{invitation_id})
            if button_id.startswith(('accept_client_', 'decline_client_')):
                # Extract the ID part (could be UUID invitation_id or numeric client_id)
                id_part = button_id.replace('accept_client_', '').replace('decline_client_', '')

                # Check if this is a UUID invitation_id (from client_invitations table)
                # UUIDs contain hyphens, numeric client_ids do not
                if '-' in id_part:
                    # This is likely a UUID invitation_id, route to invitation handler
                    return self.invitation_handler.handle_invitation_button(phone, button_id)

                # Otherwise, this is a numeric client_id, route to relationship handler
                return self.relationship_handler.handle_relationship_button(phone, button_id)

            elif button_id.startswith(('accept_trainer_', 'decline_trainer_', 'send_invitation_', 'cancel_invitation_', 'resend_invite_', 'cancel_invite_', 'contact_client_')):
                return self.relationship_handler.handle_relationship_button(phone, button_id)

            elif button_id.startswith(('approve_new_client_', 'reject_new_client_')) or button_id == 'share_contact_instructions':
                return self.client_creation_handler.handle_client_creation_button(phone, button_id)

            elif button_id in ['register_client', 'login_trainer', 'login_client']:
                return self.registration_handler.handle_registration_button(phone, button_id)

            elif button_id.startswith('confirm_contact_') or button_id in ['edit_contact_name', 'edit_contact_phone', 'edit_contact_again', 'confirm_edited_contact']:
                return self.contact_confirmation_handler.handle_contact_confirmation_button(phone, button_id)

            elif button_id in ['client_fills_profile', 'trainer_fills_profile', 'send_secondary_invitation', 'cancel_add_client', 'add_client_type', 'add_client_share']:
                return self.client_creation_handler.handle_add_client_button(phone, button_id)

            elif button_id in ['use_standard', 'set_custom', 'discuss_later']:
                return self.client_creation_handler.handle_pricing_button(phone, button_id)

            elif button_id in ['continue_task', 'start_over', 'resume_add_client', 'start_fresh_add_client']:
                if self.timeout_handler:
                    return self.timeout_handler.handle_timeout_button(phone, button_id)
                else:
                    log_error("Timeout handler not initialized")
                    return {'success': False, 'response': 'Service unavailable', 'handler': 'timeout_handler_unavailable'}

            elif button_id.startswith('view_') or button_id == 'back_to_profile':
                # Profile section view buttons (view_basic_info, view_fitness_goals, etc.)
                log_info(f"Routing {button_id} to ProfileViewer")
                return self._handle_profile_view_button(phone, button_id)

            else:
                log_error(f"Unknown button ID: {button_id}")
                return {'success': False, 'response': 'Unknown button action', 'handler': 'button_unknown'}
                
        except Exception as e:
            log_error(f"Error handling button response: {str(e)}")
            return {'success': False, 'response': 'Error processing button', 'handler': 'button_error'}
    
    def handle_logged_in_message(self, phone: str, message: str, role: str) -> Dict:
        """
        Handle messages from logged-in users.
        Called by MessageRouter for logged-in users.
        """
        try:
            # Use logged_in_user_handler for message processing
            from ..logged_in_user_handler import LoggedInUserHandler
            logged_in_handler = LoggedInUserHandler(
                self.db, self.whatsapp, self.auth_service, self.task_service, 
                getattr(self, 'reg_service', None)
            )
            return logged_in_handler.handle_logged_in_user(phone, message, role)
            
        except Exception as e:
            log_error(f"Error handling logged-in message: {str(e)}")
            return {'success': False, 'response': 'Error processing message', 'handler': 'logged_in_message_error'}
    
    def _handle_command_button(self, phone: str, button_id: str) -> Dict:
        """
        Handle command buttons (starting with /) by routing through logged_in_user_handler.
        This avoids creating a new MessageRouter instance and circular imports.
        """
        try:
            # Get user's login status to determine role
            login_status = self.auth_service.get_login_status(phone)
            
            if not login_status:
                # User not logged in - route through message router for proper handling
                from services.message_router.message_router import MessageRouter
                router = MessageRouter(self.db, self.whatsapp)
                return router.route_message(phone, button_id, button_id=None)
            
            # User is logged in - use logged_in_user_handler directly
            from ..logged_in_user_handler import LoggedInUserHandler
            logged_in_handler = LoggedInUserHandler(
                self.db, self.whatsapp, self.auth_service, self.task_service, 
                getattr(self, 'reg_service', None)
            )
            return logged_in_handler.handle_logged_in_button(phone, button_id, login_status)
            
        except Exception as e:
            log_error(f"Error handling command button: {str(e)}")
            return {'success': False, 'response': 'Error processing command', 'handler': 'command_button_error'}
    
    def _handle_profile_view_button(self, phone: str, button_id: str) -> Dict:
        """
        Handle profile section view buttons (view_basic_info, view_fitness_goals, etc.)
        """
        try:
            from services.profile_viewer.profile_viewer import ProfileViewer
            
            # Get user's login status
            login_status = self.auth_service.get_login_status(phone)
            
            if not login_status:
                self.whatsapp.send_message(phone, "Please log in first to view your profile.")
                return {'success': False, 'response': 'Not logged in', 'handler': 'profile_view_not_logged_in'}
            
            # Extract role and user_id from login_status
            role = login_status.get('role')
            user_id = login_status.get('trainer_id') if role == 'trainer' else login_status.get('client_id')
            
            log_info(f"Profile view button - role: {role}, user_id: {user_id}, button_id: {button_id}")
            
            # Initialize ProfileViewer
            profile_viewer = ProfileViewer(self.db, self.whatsapp)
            
            # Handle back_to_profile button or /view-profile command
            if button_id in ['back_to_profile', '/view-profile']:
                return profile_viewer.show_profile_menu(phone, role, user_id)
            
            # Handle view_* buttons (e.g., view_basic_info)
            if button_id.startswith('view_'):
                # Extract section_id (e.g., 'view_basic_info' -> 'view_basic_info')
                return profile_viewer.show_profile_section(phone, role, user_id, button_id)
            
            return {'success': False, 'response': 'Unknown profile button', 'handler': 'profile_view_unknown'}
            
        except Exception as e:
            log_error(f"Error handling profile view button: {str(e)}")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}")
            self.whatsapp.send_message(phone, "Sorry, there was an error viewing your profile. Please try again.")
            return {'success': False, 'response': 'Error viewing profile', 'handler': 'profile_view_error'}