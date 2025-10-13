#!/usr/bin/env python3
"""
Test WhatsApp Flow Creation with different Business Account IDs
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

def test_business_account_id(business_account_id, access_token):
    """Test if a business account ID works for flow creation"""
    
    print(f"\n🧪 Testing Business Account ID: {business_account_id}")
    
    # Test 1: List flows
    try:
        url = f"https://graph.facebook.com/v18.0/{business_account_id}/flows"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        print(f"   📋 Testing flow listing...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            flows_data = response.json()
            flows = flows_data.get('data', [])
            print(f"   ✅ Flow listing works! Found {len(flows)} flows")
            
            # Test 2: Try creating a test flow
            print(f"   🚀 Testing flow creation...")
            
            create_url = f"https://graph.facebook.com/v18.0/{business_account_id}/flows"
            create_payload = {
                "name": "test_flow_" + str(int(os.urandom(4).hex(), 16)),
                "categories": ["UTILITY"]
            }
            
            create_response = requests.post(create_url, headers=headers, json=create_payload, timeout=10)
            
            if create_response.status_code == 200:
                result = create_response.json()
                flow_id = result.get('id')
                print(f"   ✅ Flow creation works! Created flow: {flow_id}")
                
                # Clean up - delete the test flow
                delete_url = f"https://graph.facebook.com/v18.0/{flow_id}"
                delete_response = requests.delete(delete_url, headers=headers, timeout=10)
                
                if delete_response.status_code == 200:
                    print(f"   🗑️ Test flow deleted successfully")
                else:
                    print(f"   ⚠️ Could not delete test flow: {delete_response.status_code}")
                
                return True
            else:
                print(f"   ❌ Flow creation failed: {create_response.status_code} - {create_response.text}")
                return False
        else:
            print(f"   ❌ Flow listing failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing business account: {str(e)}")
        return False

def main():
    """Main test function"""
    
    access_token = os.environ.get('ACCESS_TOKEN')
    phone_number_id = os.environ.get('PHONE_NUMBER_ID', '671257819413918')
    
    if not access_token:
        print("❌ ACCESS_TOKEN not found")
        return
    
    print("🧪 Testing WhatsApp Flow Creation")
    print("=" * 50)
    print(f"📱 Phone Number ID: {phone_number_id}")
    print(f"🔑 Access Token: {access_token[:20]}...")
    
    # Common business account ID patterns to test
    test_ids = [
        phone_number_id,  # Often the same as phone number ID
        "671257819413918",  # Explicit phone number ID
        # Add more potential IDs here if you know them
    ]
    
    # Try to get the business account ID from the phone number
    try:
        print(f"\n🔍 Trying to find business account from phone number...")
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}?fields=business_account_id"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'business_account_id' in data:
                business_account_id = data['business_account_id']
                print(f"   ✅ Found business account ID: {business_account_id}")
                test_ids.insert(0, business_account_id)  # Test this first
            else:
                print(f"   ℹ️ No business_account_id field in response: {data}")
        else:
            print(f"   ❌ Could not get phone number details: {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Error getting business account: {str(e)}")
    
    # Test each potential business account ID
    working_id = None
    
    for test_id in test_ids:
        if test_business_account_id(test_id, access_token):
            working_id = test_id
            break
    
    print("\n" + "=" * 50)
    
    if working_id:
        print(f"🎉 SUCCESS! Working Business Account ID: {working_id}")
        print(f"\n📝 Add this to your .env file:")
        print(f"WHATSAPP_BUSINESS_ACCOUNT_ID=\"{working_id}\"")
        
        # Update config.py suggestion
        print(f"\n💡 Or update config.py:")
        print(f"WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '{working_id}')")
        
    else:
        print("❌ No working Business Account ID found")
        print("\n💡 Next steps:")
        print("1. Check WhatsApp Business Manager for your Business Account ID")
        print("2. Verify your access token has 'whatsapp_business_management' permission")
        print("3. Contact WhatsApp support if needed")

if __name__ == "__main__":
    main()