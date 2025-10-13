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
            
            # Extract flow data from WhatsApp webhook structure
            entries = webhook_data.get('entry', [])
            
            if not entries:
                log_warning("No entries found in webhook data")
                return jsonify({'status': 'error', 'message': 'No entries found'}), 400
            
            processed_count = 0
            
            for entry in entries:
                changes = entry.get('changes', [])
                
                for change in changes:
                    value = change.get('value', {})
                    
                    # Handle flow completion messages
                    messages = value.get('messages', [])
                    
                    for message in messages:
                        phone_number = message.get('from')
                        message_type = message.get('type')
                        
                        if message_type == 'interactive':
                            interactive = message.get('interactive', {})
                            
                            if interactive.get('type') == 'flow':
                                # This is a flow completion
                                flow_response_data = interactive.get('flow_response', {})
                                
                                if flow_response_data:
                                    log_info(f"Processing flow completion from {phone_number}")
                                    
                                    # Add phone number to flow response data
                                    flow_response_data['phone_number'] = phone_number
                                    flow_response_data['message_id'] = message.get('id')
                                    flow_response_data['timestamp'] = message.get('timestamp')
                                    
                                    # Process the flow response
                                    result = flow_handler.handle_flow_response(flow_response_data)
                                    
                                    if result.get('success'):
                                        log_info(f"Flow processed successfully for {phone_number}: {result.get('message')}")
                                        processed_count += 1
                                        
                                        # Update conversation state to clear registration mode
                                        # This allows the user to use normal AI features after registration
                                        try:
                                            from services.refiloe import RefiloeAI
                                            refiloe = RefiloeAI(supabase, whatsapp_service)
                                            refiloe.update_conversation_state(phone_number, 'IDLE')
                                            log_info(f"Cleared registration state for {phone_number}")
                                        except Exception as state_error:
                                            log_warning(f"Could not clear conversation state: {str(state_error)}")
                                        
                                    else:
                                        log_error(f"Flow processing failed for {phone_number}: {result.get('error')}")
                                        
                                        # Send error message to user
                                        error_message = (
                                            "Sorry, there was an issue processing your registration. "
                                            "Please try again or contact support."
                                        )
                                        whatsapp_service.send_message(phone_number, error_message)
                    
                    # Handle flow interaction events (button clicks, screen changes)
                    flow_events = value.get('flow_events', [])
                    
                    for flow_event in flow_events:
                        event_type = flow_event.get('type')
                        phone_number = flow_event.get('from')
                        
                        if event_type in ['flow_started', 'flow_screen_changed']:
                            log_info(f"Flow event: {event_type} from {phone_number}")
                            # Could track analytics here
                        
                        elif event_type == 'flow_abandoned':
                            log_info(f"Flow abandoned by {phone_number}")
                            
                            # Optionally send a follow-up message
                            follow_up_message = (
                                "I noticed you didn't complete the registration form. "
                                "No worries! Just type 'I'm a trainer' again and I'll help you register step by step."
                            )
                            whatsapp_service.send_message(phone_number, follow_up_message)
            
            if processed_count > 0:
                log_info(f"Successfully processed {processed_count} flow completions")
            
            return jsonify({'status': 'success', 'processed': processed_count}), 200
            
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
