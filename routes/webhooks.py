from flask import Blueprint, request, jsonify

webhooks_bp = Blueprint('webhooks', __name__)

@webhooks_bp.route('/payfast', methods=['POST'])
def payfast_webhook():
    # Handle PayFast webhook here
    return jsonify({'message': 'Webhook received'}), 200