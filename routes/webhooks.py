"""WhatsApp webhook routes"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import traceback
import pytz
from utils.logger import log_error, log_info, log_warning

webhooks_bp = Blueprint('webhooks', __name__)

@webhooks_bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Main WhatsApp webhook endpoint"""
    from flask import current_app
    from config import Config
    
    # Get services from app context
    services = current_app.config.get('services', {})
    whatsapp_service = services.get('whatsapp')
    refiloe_service = services.get('refiloe')
    rate_limiter = services.get('rate_limiter')
    input_sanitizer = services.get('input_sanitizer')
    
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if verify_token == Config.VERIFY_TOKEN:
            log_info("Webhook verified successfully")
            return challenge
        else:
            log_warning("Invalid verification token")
            return 'Invalid verification token', 403
    
    elif request.method == 'POST':
        try:
            if Config.ENABLE_RATE_LIMITING:
                ip_address = request.remote_addr
                if not rate_limiter.check_webhook_rate(ip_address):
                    log_warning(f"Rate limit exceeded for IP: {ip_address}")
                    return jsonify({"error": "Rate limit exceeded"}), 429
            
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            if 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message in change['value']['messages']:
                                    process_message(message, change['value'].get('contacts', []))
            
            return jsonify({"status": "success"}), 200
            
        except Exception as e:
            log_error(f"Webhook processing error: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"error": "Internal server error"}), 500

def process_message(message: dict, contacts: list):
    """Process incoming WhatsApp message"""
    from flask import current_app
    from config import Config
    
    # Get services from app context
    services = current_app.config.get('services', {})
    whatsapp_service = services.get('whatsapp')
    refiloe_service = services.get('refiloe')
    rate_limiter = services.get('rate_limiter')
    input_sanitizer = services.get('input_sanitizer')
    
    try:
        from_number = message['from']
        message_type = message.get('type', 'text')
        
        if Config.ENABLE_RATE_LIMITING:
            allowed, error_msg = rate_limiter.check_message_rate(from_number, message_type)
            if not allowed:
                if error_msg:
                    whatsapp_service.send_message(from_number, error_msg)
                return
        
        contact_name = "User"
        if contacts:
            contact = next((c for c in contacts if c['wa_id'] == from_number), None)
            if contact:
                contact_name = contact.get('profile', {}).get('name', 'User')
        
        message_data = {
            'from': from_number,
            'type': message_type,
            'contact_name': contact_name
        }
        
        if message_type == 'text':
            text_body = message.get('text', {}).get('body', '')
            sanitized, is_safe, warnings = input_sanitizer.sanitize_message(text_body, from_number)
            if not is_safe:
                whatsapp_service.send_message(from_number, "Sorry, your message contained invalid content.")
                return
            message_data['text'] = {'body': sanitized}
        elif message_type == 'audio':
            message_data['audio'] = message.get('audio', {})
        elif message_type == 'image':
            message_data['image'] = message.get('image', {})
        elif message_type == 'interactive':
            message_data['interactive'] = message.get('interactive', {})
        elif message_type == 'button':
            message_data['button'] = message.get('button', {})
        
        response = refiloe_service.process_message(message_data)
        
        if response.get('success') and response.get('message'):
            whatsapp_service.send_message(from_number, response['message'])
            
            if response.get('media_url'):
                whatsapp_service.send_media_message(from_number, response['media_url'], 'image')
            
            if response.get('buttons'):
                whatsapp_service.send_message_with_buttons(
                    from_number,
                    response.get('header', 'Options'),
                    response['buttons']
                )
            
    except Exception as e:
        log_error(f"Message processing error: {str(e)}")
        try:
            whatsapp_service.send_message(
                from_number,
                "Sorry, I encountered an error processing your message. Please try again."
            )
        except:
            pass

def process_whatsapp_message(data: dict, refiloe_service) -> dict:
    """Process incoming WhatsApp messages including interactive responses"""
    try:
        # Extract message details
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])
        
        if not messages:
            return {'status': 'no_message'}
        
        message = messages[0]
        from_number = message.get('from')
        message_type = message.get('type')
        
        # Build message data structure
        message_data = {
            'from': from_number,
            'type': message_type,
            'timestamp': message.get('timestamp')
        }
        
        # Handle different message types
        if message_type == 'text':
            message_data['text'] = message.get('text', {})
            
        elif message_type == 'interactive':
            # Handle interactive message responses
            interactive = message.get('interactive', {})
            interactive_type = interactive.get('type')
            
            message_data['interactive'] = {
                'type': interactive_type
            }
            
            if interactive_type == 'button_reply':
                # User clicked a button
                button_reply = interactive.get('button_reply', {})
                message_data['interactive']['button_reply'] = {
                    'id': button_reply.get('id'),
                    'title': button_reply.get('title')
                }
                
                # Also add as text for backward compatibility
                message_data['text'] = {
                    'body': button_reply.get('title', '')
                }
                
            elif interactive_type == 'list_reply':
                # User selected from a list
                list_reply = interactive.get('list_reply', {})
                message_data['interactive']['list_reply'] = {
                    'id': list_reply.get('id'),
                    'title': list_reply.get('title'),
                    'description': list_reply.get('description')
                }
                
                # Also add as text for backward compatibility
                message_data['text'] = {
                    'body': list_reply.get('title', '')
                }
                
        elif message_type == 'button':
            # Legacy button response (from older WhatsApp versions)
            button = message.get('button', {})
            message_data['button'] = button
            message_data['text'] = {
                'body': button.get('text', '')
            }
            
        elif message_type == 'image':
            message_data['image'] = message.get('image', {})
            
        elif message_type == 'document':
            message_data['document'] = message.get('document', {})
            
        elif message_type == 'audio':
            message_data['audio'] = message.get('audio', {})
            
        elif message_type == 'location':
            message_data['location'] = message.get('location', {})
        
        # Process the message with Refiloe
        response = refiloe_service.process_message(message_data)
        
        # Send response if not an interactive message (those are sent directly)
        if response.get('success') and not response.get('interactive_sent'):
            if response.get('message'):
                # Send the response message
                refiloe_service.whatsapp.send_message(
                    from_number,
                    response['message']
                )
        
        return {'status': 'processed', 'response': response}
        
    except Exception as e:
        log_error(f"Error processing WhatsApp message: {str(e)}")
        return {'status': 'error', 'error': str(e)}
