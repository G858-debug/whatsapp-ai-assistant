#!/usr/bin/env python3
"""
Discover WhatsApp Business Account ID
"""

import os
import sys
import requests

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
                    # Remove quotes if present
                    value = value.strip('"\'')
                    env_vars[key] = value
                    os.environ[key] = value
    
    return env_vars

# Load environment
env_vars = load_env_file()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

def discover_business_account():
    """Discover the correct Business Account ID"""
    
    access_token = Config.WHATSAPP_ACCESS_TOKEN
    phone_number_id = Config.PHONE_NUMBER_ID
    
    if not access_token:
        print("❌ ACCESS_TOKEN not found in configuration")
        return
    
    print("🔍 Discovering WhatsApp Business Account ID...")
    print(f"📱 Phone Number ID: {phone_number_id}")
    print(f"🔑 Access Token: {access_token[:20]}...")
    print()
    
    # Method 1: Get phone number details to find business account
    try:
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        print("1️⃣ Getting phone number details...")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Phone number data: {data}")
            
            # Look for business account ID in the response
            if 'business_account_id' in data:
                business_account_id = data['business_account_id']
                print(f"🎯 Found Business Account ID: {business_account_id}")
                return business_account_id
        else:
            print(f"❌ Failed to get phone number details: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Error getting phone number details: {str(e)}")
    
    # Method 2: Try using phone number ID as business account ID (common case)
    try:
        print("\n2️⃣ Testing if phone number ID works as business account ID...")
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/flows"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Phone number ID works as business account ID: {phone_number_id}")
            return phone_number_id
        else:
            print(f"❌ Phone number ID doesn't work as business account: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Error testing phone number ID: {str(e)}")
    
    # Method 3: Try to get user's business accounts
    try:
        print("\n3️⃣ Getting user's business accounts...")
        url = "https://graph.facebook.com/v18.0/me/businesses"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            businesses = data.get('data', [])
            
            print(f"✅ Found {len(businesses)} business accounts:")
            for business in businesses:
                business_id = business.get('id')
                business_name = business.get('name', 'Unknown')
                print(f"   - {business_name} (ID: {business_id})")
                
                # Test if this business account has WhatsApp
                try:
                    test_url = f"https://graph.facebook.com/v18.0/{business_id}/phone_numbers"
                    test_response = requests.get(test_url, headers=headers, timeout=10)
                    
                    if test_response.status_code == 200:
                        phone_data = test_response.json()
                        phones = phone_data.get('data', [])
                        
                        for phone in phones:
                            if phone.get('id') == phone_number_id:
                                print(f"🎯 Found matching business account: {business_id}")
                                return business_id
                
                except Exception:
                    continue
        else:
            print(f"❌ Failed to get business accounts: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Error getting business accounts: {str(e)}")
    
    print("\n❌ Could not determine Business Account ID")
    print("\n💡 Suggestions:")
    print("1. Check your WhatsApp Business Manager for the correct Business Account ID")
    print("2. Verify your access token has the correct permissions")
    print("3. Try using the phone number ID as business account ID (common setup)")
    
    return None

if __name__ == "__main__":
    result = discover_business_account()
    if result:
        print(f"\n🎉 Recommended Business Account ID: {result}")
        print(f"\nAdd this to your .env file:")
        print(f"WHATSAPP_BUSINESS_ACCOUNT_ID=\"{result}\"")
    else:
        print(f"\n💭 If unsure, try using your phone number ID: {Config.PHONE_NUMBER_ID}")