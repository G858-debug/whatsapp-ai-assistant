"""
Contact Confirmation Button Handler
Handles button responses for contact share confirmations
"""
from typing import Dict
from utils.logger import log_info, log_error


class ContactConfirmationButtonHandler:
    """Handles contact confirmation button responses"""

    def __init__(self, supabase_client, whatsapp_service, auth_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.task_service = task_service

    def handle_contact_confirmation_button(self, phone: str, button_id: str) -> Dict:
        """
        Handle contact confirmation button clicks

        Args:
            phone: User's phone number
            button_id: Button ID clicked (confirm_contact_yes, confirm_contact_edit)

        Returns:
            Dict with success status and response
        """
        try:
            # Get user's role and check if they have a running task
            login_status = self.auth_service.get_login_status(phone)
            if not login_status:
                return {
                    'success': False,
                    'response': "Please log in first to continue.",
                    'handler': 'contact_confirmation_not_logged_in'
                }

            role = login_status
            user_id = self.auth_service.get_user_id_by_role(phone, role)

            if not user_id:
                return {
                    'success': False,
                    'response': "Sorry, I couldn't find your account. Please log in again.",
                    'handler': 'contact_confirmation_user_not_found'
                }

            # Get running task
            task = self.task_service.get_running_task(phone, role)

            if not task or task.get('task_type') != 'confirm_shared_contact':
                return {
                    'success': False,
                    'response': "❌ No contact confirmation in progress. Please share a contact first.",
                    'handler': 'contact_confirmation_no_task'
                }

            task_id = task.get('id')
            task_data = task.get('task_data', {})
            contact_data = task_data.get('contact_data', {})

            # Handle button response
            if button_id == 'confirm_contact_yes':
                return self._handle_confirm_yes(phone, role, user_id, task_id, contact_data)

            elif button_id == 'confirm_contact_edit':
                return self._handle_edit_details(phone, role, task_id, contact_data)

            else:
                log_error(f"Unknown contact confirmation button: {button_id}")
                return {
                    'success': False,
                    'response': "Unknown button action",
                    'handler': 'contact_confirmation_unknown_button'
                }

        except Exception as e:
            log_error(f"Error handling contact confirmation button: {str(e)}")
            return {
                'success': False,
                'response': "❌ Sorry, I encountered an error. Please try again.",
                'handler': 'contact_confirmation_button_error'
            }

    def _handle_confirm_yes(
        self,
        phone: str,
        role: str,
        user_id: str,
        task_id: str,
        contact_data: Dict
    ) -> Dict:
        """Handle 'Yes, Continue' button click - route to add client flow"""
        try:
            from services.relationships.client_checker import ClientChecker

            name = contact_data.get('name', 'Unknown')
            contact_phone = contact_data.get('phone')

            if not contact_phone:
                msg = "❌ Missing phone number in contact. Please share the contact again."
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task_id, role)
                return {'success': False, 'response': msg, 'handler': 'contact_confirmation_no_phone'}

            # Check client status
            client_checker = ClientChecker(self.db, self.whatsapp)
            check_result = client_checker.check_client_status(contact_phone, user_id)

            scenario = check_result.get('scenario')
            log_info(f"Contact {name} ({contact_phone}) scenario: {scenario}")

            # Complete the confirmation task
            self.task_service.complete_task(task_id, role)

            # Route based on scenario
            if scenario == 'SCENARIO_NEW':
                # New client - ask who fills the profile
                msg = (
                    f"🎉 *New Client!*\n\n"
                    f"{name} ({contact_phone}) is new to Refiloe!\n\n"
                    f"Who should fill in their fitness profile?"
                )
                buttons = [
                    {'id': 'client_fills_profile', 'title': '📱 Client Fills'},
                    {'id': 'trainer_fills_profile', 'title': '✏️ I\'ll Fill It'}
                ]
                self.whatsapp.send_button_message(phone, msg, buttons)

                # Create a new task to track the profile filling choice
                self.task_service.create_task(
                    user_id=phone,
                    role='trainer',
                    task_type='add_client_profile_choice',
                    task_data={
                        'step': 'choose_profile_method',
                        'trainer_id': user_id,
                        'contact_data': contact_data
                    }
                )

                return {'success': True, 'response': msg, 'handler': 'contact_confirmed_new_client'}

            elif scenario == 'SCENARIO_AVAILABLE':
                # Client exists but no trainer - send invitation
                client_id = check_result.get('client_id')
                msg = (
                    f"👤 *Existing Client Found!*\n\n"
                    f"{name} is already registered on Refiloe but doesn't have a trainer yet.\n\n"
                    f"I'll send them an invitation to connect with you!"
                )
                self.whatsapp.send_message(phone, msg)

                # Send invitation
                from services.commands.trainer.relationships.invitation_commands import handle_invite_client
                # Note: This will need the invitation system to handle existing clients

                return {'success': True, 'response': msg, 'handler': 'contact_confirmed_existing_available'}

            elif scenario == 'SCENARIO_ALREADY_YOURS':
                # Already this trainer's client
                msg = (
                    f"ℹ️ *Already Your Client!*\n\n"
                    f"{name} is already one of your clients.\n\n"
                    f"You can view their details with /view-trainees"
                )
                self.whatsapp.send_message(phone, msg)
                return {'success': True, 'response': msg, 'handler': 'contact_confirmed_already_yours'}

            elif scenario == 'SCENARIO_HAS_OTHER_TRAINER':
                # Has another trainer - multi-trainer scenario
                msg = (
                    f"👥 *Client Has Another Trainer*\n\n"
                    f"{name} currently trains with another trainer.\n\n"
                    f"Would you like to send them an invitation to work with you as well?"
                )
                buttons = [
                    {'id': 'send_secondary_invitation', 'title': '✅ Yes, Invite'},
                    {'id': 'cancel_add_client', 'title': '❌ Cancel'}
                ]
                self.whatsapp.send_button_message(phone, msg, buttons)

                # Store for secondary invitation flow
                self.task_service.create_task(
                    user_id=phone,
                    role='trainer',
                    task_type='secondary_trainer_invitation',
                    task_data={
                        'step': 'confirm_secondary',
                        'trainer_id': user_id,
                        'contact_data': contact_data,
                        'client_id': check_result.get('client_id')
                    }
                )

                return {'success': True, 'response': msg, 'handler': 'contact_confirmed_has_trainer'}

            else:
                # Unknown scenario
                msg = "❌ Sorry, I encountered an error checking this contact. Please try again."
                self.whatsapp.send_message(phone, msg)
                return {'success': False, 'response': msg, 'handler': 'contact_confirmation_unknown_scenario'}

        except Exception as e:
            log_error(f"Error processing confirmed contact: {str(e)}")
            msg = "❌ Sorry, I encountered an error. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'contact_confirmation_processing_error'}

    def _handle_edit_details(
        self,
        phone: str,
        role: str,
        task_id: str,
        contact_data: Dict
    ) -> Dict:
        """Handle 'Edit Details' button click"""
        try:
            name = contact_data.get('name', 'Unknown')
            contact_phone = contact_data.get('phone', 'N/A')
            emails = contact_data.get('emails', [])

            # Update task to collect edited details
            task_data = {
                'step': 'edit_contact_name',
                'contact_data': contact_data,
                'original_data': contact_data.copy()
            }

            self.task_service.update_task(task_id, role, task_data)

            # Ask for name
            msg = (
                f"📝 *Edit Contact Details*\n\n"
                f"Current name: *{name}*\n"
                f"Current phone: *{contact_phone}*\n"
            )

            if emails:
                msg += f"Current email: *{emails[0]}*\n"

            msg += (
                f"\n"
                f"Let's update the details. First, please send the contact's *full name*:\n\n"
                f"(Type /cancel to go back)"
            )

            self.whatsapp.send_message(phone, msg)

            log_info(f"User {phone} started editing contact: {name}")

            return {
                'success': True,
                'response': msg,
                'handler': 'contact_edit_started'
            }

        except Exception as e:
            log_error(f"Error handling edit details: {str(e)}")
            return {
                'success': False,
                'response': "❌ Sorry, I encountered an error. Please try sharing the contact again.",
                'handler': 'contact_edit_error'
            }
