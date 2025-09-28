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
    
    def send_message(self, phone_number: str, message: str, 
                    buttons: List[Dict] = None) -> Dict:
        """Send WhatsApp message"""
        try:
            # Format phone number
            phone = self._format_phone_number(phone_number)
            
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
    
    def send_template_message(self, phone_number: str, template_name: str, 
                             parameters: List[str] = None) -> Dict:
        """Send WhatsApp template message"""
        try:
            phone = self._format_phone_number(phone_number)
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"}
                }
            }
            
            if parameters:
                payload["template"]["components"] = [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in parameters]
                }]
            
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
                log_info(f"Template {template_name} sent to {phone}")
                return {'success': True}
            else:
                log_error(f"Failed to send template: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending template message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
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
        
        # Handle South African numbers
        if digits.startswith('0'):
            digits = '27' + digits[1:]
        elif not digits.startswith('27'):
            digits = '27' + digits
        
        return digits
    
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
            
            # Format buttons (WhatsApp allows max 3 buttons)
            for i, button in enumerate(buttons[:3]):
                payload["interactive"]["action"]["buttons"].append({
                    "type": "reply",
                    "reply": {
                        "id": button.get('id', f'button_{i}'),
                        "title": button.get('title', 'Option')[:20]  # Max 20 chars
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