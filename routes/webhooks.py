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
