#!/usr/bin/env python3
"""
Test WhatsApp Flow Webhook Processing
Simulates flow completion webhooks to test the processing system
"""

import os
import sys
import json
import requests
from datetime import datetime

# Load environment variables manually
def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
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

env_vars = load_env_file()

def create_sample_flow_webhook():
    """Create a sample flow completion webhook payload"""
    
    # Sample trainer data that would come from the flow
    sample_trainer_data = {
        'full_name': 'John Smith',
        'email': 'john.smith@example.com',
        'city': 'Cape Town',
        'specialization': 'personal_training',
        'experience_years': '2-3',
        'pricing_per_session': '450',
        'available_days': ['monday', 'wednesday', 'friday'],
        'preferred_time_slots': 'morning',
        'subscription_plan': 'premium',
        'notification_preferences': ['booking_notifications', 'payment_reminders'],
        'terms_accepted': True,
        'marketing_consent': False
    }
    
    # WhatsApp webhook structure for flow completion
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "671257819413918",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "+27730564882",
                                "phone_number_id": "671257819413918"
                            },
                            "messages": [
                                {
                                    "from": "+27123456789",  # Test phone number
                                    "id": f"wamid.test_{int(datetime.now().timestamp())}",
                                    "timestamp": str(int(datetime.now().timestamp())),
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "flow",
                                        "flow_response": {
                                            "name": "trainer_onboarding_flow",
                                            "flow_token": f"test_token_{int(datetime.now().timestamp())}",
                                            "data": sample_trainer_data
                                        }
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    return webhook_payload

def test_flow_webhook_locally():
    """Test flow webhook processing locally (without sending HTTP request)"""
    
    print("🧪 Testing Flow Webhook Processing Locally")
    print("=" * 50)
    
    try:
        # Add parent directory to path
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        
        from services.whatsapp_flow_handler import WhatsAppFlowHandler
        from config import Config
        
        # Mock supabase and whatsapp service for testing
        class MockSupabase:
            def table(self, table_name):
                return MockTable()
        
        class MockTable:
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
                print(f"📱 Would send message to {phone}: {message[:100]}...")
                return {'success': True}
        
        # Initialize flow handler with mocks
        mock_supabase = MockSupabase()
        mock_whatsapp = MockWhatsAppService()
        
        flow_handler = WhatsAppFlowHandler(mock_supabase, mock_whatsapp)
        
        # Create sample flow response data
        sample_flow_data = {
            'phone_number': '+27123456789',
            'flow_response': {
                'name': 'trainer_onboarding_flow',
                'flow_token': 'test_token_123',
                'data': {
                    'full_name': 'John Smith',
                    'email': 'john.smith@example.com',
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
            }
        }
        
        print("1️⃣ Testing flow response processing...")
        print(f"   Phone: {sample_flow_data['phone_number']}")
        print(f"   Trainer: {sample_flow_data['flow_response']['data']['full_name']}")
        print(f"   Email: {sample_flow_data['flow_response']['data']['email']}")
        
        # Process the flow response
        result = flow_handler.handle_flow_response(sample_flow_data)
        
        if result.get('success'):
            print(f"✅ Flow processing successful!")
            print(f"   Message: {result.get('message')}")
            print(f"   Method: {result.get('method', 'unknown')}")
            if result.get('trainer_id'):
                print(f"   Trainer ID: {result.get('trainer_id')}")
        else:
            print(f"❌ Flow processing failed!")
            print(f"   Error: {result.get('error')}")
            if result.get('details'):
                print(f"   Details: {result.get('details')}")
        
        return result.get('success', False)
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("   Make sure you're running from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False

def test_webhook_endpoint():
    """Test the actual webhook endpoint (if server is running)"""
    
    print("\n2️⃣ Testing Webhook Endpoint...")
    
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    webhook_url = f"{base_url}/flow/webhook/flow"
    
    print(f"   Webhook URL: {webhook_url}")
    
    # Create sample webhook payload
    webhook_payload = create_sample_flow_webhook()
    
    try:
        response = requests.post(
            webhook_url,
            json=webhook_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook endpoint working!")
            print(f"   Status: {result.get('status')}")
            print(f"   Processed: {result.get('processed', 0)} flows")
        else:
            print(f"❌ Webhook endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
        
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print("⚠️ Could not connect to webhook endpoint")
        print("   This is expected if the server is not running")
        return None
    except Exception as e:
        print(f"❌ Webhook test error: {str(e)}")
        return False

def validate_flow_json_structure():
    """Validate that our flow JSON matches expected webhook structure"""
    
    print("\n3️⃣ Validating Flow JSON Structure...")
    
    flow_json_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'whatsapp_flows', 
        'trainer_onboarding_flow.json'
    )
    
    if not os.path.exists(flow_json_path):
        print(f"❌ Flow JSON not found: {flow_json_path}")
        return False
    
    try:
        with open(flow_json_path, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)
        
        screens = flow_data.get('screens', [])
        version = flow_data.get('version', 'Unknown')
        
        print(f"✅ Flow JSON loaded successfully")
        print(f"   Version: {version}")
        print(f"   Screens: {len(screens)}")
        
        # Check for required form fields
        required_fields = [
            'full_name', 'email', 'city', 'specialization', 
            'experience_years', 'pricing_per_session', 'terms_accepted'
        ]
        
        found_fields = []
        
        for screen in screens:
            layout = screen.get('layout', {})
            children = layout.get('children', [])
            
            for child in children:
                if child.get('type') == 'FORM':
                    form_children = child.get('children', [])
                    for form_field in form_children:
                        field_name = form_field.get('name')
                        if field_name:
                            found_fields.append(field_name)
        
        print(f"   Form fields found: {len(found_fields)}")
        
        missing_fields = [field for field in required_fields if field not in found_fields]
        
        if missing_fields:
            print(f"⚠️ Missing required fields: {missing_fields}")
        else:
            print(f"✅ All required fields present")
        
        return len(missing_fields) == 0
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        return False

def main():
    """Main test function"""
    
    print("🔧 WhatsApp Flow Webhook Testing")
    print("=" * 50)
    
    # Run all tests
    local_test_passed = test_flow_webhook_locally()
    endpoint_test_result = test_webhook_endpoint()
    json_validation_passed = validate_flow_json_structure()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    print(f"Local Processing: {'✅ Passed' if local_test_passed else '❌ Failed'}")
    
    if endpoint_test_result is None:
        print(f"Webhook Endpoint: ⚠️ Server not running")
    else:
        print(f"Webhook Endpoint: {'✅ Passed' if endpoint_test_result else '❌ Failed'}")
    
    print(f"Flow JSON Structure: {'✅ Valid' if json_validation_passed else '❌ Issues'}")
    
    if local_test_passed and json_validation_passed:
        print("\n🎉 Flow webhook processing is ready!")
        print("   ✅ Flow response processing works correctly")
        print("   ✅ Trainer data extraction is functional")
        print("   ✅ Flow JSON structure is valid")
    else:
        print("\n⚠️ Some issues found - check the details above")
    
    print("\n🚀 Next steps:")
    print("   1. Deploy the updated webhook handler")
    print("   2. Test with actual WhatsApp Flow (when Business Account ID is configured)")
    print("   3. Monitor flow completion rates")

if __name__ == "__main__":
    main()