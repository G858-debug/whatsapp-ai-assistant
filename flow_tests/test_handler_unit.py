#!/usr/bin/env python3
"""
Unit test for the webhook handler
Tests the handler without running the Flask server
"""

import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_webhook_handler import TrainerOnboardingWebhookHandler

def test_handler():
    """Test the webhook handler with sample data"""
    print("=" * 60)
    print("Testing Webhook Handler")
    print("=" * 60)

    # Initialize handler
    handler = TrainerOnboardingWebhookHandler()

    # Load sample webhook payload
    sample_file = os.path.join(os.path.dirname(__file__), 'sample_webhook_payload.json')

    with open(sample_file, 'r') as f:
        webhook_data = json.load(f)

    print(f"\nLoaded sample webhook from: {sample_file}")
    print(f"Processing webhook...\n")

    # Process the webhook
    result = handler.process_webhook(webhook_data)

    # Display result
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("=" * 60)

    # Check if test_flow_responses.json was created
    log_file = os.path.join(os.path.dirname(__file__), 'test_flow_responses.json')
    if os.path.exists(log_file):
        print(f"\n✅ Log file created: {log_file}")
        with open(log_file, 'r') as f:
            responses = json.load(f)
            print(f"✅ Number of logged responses: {len(responses)}")
            if responses:
                print(f"\n📊 Latest response:")
                print(json.dumps(responses[-1]['extracted_data'], indent=2))
    else:
        print(f"\n❌ Log file not created")

    # Verify result
    if result['status'] == 'success':
        print("\n🎉 Test PASSED!")
        return True
    else:
        print("\n❌ Test FAILED!")
        print(f"Error: {result.get('message')}")
        return False

if __name__ == "__main__":
    success = test_handler()
    sys.exit(0 if success else 1)
