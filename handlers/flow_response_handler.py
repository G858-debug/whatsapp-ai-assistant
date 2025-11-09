"""
WhatsApp Flow Response Handler

This module processes WhatsApp Flow completion webhooks. When a user completes
a WhatsApp Flow (interactive form), this handler extracts the submitted data,
routes it to the appropriate flow processor, and returns the proper webhook response.
"""

import json
from typing import Dict, Any, Optional

from utils.logger import log_info, log_error, log_warning
from services.flows.whatsapp_flow_trainer_onboarding import WhatsAppFlowTrainerOnboarding


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

        # Extract flow_token if present (optional field used for flow identification)
        flow_token = nfm_reply.get('body', '')
        if flow_token:
            log_info(f"Flow token: {flow_token}")

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

        # Step 6: Route to appropriate flow handler
        log_info(f"Step 2: Routing flow '{flow_name}' to appropriate handler")

        # Check if it's trainer onboarding (handles both specific name and generic "flow")
        if flow_name == 'trainer_onboarding_flow' or flow_name == 'flow':
            # If generic "flow" name, check if it's trainer onboarding based on flow_token
            if flow_name == 'flow':
                # Check if flow_token indicates trainer onboarding
                if flow_token and 'trainer_onboarding' in flow_token:
                    log_info(f"Detected trainer onboarding flow from generic 'flow' name via token: {flow_token}")
                else:
                    log_warning(f"Generic 'flow' name without trainer_onboarding token - may not be trainer onboarding")

            try:
                log_info(f"Processing trainer onboarding flow completion for {phone_number}")

                # Initialize the trainer onboarding flow handler
                trainer_onboarding_service = WhatsAppFlowTrainerOnboarding(supabase, whatsapp_service)
                result = trainer_onboarding_service.process_flow_completion(flow_data, phone_number)

                if result.get('success'):
                    log_info(f"✅ Trainer onboarding completed successfully for {phone_number}")
                    log_info(f"Trainer ID: {result.get('trainer_id')}")

                    return {
                        'success': True,
                        'message': 'Flow processed successfully',
                        'data': result
                    }
                else:
                    log_warning("⚠️ Flow completion failed")
                    log_warning(f"Error: {result.get('error')}")

                    return {
                        'success': False,
                        'message': result.get('error', 'Flow processing failed'),
                        'data': result
                    }

            except Exception as e:
                error_msg = f"Error processing trainer onboarding flow: {str(e)}"
                log_error(error_msg, exc_info=True)

                return {
                    'success': False,
                    'message': error_msg,
                    'error_type': 'flow_processing_exception'
                }

        else:
            # Unknown flow type
            error_msg = f"Unknown flow type: {flow_name}"
            log_warning(error_msg)
            log_warning("No handler registered for this flow type")

            return {
                'success': False,
                'message': error_msg,
                'error_type': 'unknown_flow_type',
                'flow_name': flow_name
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
