"""
Contact Task Handler
Handles contact share and edit tasks
"""
from typing import Dict
from utils.logger import log_info, log_error, log_warning
from services.validation import get_validator


class ContactTaskHandler:
    """Handles contact-related tasks"""

    def __init__(self, supabase_client, whatsapp_service, task_service, reg_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
        self.reg_service = reg_service

    def handle_contact_task(self, phone: str, message: str, user_id: str, task: Dict) -> Dict:
        """
        Handle contact confirmation and edit tasks

        Args:
            phone: User's phone number
            message: Message text
            user_id: User ID
            task: Running task data

        Returns:
            Dict with success status and response
        """
        try:
            task_type = task.get('task_type')
            task_id = task.get('id')
            task_data = task.get('task_data', {})
            step = task_data.get('step', '')

            # Determine user role from task table
            role = 'trainer' if self.db.table('trainer_tasks').select('id').eq('id', task_id).execute().data else 'client'

            log_info(f"Handling contact task: {task_type}, step: {step}")

            if task_type == 'confirm_shared_contact':
                return self._handle_contact_edit_flow(phone, message, user_id, task_id, task_data, role)
            elif task_type == 'vcard_edge_case_handler':
                return self._handle_vcard_edge_case(phone, message, user_id, task_id, task_data, role)
            else:
                log_error(f"Unknown contact task type: {task_type}")
                return {
                    'success': False,
                    'response': "Unknown task type",
                    'handler': 'contact_task_unknown'
                }

        except Exception as e:
            log_error(f"Error handling contact task: {str(e)}")
            return {
                'success': False,
                'response': "❌ Sorry, I encountered an error. Type /stop to cancel.",
                'handler': 'contact_task_error'
            }

    def _handle_contact_edit_flow(
        self,
        phone: str,
        message: str,
        user_id: str,
        task_id: str,
        task_data: Dict,
        role: str
    ) -> Dict:
        """Handle the contact editing flow with selective field editing"""
        try:
            step = task_data.get('step', '')
            contact_data = task_data.get('contact_data', {})

            # Check for cancel command
            if message.strip().lower() == '/cancel':
                self.task_service.complete_task(task_id, role)
                msg = "❌ Cancelled. The contact was not saved."
                self.whatsapp.send_message(phone, msg)
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'contact_edit_cancelled'
                }

            # Handle editing name step
            if step == 'editing_name':
                # Save the new name
                new_name = message.strip()

                # Basic validation - at least 2 characters
                if len(new_name) < 2:
                    msg = "❌ Name must be at least 2 characters. Please try again."
                    self.whatsapp.send_message(phone, msg)
                    return {
                        'success': True,
                        'response': msg,
                        'handler': 'contact_edit_name_too_short'
                    }

                contact_data['name'] = new_name

                # Extract first and last name
                name_parts = new_name.split(maxsplit=1)
                contact_data['first_name'] = name_parts[0] if name_parts else new_name
                contact_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''

                # Update task data
                task_data['contact_data'] = contact_data

                # Send re-confirmation with buttons
                return self._send_edit_confirmation(phone, role, task_id, task_data, contact_data)

            # Handle editing phone step
            elif step == 'editing_phone':
                # Clean and validate the phone number
                phone_input = message.strip()

                # todo: reg_service will be deleted after client onboarding clean
                # Clean phone number
                if self.reg_service:
                    cleaned_phone = self.reg_service.clean_phone_number(phone_input)
                else:
                    # Basic cleaning
                    cleaned_phone = ''.join(c for c in phone_input if c.isdigit() or c == '+')

                # Basic validation - at least 10 digits
                if len(cleaned_phone.replace('+', '')) < 10:
                    msg = "❌ Invalid phone number. Please enter a valid phone number."
                    self.whatsapp.send_message(phone, msg)
                    return {
                        'success': True,
                        'response': msg,
                        'handler': 'contact_edit_phone_invalid'
                    }

                contact_data['phone'] = cleaned_phone
                contact_data['phones'] = [cleaned_phone]

                # Update task data
                task_data['contact_data'] = contact_data

                # Send re-confirmation with buttons
                return self._send_edit_confirmation(phone, role, task_id, task_data, contact_data)

            else:
                log_error(f"Unknown contact edit step: {step}")
                return {
                    'success': False,
                    'response': "❌ Something went wrong. Type /stop to cancel.",
                    'handler': 'contact_edit_unknown_step'
                }

        except Exception as e:
            log_error(f"Error in contact edit flow: {str(e)}")
            return {
                'success': False,
                'response': "❌ Sorry, I encountered an error. Type /stop to cancel.",
                'handler': 'contact_edit_flow_error'
            }

    def _send_edit_confirmation(
        self,
        phone: str,
        role: str,
        task_id: str,
        task_data: Dict,
        contact_data: Dict
    ) -> Dict:
        """Send confirmation message with updated contact details"""
        try:
            name = contact_data.get('name', 'Unknown')
            phone_num = contact_data.get('phone', 'N/A')

            # Update task to wait for confirmation
            task_data['step'] = 'confirm_edited_contact'
            self.task_service.update_task(task_id, role, task_data)

            # Show updated details with confirmation buttons
            msg = (
                f"✅ *Updated contact details*\n\n"
                f"• Name: *{name}*\n"
                f"• Phone: *{phone_num}*\n\n"
                f"Are these details now correct?"
            )

            buttons = [
                {'id': 'confirm_edited_contact', 'title': '✅ Yes, continue'},
                {'id': 'edit_contact_again', 'title': '❌ Edit again'}
            ]

            self.whatsapp.send_button_message(phone, msg, buttons)

            log_info(f"Sent edit confirmation to {phone}")

            return {
                'success': True,
                'response': msg,
                'handler': 'contact_edit_confirmation_sent'
            }

        except Exception as e:
            log_error(f"Error sending edit confirmation: {str(e)}")
            return {
                'success': False,
                'response': "❌ Error. Please try again.",
                'handler': 'contact_edit_confirmation_error'
            }

    def _handle_vcard_edge_case(
        self,
        phone: str,
        message: str,
        user_id: str,
        task_id: str,
        task_data: Dict,
        role: str
    ) -> Dict:
        """Handle vCard edge cases (missing phone, multiple phones, missing name)"""
        try:
            action_required = task_data.get('action_required')
            contact_data = task_data.get('contact_data', {})
            validator = get_validator()

            log_info(f"Handling vCard edge case: {action_required}")

            # Check for cancel command
            if message.strip().lower() in ['/cancel', '/stop']:
                self.task_service.complete_task(task_id, role)
                msg = "❌ Cancelled. You can try sharing the contact again."
                self.whatsapp.send_message(phone, msg)
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'vcard_edge_case_cancelled'
                }

            # Handle missing phone number
            if action_required == 'ask_phone':
                # Validate the phone number
                is_valid, error_msg, cleaned_phone = validator.validate_phone_number(message, phone)

                if not is_valid:
                    # Check for max retries
                    if validator.has_exceeded_max_retries(phone, 'phone'):
                        restart_msg = validator.get_restart_prompt('phone number')
                        self.whatsapp.send_message(phone, restart_msg)
                        return {
                            'success': True,
                            'response': restart_msg,
                            'handler': 'vcard_edge_case_max_retries'
                        }

                    # Send validation error
                    self.whatsapp.send_message(phone, error_msg)
                    return {
                        'success': True,
                        'response': error_msg,
                        'handler': 'vcard_edge_case_invalid_phone'
                    }

                # Update contact data with validated phone
                contact_data['phone'] = cleaned_phone
                contact_data['phones'] = [cleaned_phone]

                # Complete task and send confirmation
                self.task_service.complete_task(task_id, role)

                # Import and call contact confirmation
                from services.message_handlers.contact_share_handler import (
                    send_contact_confirmation_message,
                    create_contact_confirmation_task
                )

                # Create new confirmation task
                task_id = create_contact_confirmation_task(phone, contact_data, self.task_service, role)

                if task_id:
                    # Send confirmation message
                    send_contact_confirmation_message(phone, contact_data, self.whatsapp)

                    return {
                        'success': True,
                        'response': 'Contact updated and confirmation sent',
                        'handler': 'vcard_edge_case_phone_added'
                    }
                else:
                    log_error(f"Failed to create confirmation task for {phone}")
                    return {
                        'success': False,
                        'response': "❌ Sorry, I encountered an error. Please try again.",
                        'handler': 'vcard_edge_case_task_error'
                    }

            # Handle multiple phone numbers - choose one
            elif action_required == 'choose_phone':
                phone_options = contact_data.get('phone_options', [])

                # Validate choice
                try:
                    choice = int(message.strip())
                    if choice < 1 or choice > len(phone_options):
                        msg = (
                            f"❌ Please choose a number between 1 and {len(phone_options)}.\n\n"
                            f"Type the number of the WhatsApp phone."
                        )
                        self.whatsapp.send_message(phone, msg)
                        return {
                            'success': True,
                            'response': msg,
                            'handler': 'vcard_edge_case_invalid_choice'
                        }

                    # Get selected phone
                    selected_phone = phone_options[choice - 1]

                    # Validate the selected phone
                    is_valid, error_msg, cleaned_phone = validator.validate_phone_number(selected_phone, phone)

                    if not is_valid:
                        # Phone from contact is invalid, ask manually
                        msg = (
                            f"📱 That phone number seems invalid.\n\n"
                            f"Please enter the correct WhatsApp number manually.\n\n"
                            f"*Example:* 0730564882"
                        )
                        self.whatsapp.send_message(phone, msg)

                        # Update task to ask for phone manually
                        task_data['action_required'] = 'ask_phone'
                        self.task_service.update_task(task_id, role, task_data)

                        return {
                            'success': True,
                            'response': msg,
                            'handler': 'vcard_edge_case_phone_invalid'
                        }

                    # Update contact data with selected phone
                    contact_data['phone'] = cleaned_phone
                    contact_data['phones'] = [cleaned_phone]
                    del contact_data['phone_options']  # Clean up

                    # Complete task and send confirmation
                    self.task_service.complete_task(task_id, role)

                    # Import and call contact confirmation
                    from services.message_handlers.contact_share_handler import (
                        send_contact_confirmation_message,
                        create_contact_confirmation_task
                    )

                    # Create new confirmation task
                    task_id = create_contact_confirmation_task(phone, contact_data, self.task_service, role)

                    if task_id:
                        # Send confirmation message
                        send_contact_confirmation_message(phone, contact_data, self.whatsapp)

                        return {
                            'success': True,
                            'response': 'Phone selected and confirmation sent',
                            'handler': 'vcard_edge_case_phone_selected'
                        }
                    else:
                        log_error(f"Failed to create confirmation task for {phone}")
                        return {
                            'success': False,
                            'response': "❌ Sorry, I encountered an error. Please try again.",
                            'handler': 'vcard_edge_case_task_error'
                        }

                except ValueError:
                    msg = (
                        f"❌ Please enter a number (1, 2, 3, etc.).\n\n"
                        f"Which phone number is their WhatsApp?"
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {
                        'success': True,
                        'response': msg,
                        'handler': 'vcard_edge_case_invalid_input'
                    }

            # Handle missing name
            elif action_required == 'ask_name':
                # Validate the name
                is_valid, error_msg = validator.validate_name(message, phone)

                if not is_valid:
                    # Send validation error
                    self.whatsapp.send_message(phone, error_msg)
                    return {
                        'success': True,
                        'response': error_msg,
                        'handler': 'vcard_edge_case_invalid_name'
                    }

                # Update contact data with validated name
                name_parts = message.strip().split(maxsplit=1)
                contact_data['name'] = message.strip()
                contact_data['first_name'] = name_parts[0] if name_parts else message.strip()
                contact_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''

                # Complete task and send confirmation
                self.task_service.complete_task(task_id, role)

                # Import and call contact confirmation
                from services.message_handlers.contact_share_handler import (
                    send_contact_confirmation_message,
                    create_contact_confirmation_task
                )

                # Create new confirmation task
                task_id = create_contact_confirmation_task(phone, contact_data, self.task_service, role)

                if task_id:
                    # Send confirmation message
                    send_contact_confirmation_message(phone, contact_data, self.whatsapp)

                    return {
                        'success': True,
                        'response': 'Name added and confirmation sent',
                        'handler': 'vcard_edge_case_name_added'
                    }
                else:
                    log_error(f"Failed to create confirmation task for {phone}")
                    return {
                        'success': False,
                        'response': "❌ Sorry, I encountered an error. Please try again.",
                        'handler': 'vcard_edge_case_task_error'
                    }

            else:
                log_error(f"Unknown vCard edge case action: {action_required}")
                return {
                    'success': False,
                    'response': "❌ Something went wrong. Type /stop to cancel.",
                    'handler': 'vcard_edge_case_unknown_action'
                }

        except Exception as e:
            log_error(f"Error handling vCard edge case: {str(e)}")
            return {
                'success': False,
                'response': "❌ Sorry, I encountered an error. Type /stop to cancel.",
                'handler': 'vcard_edge_case_error'
            }
