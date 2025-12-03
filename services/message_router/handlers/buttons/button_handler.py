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
from services.auth.core.user_manager import UserManager


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

            elif button_id.startswith('confirm_delete_') or button_id == 'cancel_delete':
                # Delete account confirmation buttons
                log_info(f"Routing {button_id} to delete account handler")
                return self._handle_delete_account_button(phone, button_id)
            
            elif button_id.startswith('final_confirm_delete_') or button_id == 'final_cancel_delete':
                # Final delete account confirmation buttons (second confirmation)
                log_info(f"Routing {button_id} to final delete account handler")
                return self._handle_final_delete_confirmation(phone, button_id)

            elif button_id.startswith('help_'):
                # Help category buttons (help_account, help_clients, etc.)
                log_info(f"Routing {button_id} to help category handler")
                return self._handle_help_category(phone, button_id)

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
            # First check if it's a universal command (works in any state)
            from ..universal_command_handler import UniversalCommandHandler
            universal_handler = UniversalCommandHandler(
                self.auth_service, self.task_service, self.whatsapp
            )
            universal_result = universal_handler.handle_universal_command(phone, button_id)
            
            if universal_result is not None:
                # It was a universal command, return the result
                return universal_result
            
            # Not a universal command, check login status
            role = self.auth_service.get_login_status(phone)
            
            if not role:
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
            return logged_in_handler.handle_logged_in_button(phone, button_id, role)
            
        except Exception as e:
            log_error(f"Error handling command button: {str(e)}")
            return {'success': False, 'response': 'Error processing command', 'handler': 'command_button_error'}
    
    def _handle_help_category(self, phone: str, button_id: str) -> Dict:
        """
        Handle help category buttons (help_account, help_clients, etc.)
        Shows clickable command buttons for the selected category
        """
        try:
            # Get user's role
            role = self.auth_service.get_login_status(phone)
            
            # Define command buttons for each category (max 3 buttons per message)
            trainer_categories = {
                'help_account': {
                    'title': '👤 *Account Management*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/view-profile', 'title': '👤 View Profile'},
                        {'id': '/edit-profile', 'title': '✏️ Edit Profile'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_account2': {
                    'title': '👤 *Account Management*\n\nMore commands:',
                    'buttons': [
                        {'id': '/delete-account', 'title': '🗑️ Delete Account'},
                        {'id': '/stop', 'title': '⛔ Stop Task'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_clients': {
                    'title': '👥 *Client Management*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/invite-trainee', 'title': '📧 Invite Client'},
                        {'id': '/view-trainees', 'title': '📋 View Clients'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_clients2': {
                    'title': '👥 *Client Management*\n\nMore commands:',
                    'buttons': [
                        {'id': '/remove-trainee', 'title': '❌ Remove Client'},
                        {'id': '/create-trainee', 'title': '➕ Create Client'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_habits': {
                    'title': '🎯 *Habit Management*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/create-habit', 'title': '➕ Create Habit'},
                        {'id': '/view-habits', 'title': '📋 View Habits'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_habits2': {
                    'title': '🎯 *Habit Management*\n\nMore commands:',
                    'buttons': [
                        {'id': '/edit-habit', 'title': '✏️ Edit Habit'},
                        {'id': '/delete-habit', 'title': '🗑️ Delete Habit'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_assign': {
                    'title': '📌 *Habit Assignment*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/assign-habit', 'title': '📌 Assign Habit'},
                        {'id': '/unassign-habit', 'title': '❌ Unassign Habit'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_progress': {
                    'title': '📊 *Progress Tracking*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/view-trainee-progress', 'title': '📈 Client Progress'},
                        {'id': '/trainee-weekly-report', 'title': '📅 Weekly Report'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_dashboard': {
                    'title': '📈 *Dashboard & Reports*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/trainer-dashboard', 'title': '📊 Dashboard'},
                        {'id': '/view-trainees', 'title': '📋 View Clients'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                }
            }
            
            client_categories = {
                'help_account': {
                    'title': '👤 *Account Management*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/view-profile', 'title': '👤 View Profile'},
                        {'id': '/edit-profile', 'title': '✏️ Edit Profile'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_account2': {
                    'title': '👤 *Account Management*\n\nMore commands:',
                    'buttons': [
                        {'id': '/delete-account', 'title': '🗑️ Delete Account'},
                        {'id': '/stop', 'title': '⛔ Stop Task'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_trainers': {
                    'title': '👨‍🏫 *Trainer Management*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/search-trainer', 'title': '🔍 Search Trainers'},
                        {'id': '/view-trainers', 'title': '📋 View Trainers'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_trainers2': {
                    'title': '👨‍🏫 *Trainer Management*\n\nMore commands:',
                    'buttons': [
                        {'id': '/remove-trainer', 'title': '❌ Remove Trainer'},
                        {'id': '/invite-trainer', 'title': '📧 Invite Trainer'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_habits': {
                    'title': '🎯 *Habit Tracking*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/view-my-habits', 'title': '📋 My Habits'},
                        {'id': '/log-habits', 'title': '✅ Log Habits'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_habits2': {
                    'title': '🎯 *Habit Tracking*\n\nMore commands:',
                    'buttons': [
                        {'id': '/view-progress', 'title': '📈 View Progress'},
                        {'id': '/weekly-report', 'title': '📅 Weekly Report'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                },
                'help_reports': {
                    'title': '📊 *Progress Reports*\n\nSelect a command:',
                    'buttons': [
                        {'id': '/weekly-report', 'title': '📅 Weekly Report'},
                        {'id': '/monthly-report', 'title': '📆 Monthly Report'},
                        {'id': '/help', 'title': '📚 Back to Help'}
                    ]
                }
            }
            
            # Get the appropriate category
            categories = trainer_categories if role == 'trainer' else client_categories
            category = categories.get(button_id)
            
            if not category:
                self.whatsapp.send_message(phone, "Sorry, I couldn't find that help category.")
                return {'success': False, 'response': 'Category not found', 'handler': 'help_category_not_found'}
            
            # Send with command buttons
            self.whatsapp.send_button_message(phone, category['title'], category['buttons'])
            
            return {
                'success': True,
                'response': category['title'],
                'handler': 'help_category'
            }
            
        except Exception as e:
            log_error(f"Error handling help category: {str(e)}")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}")
            self.whatsapp.send_message(phone, "Sorry, there was an error showing that help category.")
            return {'success': False, 'response': 'Error showing help category', 'handler': 'help_category_error'}
    
    def _handle_profile_view_button(self, phone: str, button_id: str) -> Dict:
        """
        Handle profile section view buttons (view_basic_info, view_fitness_goals, etc.)
        """
        try:
            from services.profile_viewer.profile_viewer import ProfileViewer
            
            # Get user's login status (returns role string or None)
            role = self.auth_service.get_login_status(phone)
            
            if not role:
                self.whatsapp.send_message(phone, "Please log in first to view your profile.")
                return {'success': False, 'response': 'Not logged in', 'handler': 'profile_view_not_logged_in'}
            
            # Get user_id by role
            user_id = self.auth_service.get_user_id_by_role(phone, role)
            
            if not user_id:
                log_error(f"User ID not found for {phone} with role {role}")
                self.whatsapp.send_message(phone, "Sorry, there was an error with your account. Please try logging in again.")
                return {'success': False, 'response': 'User ID not found', 'handler': 'profile_view_user_id_error'}
            
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
    
    def _handle_delete_account_button(self, phone: str, button_id: str) -> Dict:
        """
        Handle first delete account confirmation button
        Shows second confirmation with final warning
        """
        try:
            # Check if cancelled
            if button_id == 'cancel_delete':
                msg = (
                    "✅ *Account Deletion Cancelled*\n\n"
                    "Your account is safe. No changes were made.\n\n"
                    "Type /help to see what you can do."
                )
                self.whatsapp.send_message(phone, msg)
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'delete_account_cancelled'
                }
            
            # Extract role from button_id (confirm_delete_trainer or confirm_delete_client)
            role = button_id.replace('confirm_delete_', '')
            
            # Get user info
            login_status = self.auth_service.get_login_status(phone)
            if not login_status or login_status != role:
                msg = "❌ Invalid session. Please try again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'delete_invalid_session'}
            
            user_id = self.auth_service.get_user_id_by_role(phone, role)
            if not user_id:
                msg = "❌ User ID not found. Please try again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'delete_user_id_not_found'}
            
            # Check if user has other role
            roles = self.auth_service.get_user_roles(phone)
            other_role = 'client' if role == 'trainer' else 'trainer'
            has_other_role = bool(roles[other_role])
            
            # Build final confirmation message
            final_warning = (
                "⚠️ *FINAL CONFIRMATION*\n\n"
                f"This is your last chance to cancel!\n\n"
                f"Deleting your *{role.title()}* account will:\n"
            )
            
            if role == 'trainer':
                final_warning += (
                    "• Permanently remove all your trainer data\n"
                    "• Remove you from all client lists\n"
                    "• Delete all habits you created\n"
                    "• Remove all habit assignments\n"
                )
            else:
                final_warning += (
                    "• Permanently remove all your client data\n"
                    "• Remove you from all trainer lists\n"
                    "• Delete all your habit logs\n"
                )
            
            if has_other_role:
                final_warning += f"\n✅ Your {other_role} account will remain active."
            else:
                final_warning += "\n⚠️ Your entire account will be deleted."
            
            final_warning += "\n\n*THIS CANNOT BE UNDONE!*"
            
            # Send final confirmation with buttons
            button_message = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": final_warning
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": f"final_confirm_delete_{role}_{user_id}",
                                    "title": "⚠️ DELETE NOW"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "final_cancel_delete",
                                    "title": "❌ Cancel"
                                }
                            }
                        ]
                    }
                }
            }
            
            result = self.whatsapp.send_button_message(button_message)
            
            if result.get('success'):
                return {
                    'success': True,
                    'response': final_warning,
                    'handler': 'delete_final_confirmation_sent'
                }
            else:
                msg = "❌ Error sending confirmation. Please try again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'delete_button_send_error'}
        
        except Exception as e:
            log_error(f"Error handling delete account button: {str(e)}")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}")
            msg = "❌ Error processing deletion. Your account is safe."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'delete_button_error'}
    
    def _handle_final_delete_confirmation(self, phone: str, button_id: str) -> Dict:
        """
        Handle final delete account confirmation button
        Actually executes the deletion
        """
        try:
            # Check if cancelled
            if button_id == 'final_cancel_delete':
                msg = (
                    "✅ *Account Deletion Cancelled*\n\n"
                    "Your account is safe. No changes were made.\n\n"
                    "Type /help to see what you can do."
                )
                self.whatsapp.send_message(phone, msg)
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'delete_account_cancelled_final'
                }
            
            # Extract role and user_id from button_id (final_confirm_delete_trainer_TR_ASRA_111)
            parts = button_id.replace('final_confirm_delete_', '').split('_', 1)
            if len(parts) != 2:
                msg = "❌ Invalid confirmation. Please try again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'delete_invalid_button_format'}
            
            role, user_id = parts
            
            # Verify user session
            login_status = self.auth_service.get_login_status(phone)
            if not login_status or login_status != role:
                msg = "❌ Invalid session. Please try again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'delete_invalid_session_final'}
            
            # Verify user_id matches
            current_user_id = self.auth_service.get_user_id_by_role(phone, role)
            if current_user_id != user_id:
                msg = "❌ User ID mismatch. Please try again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'delete_user_id_mismatch'}
            
            log_info(f"Executing account deletion for {phone} ({role})")
            
            # Execute deletion using UserManager directly
            user_manager = UserManager(self.db)
            success = user_manager.delete_user_role(phone, role)
            
            if success:
                # Check if user has other role
                roles = self.auth_service.get_user_roles(phone)
                other_role = 'client' if role == 'trainer' else 'trainer'
                
                if roles[other_role]:
                    # User still has other role
                    msg = (
                        f"✅ *{role.title()} Account Deleted*\n\n"
                        f"Your {role} account has been permanently deleted.\n\n"
                        f"Your {other_role} account is still active.\n\n"
                        f"Type /help to see what you can do as a {other_role}."
                    )
                else:
                    # User completely deleted
                    msg = (
                        "✅ *Account Deleted*\n\n"
                        "Your account has been permanently deleted.\n\n"
                        "Thank you for using Refiloe. You're welcome back anytime!\n\n"
                        "To register again, just send me a message."
                    )
                
                self.whatsapp.send_message(phone, msg)
                
                log_info(f"Account deletion completed for {phone}")
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'delete_account_success'
                }
            else:
                # Deletion failed
                msg = (
                    "❌ *Deletion Failed*\n\n"
                    "Sorry, I encountered an error deleting your account.\n\n"
                    "Your account is still active. Please try again or contact support."
                )
                self.whatsapp.send_message(phone, msg)
                
                return {
                    'success': False,
                    'response': msg,
                    'handler': 'delete_account_failed'
                }
        
        except Exception as e:
            log_error(f"Error executing account deletion: {str(e)}")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}")
            
            msg = (
                "❌ *Deletion Failed*\n\n"
                "Sorry, I encountered an error deleting your account.\n\n"
                "Your account is still active. Please try again or contact support."
            )
            self.whatsapp.send_message(phone, msg)
            
            return {
                'success': False,
                'response': msg,
                'handler': 'delete_execution_error'
            }
