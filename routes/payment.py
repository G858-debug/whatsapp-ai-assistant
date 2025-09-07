"""Payment related routes"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from utils.logger import log_error, log_warning

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/webhook/payfast', methods=['POST'])
def payfast_webhook():
    """Handle PayFast payment webhooks"""
    from app import payment_manager, payfast_handler
    
    try:
        data = request.form.to_dict()
        signature = request.headers.get('X-PayFast-Signature', '')
        
        if not payment_manager.verify_webhook_signature(data, signature):
            log_warning("Invalid PayFast signature")
            return 'Invalid signature', 403
        
        result = payfast_handler.process_payment_notification(data)
        
        if result['success']:
            return 'OK', 200
        else:
            return 'Processing failed', 500
            
    except Exception as e:
        log_error(f"PayFast webhook error: {str(e)}")
        return 'Internal error', 500