from flask import Blueprint, request, jsonify
from utils.logger import log_info, log_error, log_warning
from datetime import datetime, timedelta

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
                        
                        # Check if it's a message (not a status update)
                        if 'messages' in value:
                            for message in value['messages']:
                                phone = message.get('from')
                                text = message.get('text', {}).get('body', '')
                                message_id = message.get('id')
                                timestamp = message.get('timestamp')
                                
                                # Get Supabase client
                                supabase = app.config['supabase']
                                
                                # Check 1: Exact duplicate (same WhatsApp message ID)
                                try:
                                    existing = supabase.table('processed_messages').select('id').eq(
                                        'whatsapp_message_id', message_id
                                    ).execute()
                                    
                                    if existing.data:
                                        log_info(f"Duplicate webhook for message {message_id} ignored")
                                        continue
                                except Exception as e:
                                    # If table doesn't exist yet, continue processing
                                    log_warning(f"Could not check for duplicates: {str(e)}")
                                
                                # Check 2: Rapid-fire same content (prevents same text within 2 seconds)
                                try:
                                    recent_duplicate = supabase.table('processed_messages').select('id').eq(
                                        'phone_number', phone
                                    ).eq('message_text', text).gte(
                                        'created_at', (datetime.now() - timedelta(seconds=2)).isoformat()
                                    ).execute()
                                    
                                    if recent_duplicate.data:
                                        log_info(f"Rapid duplicate from {phone} ignored: {text[:50]}")
                                        continue
                                except Exception as e:
                                    # If check fails, continue processing to avoid blocking messages
                                    log_warning(f"Could not check for rapid duplicates: {str(e)}")
                                
                                # Store message to prevent reprocessing
                                try:
                                    supabase.table('processed_messages').insert({
                                        'whatsapp_message_id': message_id,
                                        'phone_number': phone,
                                        'message_text': text[:500] if text else '',  # Store first 500 chars
                                        'timestamp': str(timestamp) if timestamp else None,
                                        'created_at': datetime.now().isoformat()
                                    }).execute()
                                except Exception as e:
                                    # Log but don't block message processing
                                    log_warning(f"Could not store processed message: {str(e)}")
                                
                                log_info(f"Processing message from {phone}: {text}")
                                
                                # Get Refiloe service from app config
                                refiloe = app.config['services']['refiloe']
                                
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
                                    
                                    # Generate smart response using existing method
                                    response_text = ai_handler.generate_smart_response(
                                        intent, 
                                        sender_type='unknown',  # or determine from database
                                        sender_data={'name': 'there', 'whatsapp': phone}
                                    )
                                    
                                    # If no smart response generated, use the response generator
                                    if not response_text or response_text == "":
                                        from services.ai_intent_responses import AIResponseGenerator
                                        response_generator = AIResponseGenerator()
                                        response_text = response_generator.generate_response(
                                            intent,
                                            'unknown',
                                            {'name': 'there', 'whatsapp': phone}
                                        )
                                    
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
