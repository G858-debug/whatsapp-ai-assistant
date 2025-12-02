"""
WhatsApp Flow Response Handler

This module processes WhatsApp Flow completion webhooks. When a user completes
a WhatsApp Flow (interactive form), this handler extracts the submitted data,
routes it to the appropriate flow processor, and returns the proper webhook response.
"""

import json
from typing import Dict, Any, Optional

from utils.logger import log_info, log_error, log_warning
from services.flows.registration.whatsapp_flow_trainer_onboarding import WhatsAppFlowTrainerOnboarding
from services.whatsapp_flow_handler import WhatsAppFlowHandler
from services.flow_webhooks.flow_endpoint import FlowEndpointHandler


def process_flow_webhook(webhook_data: dict, supabase, whatsapp_service) -> dict:
    """
    Process WhatsApp Flow completion webhooks.

    This function handles incoming webhook data when a user completes a WhatsApp Flow.
    It extracts the flow information, identifies the flow type, and routes the data
    to the appropriate flow processor.

    Args:
        webhook_data: The complete webhook payload from WhatsApp
        supabase: Supabase client for database operations
        whatsapp_service: WhatsApp service for sending messages

    Returns:
        Dict with status, message, and any relevant data:
        {
            'success': bool,
            'message': str,
            'data': dict (optional)
        }
    """
    try:
        log_info("=" * 60)
        log_info("Processing WhatsApp Flow completion webhook")
        log_info(f"Webhook data: {json.dumps(webhook_data, indent=2)}")

        # Step 1: Navigate through WhatsApp webhook structure
        log_info("Step 1: Extracting flow information from webhook structure")

        # Validate basic webhook structure
        if 'entry' not in webhook_data or not isinstance(webhook_data['entry'], list):
            error_msg = "Invalid webhook structure: missing 'entry' field or not a list"
            log_error(f"Webhook validation failed: {error_msg}")
            log_error(f"Received structure: {webhook_data.keys()}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'invalid_webhook_structure'
            }

        if len(webhook_data['entry']) == 0:
            error_msg = "Invalid webhook structure: 'entry' array is empty"
            log_error(f"Webhook validation failed: {error_msg}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'empty_entry_array'
            }

        entry = webhook_data['entry'][0]
        log_info(f"Entry extracted: {entry.get('id', 'unknown')}")

        # Extract changes array
        if 'changes' not in entry or not isinstance(entry['changes'], list):
            error_msg = "Invalid webhook structure: missing 'changes' field in entry"
            log_error(f"Webhook validation failed: {error_msg}")
            log_error(f"Entry structure: {entry.keys()}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'invalid_entry_structure'
            }

        if len(entry['changes']) == 0:
            error_msg = "Invalid webhook structure: 'changes' array is empty"
            log_error(f"Webhook validation failed: {error_msg}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'empty_changes_array'
            }

        change = entry['changes'][0]
        log_info(f"Change type: {change.get('field', 'unknown')}")

        # Extract value object
        if 'value' not in change:
            error_msg = "Invalid webhook structure: missing 'value' field in change"
            log_error(f"Webhook validation failed: {error_msg}")
            log_error(f"Change structure: {change.keys()}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'invalid_change_structure'
            }

        value = change['value']
        log_info(f"Value metadata: {value.get('metadata', {})}")

        # Extract messages array
        if 'messages' not in value or not isinstance(value['messages'], list):
            error_msg = "Invalid webhook structure: missing 'messages' field in value"
            log_error(f"Webhook validation failed: {error_msg}")
            log_error(f"Value structure: {value.keys()}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'invalid_value_structure'
            }

        if len(value['messages']) == 0:
            error_msg = "Invalid webhook structure: 'messages' array is empty"
            log_error(f"Webhook validation failed: {error_msg}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'empty_messages_array'
            }

        message = value['messages'][0]
        log_info(f"Message ID: {message.get('id', 'unknown')}")
        log_info(f"Message type: {message.get('type', 'unknown')}")

        # Step 2: Extract phone number
        if 'from' not in message:
            error_msg = "Invalid message structure: missing 'from' field"
            log_error(f"Message validation failed: {error_msg}")
            log_error(f"Message structure: {message.keys()}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'missing_phone_number'
            }

        phone_number = message['from']
        log_info(f"Phone number extracted: {phone_number}")

        # Step 3: Extract interactive flow reply data
        if 'interactive' not in message:
            error_msg = "Invalid message structure: missing 'interactive' field"
            log_error(f"Message validation failed: {error_msg}")
            log_error(f"Message structure: {message.keys()}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'not_interactive_message'
            }

        interactive = message['interactive']
        log_info(f"Interactive type: {interactive.get('type', 'unknown')}")

        if 'nfm_reply' not in interactive:
            error_msg = "Invalid interactive structure: missing 'nfm_reply' field"
            log_error(f"Interactive validation failed: {error_msg}")
            log_error(f"Interactive structure: {interactive.keys()}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'not_nfm_reply'
            }

        nfm_reply = interactive['nfm_reply']

        # Step 4: Extract flow name and response data
        if 'name' not in nfm_reply:
            error_msg = "Invalid nfm_reply structure: missing 'name' field"
            log_error(f"NFM reply validation failed: {error_msg}")
            log_error(f"NFM reply structure: {nfm_reply.keys()}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'missing_flow_name'
            }

        flow_name = nfm_reply['name']
        log_info(f"Flow name: {flow_name}")

        if 'response_json' not in nfm_reply:
            error_msg = "Invalid nfm_reply structure: missing 'response_json' field"
            log_error(f"NFM reply validation failed: {error_msg}")
            log_error(f"NFM reply structure: {nfm_reply.keys()}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'missing_response_json'
            }

        response_json_str = nfm_reply['response_json']
        log_info(f"Response JSON (raw): {response_json_str}")

        # Step 5: Parse response_json
        try:
            flow_data = json.loads(response_json_str)
            log_info(f"Parsed flow data: {json.dumps(flow_data, indent=2)}")
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse response_json as JSON: {str(e)}"
            log_error(error_msg)
            log_error(f"Invalid JSON string: {response_json_str}")
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'invalid_json_format'
            }

        # Extract flow_token from INSIDE the parsed JSON (not from nfm_reply body)
        flow_token = flow_data.get('flow_token', '')
        if flow_token:
            log_info(f"Flow token: {flow_token}")

        # Step 6: Route to appropriate flow handler based on flow_token
        log_info(f"Step 2: Routing flow '{flow_name}' with token '{flow_token}' to appropriate handler")

        # Route based on flow_token first (most reliable)
        if flow_token and 'client_onboarding_invitation' in flow_token:
            log_info(f"Routing to client profile completion handler based on token: {flow_token}")

            # Handle client profile completion flow
            flow_endpoint_handler = FlowEndpointHandler(supabase, whatsapp_service)
            result = flow_endpoint_handler.handle_client_profile_completion(
                flow_data,
                phone_number
            )

            if result.get('success'):
                log_info(f"✅ Client profile completion flow completed successfully")
                return {
                    'success': True,
                    'message': result.get('message', 'Client profile completed'),
                    'client_id': result.get('client_id')
                }
            else:
                log_error(f"❌ Client profile completion flow failed: {result.get('error')}")
                return {
                    'success': False,
                    'message': result.get('error', 'Flow processing failed')
                }

        elif flow_token and 'trainer_add_client' in flow_token:
            log_info(f"Routing to trainer add client handler based on token: {flow_token}")

            # Wrap the flow_data in the expected structure
            # The handler expects the data to be passed as a flow_response dict
            flow_response = flow_data  # The parsed data IS the flow response

            flow_handler = WhatsAppFlowHandler(supabase, whatsapp_service)
            result = flow_handler._handle_trainer_add_client_response(
                flow_response,  # Pass as flow_response, not flow_data
                phone_number,
                flow_token
            )

            if result.get('success'):
                log_info(f"✅ Trainer add client flow completed successfully")
                return {
                    'success': True,
                    'message': result.get('message', 'Client invitation sent'),
                    'trainer_id': result.get('trainer_id')
                }
            else:
                log_error(f"❌ Trainer add client flow failed: {result.get('error')}")
                return {
                    'success': False,
                    'message': result.get('error', 'Flow processing failed')
                }

        elif flow_token and 'trainer_onboarding' in flow_token or flow_name == 'trainer_onboarding_flow':
            log_info(f"Routing to trainer onboarding handler")
            trainer_onboarding_service = WhatsAppFlowTrainerOnboarding(supabase, whatsapp_service)
            result = trainer_onboarding_service.process_flow_completion(flow_data, phone_number)

            if result.get('success'):
                log_info(f"✅ Trainer onboarding completed successfully")
                return {
                    'success': True,
                    'message': 'Trainer registered successfully',
                    'trainer_id': result.get('trainer_id')
                }
            else:
                log_warning(f"Flow validation failed: {result.get('error')}")
                return {
                    'success': False,
                    'message': result.get('error', 'Validation failed')
                }

        else:
            # Unknown flow type
            log_error(f"Unknown flow type - name: {flow_name}, token: {flow_token}")
            return {
                'success': False,
                'message': f'Unknown flow type: {flow_name}'
            }

    except KeyError as e:
        error_msg = f"Missing required field in webhook structure: {str(e)}"
        log_error(error_msg, exc_info=True)
        log_error(f"Full webhook data: {json.dumps(webhook_data, indent=2)}")

        return {
            'success': False,
            'message': error_msg,
            'error_type': 'missing_field'
        }

    except Exception as e:
        error_msg = f"Unexpected error processing flow webhook: {str(e)}"
        log_error(error_msg, exc_info=True)
        log_error(f"Full webhook data: {json.dumps(webhook_data, indent=2)}")

        return {
            'success': False,
            'message': error_msg,
            'error_type': 'unexpected_exception'
        }

    finally:
        log_info("=" * 60)


def extract_flow_info(webhook_data: dict) -> Optional[Dict[str, Any]]:
    """
    Extract flow information from webhook data without processing.

    This is a utility function that can be used to preview flow data
    before processing, or for debugging purposes.

    Args:
        webhook_data: The complete webhook payload from WhatsApp

    Returns:
        Dict with extracted flow info, or None if extraction fails:
        {
            'phone_number': str,
            'flow_name': str,
            'flow_data': dict,
            'message_id': str
        }
    """
    try:
        message = webhook_data['entry'][0]['changes'][0]['value']['messages'][0]
        nfm_reply = message['interactive']['nfm_reply']

        return {
            'phone_number': message['from'],
            'flow_name': nfm_reply['name'],
            'flow_data': json.loads(nfm_reply['response_json']),
            'message_id': message.get('id'),
            'timestamp': message.get('timestamp')
        }
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        log_error(f"Failed to extract flow info: {str(e)}")
        return None
