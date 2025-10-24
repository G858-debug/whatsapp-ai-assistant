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
                                message_id = message.get('id')
                                timestamp = message.get('timestamp')
                                message_type = message.get('type', 'text')
                                
                                # Initialize text variable
                                text = ''
                                button_id = ''
                                
                                # Handle different message types
                                if message_type == 'interactive':
                                    # This is a button click, list reply, or flow response
                                    interactive = message.get('interactive', {})
                                    interactive_type = interactive.get('type')
                                    
                                    if interactive_type == 'button_reply':
                                        # Button click
                                        button_reply = interactive.get('button_reply', {})
                                        text = button_reply.get('title', '')
                                        button_id = button_reply.get('id', '')
                                        log_info(f"Button clicked - ID: {button_id}, Title: {text}")
                                    elif interactive_type == 'list_reply':
                                        # List selection
                                        list_reply = interactive.get('list_reply', {})
                                        text = list_reply.get('title', '')
                                        button_id = list_reply.get('id', '')
                                        log_info(f"List selected - ID: {button_id}, Title: {text}")
                                    elif interactive_type == 'flow':
                                        # Flow response - handle via flow webhook
                                        flow_response = interactive.get('flow_response', {})
                                        if flow_response:
                                            log_info(f"Flow response received from {phone}")
                                            # Process flow response via flow handler
                                            try:
                                                from app import app
                                                flow_handler = app.config['services'].get('flow_handler')
                                                if flow_handler:
                                                    result = flow_handler.handle_flow_response(flow_response)
                                                    if result.get('success'):
                                                        log_info(f"Flow processed successfully: {result.get('message')}")
                                                    else:
                                                        log_error(f"Flow processing failed: {result.get('error')}")
                                            except Exception as e:
                                                log_error(f"Error processing flow response: {str(e)}")
                                            continue  # Skip normal message processing for flows
                                
                                elif message_type == 'button':
                                    # Legacy button format
                                    button = message.get('button', {})
                                    text = button.get('text', '')
                                    button_id = button.get('payload', '')
                                    log_info(f"Legacy button - ID: {button_id}, Text: {text}")
                                
                                else:
                                    # Regular text message or other types
                                    text = message.get('text', {}).get('body', '')
                                
                                # If we have a button_id but no text, use the button_id as text
                                if button_id and not text:
                                    # Map button IDs to their expected text
                                    button_map = {
                                        'register_trainer': "I'm a Trainer",
                                        'register_client': 'Find a Trainer',
                                        'learn_about_me': 'Learn about me'
                                    }
                                    text = button_map.get(button_id, button_id)
                                    log_info(f"Mapped button_id '{button_id}' to text '{text}'")
                                
                                # Log what we extracted
                                log_info(f"Message type: {message_type}, Text: '{text}', Button ID: '{button_id}'")
                                
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
                                # Only check if text is not empty
                                if text:
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
                                        'message_text': text[:500] if text else button_id or 'empty',  # Store button_id if no text
                                        'timestamp': str(timestamp) if timestamp else None,
                                        'created_at': datetime.now().isoformat()
                                    }).execute()
                                except Exception as e:
                                    # Log but don't block message processing
                                    log_warning(f"Could not store processed message: {str(e)}")
                                
                                log_info(f"Processing message from {phone}: {text or 'EMPTY MESSAGE'}")
                                
                                # Handle empty messages
                                if not text and not button_id:
                                    log_warning(f"Empty message received from {phone}")
                                    whatsapp_service = app.config['services']['whatsapp']
                                    prompt = (
                                        "I didn't catch that! 😊\n\n"
                                        "Please send me a message or use one of the buttons."
                                    )
                                    whatsapp_service.send_message(phone, prompt)
                                    continue
                                
                                # PHASE 1 INTEGRATION: Use MessageRouter for new system
                                try:
                                    from services.message_router import MessageRouter
                                    whatsapp_service = app.config['services']['whatsapp']
                                    
                                    # Initialize MessageRouter
                                    router = MessageRouter(supabase, whatsapp_service)
                                    
                                    # Route the message
                                    result = router.route_message(phone, text)
                                    
                                    log_info(f"Message routed successfully: {result.get('handler')}")
                                    
                                except Exception as router_error:
                                    log_error(f"MessageRouter error: {str(router_error)}")
                                    
                                    # Fallback to old system if Phase 1 fails
                                    log_info("Falling back to legacy Refiloe handler")
                                    refiloe = app.config['services']['refiloe']
                                    
                                    if hasattr(refiloe, 'handle_message'):
                                        result = refiloe.handle_message(phone, text)
                                    elif hasattr(refiloe, 'process_whatsapp_message'):
                                        result = refiloe.process_whatsapp_message(phone, text)
                                    else:
                                        # Last resort fallback
                                        whatsapp_service = app.config['services']['whatsapp']
                                        whatsapp_service.send_message(
                                            phone,
                                            "Sorry, I encountered an error. Please try again."
                                        )
                                        result = {'success': False}
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
