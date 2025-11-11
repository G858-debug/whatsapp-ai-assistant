"""
Contact Share Handler
Handles WhatsApp vCard contact messages shared by trainers
"""
from typing import Dict, Optional, List
from utils.logger import log_info, log_error, log_warning
from services.validation import get_validator


def parse_vcard(webhook_data: Dict) -> Optional[Dict]:
    """
    Parse vCard contact data from WhatsApp webhook payload

    Args:
        webhook_data: Full webhook payload from WhatsApp

    Returns:
        Dict with parsed contact data or None if parsing fails
        {
            'name': str,           # Full formatted name
            'first_name': str,     # First name
            'last_name': str,      # Last name (optional)
            'phones': List[str],   # List of phone numbers
            'emails': List[str],   # List of emails (optional)
            'phone': str           # Primary phone (first mobile number)
        }
    """
    try:
        # Extract contact data from webhook structure
        # Webhook format: entry[0] -> changes[0] -> value -> messages[0] -> contacts[0]
        if not webhook_data or 'entry' not in webhook_data:
            log_error("Invalid webhook data: missing 'entry'")
            return None

        entry = webhook_data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        if not messages:
            log_error("No messages found in webhook data")
            return None

        message = messages[0]
        message_type = message.get('type')

        if message_type != 'contacts':
            log_warning(f"Message type is not 'contacts': {message_type}")
            return None

        # Extract contacts array
        contacts = message.get('contacts', [])
        if not contacts:
            log_error("No contacts found in contact message")
            return None

        # Get first contact (WhatsApp typically sends one contact per message)
        contact = contacts[0]

        # Parse name information
        name_data = contact.get('name', {})
        formatted_name = name_data.get('formatted_name', '')
        first_name = name_data.get('first_name', '')
        last_name = name_data.get('last_name', '')

        # Use formatted_name if available, otherwise construct from parts
        full_name = formatted_name or f"{first_name} {last_name}".strip()
        if not full_name:
            log_error("No name found in contact")
            return None

        # Parse phone numbers
        phones_data = contact.get('phones', [])
        phones = []
        primary_phone = None

        for phone_entry in phones_data:
            phone_number = phone_entry.get('phone', '').strip()
            phone_type = phone_entry.get('type', '').lower()

            if phone_number:
                phones.append(phone_number)

                # Prefer mobile/cell numbers as primary
                if not primary_phone or phone_type in ['mobile', 'cell', 'iphone']:
                    primary_phone = phone_number

        # Use first phone if no mobile found
        if not primary_phone and phones:
            primary_phone = phones[0]

        if not primary_phone:
            log_error("No phone number found in contact")
            return None

        # Parse email addresses (optional)
        emails_data = contact.get('emails', [])
        emails = []

        for email_entry in emails_data:
            email = email_entry.get('email', '').strip()
            if email:
                emails.append(email)

        # Build parsed contact data
        parsed_contact = {
            'name': full_name,
            'first_name': first_name or full_name.split()[0] if full_name else '',
            'last_name': last_name or ' '.join(full_name.split()[1:]) if full_name and ' ' in full_name else '',
            'phones': phones,
            'emails': emails,
            'phone': primary_phone
        }

        log_info(f"Successfully parsed contact: {parsed_contact['name']} ({parsed_contact['phone']})")
        return parsed_contact

    except Exception as e:
        log_error(f"Error parsing vCard: {str(e)}")
        return None


def create_contact_confirmation_task(
    trainer_phone: str,
    contact_data: Dict,
    task_service,
    role: str = 'trainer'
) -> Optional[str]:
    """
    Create a task to confirm the shared contact details

    Args:
        trainer_phone: Trainer's phone number
        contact_data: Parsed contact data from parse_vcard
        task_service: TaskService instance
        role: User role (default: 'trainer')

    Returns:
        Task ID if successful, None otherwise
    """
    try:
        # Build task data with contact information
        task_data = {
            'step': 'confirm_shared_contact',
            'contact_data': contact_data,
            'action': 'share_contact'
        }

        # Create task
        task_id = task_service.create_task(
            user_id=trainer_phone,
            role=role,
            task_type='confirm_shared_contact',
            task_data=task_data
        )

        if task_id:
            log_info(f"Created contact confirmation task {task_id} for {trainer_phone}")
        else:
            log_error(f"Failed to create contact confirmation task for {trainer_phone}")

        return task_id

    except Exception as e:
        log_error(f"Error creating contact confirmation task: {str(e)}")
        return None


def send_contact_confirmation_message(
    trainer_phone: str,
    contact_data: Dict,
    whatsapp_service
) -> bool:
    """
    Send confirmation message with interactive buttons

    Args:
        trainer_phone: Trainer's phone number
        contact_data: Parsed contact data
        whatsapp_service: WhatsAppService instance

    Returns:
        True if message sent successfully, False otherwise
    """
    try:
        # Format contact details for confirmation
        name = contact_data.get('name', 'Unknown')
        phone = contact_data.get('phone', 'N/A')
        emails = contact_data.get('emails', [])

        # Build confirmation message
        message = (
            f"📇 *Contact Received*\n\n"
            f"*Name:* {name}\n"
            f"*Phone:* {phone}\n"
        )

        if emails:
            message += f"*Email:* {emails[0]}\n"

        message += (
            f"\n"
            f"Would you like to continue with this contact information?"
        )

        # Create interactive buttons
        buttons = [
            {
                'id': 'confirm_contact_yes',
                'title': '✅ Yes, Continue'
            },
            {
                'id': 'confirm_contact_edit',
                'title': '❌ Edit Details'
            }
        ]

        # Send button message
        result = whatsapp_service.send_button_message(
            trainer_phone,
            message,
            buttons
        )

        if result.get('success'):
            log_info(f"Sent contact confirmation to {trainer_phone}")
            return True
        else:
            log_error(f"Failed to send contact confirmation: {result.get('error')}")
            return False

    except Exception as e:
        log_error(f"Error sending contact confirmation message: {str(e)}")
        return False


def handle_contact_message(
    trainer_phone: str,
    webhook_data: Dict,
    task_service,
    whatsapp_service,
    role: str = 'trainer'
) -> Dict:
    """
    Main handler for contact share messages

    Args:
        trainer_phone: Trainer's phone number
        webhook_data: Full webhook payload
        task_service: TaskService instance
        whatsapp_service: WhatsAppService instance
        role: User role (default: 'trainer')

    Returns:
        Dict with success status and message
    """
    try:
        # Parse the vCard contact data
        contact_data = parse_vcard(webhook_data)

        if not contact_data:
            return {
                'success': False,
                'response': "❌ Sorry, I couldn't read that contact. Please try sharing it again.",
                'handler': 'contact_parse_error'
            }

        # Validate and handle vCard edge cases
        validator = get_validator()
        edge_case_result = validator.handle_vcard_edge_cases(contact_data)

        log_info(f"vCard edge case result: {edge_case_result['status']}")

        # Handle edge cases
        if edge_case_result['status'] != 'valid':
            # Create a task to collect missing information
            action = edge_case_result.get('action_required')

            if action in ['ask_phone', 'choose_phone', 'ask_name']:
                task_data = {
                    'step': 'vcard_edge_case',
                    'contact_data': edge_case_result['data'],
                    'action_required': action,
                    'original_contact_data': contact_data
                }

                task_id = task_service.create_task(
                    user_id=trainer_phone,
                    role=role,
                    task_type='vcard_edge_case_handler',
                    task_data=task_data
                )

                if task_id:
                    # Send the edge case message
                    whatsapp_service.send_message(trainer_phone, edge_case_result['message'])

                    return {
                        'success': True,
                        'response': edge_case_result['message'],
                        'handler': f'contact_edge_case_{action}'
                    }
                else:
                    log_error(f"Failed to create vCard edge case task for {trainer_phone}")
                    return {
                        'success': False,
                        'response': "❌ Sorry, I encountered an error. Please try again.",
                        'handler': 'contact_edge_case_task_error'
                    }
            else:
                # Unknown action or error
                return {
                    'success': False,
                    'response': edge_case_result['message'],
                    'handler': 'contact_edge_case_error'
                }

        # Use validated contact data
        validated_contact_data = edge_case_result['data']

        # Create confirmation task
        task_id = create_contact_confirmation_task(
            trainer_phone,
            validated_contact_data,
            task_service,
            role
        )

        if not task_id:
            return {
                'success': False,
                'response': "❌ Sorry, I encountered an error processing the contact. Please try again.",
                'handler': 'contact_task_error'
            }

        # Send confirmation message
        sent = send_contact_confirmation_message(
            trainer_phone,
            validated_contact_data,
            whatsapp_service
        )

        if not sent:
            # Clean up task if message failed
            task_service.stop_task(task_id, role)
            return {
                'success': False,
                'response': "❌ Sorry, I couldn't send the confirmation message. Please try again.",
                'handler': 'contact_message_error'
            }

        return {
            'success': True,
            'response': 'Contact confirmation sent',
            'handler': 'contact_share_handler'
        }

    except Exception as e:
        log_error(f"Error handling contact message: {str(e)}")
        return {
            'success': False,
            'response': "❌ Sorry, I encountered an error. Please try again.",
            'handler': 'contact_handler_error'
        }
