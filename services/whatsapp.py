"""WhatsApp messaging service"""
import requests
from typing import Dict, List, Optional
from utils.logger import log_info, log_error
import json

class WhatsAppService:
    """Service for sending WhatsApp messages"""
    
    def __init__(self, config, supabase_client, logger):
        self.config = config
        self.db = supabase_client
        self.logger = logger
        self.api_url = config.WHATSAPP_API_URL
        self.api_token = config.WHATSAPP_API_TOKEN
        
    def send_message(self, phone: str, message: str, buttons: List[Dict] = None) -> bool:
        """
        Send WhatsApp message
        
        Args:
            phone: Recipient phone number
            message: Message text
            buttons: Optional button list
            
        Returns:
            True if sent successfully
        """
        try:
            # Format phone number
            phone = self._format_phone(phone)
            
            # Build payload
            payload = {
                'to': phone,
                'type': 'text',
                'text': {
                    'body': message
                }
            }
            
            # Add buttons if provided
            if buttons:
                payload['type'] = 'interactive'
                payload['interactive'] = {
                    'type': 'button',
                    'body': {'text': message},
                    'action': {'buttons': buttons}
                }
            
            # Send request
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Message sent to {phone}")
                return True
            else:
                log_error(f"Failed to send message: {response.status_code}")
                return False
                
        except Exception as e:
            log_error(f"Error sending WhatsApp message: {str(e)}")
            return False
    
    def send_template(self, phone: str, template_name: str, 
                     parameters: List[str] = None) -> bool:
        """Send WhatsApp template message"""
        try:
            phone = self._format_phone(phone)
            
            payload = {
                'to': phone,
                'type': 'template',
                'template': {
                    'name': template_name,
                    'language': {'code': 'en'}
                }
            }
            
            if parameters:
                payload['template']['components'] = [{
                    'type': 'body',
                    'parameters': [
                        {'type': 'text', 'text': param}
                        for param in parameters
                    ]
                }]
            
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            log_error(f"Error sending template: {str(e)}")
            return False
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number for WhatsApp"""
        # Remove all non-digits
        phone = ''.join(filter(str.isdigit, phone))
        
        # Add country code if missing
        if not phone.startswith('27'):
            if phone.startswith('0'):
                phone = '27' + phone[1:]
            else:
                phone = '27' + phone
        
        return phone