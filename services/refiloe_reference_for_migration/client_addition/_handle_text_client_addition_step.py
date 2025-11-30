"""
 Handle Text Client Addition Step
Handle text-based client addition steps
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_text_client_addition_step(self, phone: str, message: str, context: Dict) -> Dict:
    """Handle text-based client addition steps"""
    try:
        step = context.get('step', 'name')
        client_data = context.get('client_data', {})
        
        if step == 'name':
            # Validate name
            name = message.strip()
            if len(name) < 2:
                return {
                    'success': False,
                    'message': "Please enter a valid name (at least 2 characters)."
                }
            
            client_data['name'] = name
            
            return {
                'success': True,
                'message': f"Great! Now what's {name}'s phone number?\n\n📱 *Step 2 of 4*\n\nEnter their South African number (e.g., 0821234567)",
                'context': {
                    'step': 'phone',
                    'client_data': client_data
                }
            }
        
        elif step == 'phone':
            # Validate phone number
            from utils.validators import Validators
            validator = Validators()
            
            is_valid, formatted_phone, error = validator.validate_phone_number(message.strip())
            
            if not is_valid:
                return {
                    'success': False,
                    'message': f"❌ {error}\n\nPlease enter a valid South African number (e.g., 0821234567 or +27821234567)"
                }
            
            # Check for duplicate
            user_context = self.get_user_context(phone)
            trainer_id = user_context.get('user_data', {}).get('id')
            
            if trainer_id:
                existing_client = self.db.table('clients').select('*').eq('trainer_id', trainer_id).eq('whatsapp', formatted_phone).execute()
                if existing_client.data:
                    return {
                        'success': False,
                        'message': f"❌ You already have a client with phone number {formatted_phone}.\n\nPlease enter a different number."
                    }
            
            client_data['phone'] = formatted_phone
            
            return {
                'success': True,
                'message': f"Perfect! What's {client_data['name']}'s email address?\n\n📧 *Step 3 of 4*\n\nEnter their email or type 'skip' if they don't have one.",
                'context': {
                    'step': 'email',
                    'client_data': client_data
                }
            }
        
        elif step == 'email':
            # Validate email (optional)
            email_input = message.strip().lower()
            
            if email_input == 'skip':
                client_data['email'] = None
            else:
                from utils.validators import Validators
                validator = Validators()
                
                is_valid, error = validator.validate_email(email_input)
                
                if not is_valid:
                    return {
                        'success': False,
                        'message': f"❌ {error}\n\nPlease enter a valid email or type 'skip'"
                    }
                
                client_data['email'] = email_input
            
            return {
                'success': True,
                'message': f"Excellent! How would you like to add {client_data['name']}?\n\n🤔 *Step 4 of 4*\n\n1️⃣ Send them an invitation (they accept via WhatsApp)\n2️⃣ Add them directly (they can start messaging you)\n\nReply '1' or '2'",
                'context': {
                    'step': 'method',
                    'client_data': client_data
                }
            }
        
        elif step == 'method':
            # Process addition method
            method_input = message.strip()
            
            if method_input == '1':
                # Send invitation
                return self._process_text_client_invitation(phone, client_data)
            elif method_input == '2':
                # Add directly
                return self._process_text_client_direct_add(phone, client_data)
            else:
                return {
                    'success': False,
                    'message': "Please reply '1' to send an invitation or '2' to add them directly."
                }
        
        else:
            return {
                'success': False,
                'message': "❌ Something went wrong. Let's start over. Type /add_client to begin."
            }
            
    except Exception as e:
        log_error(f"Error handling text client addition step: {str(e)}")
        return {
            'success': False,
            'message': "❌ Sorry, there was an error. Please try again."
        }
