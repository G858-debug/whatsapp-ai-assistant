from flask import Blueprint, request, jsonify
from utils.logger import log_info, log_error
from datetime import datetime
import hashlib
import hmac
import json
import base64
import os
from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1, hashes
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from handlers.flow_data_exchange import handle_flow_data_exchange, get_collected_data

whatsapp_flow_bp = Blueprint('whatsapp_flow', __name__)

def decrypt_request(encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64):
    """Decrypt WhatsApp Flow request data"""
    try:
        # Load private key from environment
        private_key_str = os.environ.get('WHATSAPP_FLOW_PRIVATE_KEY')
        if not private_key_str:
            raise Exception("WHATSAPP_FLOW_PRIVATE_KEY environment variable not set")
        
        flow_data = base64.b64decode(encrypted_flow_data_b64)
        iv = base64.b64decode(initial_vector_b64)
        
        # Decrypt the AES encryption key
        encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
        private_key = load_pem_private_key(
            private_key_str.encode('utf-8'), password=None)
        aes_key = private_key.decrypt(encrypted_aes_key, OAEP(
            mgf=MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        
        # Decrypt the Flow data
        encrypted_flow_data_body = flow_data[:-16]
        encrypted_flow_data_tag = flow_data[-16:]
        decryptor = Cipher(algorithms.AES(aes_key),
                          modes.GCM(iv, encrypted_flow_data_tag)).decryptor()
        decrypted_data_bytes = decryptor.update(
            encrypted_flow_data_body) + decryptor.finalize()
        decrypted_data = json.loads(decrypted_data_bytes.decode("utf-8"))
        return decrypted_data, aes_key, iv
    except Exception as e:
        log_error(f"Decryption error: {str(e)}")
        raise

def encrypt_response(response, aes_key, iv):
    """Encrypt WhatsApp Flow response data"""
    try:
        # Flip the initialization vector
        flipped_iv = bytearray()
        for byte in iv:
            flipped_iv.append(byte ^ 0xFF)
        
        # Encrypt the response data
        encryptor = Cipher(algorithms.AES(aes_key),
                          modes.GCM(flipped_iv)).encryptor()
        return base64.b64encode(
            encryptor.update(json.dumps(response).encode("utf-8")) +
            encryptor.finalize() +
            encryptor.tag
        ).decode("utf-8")
    except Exception as e:
        log_error(f"Encryption error: {str(e)}")
        raise

def validate_signature(payload, signature, app_secret):
    """Validate WhatsApp webhook signature"""
    try:
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Remove 'sha256=' prefix if present
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        log_error(f"Signature validation error: {str(e)}")
        return False

def get_next_screen(current_screen, form_data):
    """Determine the next screen based on current screen and form data"""
    screen_flow = {
        'welcome': 'basic_info',
        'basic_info': 'business_details',
        'business_details': 'availability',
        'availability': 'preferences',
        'preferences': 'business_setup',
        'business_setup': 'pricing_smart',
        'pricing_smart': 'terms_agreement'
    }
    return screen_flow.get(current_screen, 'welcome')

def get_previous_screen(current_screen):
    """Get the previous screen for back navigation"""
    screen_flow = {
        'basic_info': 'welcome',
        'business_details': 'basic_info',
        'availability': 'business_details',
        'preferences': 'availability',
        'business_setup': 'preferences',
        'pricing_smart': 'business_setup',
        'terms_agreement': 'pricing_smart'
    }
    return screen_flow.get(current_screen, 'welcome')

def get_screen_data(screen_name, existing_data=None):
    """Get data for a specific screen"""
    if existing_data is None:
        existing_data = {}
    
    # Return any pre-filled data for the screen
    return {}

def process_trainer_registration(flow_data, flow_token):
    """Process trainer registration from flow data"""
    try:
        from app import app
        db = app.config['supabase']
        whatsapp_service = app.config['services']['whatsapp']
        
        # Extract trainer data from flow
        trainer_data = {
            'name': f"{flow_data.get('first_name', '')} {flow_data.get('surname', '')}".strip(),
            'first_name': flow_data.get('first_name', ''),
            'last_name': flow_data.get('surname', ''),
            'email': flow_data.get('email', '').lower(),
            'city': flow_data.get('city', ''),
            'business_name': flow_data.get('business_name', ''),
            'specialization': ', '.join(flow_data.get('specializations', [])),
            'experience_years': flow_data.get('experience_years', '0-1'),
            'pricing_per_session': float(flow_data.get('pricing_per_session', 500)),
            'available_days': flow_data.get('available_days', []),
            'preferred_time_slots': flow_data.get('preferred_time_slots', ''),
            'subscription_plan': flow_data.get('subscription_plan', 'free'),
            'services_offered': flow_data.get('services_offered', []),
            'pricing_flexibility': flow_data.get('pricing_flexibility', []),
            'notification_preferences': flow_data.get('notification_preferences', []),
            'marketing_consent': flow_data.get('marketing_consent', False),
            'terms_accepted': flow_data.get('terms_accepted', False),
            'additional_notes': flow_data.get('additional_notes', ''),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'flow_token': flow_token
        }
        
        # Extract phone number from flow token if possible
        if '_' in flow_token:
            parts = flow_token.split('_')
            if len(parts) >= 3:
                phone_number = parts[2]  # trainer_onboarding_{phone}_{timestamp}
                trainer_data['whatsapp'] = phone_number
        
        # Save to database
        result = db.table('trainers').insert(trainer_data).execute()
        
        if result.data:
            trainer_id = result.data[0]['id']
            log_info(f"Trainer registration completed via flow: {trainer_id}")
            
            # Send confirmation message if we have phone number
            if trainer_data.get('whatsapp'):
                try:
                    whatsapp_service.send_message(
                        trainer_data['whatsapp'],
                        f"🎉 Welcome to Refiloe, {trainer_data['first_name']}!\n\n"
                        "Your trainer profile has been created successfully. "
                        "You can now start connecting with clients and managing your fitness business.\n\n"
                        "Type /help to see what you can do!"
                    )
                except Exception as msg_error:
                    log_error(f"Failed to send confirmation message: {str(msg_error)}")
            
            return {
                'success': True,
                'trainer_id': trainer_id,
                'message': 'Registration completed successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to save trainer data'
            }
            
    except Exception as e:
        log_error(f"Error processing trainer registration: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

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
        
        # For health checks, return encrypted success response
        try:
            response = {"data": {"status": "active"}}
            # For GET requests, we don't have encryption keys, so return JSON
            return jsonify(response), 200
        except Exception as health_error:
            log_error(f"Health check response error: {str(health_error)}")
            return "OK", 200
        
    except Exception as e:
        log_error(f"Health check error: {str(e)}")
        return "OK", 200

@whatsapp_flow_bp.route('/webhooks/whatsapp-flow', methods=['POST'])
def handle_whatsapp_flow():
    """
    Handle WhatsApp Flow form submissions with proper encryption/decryption
    """
    try:
        # Get raw request body for signature validation
        raw_body = request.get_data()
        
        # Validate signature if app secret is configured
        app_secret = os.environ.get('WHATSAPP_APP_SECRET')
        if app_secret:
            signature = request.headers.get('X-Hub-Signature-256')
            if signature and not validate_signature(raw_body, signature, app_secret):
                log_error("Invalid webhook signature")
                return "", 401
        
        # Parse JSON data
        data = request.get_json()
        log_info(f"Received WhatsApp Flow request with keys: {list(data.keys()) if data else 'None'}")
        
        # Handle encrypted flow data
        if data and 'encrypted_flow_data' in data:
            try:
                # Decrypt the request
                decrypted_data, aes_key, iv = decrypt_request(
                    data['encrypted_flow_data'],
                    data['encrypted_aes_key'], 
                    data['initial_vector']
                )
                
                # Extract key values from decrypted data
                action = decrypted_data.get('action', '')
                flow_token = decrypted_data.get('flow_token', '')
                screen = decrypted_data.get('screen', '')

                # Log extracted values for debugging
                log_info(f"Flow request - action: {action}, flow_token: {flow_token}, screen: {screen}")
                log_info(f"Decrypted flow data keys: {list(decrypted_data.keys())}")
                log_info(f"Full decrypted data: {json.dumps(decrypted_data, indent=2)}")

                # Call the flow data exchange handler
                log_info(f"Calling handle_flow_data_exchange for action: {action}")
                response_data = handle_flow_data_exchange(decrypted_data, flow_token)
                log_info(f"Handler returned response: {json.dumps(response_data, indent=2)}")

                # Handle "complete" action - extract and return all form data
                if action.lower() == 'complete':
                    log_info(f"Flow complete action detected for token: {flow_token}")

                    # Log all keys received in decrypted_data for debugging
                    log_info(f"All keys in decrypted_data: {list(decrypted_data.keys())}")

                    # Extract ALL form fields (exclude system fields)
                    system_fields = {'action', 'screen', 'flow_token'}
                    collected_data = {
                        key: value
                        for key, value in decrypted_data.items()
                        if key not in system_fields
                    }

                    # Log what we extracted
                    log_info(f"Extracted {len(collected_data)} form fields: {list(collected_data.keys())}")
                    log_info(f"Complete form data collected: {json.dumps(collected_data, indent=2)}")

                    # Add collected data to response
                    if collected_data:
                        if 'data' not in response_data:
                            response_data['data'] = {}
                        response_data['data'].update(collected_data)
                        log_info(f"Flow complete, returning {len(collected_data)} fields in response")
                    else:
                        log_info(f"No form data found in decrypted_data (only system fields present)")

                # Use response_data as the response to encrypt
                response = response_data
                
                # Encrypt and return response as Base64 string
                encrypted_response = encrypt_response(response, aes_key, iv)
                return encrypted_response, 200, {'Content-Type': 'text/plain'}
                
            except Exception as decrypt_error:
                log_error(f"Decryption/processing error: {str(decrypt_error)}")
                # Return HTTP 421 for decryption errors as per WhatsApp docs
                return "", 421
        
        # Handle legacy unencrypted flow data (fallback)
        return handle_legacy_flow_data(data)
        
    except Exception as e:
        log_error(f"WhatsApp Flow error: {str(e)}")
        return "", 500

def handle_legacy_flow_data(data):
    """Handle legacy unencrypted flow data"""
    try:
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400
        
        # Handle unencrypted flow data (legacy format)
        flow_data = data.get('data', {})
        
        # Get form responses
        basic_info = flow_data.get('basic_info_form', {})
        business_info = flow_data.get('business_form', {})
        terms = flow_data.get('terms_form', {})
        
        # Extract user phone number (from the flow metadata)
        phone = data.get('phone_number', '')
        
        # Import services
        from app import app
        db = app.config['supabase']
        
        # Create trainer profile
        trainer_data = {
            'name': f"{basic_info.get('first_name', '')} {basic_info.get('surname', '')}",
            'whatsapp': phone,
            'email': basic_info.get('email', ''),
            'city': basic_info.get('city', ''),
            'business_name': business_info.get('business_name', ''),
            'specializations': business_info.get('specializations', []),
            'experience_years': business_info.get('experience_years', ''),
            'pricing_per_session': business_info.get('pricing_per_session', 500),
            'terms_accepted': terms.get('terms_accepted', False),
            'additional_notes': terms.get('additional_notes', ''),
            'status': 'active',
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
        log_error(f"Legacy flow error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Registration failed. Please try again."
        }), 500

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