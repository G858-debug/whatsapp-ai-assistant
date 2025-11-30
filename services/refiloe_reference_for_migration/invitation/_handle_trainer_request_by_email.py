"""
 Handle Trainer Request By Email
Handle client request for specific trainer by email
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_trainer_request_by_email(self, client_phone: str, message: str) -> Dict:
    """Handle client request for specific trainer by email"""
    try:
        message_lower = message.strip().lower()
        
        # Check if this looks like a trainer email request
        email_patterns = [
            r'trainer\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'i want trainer\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'find trainer\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]
        
        import re
        trainer_email = None
        
        for pattern in email_patterns:
            match = re.search(pattern, message_lower)
            if match:
                trainer_email = match.group(1)
                break
        
        if not trainer_email:
            return {'handled': False}
        
        # Look up trainer by email
        trainer_result = self.db.table('trainers').select('*').eq('email', trainer_email).execute()
        
        if not trainer_result.data:
            return {
                'handled': True,
                'message': f"I couldn't find a trainer with email {trainer_email}. Please check the email address or ask them to register as a trainer first."
            }
        
        trainer = trainer_result.data[0]
        trainer_id = trainer['id']
        trainer_name = trainer['name']
        business_name = trainer.get('business_name', f"{trainer_name}'s Training")
        
        # Check if client already has this trainer
        existing_client = self.db.table('clients').select('*').eq('whatsapp', client_phone).eq('trainer_id', trainer_id).execute()
        
        if existing_client.data:
            return {
                'handled': True,
                'message': f"You're already connected with {trainer_name}! You can start booking sessions and tracking your progress."
            }
        
        # Check for existing pending request
        existing_request = self.db.table('clients').select('*').eq('whatsapp', client_phone).eq('trainer_id', trainer_id).eq('connection_status', 'pending').execute()
        
        if existing_request.data:
            return {
                'handled': True,
                'message': f"You already have a pending request with {trainer_name}. Please wait for them to approve your request."
            }
        
        # Create client request (pending approval)
        client_data = {
            'name': 'Pending Client',  # Will be updated during registration
            'whatsapp': client_phone,
            'trainer_id': trainer_id,
            'connection_status': 'pending',
            'requested_by': 'client',
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        result = self.db.table('clients').insert(client_data).execute()
        
        if result.data:
            # Notify trainer of new client request
            trainer_phone = trainer['whatsapp']
            trainer_notification = (
                f"👋 *New Client Request!*\n\n"
                f"Someone wants to train with you!\n"
                f"📱 Phone: {client_phone}\n\n"
                f"💡 *Actions:*\n"
                f"• `/pending_requests` - View all requests\n"
                f"• `/approve_client {client_phone}` - Approve this client\n"
                f"• `/decline_client {client_phone}` - Decline this request\n\n"
                f"What would you like to do?"
            )
            
            try:
                from app import app
                whatsapp_service = app.config['services']['whatsapp']
                whatsapp_service.send_message(trainer_phone, trainer_notification)
            except Exception as e:
                log_warning(f"Could not notify trainer of client request: {str(e)}")
            
            return {
                'handled': True,
                'message': (
                    f"✅ *Request Sent!*\n\n"
                    f"I've sent your training request to {trainer_name} from {business_name}.\n\n"
                    f"They'll review your request and get back to you soon. You'll receive a notification once they respond!\n\n"
                    f"💡 *What happens next:*\n"
                    f"• {trainer_name} will review your request\n"
                    f"• If approved, you'll start registration\n"
                    f"• If declined, you can search for other trainers\n\n"
                    f"Thanks for your patience! 🙏"
                )
            }
        else:
            return {
                'handled': True,
                'message': "❌ Sorry, there was an error sending your trainer request. Please try again."
            }
            
    except Exception as e:
        log_error(f"Error handling trainer request by email: {str(e)}")
        return {'handled': False}
