#!/usr/bin/env python3
"""
WhatsApp Flow Test Script - Trainer Onboarding
==============================================
Sends a test interactive flow message to verify trainer onboarding flow integration.

This script:
1. Loads environment variables from .env
2. Sends a WhatsApp Flow message to a test number
3. Includes proper error handling and detailed response logging

Usage:
    python send_test_flow.py

Author: Claude
Date: 2025-11-08
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Terminal colors for better output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}\n")

def print_success(text: str):
    """Print a success message with checkmark emoji"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    """Print an error message with X emoji"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text: str):
    """Print an info message with chart emoji"""
    print(f"{Colors.BLUE}📊 {text}{Colors.END}")

def send_flow_message():
    """
    Send a WhatsApp Flow interactive message for trainer onboarding
    """
    print_header("WhatsApp Flow Test - Trainer Onboarding")

    # Load environment variables
    load_dotenv()

    # Get credentials from environment
    phone_number_id = os.getenv('PHONE_NUMBER_ID', '671257819413918')
    access_token = os.getenv('ACCESS_TOKEN')

    # Validate required environment variables
    if not access_token:
        print_error("ACCESS_TOKEN not found in environment variables")
        print(f"{Colors.YELLOW}Please ensure .env file exists with ACCESS_TOKEN set{Colors.END}")
        sys.exit(1)

    # Flow configuration
    recipient = "27731863036"  # Phone number without + prefix
    flow_id = "775047838492907"
    flow_name = "trainer_onboarding_flow"

    # Generate unique flow token with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    flow_token = f"TRAINER_ONBOARDING_TEST_TOKEN_{timestamp}"

    # API endpoint
    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"

    # Message payload
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "header": {
                "type": "text",
                "text": "Welcome to Refiloe! 🌟"
            },
            "body": {
                "text": "Ready to join Refiloe? 🎯 Complete your trainer profile to get started!"
            },
            "footer": {
                "text": "Takes only 2 minutes"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    "flow_token": flow_token,
                    "flow_id": flow_id,
                    "flow_cta": "Start Registration ✨",
                    "flow_action": "navigate",
                    "flow_action_payload": {
                        "screen": "welcome"
                    }
                }
            }
        }
    }

    # Headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Print request details
    print(f"{Colors.BOLD}Request Details:{Colors.END}")
    print(f"  {Colors.BLUE}→{Colors.END} Endpoint: {url}")
    print(f"  {Colors.BLUE}→{Colors.END} Recipient: +{recipient}")
    print(f"  {Colors.BLUE}→{Colors.END} Flow ID: {flow_id}")
    print(f"  {Colors.BLUE}→{Colors.END} Flow Name: {flow_name}")
    print(f"  {Colors.BLUE}→{Colors.END} Flow Token: {flow_token}")
    print()

    # Print payload (pretty formatted)
    print(f"{Colors.BOLD}Message Payload:{Colors.END}")
    print(json.dumps(payload, indent=2))
    print()

    # Send the request
    try:
        print(f"{Colors.YELLOW}⏳ Sending flow message...{Colors.END}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        # Print response details
        print()
        print_info(f"Response Status Code: {response.status_code}")
        print()

        # Parse response
        try:
            response_data = response.json()
            print(f"{Colors.BOLD}Full API Response:{Colors.END}")
            print(json.dumps(response_data, indent=2))
            print()
        except json.JSONDecodeError:
            print_error("Failed to parse JSON response")
            print(f"{Colors.YELLOW}Raw Response:{Colors.END}")
            print(response.text)
            print()

        # Check if successful
        if response.status_code == 200:
            if 'messages' in response_data and len(response_data['messages']) > 0:
                message_id = response_data['messages'][0].get('id', 'Unknown')
                print_success(f"Flow message sent successfully!")
                print_success(f"Message ID: {message_id}")
                print()
                print(f"{Colors.GREEN}✨ Check WhatsApp at +{recipient} for the flow message{Colors.END}")
            else:
                print_success("Request completed but no message ID returned")
        else:
            print_error(f"Failed to send flow message")
            if 'error' in response_data:
                error = response_data['error']
                print_error(f"Error Type: {error.get('type', 'Unknown')}")
                print_error(f"Error Code: {error.get('code', 'Unknown')}")
                print_error(f"Error Message: {error.get('message', 'Unknown')}")
                if 'error_data' in error:
                    print_error(f"Error Details: {json.dumps(error['error_data'], indent=2)}")
            sys.exit(1)

    except requests.exceptions.Timeout:
        print_error("Request timed out after 30 seconds")
        sys.exit(1)

    except requests.exceptions.ConnectionError:
        print_error("Failed to connect to WhatsApp API")
        print(f"{Colors.YELLOW}Please check your internet connection{Colors.END}")
        sys.exit(1)

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {str(e)}")
        sys.exit(1)

    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    send_flow_message()
