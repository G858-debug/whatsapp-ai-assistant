from flask import Blueprint, request, jsonify
from utils.logger import log_info, log_error, log_warning

webhooks_bp = Blueprint('webhooks', __name__)

@webhooks_bp.route('/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages"""
    
    # GET request is for webhook verification
    if request.method == 'GET':
        try:
            # WhatsApp sends these parameters for verification
            mode = request.args.get('hub.mode')
            token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')
            
            # Check if mode and token are correct
            if mode == 'subscribe' and token == 'your_verify_token_here':
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
            # Get the message data
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
                                
                                # Process the message
                                result = refiloe.process_message(phone, text)
                                log_info(f"Message processed: {result}")
            
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            log_error(f"Error processing webhook: {str(e)}")
            return jsonify({'error': str(e)}), 500

@webhooks_bp.route('/payfast', methods=['POST'])
def payfast_webhook():
    # Handle PayFast webhook here
    return jsonify({'message': 'Webhook received'}), 200
