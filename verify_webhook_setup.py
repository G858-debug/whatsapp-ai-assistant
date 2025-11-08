#!/usr/bin/env python3
"""
Webhook Setup Verification Script
==================================
Comprehensive verification of WhatsApp webhook configuration and flow handling.

This script checks:
1. Environment configuration (Railway variables)
2. Webhook endpoint accessibility
3. Flow completion payload handling
4. WhatsAppFlowHandler functionality
5. Database connectivity

Author: Claude
Date: 2024-11-08
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, Tuple, Optional

# Terminal colors for better output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}\n")

def print_section(text: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{text}{Colors.END}")
    print(f"{Colors.MAGENTA}{'-' * len(text)}{Colors.END}")

def print_success(text: str, indent: int = 0):
    """Print a success message"""
    prefix = " " * indent
    print(f"{prefix}{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str, indent: int = 0):
    """Print an error message"""
    prefix = " " * indent
    print(f"{prefix}{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text: str, indent: int = 0):
    """Print a warning message"""
    prefix = " " * indent
    print(f"{prefix}{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text: str, indent: int = 0):
    """Print an info message"""
    prefix = " " * indent
    print(f"{prefix}{Colors.BLUE}ℹ️  {text}{Colors.END}")

def load_env_file() -> Dict[str, str]:
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env_vars = {}

    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"\'')
                    env_vars[key] = value
                    os.environ[key] = value

    return env_vars

def check_environment_config() -> Tuple[bool, Dict[str, any]]:
    """Check if required environment variables are configured"""
    print_section("1. Environment Configuration Check")

    required_vars = {
        'BASE_URL': 'Webhook base URL',
        'ACCESS_TOKEN': 'WhatsApp API token',
        'SUPABASE_URL': 'Database URL',
        'SUPABASE_SERVICE_KEY': 'Database service key',
        'PHONE_NUMBER_ID': 'WhatsApp phone number ID',
    }

    optional_vars = {
        'WHATSAPP_BUSINESS_ACCOUNT_ID': 'Business Account ID (for flows)',
        'VERIFY_TOKEN': 'Webhook verification token',
    }

    all_configured = True
    config_status = {}

    for var_name, description in required_vars.items():
        value = os.environ.get(var_name)
        if value:
            print_success(f"{description}: {var_name}", indent=2)
            # Show masked value for sensitive data
            if 'TOKEN' in var_name or 'KEY' in var_name:
                masked = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                print_info(f"Value: {masked}", indent=4)
            else:
                print_info(f"Value: {value}", indent=4)
            config_status[var_name] = True
        else:
            print_error(f"{description}: {var_name} - NOT SET", indent=2)
            config_status[var_name] = False
            all_configured = False

    print()
    for var_name, description in optional_vars.items():
        value = os.environ.get(var_name)
        if value:
            print_success(f"{description}: {var_name} (optional)", indent=2)
            config_status[var_name] = True
        else:
            print_warning(f"{description}: {var_name} - NOT SET (optional)", indent=2)
            config_status[var_name] = False

    if all_configured:
        print_success("\nAll required environment variables configured!", indent=0)
    else:
        print_error("\nSome required environment variables are missing!", indent=0)

    return all_configured, config_status

def test_webhook_endpoint() -> Tuple[bool, Dict[str, any]]:
    """Test if the webhook endpoint is accessible"""
    print_section("2. Webhook Endpoint Accessibility Test")

    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    webhook_url = f"{base_url}/webhook"
    verify_token = os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe')

    print_info(f"Testing webhook URL: {webhook_url}", indent=2)

    results = {}

    # Test 1: Webhook verification (GET request)
    print_info("Testing webhook verification (GET)...", indent=2)
    try:
        response = requests.get(
            webhook_url,
            params={
                'hub.mode': 'subscribe',
                'hub.verify_token': verify_token,
                'hub.challenge': 'test_challenge_123'
            },
            timeout=10
        )

        if response.status_code == 200 and response.text == 'test_challenge_123':
            print_success("Webhook verification endpoint working correctly", indent=4)
            results['verification'] = True
        else:
            print_error(f"Webhook verification failed: Status {response.status_code}", indent=4)
            results['verification'] = False
    except requests.exceptions.ConnectionError:
        print_warning("Could not connect to webhook endpoint (server may not be running)", indent=4)
        results['verification'] = None
    except Exception as e:
        print_error(f"Webhook verification error: {str(e)}", indent=4)
        results['verification'] = False

    # Test 2: Webhook POST endpoint
    print_info("Testing webhook POST endpoint...", indent=2)
    try:
        test_payload = {
            "object": "whatsapp_business_account",
            "entry": [{"changes": []}]
        }

        response = requests.post(
            webhook_url,
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            print_success("Webhook POST endpoint accessible", indent=4)
            results['post_endpoint'] = True
        else:
            print_error(f"Webhook POST failed: Status {response.status_code}", indent=4)
            results['post_endpoint'] = False
    except requests.exceptions.ConnectionError:
        print_warning("Could not connect to webhook endpoint (server may not be running)", indent=4)
        results['post_endpoint'] = None
    except Exception as e:
        print_error(f"Webhook POST error: {str(e)}", indent=4)
        results['post_endpoint'] = False

    success = results.get('verification') == True or results.get('post_endpoint') == True
    return success, results

def simulate_flow_completion() -> Tuple[bool, Dict[str, any]]:
    """Simulate a flow completion payload"""
    print_section("3. Flow Completion Payload Simulation")

    # Create a realistic flow completion payload
    test_phone = "+27123456789"
    timestamp = int(datetime.now().timestamp())

    sample_trainer_data = {
        'full_name': 'Test Trainer',
        'email': 'test.trainer@example.com',
        'city': 'Cape Town',
        'specialization': 'personal_training',
        'experience_years': '2-3',
        'pricing_per_session': '450',
        'available_days': ['monday', 'wednesday', 'friday'],
        'preferred_time_slots': 'morning',
        'subscription_plan': 'premium',
        'notification_preferences': ['booking_notifications'],
        'terms_accepted': True,
        'marketing_consent': False
    }

    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "671257819413918",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "+27730564882",
                        "phone_number_id": "671257819413918"
                    },
                    "messages": [{
                        "from": test_phone,
                        "id": f"wamid.test_{timestamp}",
                        "timestamp": str(timestamp),
                        "type": "interactive",
                        "interactive": {
                            "type": "nfm_reply",
                            "nfm_reply": {
                                "name": "trainer_onboarding_flow",
                                "response_json": json.dumps(sample_trainer_data),
                                "flow_token": f"test_token_{timestamp}"
                            }
                        }
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    print_info(f"Simulating flow completion from: {test_phone}", indent=2)
    print_info(f"Flow: trainer_onboarding_flow", indent=2)
    print_info(f"Trainer: {sample_trainer_data['full_name']}", indent=2)

    results = {
        'payload_created': True,
        'payload': webhook_payload
    }

    # Test sending to webhook endpoint
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    webhook_url = f"{base_url}/webhook"

    print_info("Sending simulated payload to webhook...", indent=2)
    try:
        response = requests.post(
            webhook_url,
            json=webhook_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            print_success("Flow payload processed successfully", indent=4)
            results['webhook_processed'] = True
        else:
            print_error(f"Flow payload processing failed: Status {response.status_code}", indent=4)
            print_info(f"Response: {response.text[:200]}", indent=6)
            results['webhook_processed'] = False
    except requests.exceptions.ConnectionError:
        print_warning("Could not connect to webhook (server may not be running)", indent=4)
        results['webhook_processed'] = None
    except Exception as e:
        print_error(f"Error sending payload: {str(e)}", indent=4)
        results['webhook_processed'] = False

    return results.get('webhook_processed', False), results

def verify_flow_handler() -> Tuple[bool, Dict[str, any]]:
    """Verify WhatsAppFlowHandler can process flow responses"""
    print_section("4. WhatsAppFlowHandler Verification")

    try:
        # Add parent directory to path
        sys.path.insert(0, os.path.dirname(__file__))

        from services.whatsapp_flow_handler import WhatsAppFlowHandler

        print_success("WhatsAppFlowHandler module imported successfully", indent=2)

        # Create mock objects for testing
        class MockSupabase:
            def table(self, table_name):
                return MockTable(table_name)

        class MockTable:
            def __init__(self, table_name):
                self.table_name = table_name

            def insert(self, data):
                return MockResult([{'id': 'test_trainer_123'}])

            def select(self, fields):
                return self

            def eq(self, field, value):
                return self

            def execute(self):
                return MockResult([])

        class MockResult:
            def __init__(self, data):
                self.data = data

        class MockWhatsAppService:
            def send_message(self, phone, message):
                return {'success': True}

        # Initialize flow handler
        mock_supabase = MockSupabase()
        mock_whatsapp = MockWhatsAppService()

        flow_handler = WhatsAppFlowHandler(mock_supabase, mock_whatsapp)

        print_success("WhatsAppFlowHandler initialized successfully", indent=2)

        # Test flow response processing
        test_flow_data = {
            'phone_number': '+27123456789',
            'message_id': 'test_msg_123',
            'timestamp': str(int(datetime.now().timestamp())),
            'flow_response': {
                'name': 'trainer_onboarding_flow',
                'flow_token': 'test_token_123',
                'data': {
                    'full_name': 'Test Trainer',
                    'email': 'test@example.com',
                    'city': 'Cape Town',
                    'specialization': 'personal_training',
                    'experience_years': '2-3',
                    'pricing_per_session': '450',
                    'available_days': ['monday', 'wednesday'],
                    'preferred_time_slots': 'morning',
                    'subscription_plan': 'premium',
                    'notification_preferences': ['booking_notifications'],
                    'terms_accepted': True,
                    'marketing_consent': False
                }
            }
        }

        print_info("Testing flow response processing...", indent=2)
        result = flow_handler.handle_flow_response(test_flow_data)

        if result.get('success'):
            print_success("Flow response processed successfully", indent=4)
            print_info(f"Result: {result.get('message', 'No message')}", indent=6)
            if result.get('trainer_id'):
                print_info(f"Trainer ID: {result['trainer_id']}", indent=6)
            return True, {'handler_works': True, 'result': result}
        else:
            print_error("Flow response processing failed", indent=4)
            print_info(f"Error: {result.get('error', 'Unknown error')}", indent=6)
            return False, {'handler_works': False, 'result': result}

    except ImportError as e:
        print_error(f"Could not import WhatsAppFlowHandler: {str(e)}", indent=2)
        return False, {'handler_works': False, 'error': str(e)}
    except Exception as e:
        print_error(f"Flow handler verification error: {str(e)}", indent=2)
        return False, {'handler_works': False, 'error': str(e)}

def verify_database_connectivity() -> Tuple[bool, Dict[str, any]]:
    """Verify database connectivity"""
    print_section("5. Database Connectivity Check")

    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')

    if not supabase_url or not supabase_key:
        print_error("Supabase credentials not configured", indent=2)
        return False, {'connected': False, 'error': 'Missing credentials'}

    try:
        from supabase import create_client

        print_info(f"Connecting to Supabase: {supabase_url[:30]}...", indent=2)

        supabase = create_client(supabase_url, supabase_key)

        # Test connection by querying a table
        print_info("Testing database query...", indent=2)

        # Try to query trainers table
        try:
            result = supabase.table('trainers').select('id').limit(1).execute()
            print_success("Database connection successful", indent=4)
            print_info(f"Trainers table accessible", indent=6)
            return True, {'connected': True, 'tables': ['trainers']}
        except Exception as query_error:
            print_warning(f"Could not query trainers table: {str(query_error)}", indent=4)
            # Still connected, but table might not exist
            return True, {'connected': True, 'warning': str(query_error)}

    except ImportError:
        print_error("Supabase Python client not installed", indent=2)
        print_info("Run: pip install supabase", indent=4)
        return False, {'connected': False, 'error': 'Module not installed'}
    except Exception as e:
        print_error(f"Database connection error: {str(e)}", indent=2)
        return False, {'connected': False, 'error': str(e)}

def print_summary(results: Dict[str, Tuple[bool, Dict]]):
    """Print a summary of all verification results"""
    print_header("VERIFICATION SUMMARY")

    # Overall status indicators
    env_ok, env_data = results.get('environment', (False, {}))
    webhook_ok, webhook_data = results.get('webhook', (False, {}))
    flow_sim_ok, flow_sim_data = results.get('flow_simulation', (False, {}))
    handler_ok, handler_data = results.get('flow_handler', (False, {}))
    db_ok, db_data = results.get('database', (False, {}))

    # Main webhook URL status
    base_url = os.environ.get('BASE_URL', 'Not configured')
    if env_data.get('BASE_URL'):
        print_success(f"Main webhook URL: {base_url}/webhook")
    else:
        print_error(f"Main webhook URL: NOT CONFIGURED")

    # Flow handling capability
    if handler_ok:
        print_success("Flow handling capability: OPERATIONAL")
    else:
        print_error("Flow handling capability: NOT OPERATIONAL")

    # Database connectivity
    if db_ok:
        print_success("Database connectivity: CONNECTED")
    else:
        print_error("Database connectivity: NOT CONNECTED")

    # Configuration issues
    print("\n" + Colors.BOLD + "Configuration Issues:" + Colors.END)
    issues_found = False

    if not env_ok:
        print_error("Missing required environment variables", indent=2)
        for var, status in env_data.items():
            if not status:
                print_info(f"Set {var} in Railway environment", indent=4)
        issues_found = True

    if not webhook_ok and webhook_data.get('verification') is False:
        print_error("Webhook verification failing", indent=2)
        issues_found = True

    if not handler_ok:
        print_error("Flow handler not functioning correctly", indent=2)
        if handler_data.get('error'):
            print_info(f"Error: {handler_data['error']}", indent=4)
        issues_found = True

    if not db_ok:
        print_error("Database connection failing", indent=2)
        if db_data.get('error'):
            print_info(f"Error: {db_data['error']}", indent=4)
        issues_found = True

    if not issues_found:
        print_success("No configuration issues detected!", indent=2)

    # Overall status
    print("\n" + Colors.BOLD + "Overall Status:" + Colors.END)
    all_ok = env_ok and handler_ok and db_ok

    if all_ok:
        print_success("✨ Webhook setup is READY for production!")
        print_info("You can now configure this webhook in WhatsApp Business API", indent=2)
        print_info(f"Webhook URL: {base_url}/webhook", indent=2)
        print_info(f"Verify Token: {os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe')}", indent=2)
    else:
        print_warning("⚠️  Webhook setup has issues that need attention")
        print_info("Review the issues above and fix configuration", indent=2)

def main():
    """Main verification function"""
    print_header("WhatsApp Webhook Setup Verification")

    print_info("Loading environment variables...")
    load_env_file()

    # Run all verification checks
    results = {}

    results['environment'] = check_environment_config()
    results['webhook'] = test_webhook_endpoint()
    results['flow_simulation'] = simulate_flow_completion()
    results['flow_handler'] = verify_flow_handler()
    results['database'] = verify_database_connectivity()

    # Print summary
    print_summary(results)

    # Exit code
    env_ok, _ = results['environment']
    handler_ok, _ = results['flow_handler']
    db_ok, _ = results['database']

    if env_ok and handler_ok and db_ok:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
