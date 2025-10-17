from flask import Blueprint, request, jsonify
from utils.logger import log_info, log_error
from datetime import datetime
import hashlib
import hmac

whatsapp_flow_bp = Blueprint('whatsapp_flow', __name__)

@whatsapp_flow_bp.route('/webhooks/whatsapp-flow', methods=['GET'])
def whatsapp_flow_health_check():
    """Health check endpoint for WhatsApp Flow"""
    try:
        # Check if this is a webhook verification request
        hub_challenge = request.args.get('hub.challenge')
        hub_verify_token = request.args.get('hub.verify_token')
        hub_mode = request.args.get('hub.mode')
        
        log_info(f"Health check request - mode: {hub_mode}, challenge: {hub_challenge}, token: {hub_verify_token}")
        
        # If it's a verification request, return the challenge
        if hub_mode == 'subscribe' and hub_challenge:
            log_info(f"Returning challenge: {hub_challenge}")
            return hub_challenge, 200, {'Content-Type': 'text/plain'}
        
        # For WhatsApp Flow health checks, return Base64 encoded response
        import base64
        import json
        
        response = {
            "status": "success",
            "message": "Trainer profile created successfully via WhatsApp Flow"
        }
        
        # Convert to JSON and encode to Base64
        json_string = json.dumps(response)
        encoded_response = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
        
        log_info(f"Returning Base64 encoded response: {encoded_response}")
        
        return encoded_response, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        log_error(f"Health check error: {str(e)}")
        return "OK", 200

@whatsapp_flow_bp.route('/webhooks/whatsapp-flow/test', methods=['POST'])
def test_flow_endpoint():
    """Test endpoint for flow debugging"""
    try:
        data = request.get_json()
        headers = dict(request.headers)
        
        return jsonify({
            "status": "success",
            "message": "Test endpoint received data",
            "received_data": data,
            "headers": headers,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@whatsapp_flow_bp.route('/webhooks/whatsapp-flow', methods=['POST'])
def handle_whatsapp_flow():
    """
    Handle WhatsApp Flow form submissions
    """
    try:
        # Get the flow data
        data = request.get_json()
        log_info(f"Received WhatsApp Flow data: {data}")
        
        # Log webhook data for debugging (just to application logs for now)
        log_info(f"Webhook headers: {dict(request.headers)}")
        log_info(f"Webhook method: {request.method}")
        log_info(f"Webhook endpoint: /webhooks/whatsapp-flow")
        
        # Handle encrypted flow data if present
        if 'encrypted_flow_data' in data:
            # This is an encrypted flow response - delegate to the flow handler
            from services.whatsapp_flow_handler import WhatsAppFlowHandler
            from app import app
            
            db = app.config['supabase']
            whatsapp_service = app.config['services']['whatsapp']
            
            # Log the request headers for debugging
            log_info(f"Request headers: {dict(request.headers)}")
            
            # Try to extract phone number from headers or recent context
            phone_from_header = (request.headers.get('X-WhatsApp-Phone-Number') or
                               request.headers.get('X-WhatsApp-From') or
                               request.headers.get('From'))
            
            if phone_from_header:
                log_info(f"Found phone number in headers: {phone_from_header}")
                # Add phone number to data for the handler
                data['phone_number'] = phone_from_header
            
            flow_handler = WhatsAppFlowHandler(db, whatsapp_service)
            
            # Decrypt and process the flow data
            result = flow_handler.handle_encrypted_flow_response(data)
            
            if result.get('success'):
                return jsonify({
                    "status": "success",
                    "message": result.get('message', 'Flow processed successfully')
                }), 200
            else:
                log_error(f"Encrypted flow processing failed: {result.get('error')}")
                # Return success anyway to prevent WhatsApp from retrying
                return jsonify({
                    "status": "success", 
                    "message": "Flow received - processing in background"
                }), 200
        
        # Handle unencrypted flow data (legacy format)
        flow_data = data.get('data', {})
        
        # Get form responses
        basic_info = flow_data.get('basic_info_form', {})
        business_info = flow_data.get('business_form', {})
        terms = flow_data.get('terms_form', {})
        
        # Extract user phone number (from the flow metadata)
        phone = data.get('phone_number', '')
        
        # Import services
        try:
            from app import app
            db = app.config['supabase']
        except Exception as import_error:
            log_error(f"Error importing app services: {str(import_error)}")
            return jsonify({
                "status": "error",
                "message": "Service configuration error"
            }), 500
        
        # Create trainer profile
        trainer_data = {
            'name': f"{basic_info.get('first_name', '')} {basic_info.get('surname', '')}",
            'whatsapp': phone,
            'email': basic_info.get('email', ''),
            'city': basic_info.get('city', ''),
            'business_name': business_info.get('business_name', ''),
            'specializations': business_info.get('specializations', []),
            'experience_years': business_info.get('experience_years', ''),
            'pricing_per_session': business_info.get('pricing_per_session', 500),  # Fixed field name
            'terms_accepted': terms.get('terms_accepted', False),
            'additional_notes': terms.get('additional_notes', ''),
            'status': 'active',  # Changed from pending_review to active
            'created_at': datetime.now().isoformat()
        }
        
        # Save to database
        result = db.table('trainers').insert(trainer_data).execute()
        
        if result.data:
            log_info(f"Trainer registration successful for {phone}")
            
            # Send confirmation via WhatsApp
            whatsapp = app.config['services']['whatsapp']
            whatsapp.send_message(
                phone,
                f"Welcome to Refiloe, {basic_info.get('first_name')}! 🎉\n\n"
                "Your trainer profile has been created successfully. "
                "We'll review your application and send you a link to set up "
                "your availability within 24 hours.\n\n"
                "If you have any questions, just message me!"
            )
            
            return jsonify({
                "status": "success",
                "message": "Registration completed"
            }), 200
        else:
            raise Exception("Failed to save trainer data")
            
    except Exception as e:
        log_error(f"WhatsApp Flow error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Registration failed. Please try again."
        }), 500
