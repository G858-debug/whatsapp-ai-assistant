#!/usr/bin/env python3
"""
WhatsApp Flow Test Webhook Handler
Creates a test Flask route to process WhatsApp Flow webhook data for trainer onboarding.

This is a TESTING ONLY handler that:
- Receives WhatsApp Flow webhook data
- Extracts trainer onboarding form fields
- Logs all data to test_flow_responses.json
- Does NOT interact with the database
- Returns appropriate responses to WhatsApp

Flow ID: 775047838492907 (trainer_onboarding_flow)
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify

# Add parent directory to path to import from main codebase
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import log_info, log_error, log_warning

# Constants
FLOW_ID = "775047838492907"
FLOW_NAME = "trainer_onboarding_flow"
LOG_FILE = os.path.join(os.path.dirname(__file__), "test_flow_responses.json")

# Create Flask app for testing
app = Flask(__name__)


class TrainerOnboardingWebhookHandler:
    """Handler for trainer onboarding flow webhook testing"""

    def __init__(self, log_file: str = LOG_FILE):
        """
        Initialize the webhook handler

        Args:
            log_file: Path to the JSON file for logging responses
        """
        self.log_file = log_file
        self.required_fields = [
            'full_name',
            'email',
            'phone',
            'city',
            'specialization',
            'experience_years',
            'pricing_per_session',
            'terms_accepted'
        ]

    def extract_flow_data(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract trainer onboarding data from WhatsApp webhook payload

        Args:
            webhook_data: The webhook payload from WhatsApp

        Returns:
            Extracted flow data or None if extraction fails
        """
        try:
            log_info("Starting flow data extraction...")

            # Navigate through WhatsApp webhook structure
            entries = webhook_data.get('entry', [])

            if not entries:
                log_warning("No entries found in webhook data")
                return None

            for entry in entries:
                changes = entry.get('changes', [])

                for change in changes:
                    value = change.get('value', {})
                    messages = value.get('messages', [])

                    for message in messages:
                        message_type = message.get('type')

                        # Look for interactive flow messages
                        if message_type == 'interactive':
                            interactive = message.get('interactive', {})

                            # Check if it's an nfm_reply (flow completion)
                            if interactive.get('type') == 'nfm_reply':
                                nfm_reply = interactive.get('nfm_reply', {})

                                # Extract response JSON
                                response_json = nfm_reply.get('response_json', '')

                                if response_json:
                                    # Parse the JSON string
                                    flow_data = json.loads(response_json)

                                    # Add metadata
                                    flow_data['_metadata'] = {
                                        'phone_number': message.get('from'),
                                        'message_id': message.get('id'),
                                        'timestamp': message.get('timestamp'),
                                        'flow_id': FLOW_ID,
                                        'flow_name': FLOW_NAME,
                                        'extracted_at': datetime.now().isoformat()
                                    }

                                    log_info(f"Successfully extracted flow data from {flow_data['_metadata']['phone_number']}")
                                    return flow_data

            log_warning("No flow data found in webhook payload")
            return None

        except json.JSONDecodeError as e:
            log_error(f"JSON decode error: {str(e)}")
            return None
        except Exception as e:
            log_error(f"Error extracting flow data: {str(e)}")
            return None

    def validate_flow_data(self, flow_data: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate that all required fields are present

        Args:
            flow_data: The extracted flow data

        Returns:
            Tuple of (is_valid, missing_fields)
        """
        missing_fields = []

        for field in self.required_fields:
            if field not in flow_data:
                missing_fields.append(field)

        is_valid = len(missing_fields) == 0

        if is_valid:
            log_info("All required fields present in flow data")
        else:
            log_warning(f"Missing required fields: {', '.join(missing_fields)}")

        return is_valid, missing_fields

    def format_phone_number(self, phone: str) -> str:
        """
        Format phone number to South African format

        Args:
            phone: Raw phone number

        Returns:
            Formatted phone number
        """
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))

        # Ensure it starts with 27 (South Africa)
        if not phone.startswith('27'):
            if phone.startswith('0'):
                phone = '27' + phone[1:]
            else:
                phone = '27' + phone

        return phone

    def log_response(self, flow_data: Dict[str, Any], webhook_data: Dict[str, Any]) -> bool:
        """
        Log the flow response to JSON file

        Args:
            flow_data: The extracted and validated flow data
            webhook_data: The original webhook payload

        Returns:
            True if logging successful, False otherwise
        """
        try:
            # Load existing responses
            responses = []
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    try:
                        responses = json.load(f)
                    except json.JSONDecodeError:
                        log_warning("Existing log file was empty or invalid, starting fresh")
                        responses = []

            # Create log entry
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'flow_id': FLOW_ID,
                'flow_name': FLOW_NAME,
                'extracted_data': {
                    'full_name': flow_data.get('full_name'),
                    'email': flow_data.get('email'),
                    'phone': self.format_phone_number(flow_data.get('phone', '')),
                    'city': flow_data.get('city'),
                    'specialization': flow_data.get('specialization'),
                    'experience_years': flow_data.get('experience_years'),
                    'pricing_per_session': flow_data.get('pricing_per_session'),
                    'terms_accepted': flow_data.get('terms_accepted')
                },
                'metadata': flow_data.get('_metadata', {}),
                'raw_webhook': webhook_data
            }

            # Add to responses
            responses.append(log_entry)

            # Save to file
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(responses, f, indent=2, ensure_ascii=False)

            log_info(f"Logged flow response to {self.log_file}")
            log_info(f"Total responses logged: {len(responses)}")

            return True

        except Exception as e:
            log_error(f"Error logging response: {str(e)}")
            return False

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the webhook data and return response

        Args:
            webhook_data: The webhook payload from WhatsApp

        Returns:
            Response dictionary
        """
        try:
            log_info("=" * 60)
            log_info("Processing trainer onboarding flow webhook")
            log_info("=" * 60)

            # Extract flow data
            flow_data = self.extract_flow_data(webhook_data)

            if not flow_data:
                return {
                    'status': 'error',
                    'message': 'Could not extract flow data from webhook',
                    'code': 'EXTRACTION_FAILED'
                }

            # Validate flow data
            is_valid, missing_fields = self.validate_flow_data(flow_data)

            if not is_valid:
                return {
                    'status': 'error',
                    'message': f'Missing required fields: {", ".join(missing_fields)}',
                    'code': 'VALIDATION_FAILED',
                    'missing_fields': missing_fields
                }

            # Log the response
            logged = self.log_response(flow_data, webhook_data)

            if not logged:
                log_warning("Failed to log response, but continuing...")

            # Create success response
            phone = self.format_phone_number(flow_data.get('phone', ''))
            name = flow_data.get('full_name', 'Trainer')

            log_info(f"Successfully processed onboarding for {name} ({phone})")
            log_info("=" * 60)

            return {
                'status': 'success',
                'message': 'Trainer onboarding data received and logged',
                'data': {
                    'name': name,
                    'phone': phone,
                    'email': flow_data.get('email'),
                    'logged': logged
                }
            }

        except Exception as e:
            log_error(f"Error processing webhook: {str(e)}")
            return {
                'status': 'error',
                'message': f'Internal error: {str(e)}',
                'code': 'INTERNAL_ERROR'
            }


# Initialize handler
webhook_handler = TrainerOnboardingWebhookHandler()


@app.route('/test/flow/trainer-onboarding', methods=['POST'])
def test_trainer_onboarding_webhook():
    """
    Test webhook endpoint for trainer onboarding flow

    This endpoint:
    1. Receives WhatsApp Flow webhook data
    2. Extracts trainer onboarding fields
    3. Logs data to test_flow_responses.json
    4. Returns success response to WhatsApp
    """
    try:
        # Get webhook data
        webhook_data = request.get_json()

        if not webhook_data:
            log_warning("Empty webhook data received")
            return jsonify({
                'status': 'error',
                'message': 'No data received'
            }), 400

        log_info(f"Received webhook data: {json.dumps(webhook_data, indent=2)}")

        # Process the webhook
        result = webhook_handler.process_webhook(webhook_data)

        # Determine HTTP status code
        status_code = 200 if result['status'] == 'success' else 400

        # Return response
        return jsonify(result), status_code

    except Exception as e:
        log_error(f"Error in webhook endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500


@app.route('/test/flow/trainer-onboarding', methods=['GET'])
def test_trainer_onboarding_info():
    """
    Get information about the test webhook endpoint
    """
    return jsonify({
        'endpoint': '/test/flow/trainer-onboarding',
        'method': 'POST',
        'flow_id': FLOW_ID,
        'flow_name': FLOW_NAME,
        'required_fields': webhook_handler.required_fields,
        'log_file': LOG_FILE,
        'description': 'Test webhook handler for trainer onboarding flow',
        'note': 'This is for TESTING ONLY - no database interaction'
    })


@app.route('/test/flow/responses', methods=['GET'])
def get_test_responses():
    """
    Get all logged test responses
    """
    try:
        if not os.path.exists(LOG_FILE):
            return jsonify({
                'status': 'success',
                'responses': [],
                'count': 0,
                'message': 'No responses logged yet'
            })

        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            responses = json.load(f)

        return jsonify({
            'status': 'success',
            'responses': responses,
            'count': len(responses)
        })

    except Exception as e:
        log_error(f"Error reading responses: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/test/flow/clear', methods=['POST'])
def clear_test_responses():
    """
    Clear all logged test responses
    """
    try:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            log_info("Test responses cleared")

        return jsonify({
            'status': 'success',
            'message': 'Test responses cleared'
        })

    except Exception as e:
        log_error(f"Error clearing responses: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/test/flow', methods=['GET'])
def test_flow_home():
    """
    Test flow webhook home - shows available endpoints
    """
    return jsonify({
        'service': 'WhatsApp Flow Test Webhook Handler',
        'endpoints': {
            'webhook': {
                'url': '/test/flow/trainer-onboarding',
                'methods': ['GET', 'POST'],
                'description': 'Main webhook endpoint for trainer onboarding flow'
            },
            'responses': {
                'url': '/test/flow/responses',
                'methods': ['GET'],
                'description': 'View all logged responses'
            },
            'clear': {
                'url': '/test/flow/clear',
                'methods': ['POST'],
                'description': 'Clear all logged responses'
            }
        },
        'flow_info': {
            'id': FLOW_ID,
            'name': FLOW_NAME
        }
    })


def main():
    """
    Main function to run the test webhook handler
    """
    print("=" * 60)
    print("WhatsApp Flow Test Webhook Handler")
    print("=" * 60)
    print(f"Flow ID: {FLOW_ID}")
    print(f"Flow Name: {FLOW_NAME}")
    print(f"Log File: {LOG_FILE}")
    print()
    print("Available endpoints:")
    print("  POST /test/flow/trainer-onboarding  - Main webhook")
    print("  GET  /test/flow/trainer-onboarding  - Endpoint info")
    print("  GET  /test/flow/responses            - View logged responses")
    print("  POST /test/flow/clear                - Clear responses")
    print("  GET  /test/flow                      - Service info")
    print("=" * 60)
    print()

    # Run the Flask app
    port = int(os.environ.get('TEST_PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)


if __name__ == "__main__":
    main()
