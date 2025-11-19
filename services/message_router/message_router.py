"""
Main Message Router - Phase 1 Integration
Routes incoming messages based on authentication status and user role
"""
from typing import Dict, Optional
from utils.logger import log_info, log_error
from services.auth import AuthenticationService, RegistrationService, TaskService

from .handlers.button_handler import ButtonHandler
from .handlers.universal_command_handler import UniversalCommandHandler
from .handlers.new_user_handler import NewUserHandler
from .handlers.login_handler import LoginHandler
from .handlers.logged_in_user_handler import LoggedInUserHandler
from .utils.message_history import MessageHistoryManager


class MessageRouter:
    """Routes messages to appropriate handlers based on user authentication state"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = AuthenticationService(supabase_client)
        self.reg_service = RegistrationService(supabase_client)
        self.task_service = TaskService(supabase_client)
        
        # Initialize handlers
        self.button_handler = ButtonHandler(self.db, self.whatsapp, self.auth_service, self.reg_service, self.task_service)
        self.universal_command_handler = UniversalCommandHandler(
            self.auth_service, self.task_service, self.whatsapp
        )
        self.new_user_handler = NewUserHandler(
            self.db, self.whatsapp, self.auth_service, self.reg_service, self.task_service
        )
        self.login_handler = LoginHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service
        )
        self.logged_in_user_handler = LoggedInUserHandler(
            self.db, self.whatsapp, self.auth_service, self.task_service, self.reg_service
        )
        self.message_history = MessageHistoryManager(self.db)
    
    def route_message(self, phone: str, message: str, button_id: str = None) -> Dict:
        """
        Main routing logic - determines where to send the message
        Returns: {'success': bool, 'response': str, 'handler': str}
        """
        try:
            log_info(f"Routing message from {phone}: {message[:50]}")

            # Step 0: Check for button responses (Phase 2 invitations)
            if button_id:
                return self.button_handler.handle_button_response(phone, button_id)

            # Step 0.1: Check for WhatsApp template quick reply buttons
            # These come as regular messages with specific text patterns
            if message.strip() in ['✅ Accept invitation', '❌ Decline']:
                log_info(f"Detected template button response: {message.strip()}")
                return self._handle_template_response(phone, message.strip())

            # Step 0.5: Check for /reset_me command (highest priority - works in any state)
            if message.strip().lower() == '/reset_me':
                try:
                    from services.refiloe import RefiloeService
                    refiloe = RefiloeService(self.db)
                    return refiloe._handle_reset_command(phone)
                except Exception as e:
                    log_error(f"Error handling reset command: {str(e)}")
                    return {
                        'success': False,
                        'response': "❌ Reset failed. Please try again or contact support."
                    }

            # Step 1: Check for universal commands (work regardless of state)
            if message.startswith('/'):
                universal_result = self.universal_command_handler.handle_universal_command(phone, message)
                if universal_result is not None:
                    return universal_result
                # If None, it's not a universal command, continue routing
            
            # Step 2: Check for running registration tasks (before checking user exists)
            # This handles the case where registration is in progress but user not created yet
            trainer_task = self.task_service.get_running_task(phone, 'trainer')
            client_task = self.task_service.get_running_task(phone, 'client')
            
            if trainer_task and trainer_task.get('task_type') == 'registration':
                from services.flows import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.continue_registration(phone, message, 'trainer', trainer_task)
            
            if client_task and client_task.get('task_type') == 'registration':
                from services.flows import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.continue_registration(phone, message, 'client', client_task)
            
            # Step 3: Check if user exists
            user = self.auth_service.check_user_exists(phone)
            
            if not user:
                # New user - start registration flow
                return self.new_user_handler.handle_new_user(phone, message)
            
            # Step 4: Check login status
            login_status = self.auth_service.get_login_status(phone)
            
            if not login_status:
                # User exists but not logged in
                return self.login_handler.handle_login_flow(phone, message)
            
            # Step 5: User is logged in - route to role handler
            return self.logged_in_user_handler.handle_logged_in_user(phone, message, login_status)
            
        except Exception as e:
            log_error(f"Error routing message: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'error'
            }

    def _handle_template_response(self, phone: str, button_text: str) -> Dict:
        """Handle responses to template quick reply buttons"""
        try:
            log_info(f"Handling template response from {phone}: {button_text}")

            # Find pending invitation for this phone number
            # Check for multiple statuses to handle both Flow button and quick reply button clicks
            invitation = self.db.table('client_invitations').select('*').eq(
                'client_phone', phone
            ).in_('status', ['pending', 'pending_client_completion', 'sent', 'accepted']).order(
                'created_at', desc=True
            ).limit(1).execute()

            if not invitation.data:
                log_error(f"No pending invitation found for {phone}")
                return {
                    'success': False,
                    'response': "No pending invitation found. If you have an invitation, please use the link in the message.",
                    'handler': 'template_no_invitation'
                }

            invitation_data = invitation.data[0]
            invitation_id = invitation_data['id']

            if button_text == '✅ Accept invitation':
                log_info(f"Client {phone} accepting invitation {invitation_id} via template")

                # Update invitation status
                self.db.table('client_invitations').update({
                    'status': 'accepted'
                }).eq('id', invitation_id).execute()

                # Get trainer details
                trainer = self._get_trainer(invitation_data['trainer_id'])
                trainer_name = 'your trainer'
                if trainer:
                    trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip() or 'your trainer'

                # Launch WhatsApp Flow for profile completion
                flow_message = (
                    f"Great! Let's set up your fitness profile 📝\n\n"
                    f"This helps {trainer_name} create the perfect program for you."
                )

                # Use the invitation handler's flow launch method
                from .handlers.buttons.invitation_buttons import InvitationButtonHandler
                invitation_handler = InvitationButtonHandler(self.db, self.whatsapp, self.auth_service)

                flow_result = invitation_handler._launch_client_onboarding_flow(
                    phone=phone,
                    invitation_id=invitation_id,
                    trainer_id=invitation_data['trainer_id'],
                    trainer_name=trainer_name
                )

                if flow_result.get('success'):
                    return {
                        'success': True,
                        'response': flow_message,
                        'handler': 'template_accept_invitation'
                    }
                else:
                    return {
                        'success': False,
                        'response': 'Failed to launch onboarding flow. Please try again.',
                        'handler': 'template_flow_failed',
                        'error': flow_result.get('error')
                    }

            elif button_text == '❌ Decline':
                log_info(f"Client {phone} declining invitation {invitation_id} via template")

                # Update invitation status
                self.db.table('client_invitations').update({
                    'status': 'declined'
                }).eq('id', invitation_id).execute()

                # Ask for optional reason
                response = (
                    "Thanks for letting us know.\n\n"
                    "Mind sharing why? (Optional)\n"
                    "• Not interested right now\n"
                    "• Found another trainer\n"
                    "• Too expensive\n"
                    "• Other reason\n\n"
                    "You can type your reason or type /skip to finish."
                )

                # Create task for collecting decline reason
                self.task_service.create_task(
                    phone=phone,
                    user_type='client',
                    task_type='decline_reason',
                    task_data={
                        'invitation_id': invitation_id,
                        'trainer_id': str(invitation_data['trainer_id'])
                    }
                )

                # Notify trainer
                trainer_phone = self._get_trainer_phone(invitation_data['trainer_id'])
                if trainer_phone:
                    client_name = invitation_data.get('client_name', 'A client')
                    trainer_msg = f"ℹ️ {client_name} declined your invitation."
                    self.whatsapp.send_message(trainer_phone, trainer_msg)

                return {
                    'success': True,
                    'response': response,
                    'handler': 'template_decline_invitation'
                }

            return {
                'success': False,
                'response': "Unknown template button action",
                'handler': 'template_unknown'
            }

        except Exception as e:
            log_error(f"Error handling template response: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error processing your response. Please try again.",
                'handler': 'template_error'
            }

    def _get_trainer(self, trainer_id: str) -> Optional[Dict]:
        """Get trainer details by ID"""
        try:
            result = self.db.table('trainers').select('*').eq('id', trainer_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            log_error(f"Error getting trainer: {str(e)}")
            return None

    def _get_trainer_phone(self, trainer_id: str) -> Optional[str]:
        """Get trainer phone number by ID"""
        try:
            trainer = self._get_trainer(trainer_id)
            if trainer:
                return trainer.get('whatsapp') or trainer.get('phone')
            return None
        except Exception as e:
            log_error(f"Error getting trainer phone: {str(e)}")
            return None