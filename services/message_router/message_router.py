"""
Main Message Router - Phase 1 Integration
Routes incoming messages based on authentication status and user role
"""
from typing import Dict, Optional
from datetime import datetime
from utils.logger import log_info, log_error
from services.auth import AuthenticationService, RegistrationService, TaskService
from services.auth.core.user_manager import UserManager

from .handlers.buttons.button_handler import ButtonHandler
from .handlers.universal_command_handler import UniversalCommandHandler
from .handlers.new_user_handler import NewUserHandler
# from .handlers.login_handler import LoginHandler
# from .handlers.logged_in_user_handler import LoggedInUserHandler  # Now accessed through button_handler
# from .utils.message_history import MessageHistoryManager


class MessageRouter:
    """Routes messages to appropriate handlers based on user authentication state"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = AuthenticationService(supabase_client)
        self.user_manager = UserManager(supabase_client)
        # todo: will be deleted after client onboarding clean
        self.reg_service = RegistrationService(supabase_client)
        self.task_service = TaskService(supabase_client)
        
        # Initialize handlers
        # todo: reg_service will be deleted after client onboarding clean
        self.button_handler = ButtonHandler(self.db, self.whatsapp, self.auth_service, self.reg_service, self.task_service)
        self.universal_command_handler = UniversalCommandHandler(
            self.auth_service, self.task_service, self.whatsapp
        )
        # todo: reg_service will be deleted after client onboarding clean
        self.new_user_handler = NewUserHandler(
            self.db, self.whatsapp, self.auth_service, self.reg_service, self.task_service
        )
        # self.login_handler = LoginHandler(
        #     self.db, self.whatsapp, self.auth_service, self.task_service
        # )
        # Logged-in user handling is now done through button_handler
        # self.message_history = MessageHistoryManager(self.db)
    
    def route_message(self, phone: str, message: str, button_id: str = None) -> Dict:
        """
        Main routing logic - determines where to send the message
        Returns: {'success': bool, 'response': str, 'handler': str}
        """
        try:
            log_info(f"Routing message from {phone}: {message[:50]}")

            # Step 0: Check for button responses (includes registration buttons)
            if button_id:
                log_info(f"Button message received - phone: {phone}, button_id: {button_id}")
                log_info(f"Routing to button_handler.handle_button_response")
                return self.button_handler.handle_button_response(phone, button_id)

            # Step 0.1: Check for WhatsApp template quick reply buttons
            # These come as regular messages with specific text patterns
            # todo: added for custom whatsapp message template, should be in separate files and should be in more clean and full proof way if possible
            if message.strip() in ['✅ Accept invitation', '❌ Decline']:
                log_info(f"Template button message received - phone: {phone}, button_text: '{message.strip()}'")
                log_info(f"Routing to _handle_template_response")
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
            # todo : will be deleted after the client onbording and client add work
            client_task = self.task_service.get_running_task(phone, 'client')
            
            if client_task and client_task.get('task_type') == 'registration':
                from services.flows import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.continue_registration(phone, message, 'client', client_task)
            
            # Step 3: Check if user exists (direct call to user_manager)
            user = self.user_manager.check_user_exists(phone)
            
            if not user:
                # New user - start registration flow
                return self.new_user_handler.handle_new_user(phone, message)
            
            # Step 4: Check login status (direct access to avoid extra layer)
            login_status = user.get('login_status')  # Direct from user dict
            
            if not login_status:
                # User exists but not logged in
                # Try auto-login if user has only one role
                auto_login_result = self._try_auto_login(phone, user)
                
                if auto_login_result:
                    log_info(f"Auto-logged in {phone} as {auto_login_result}")
                    login_status = auto_login_result
               
            
            # Step 5: User is logged in - route through button_handler
            # Button handler delegates to logged_in_user_handler for unified message/button handling
            return self.button_handler.handle_logged_in_message(phone, message, login_status)
            
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
            log_info(f"[_handle_template_response] START - phone: {phone}, button_text: '{button_text}'")

            # Find pending invitation for this phone number
            # Check for multiple statuses to handle both Flow button and quick reply button clicks
            invitation = self.db.table('client_invitations').select('*').eq(
                'client_phone', phone
            ).in_('status', ['pending', 'pending_client_completion', 'sent', 'accepted']).order(
                'created_at', desc=True
            ).limit(1).execute()

            log_info(f"[_handle_template_response] Invitation query result - found: {len(invitation.data) > 0}, count: {len(invitation.data) if invitation.data else 0}")

            if not invitation.data:
                log_error(f"[_handle_template_response] No pending invitation found for {phone}")
                return {
                    'success': False,
                    'response': "No pending invitation found. If you have an invitation, please use the link in the message.",
                    'handler': 'template_no_invitation'
                }

            invitation_data = invitation.data[0]
            invitation_id = invitation_data['id']
            log_info(f"[_handle_template_response] Invitation found - id: {invitation_id}, status: {invitation_data.get('status')}, trainer_id: {invitation_data.get('trainer_id')}")

            if button_text == '✅ Accept invitation':
                log_info(f"[_handle_template_response] Client {phone} accepting invitation {invitation_id} via template")

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

                log_info(f"[_handle_template_response] Launching client onboarding flow - invitation_id: {invitation_id}, trainer_id: {invitation_data['trainer_id']}, trainer_name: '{trainer_name}', phone: {phone}")

                flow_result = invitation_handler._launch_client_onboarding_flow(
                    phone=phone,
                    invitation_id=invitation_id,
                    trainer_id=invitation_data['trainer_id'],
                    trainer_name=trainer_name
                )

                log_info(f"[_handle_template_response] Flow launch result - success: {flow_result.get('success')}, error: {flow_result.get('error', 'None')}")

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
                log_info(f"[_handle_template_response] Client {phone} declining invitation {invitation_id} via template")

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
    
    def _try_auto_login(self, phone: str, user: Dict) -> Optional[str]:
        """
        Try to auto-login user if they have only one role
        
        Args:
            phone: User's phone number
            user: User data from users table
        
        Returns:
            'trainer' or 'client' if auto-login successful, None otherwise
        """
        try:
            trainer_id = user.get('trainer_id')
            client_id = user.get('client_id')
            
            # If user has both roles, auto-login as trainer (priority role)
            if trainer_id and client_id:
                log_info(f"User {phone} has both roles, auto-logging in as trainer (priority)")
                # Direct update to avoid extra layer
                clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                self.db.table('users').update({
                    'login_status': 'trainer',
                    'updated_at': datetime.now().isoformat()
                }).eq('phone_number', clean_phone).execute()
                
                # Send informational message about switching roles
                switch_msg = (
                    "👋 Welcome back!\n\n"
                    "You're logged in as a *Trainer*.\n\n"
                    "💡 *Want to interact as a Client?*\n"
                    "Delete your trainer account by typing:\n"
                    "`/delete_account`\n\n"
                    "After deletion, your next message will automatically identify you as a client."
                )
                self.whatsapp.send_message(phone, switch_msg)
                
                return 'trainer'
            
            # If user has only trainer role, auto-login as trainer
            if trainer_id and not client_id:
                log_info(f"Auto-logging in {phone} as trainer (trainer_id: {trainer_id})")
                # Direct update to avoid extra layer
                clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                self.db.table('users').update({
                    'login_status': 'trainer',
                    'updated_at': datetime.now().isoformat()
                }).eq('phone_number', clean_phone).execute()
                return 'trainer'
            
            # If user has only client role, auto-login as client
            if client_id and not trainer_id:
                log_info(f"Auto-logging in {phone} as client (client_id: {client_id})")
                # Direct update to avoid extra layer
                clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                self.db.table('users').update({
                    'login_status': 'client',
                    'updated_at': datetime.now().isoformat()
                }).eq('phone_number', clean_phone).execute()
                return 'client'
            
            # User has no roles (shouldn't happen, but handle it)
            log_error(f"User {phone} exists but has no trainer_id or client_id")
            return None
            
        except Exception as e:
            log_error(f"Error in auto-login: {str(e)}")
            return None