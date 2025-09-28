#!/usr/bin/env python3
"""
WhatsApp Flow Webhook Handler
Handles incoming flow responses from WhatsApp Business API
"""

import json
import os
from flask import Blueprint, request, jsonify
from utils.logger import log_info, log_error, log_warning
from services.whatsapp_flow_handler import WhatsAppFlowHandler
from config import Config

# Create blueprint
flow_webhook_bp = Blueprint('flow_webhook', __name__)

def setup_flow_webhook(app, supabase, whatsapp_service):
    """Setup flow webhook routes"""
    
    # Initialize flow handler
    flow_handler = WhatsAppFlowHandler(supabase, whatsapp_service)
    
    @flow_webhook_bp.route('/webhook/flow', methods=['POST'])
    def handle_flow_webhook():
        """Handle incoming flow responses"""
        try:
            # Get webhook data
            webhook_data = request.get_json()
            
            if not webhook_data:
                log_warning("Empty webhook data received")
                return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
            log_info(f"Received flow webhook: {json.dumps(webhook_data, indent=2)}")
            
            # Extract flow data
            flow_data = webhook_data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {})
            
            if not flow_data:
                log_warning("No flow data found in webhook")
                return jsonify({'status': 'error', 'message': 'No flow data found'}), 400
            
            # Process flow messages
            messages = flow_data.get('messages', [])
            
            for message in messages:
                if message.get('type') == 'interactive' and message.get('interactive', {}).get('type') == 'flow':
                    # Handle flow response
                    interactive_data = message.get('interactive', {})
                    flow_response = interactive_data.get('flow_response', {})
                    
                    if flow_response:
                        # Process the flow response
                        result = flow_handler.handle_flow_response(flow_response)
                        
                        if result.get('success'):
                            log_info(f"Flow processed successfully: {result.get('message')}")
                        else:
                            log_error(f"Flow processing failed: {result.get('error')}")
            
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            log_error(f"Error processing flow webhook: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @flow_webhook_bp.route('/webhook/flow/status', methods=['GET'])
    def get_flow_status():
        """Get flow status for debugging"""
        try:
            phone_number = request.args.get('phone')
            if not phone_number:
                return jsonify({'status': 'error', 'message': 'Phone number required'}), 400
            
            status = flow_handler.get_flow_status(phone_number)
            return jsonify({'status': 'success', 'data': status}), 200
            
        except Exception as e:
            log_error(f"Error getting flow status: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    # Register blueprint
    app.register_blueprint(flow_webhook_bp, url_prefix='/flow')
    
    log_info("Flow webhook routes registered successfully")
