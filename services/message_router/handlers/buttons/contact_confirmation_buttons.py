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
        """Handle 'Yes, Continue' button click"""
        try:
            # This is where you would process the confirmed contact
            # For now, we'll just acknowledge and complete the task
            # TODO: Integrate with client creation flow or invitation system

            name = contact_data.get('name', 'the contact')
            contact_phone = contact_data.get('phone', 'N/A')

            # Complete the task
            self.task_service.complete_task(task_id, role)

            # Send confirmation message
            msg = (
                f"✅ *Contact Confirmed!*\n\n"
                f"*Name:* {name}\n"
                f"*Phone:* {contact_phone}\n\n"
                f"Great! I've saved this contact information.\n\n"
                f"What would you like to do next?\n"
                f"• /create-trainee - Add them as a client\n"
                f"• /invite-trainee - Send them an invitation"
            )

            self.whatsapp.send_message(phone, msg)

            log_info(f"Contact confirmed by {phone}: {name}")

            return {
                'success': True,
                'response': msg,
                'handler': 'contact_confirmed',
                'contact_data': contact_data
            }

        except Exception as e:
            log_error(f"Error handling confirm yes: {str(e)}")
            return {
                'success': False,
                'response': "❌ Sorry, I encountered an error confirming the contact.",
                'handler': 'contact_confirm_yes_error'
            }

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
