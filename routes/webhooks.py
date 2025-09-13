from flask import Blueprint, request, jsonify
from utils.logger import log_info, log_error, log_warning

webhooks_bp = Blueprint('webhooks', __name__)

@webhooks_bp.route('/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages"""
    
    # GET request is for webhook verification
    if request.method == 'GET':
        try:
            mode = request.args.get('hub.mode')
            token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')
            
            if mode == 'subscribe' and token == 'texts_to_refiloe_radebe':
                log_info("Webhook verified successfully")
                return challenge
            else:
                log_warning("Webhook verification failed")
                return 'Forbidden', 403
                
        except Exception as e:
            log_error(f"Error during webhook verification: {str(e)}")
            return 'Bad Request', 400
    
    # POST request contains the actual message
    elif request.method == 'POST':
        try:
            data = request.get_json()
            log_info(f"Received webhook data: {data}")
            
            # Import the services here to avoid circular imports
            from app import app
            
            # Extract message details
            if data and 'entry' in data:
                for entry in data['entry']:
                    for change in entry.get('changes', []):
                        value = change.get('value', {})
                        
                        # Check if it's a message
                        if 'messages' in value:
                            for message in value['messages']:
                                phone = message.get('from')
                                text = message.get('text', {}).get('body', '')
                                message_id = message.get('id')
                                
                                log_info(f"Processing message from {phone}: {text}")
                                
                                # Get Refiloe service from app config
                                refiloe = app.config['services']['refiloe']
                                
                                # FIX: Use the correct method name!
                                # Check what methods are available
                                if hasattr(refiloe, 'handle_message'):
                                    result = refiloe.handle_message(phone, text)
                                elif hasattr(refiloe, 'process_whatsapp_message'):
                                    result = refiloe.process_whatsapp_message(phone, text)
                                else:
                                    # Fallback: use AI handler directly
                                    ai_handler = app.config['services']['ai_handler']
                                    whatsapp_service = app.config['services']['whatsapp']
                                    
                                    # Process with AI
                                    intent = ai_handler.understand_message(
                                        text, 
                                        'unknown',  # We'll determine this
                                        {},
                                        []
                                    )
                                    
                                    # Send response
                                    response_text = "Hi! I received your message. Let me help you with that."
                                    if intent.get('primary_intent'):
                                        response_text = f"I understand you're asking about {intent['primary_intent']}. Let me help you."
                                    
                                    whatsapp_service.send_message(phone, response_text)
                                    result = {'success': True}
                                
                                log_info(f"Message processed: {result}")
            
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            log_error(f"Error processing webhook: {str(e)}")
            return jsonify({'error': str(e)}), 500

@webhooks_bp.route('/payfast', methods=['POST'])
def payfast_webhook():
    return jsonify({'message': 'Webhook received'}), 200
