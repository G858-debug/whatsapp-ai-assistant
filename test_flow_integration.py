#!/usr/bin/env python3
"""
Test script for WhatsApp Flow integration
Tests the complete flow from intent detection to flow sending
"""

import json
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_flow_json_loading():
    """Test that the flow JSON loads correctly"""
    print("🧪 Testing Flow JSON Loading...")
    
    try:
        flow_path = os.path.join('whatsapp_flows', 'trainer_onboarding_flow.json')
        with open(flow_path, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)
        
        # Validate basic structure
        assert 'version' in flow_data
        assert 'screens' in flow_data
        assert 'metadata' in flow_data
        
        # Check screens
        screens = flow_data['screens']
        assert len(screens) > 0
        
        # Check required screens
        screen_ids = [screen['id'] for screen in screens]
        required_screens = ['welcome', 'basic_info', 'business_details', 'availability', 'preferences', 'verification', 'success']
        
        for required_screen in required_screens:
            assert required_screen in screen_ids, f"Missing required screen: {required_screen}"
        
        print("✅ Flow JSON loads correctly")
        print(f"   - Version: {flow_data['version']}")
        print(f"   - Screens: {len(screens)}")
        print(f"   - Flow Name: {flow_data['metadata']['flow_name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flow JSON loading failed: {str(e)}")
        return False

def test_flow_handler_initialization():
    """Test that the flow handler initializes correctly"""
    print("\n🧪 Testing Flow Handler Initialization...")
    
    try:
        # Mock dependencies
        class MockSupabase:
            def table(self, name):
                return self
            def select(self, *args):
                return self
            def eq(self, *args):
                return self
            def execute(self):
                return type('Result', (), {'data': []})()
            def insert(self, data):
                return self
        
        class MockWhatsApp:
            def send_flow_message(self, message):
                return {'success': True, 'message_id': 'test_123'}
        
        # Initialize flow handler
        from services.whatsapp_flow_handler import WhatsAppFlowHandler
        
        mock_supabase = MockSupabase()
        mock_whatsapp = MockWhatsApp()
        
        flow_handler = WhatsAppFlowHandler(mock_supabase, mock_whatsapp)
        
        # Test flow message creation
        flow_message = flow_handler.create_flow_message("+27821234567")
        
        assert flow_message is not None
        assert 'to' in flow_message
        assert 'type' in flow_message
        assert flow_message['type'] == 'interactive'
        assert flow_message['interactive']['type'] == 'flow'
        
        print("✅ Flow handler initializes correctly")
        print(f"   - Flow message created successfully")
        print(f"   - Message type: {flow_message['type']}")
        print(f"   - Interactive type: {flow_message['interactive']['type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flow handler initialization failed: {str(e)}")
        return False

def test_whatsapp_service_flow_method():
    """Test that WhatsApp service has flow method"""
    print("\n🧪 Testing WhatsApp Service Flow Method...")
    
    try:
        from services.whatsapp import WhatsAppService
        
        # Check if the method exists
        assert hasattr(WhatsAppService, 'send_flow_message')
        
        # Check method signature
        import inspect
        sig = inspect.signature(WhatsAppService.send_flow_message)
        params = list(sig.parameters.keys())
        
        assert 'flow_message' in params
        
        print("✅ WhatsApp service has flow method")
        print(f"   - Method exists: send_flow_message")
        print(f"   - Parameters: {params}")
        
        return True
        
    except Exception as e:
        print(f"❌ WhatsApp service flow method test failed: {str(e)}")
        return False

def test_ai_intent_handler_flow_integration():
    """Test that AI intent handler has flow integration"""
    print("\n🧪 Testing AI Intent Handler Flow Integration...")
    
    try:
        from services.ai_intent_handler import AIIntentHandler
        
        # Check if the method exists
        assert hasattr(AIIntentHandler, '_handle_trainer_onboarding')
        assert hasattr(AIIntentHandler, '_start_chat_based_onboarding')
        
        print("✅ AI intent handler has flow integration")
        print(f"   - Method exists: _handle_trainer_onboarding")
        print(f"   - Fallback method exists: _start_chat_based_onboarding")
        
        return True
        
    except Exception as e:
        print(f"❌ AI intent handler flow integration test failed: {str(e)}")
        return False

def test_webhook_flow_processing():
    """Test that webhook can process flow responses"""
    print("\n🧪 Testing Webhook Flow Processing...")
    
    try:
        # Check if webhook has flow processing
        with open('routes/webhooks.py', 'r') as f:
            webhook_content = f.read()
        
        # Look for flow processing code
        flow_indicators = [
            "interactive_type == 'flow'",
            "flow_response",
            "handle_flow_response"
        ]
        
        for indicator in flow_indicators:
            assert indicator in webhook_content, f"Missing flow indicator: {indicator}"
        
        print("✅ Webhook has flow processing")
        print(f"   - Flow response handling implemented")
        print(f"   - Flow handler integration present")
        
        return True
        
    except Exception as e:
        print(f"❌ Webhook flow processing test failed: {str(e)}")
        return False

def test_app_core_integration():
    """Test that app core has flow integration"""
    print("\n🧪 Testing App Core Integration...")
    
    try:
        with open('app_core.py', 'r') as f:
            app_core_content = f.read()
        
        # Check for flow handler initialization
        flow_indicators = [
            "WhatsAppFlowHandler",
            "flow_handler",
            "trainer_registration_handler"
        ]
        
        for indicator in flow_indicators:
            assert indicator in app_core_content, f"Missing flow indicator: {indicator}"
        
        print("✅ App core has flow integration")
        print(f"   - Flow handler initialized")
        print(f"   - Trainer registration handler initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ App core integration test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all flow integration tests"""
    print("🚀 Starting WhatsApp Flow Integration Tests")
    print("=" * 50)
    
    tests = [
        test_flow_json_loading,
        test_flow_handler_initialization,
        test_whatsapp_service_flow_method,
        test_ai_intent_handler_flow_integration,
        test_webhook_flow_processing,
        test_app_core_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {str(e)}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test.__name__}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Flow integration is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
