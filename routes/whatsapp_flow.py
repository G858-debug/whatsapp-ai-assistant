from flask import Blueprint, request, jsonify
from utils.logger import log_info, log_error
from datetime import datetime
import hashlib
import hmac

whatsapp_flow_bp = Blueprint('whatsapp_flow', __name__)

@whatsapp_flow_bp.route('/webhooks/whatsapp-flow', methods=['POST'])
def handle_whatsapp_flow():
    """
    Handle WhatsApp Flow form submissions
    """
    try:
        # Get the flow data
        data = request.get_json()
        log_info(f"Received WhatsApp Flow data: {data}")
        
        # Extract form data from the flow
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
            'average_price': business_info.get('pricing_per_session', ''),
            'terms_accepted': terms.get('terms_accepted', False),
            'additional_notes': terms.get('additional_notes', ''),
            'status': 'pending_review',
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
