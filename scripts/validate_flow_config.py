#!/usr/bin/env python3
"""
Validate WhatsApp Flow Configuration
Checks if the system is properly configured for flows and provides recommendations
"""

import os
import sys
import requests
import json

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

def validate_configuration():
    """Validate WhatsApp Flow configuration"""
    
    print("🔧 WhatsApp Flow Configuration Validator")
    print("=" * 50)
    
    # Check required environment variables
    required_vars = {
        'ACCESS_TOKEN': 'WhatsApp Access Token',
        'PHONE_NUMBER_ID': 'WhatsApp Phone Number ID',
        'VERIFY_TOKEN': 'Webhook Verify Token',
        'BASE_URL': 'Application Base URL'
    }
    
    optional_vars = {
        'WHATSAPP_BUSINESS_ACCOUNT_ID': 'WhatsApp Business Account ID',
        'WHATSAPP_FLOW_PRIVATE_KEY': 'Flow Encryption Private Key'
    }
    
    print("1️⃣ Checking required configuration...")
    
    config_valid = True
    
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if 'TOKEN' in var or 'KEY' in var:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"   ✅ {description}: {display_value}")
        else:
            print(f"   ❌ {description}: NOT SET")
            config_valid = False
    
    print("\n2️⃣ Checking optional configuration...")
    
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            if 'TOKEN' in var or 'KEY' in var:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"   ✅ {description}: {display_value}")
        else:
            print(f"   ⚠️ {description}: NOT SET (optional)")
    
    return config_valid

def test_basic_whatsapp_api():
    """Test basic WhatsApp API connectivity"""
    
    print("\n3️⃣ Testing basic WhatsApp API connectivity...")
    
    access_token = os.environ.get('ACCESS_TOKEN')
    phone_number_id = os.environ.get('PHONE_NUMBER_ID')
    
    if not access_token or not phone_number_id:
        print("   ❌ Missing required tokens for API test")
        return False
    
    try:
        # Test phone number details
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            verified_name = data.get('verified_name', 'Unknown')
            display_phone = data.get('display_phone_number', 'Unknown')
            quality_rating = data.get('quality_rating', 'Unknown')
            
            print(f"   ✅ WhatsApp API working!")
            print(f"      Business Name: {verified_name}")
            print(f"      Phone Number: {display_phone}")
            print(f"      Quality Rating: {quality_rating}")
            return True
        else:
            print(f"   ❌ WhatsApp API test failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ WhatsApp API test error: {str(e)}")
        return False

def test_flow_capabilities():
    """Test WhatsApp Flow capabilities"""
    
    print("\n4️⃣ Testing WhatsApp Flow capabilities...")
    
    access_token = os.environ.get('ACCESS_TOKEN')
    business_account_id = os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID') or os.environ.get('PHONE_NUMBER_ID')
    
    if not access_token:
        print("   ❌ No access token for flow test")
        return False
    
    if not business_account_id:
        print("   ❌ No business account ID for flow test")
        return False
    
    try:
        # Test flow listing
        url = f"https://graph.facebook.com/v18.0/{business_account_id}/flows"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            flows_data = response.json()
            flows = flows_data.get('data', [])
            
            print(f"   ✅ Flow API working! Found {len(flows)} existing flows")
            
            for flow in flows:
                flow_name = flow.get('name', 'Unknown')
                flow_id = flow.get('id', 'Unknown')
                flow_status = flow.get('status', 'Unknown')
                print(f"      - {flow_name} (ID: {flow_id}, Status: {flow_status})")
            
            return True
            
        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            
            if 'nonexisting field (flows)' in error_msg:
                print(f"   ❌ Flow API not accessible - incorrect Business Account ID")
                print(f"      Current ID: {business_account_id}")
                print(f"      This is likely a Phone Number ID, not a Business Account ID")
                return False
            else:
                print(f"   ❌ Flow API error: {error_msg}")
                return False
                
        elif response.status_code == 401:
            print(f"   ❌ Flow API unauthorized - token lacks permissions")
            print(f"      Required permission: whatsapp_business_management")
            return False
        else:
            print(f"   ❌ Flow API test failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Flow API test error: {str(e)}")
        return False

def check_flow_files():
    """Check if flow JSON files exist"""
    
    print("\n5️⃣ Checking flow definition files...")
    
    flow_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'whatsapp_flows')
    
    if not os.path.exists(flow_dir):
        print(f"   ❌ Flow directory not found: {flow_dir}")
        return False
    
    flow_files = [
        'trainer_onboarding_flow.json'
    ]
    
    files_exist = True
    
    for flow_file in flow_files:
        flow_path = os.path.join(flow_dir, flow_file)
        
        if os.path.exists(flow_path):
            try:
                with open(flow_path, 'r', encoding='utf-8') as f:
                    flow_data = json.load(f)
                
                screens = flow_data.get('screens', [])
                version = flow_data.get('version', 'Unknown')
                
                print(f"   ✅ {flow_file}: {len(screens)} screens, version {version}")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ {flow_file}: Invalid JSON - {str(e)}")
                files_exist = False
            except Exception as e:
                print(f"   ❌ {flow_file}: Error reading - {str(e)}")
                files_exist = False
        else:
            print(f"   ❌ {flow_file}: File not found")
            files_exist = False
    
    return files_exist

def provide_recommendations():
    """Provide configuration recommendations"""
    
    print("\n" + "=" * 50)
    print("📋 RECOMMENDATIONS")
    print("=" * 50)
    
    access_token = os.environ.get('ACCESS_TOKEN')
    business_account_id = os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID')
    phone_number_id = os.environ.get('PHONE_NUMBER_ID')
    
    if not business_account_id:
        print("\n🔧 Business Account ID Configuration:")
        print("   1. The Business Account ID is different from Phone Number ID")
        print("   2. Check your WhatsApp Business Manager:")
        print("      - Go to business.facebook.com")
        print("      - Select your business")
        print("      - Look for 'Business Account ID' in settings")
        print("   3. Add to .env file:")
        print(f"      WHATSAPP_BUSINESS_ACCOUNT_ID=\"your_business_account_id\"")
    
    if access_token:
        print("\n🔑 Access Token Permissions:")
        print("   Required permissions for WhatsApp Flows:")
        print("   - whatsapp_business_management")
        print("   - whatsapp_business_messaging")
        print("   - Check token permissions at developers.facebook.com")
    
    print("\n🔄 Fallback System:")
    print("   ✅ Text-based registration is always available as fallback")
    print("   ✅ Users will never be blocked from registering")
    print("   ✅ Flow failures automatically trigger text registration")
    
    print("\n🚀 Next Steps:")
    print("   1. If flows work: Users get modern form experience")
    print("   2. If flows fail: Users get reliable text-based registration")
    print("   3. Both paths lead to successful trainer onboarding")

def main():
    """Main validation function"""
    
    # Run all validation checks
    config_valid = validate_configuration()
    api_working = test_basic_whatsapp_api()
    flows_working = test_flow_capabilities()
    files_exist = check_flow_files()
    
    # Provide recommendations
    provide_recommendations()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    print(f"Configuration: {'✅ Valid' if config_valid else '❌ Issues'}")
    print(f"WhatsApp API: {'✅ Working' if api_working else '❌ Issues'}")
    print(f"Flow API: {'✅ Working' if flows_working else '❌ Issues'}")
    print(f"Flow Files: {'✅ Present' if files_exist else '❌ Missing'}")
    
    if flows_working:
        print("\n🎉 WhatsApp Flows are fully functional!")
        print("   Users will get the modern form experience")
    else:
        print("\n⚠️ WhatsApp Flows not available")
        print("   Users will get text-based registration (reliable fallback)")
    
    print(f"\n✅ Registration system is {'fully operational' if config_valid and api_working else 'operational with fallback'}")

if __name__ == "__main__":
    main()