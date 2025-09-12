import requests
import hashlib
import hmac
from datetime import datetime
import pytz
from typing import Optional, Dict, List
import json

from utils.logger import log_error, log_info

class WhatsAppService:
    """Handle all WhatsApp API interactions"""
    
    def __init__(self, config, supabase_client, logger):
        self.config = config
        self.db = supabase_client
        self.logger = logger
        self.sa_tz = pytz.timezone(config.TIMEZONE)

        # Store WhatsApp credentials as instance attributes
       self.access_token = config.ACCESS_TOKEN
       self.phone_number_id = config.PHONE_NUMBER_ID
        
        # Track processed messages to prevent duplicates
        self.processed_messages = set()
    
    def verify_webhook_signature(self, request) -> bool:
        """Verify webhook signature from WhatsApp (security improvement)"""
        try:
            # If no webhook verify token configured, skip verification
            if not self.config.WEBHOOK_VERIFY_TOKEN:
                return True
            
            # Get signature from headers
            signature = request.headers.get('X-Hub-Signature-256', '')
            if not signature:
                log_warning("No webhook signature found")
                return True  # For now, allow unsigned requests
            
            # Calculate expected signature
            payload = request.get_data()
            expected_signature = hmac.new(
                self.config.WEBHOOK_VERIFY_TOKEN.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            provided_signature = signature.replace('sha256=', '')
            
            return hmac.compare_digest(expected_signature, provided_signature)
            
        except Exception as e:
            log_error(f"Error verifying webhook signature: {str(e)}")
            return True  # Don't block on verification errors
    
    def is_duplicate_message(self, message_id: str) -> bool:
        """Check if message has already been processed"""
        if message_id in self.processed_messages:
            return True
        
        self.processed_messages.add(message_id)
        
        # Keep set size manageable
        if len(self.processed_messages) > 1000:
            self.processed_messages.clear()
        
        return False
    
    def send_message(self, phone_number: str, message_text: str) -> Dict:
        """Send WhatsApp message and log it"""
        
        if not self.config.ACCESS_TOKEN or not self.config.PHONE_NUMBER_ID:
            log_error("Missing WhatsApp credentials")
            return {'success': False, 'error': 'WhatsApp not configured'}
        
        url = f"https://graph.facebook.com/v18.0/{self.config.PHONE_NUMBER_ID}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.config.ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messaging_product': 'whatsapp',
            'to': phone_number,
            'text': {'body': message_text}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                log_info(f"Message sent to {phone_number}")
                
                # Log to database
                self.log_message(phone_number, message_text, 'outgoing')
                
                return {
                    'success': True,
                    'message_id': response.json().get('messages', [{}])[0].get('id')
                }
            else:
                log_error(f"WhatsApp API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'WhatsApp API error: {response.status_code}'
                }
                
        except Exception as e:
            log_error(f"Error sending WhatsApp message: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_template_message(self, phone_number: str, template_name: str, 
                            parameters: list = None) -> Dict:
        """Send WhatsApp template message (for notifications)"""
        
        if not self.config.ACCESS_TOKEN or not self.config.PHONE_NUMBER_ID:
            return {'success': False, 'error': 'WhatsApp not configured'}
        
        url = f"https://graph.facebook.com/v18.0/{self.config.PHONE_NUMBER_ID}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.config.ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Build template data
        template_data = {
            'name': template_name,
            'language': {'code': 'en'}
        }
        
        if parameters:
            template_data['components'] = [{
                'type': 'body',
                'parameters': [{'type': 'text', 'text': param} for param in parameters]
            }]
        
        data = {
            'messaging_product': 'whatsapp',
            'to': phone_number,
            'type': 'template',
            'template': template_data
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                return {'success': True}
            else:
                log_error(f"Template message error: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending template: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_media_message(self, phone_number: str, media_url: str, 
                          media_type: str = 'image', caption: str = None) -> Dict:
        """Send media message (for workout programs with GIFs)"""
        
        if not self.config.ACCESS_TOKEN or not self.config.PHONE_NUMBER_ID:
            return {'success': False, 'error': 'WhatsApp not configured'}
        
        url = f"https://graph.facebook.com/v18.0/{self.config.PHONE_NUMBER_ID}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.config.ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        media_object = {
            'link': media_url
        }
        
        if caption:
            media_object['caption'] = caption
        
        data = {
            'messaging_product': 'whatsapp',
            'to': phone_number,
            'type': media_type,
            media_type: media_object
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                return {'success': True}
            else:
                log_error(f"Media message error: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending media: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def log_message(self, phone_number: str, message_text: str, direction: str):
        """Log message to database"""
        
        if not self.db:
            return
        
        try:
            # Get sender info
            trainer_id = None
            client_id = None
            
            # Check if it's a trainer
            trainer_result = self.db.table('trainers').select('id').eq(
                'whatsapp', phone_number
            ).execute()
            
            if trainer_result.data:
                trainer_id = trainer_result.data[0]['id']
            else:
                # Check if it's a client
                client_result = self.db.table('clients').select(
                    'id, trainer_id'
                ).eq('whatsapp', phone_number).execute()
                
                if client_result.data:
                    client_id = client_result.data[0]['id']
                    trainer_id = client_result.data[0]['trainer_id']
            
            # Insert message log
            self.db.table('messages').insert({
                'trainer_id': trainer_id,
                'client_id': client_id,
                'whatsapp_from': phone_number if direction == 'incoming' else 'system',
                'whatsapp_to': 'system' if direction == 'incoming' else phone_number,
                'message_text': message_text,
                'direction': direction,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
        except Exception as e:
            log_error(f"Error logging message: {str(e)}")
    
    def check_health(self) -> str:
        """Check WhatsApp service health"""
        if self.config.ACCESS_TOKEN and self.config.PHONE_NUMBER_ID:
            return 'configured'
        else:
            return 'not configured'
    
    def get_message_status(self, message_id: str) -> Optional[Dict]:
        """Get status of a sent message"""
        # This would require webhook status updates
        # For now, return None
        return None

    def send_message_with_buttons(self, phone_number: str, message: str, buttons: List[Dict]) -> Dict:
        """Send WhatsApp message with quick reply buttons"""
        
        if not self.config.ACCESS_TOKEN or not self.config.PHONE_NUMBER_ID:
            return {'success': False, 'error': 'WhatsApp not configured'}
        
        url = f"https://graph.facebook.com/v18.0/{self.config.PHONE_NUMBER_ID}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.config.ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": message
                },
                "action": {
                    "buttons": buttons[:3]  # WhatsApp limits to 3 buttons
                }
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                log_info(f"Button message sent to {phone_number}")
                
                # Log to database
                self.log_message(phone_number, message, 'outgoing')
                
                return {
                    'success': True,
                    'message_id': response.json().get('messages', [{}])[0].get('id')
                }
            else:
                log_error(f"WhatsApp button message error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'WhatsApp API error: {response.status_code}'
                }
                
        except Exception as e:
            log_error(f"Error sending button message: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def send_interactive_list(self, phone: str, header: str, body: str, 
                              button_text: str, sections: list) -> Dict:
        """Send an interactive list message to WhatsApp"""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {
                        "type": "text",
                        "text": header
                    },
                    "body": {
                        "text": body
                    },
                    "footer": {
                        "text": "Powered by Refiloe AI 💪"
                    },
                    "action": {
                        "button": button_text,
                        "sections": sections
                    }
                }
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            log_info(f"Interactive list sent to {phone}")
            return {'success': True, 'response': response.json()}
            
        except Exception as e:
            log_error(f"Error sending interactive list: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_button_message(self, phone: str, body: str, buttons: list) -> Dict:
        """Send a button message to WhatsApp"""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
            
            # WhatsApp allows maximum 3 buttons
            if len(buttons) > 3:
                buttons = buttons[:3]
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": body
                    },
                    "action": {
                        "buttons": buttons
                    }
                }
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            log_info(f"Button message sent to {phone}")
            return {'success': True, 'response': response.json()}
            
        except Exception as e:
            log_error(f"Error sending button message: {str(e)}")
            return {'success': False, 'error': str(e)}
