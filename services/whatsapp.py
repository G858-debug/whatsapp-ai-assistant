"""WhatsApp messaging service"""
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error, log_warning

class WhatsAppService:
    """Handle WhatsApp message sending and receiving"""
    
    def __init__(self, config, supabase_client, logger):
        self.config = config
        self.db = supabase_client
        self.logger = logger
        self.api_url = config.WHATSAPP_API_URL
        self.api_token = config.WHATSAPP_API_TOKEN
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Test mode support
        self.test_mode = False
        self.test_output_file = "testing/outputs/whatsapp_messages.json"
    
    def send_message(self, phone_number: str, message: str, 
                    buttons: List[Dict] = None) -> Dict:
        """Send WhatsApp message"""
        try:
            # Format phone number
            phone = self._format_phone_number(phone_number)
            
            # Test mode: write to file instead of sending
            if self.test_mode:
                return self._write_test_message(phone, message, buttons, 'text')
            
            # Build message payload
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message}
            }
            
            # Add buttons if provided
            if buttons:
                payload["type"] = "interactive"
                payload["interactive"] = {
                    "type": "button",
                    "body": {"text": message},
                    "action": {"buttons": buttons[:3]}  # Max 3 buttons
                }
            
            # Send request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Message sent to {phone}")
                return {'success': True, 'message_id': response.json().get('messages', [{}])[0].get('id')}
            else:
                log_error(f"Failed to send message: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending WhatsApp message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_template_message(self, to_phone: str, template_name: str,
                             language_code: str, components: list) -> bool:
        """
        Send a WhatsApp template message

        Args:
            to_phone: Recipient phone number (with country code)
            template_name: Name of approved template
            language_code: Language code (e.g., 'en')
            components: List of template components with parameters

        Returns:
            bool: Success status
        """
        try:
            # Clean phone number
            to_phone = self._clean_phone_number(to_phone)

            # Prepare template message
            message_data = {
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language_code
                    },
                    "components": components
                }
            }

            # Send via WhatsApp API
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=message_data,
                timeout=10
            )

            if response.status_code == 200:
                log_info(f"Template {template_name} sent to {to_phone}")
                return True
            else:
                log_error(f"Failed to send template: {response.text}")
                return False

        except Exception as e:
            log_error(f"Error sending template message: {str(e)}")
            return False
    
    def send_media_message(self, phone_number: str, media_url: str, 
                          media_type: str = 'image', caption: str = None) -> Dict:
        """Send media message (image, document, etc)"""
        try:
            phone = self._format_phone_number(phone_number)
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": media_type,
                media_type: {
                    "link": media_url
                }
            }
            
            if caption and media_type in ['image', 'video']:
                payload[media_type]["caption"] = caption
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Media sent to {phone}")
                return {'success': True}
            else:
                log_error(f"Failed to send media: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending media message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark message as read"""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.api_url}/messages",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            log_error(f"Error marking message as read: {str(e)}")
            return False
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number to WhatsApp format"""
        # Remove all non-digits
        digits = ''.join(filter(str.isdigit, phone))

        # If it already looks like an international number (11+ digits), use as-is
        if len(digits) >= 11:
            return digits

        # Handle South African numbers only (10 digits starting with 0, or 9 digits)
        if digits.startswith('0') and len(digits) == 10:
            # South African number starting with 0 (e.g., 0731234567)
            return '27' + digits[1:]
        elif len(digits) == 9 and digits.startswith(('7', '8', '6')):
            # South African mobile number without leading 0 (e.g., 731234567)
            return '27' + digits

        # For any other format, return as-is (assume it's already international)
        return digits

    def _clean_phone_number(self, phone: str) -> str:
        """
        Clean and format phone number to WhatsApp format
        Alias for _format_phone_number to ensure South African numbers start with 27
        """
        return self._format_phone_number(phone)
    
    def send_bulk_messages(self, recipients: List[Dict], message: str) -> Dict:
        """Send bulk messages to multiple recipients"""
        results = {
            'sent': [],
            'failed': []
        }
        
        for recipient in recipients:
            phone = recipient.get('phone')
            name = recipient.get('name', 'User')
            
            # Personalize message
            personalized = message.replace('{name}', name)
            
            result = self.send_message(phone, personalized)
            
            if result['success']:
                results['sent'].append(phone)
            else:
                results['failed'].append({'phone': phone, 'error': result.get('error')})
        
        return results

    def send_button_message(self, phone_number: str, message: str, 
                           buttons: List[Dict]) -> Dict:
        """Send WhatsApp message with buttons"""
        try:
            # Format phone number
            phone = self._format_phone_number(phone_number)
            
            # Test mode: write to file instead of sending
            if self.test_mode:
                return self._write_test_message(phone, message, buttons, 'button')
            
            # Build interactive message payload with buttons
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": message
                    },
                    "action": {
                        "buttons": []
                    }
                }
            }
            
            # Format buttons (WhatsApp allows max 3 buttons, max 20 chars per title)
            for i, button in enumerate(buttons[:3]):
                title = button.get('title', 'Option')
                # Truncate to 20 chars if needed, but try to keep it readable
                if len(title) > 20:
                    # Remove emoji if present to save space
                    title_no_emoji = ''.join(c for c in title if ord(c) < 0x1F000)
                    if len(title_no_emoji) <= 20:
                        title = title_no_emoji.strip()
                    else:
                        title = title[:20]
                
                payload["interactive"]["action"]["buttons"].append({
                    "type": "reply",
                    "reply": {
                        "id": button.get('id', f'button_{i}'),
                        "title": title
                    }
                })
            
            # Send request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Button message sent to {phone}")
                return {'success': True, 'message_id': response.json().get('messages', [{}])[0].get('id')}
            else:
                log_error(f"Failed to send button message: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending WhatsApp button message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_list_message(self, phone: str, body: str, button_text: str, sections: List[Dict]) -> Dict:
        """
        Send WhatsApp list message
        
        Args:
            phone: Recipient phone number
            body: Message body text
            button_text: Text for the button that opens the list (e.g., "View Sections")
            sections: List of sections with rows
                [
                    {
                        "title": "Section Title",
                        "rows": [
                            {"id": "row_id", "title": "Row Title", "description": "Row Description"}
                        ]
                    }
                ]
        
        Returns:
            Dict with success status
        """
        try:
            # Format phone number
            formatted_phone = self._format_phone_number(phone)
            
            # Test mode: write to file instead of sending
            if self.test_mode:
                return self._write_test_message(formatted_phone, body, sections, 'list')
            
            # Build interactive list message payload
            payload = {
                "messaging_product": "whatsapp",
                "to": formatted_phone,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": body
                    },
                    "action": {
                        "button": button_text,
                        "sections": sections
                    }
                }
            }
            
            # Send request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"List message sent to {formatted_phone}")
                return {'success': True, 'message_id': response.json().get('messages', [{}])[0].get('id')}
            else:
                log_error(f"Failed to send list message: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending WhatsApp list message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_document(self, phone_number: str, document_url: str, 
                     filename: str = None, caption: str = None) -> Dict:
        """Send document (PDF, CSV, etc) via WhatsApp"""
        try:
            phone = self._format_phone_number(phone_number)
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "document",
                "document": {
                    "link": document_url
                }
            }
            
            if filename:
                payload["document"]["filename"] = filename
            
            if caption:
                payload["document"]["caption"] = caption
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Document sent to {phone}")
                return {'success': True, 'message_id': response.json().get('messages', [{}])[0].get('id')}
            else:
                log_error(f"Failed to send document: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending document: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_flow_message(self, flow_message: Dict) -> Dict:
        """Send WhatsApp flow message"""
        try:
            # Extract phone number and format it
            phone = self._format_phone_number(flow_message.get('to', ''))
            
            # Update the phone number in the message
            flow_message['to'] = phone
            
            # Send request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=flow_message,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Flow message sent to {phone}")
                return {'success': True, 'message_id': response.json().get('messages', [{}])[0].get('id')}
            else:
                log_error(f"Failed to send flow message: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending WhatsApp flow message: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _write_test_message(self, phone: str, message: str, buttons: List[Dict] = None, message_type: str = 'text') -> Dict:
        """Write message to test file instead of sending to WhatsApp"""
        try:
            import os
            
            # Create test output directory if it doesn't exist
            os.makedirs(os.path.dirname(self.test_output_file), exist_ok=True)
            
            # Create message entry
            test_message = {
                'timestamp': datetime.now(self.sa_tz).isoformat(),
                'to': phone,
                'type': message_type,
                'message': message,
                'buttons': buttons if buttons else [],
                'message_id': f'test_{datetime.now().timestamp()}'
            }
            
            # Read existing messages or create new list
            messages = []
            if os.path.exists(self.test_output_file):
                try:
                    with open(self.test_output_file, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    messages = []
            
            # Add new message
            messages.append(test_message)
            
            # Write back to file
            with open(self.test_output_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            
            log_info(f"Test message logged to {phone}: {message[:50]}...")
            
            return {
                'success': True, 
                'message_id': test_message['message_id'],
                'test_mode': True
            }
            
        except Exception as e:
            log_error(f"Error writing test message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def enable_test_mode(self, output_file: str = None):
        """Enable test mode"""
        self.test_mode = True
        if output_file:
            self.test_output_file = output_file
        log_info(f"WhatsApp test mode enabled, output: {self.test_output_file}")
    
    def disable_test_mode(self):
        """Disable test mode"""
        self.test_mode = False
        log_info("WhatsApp test mode disabled")