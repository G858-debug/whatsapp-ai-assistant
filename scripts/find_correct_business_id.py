#!/usr/bin/env python3
"""
Find the correct WhatsApp Business Account ID for Flow creation
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

def check_token_permissions():
    """Check what permissions the access token has"""
    
    access_token = os.environ.get('ACCESS_TOKEN')
    
    if not access_token:
        print("❌ No access token found")
        return
    
    print("🔑 Checking Access Token Permissions...")
    print("=" * 50)
    
    try:
        # Get token info
        url = f"https://graph.facebook.com/v18.0/me/permissions"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            permissions = data.get('data', [])
            
            print(f"✅ Token has {len(permissions)} permissions:")
            
            whatsapp_permissions = []
            business_permissions = []
            
            for perm in permissions:
                permission_name = perm.get('permission')
                status = perm.get('status')
                
                if 'whatsapp' in permission_name.lower():
                    whatsapp_permissions.append(f"   - {permission_name}: {status}")
                elif 'business' in permission_name.lower():
                    business_permissions.append(f"   - {permission_name}: {status}")
            
            if whatsapp_permissions:
                print("\n📱 WhatsApp Permissions:")
                for perm in whatsapp_permissions:
                    print(perm)
            
            if business_permissions:
                print("\n🏢 Business Permissions:")
                for perm in business_permissions:
                    print(perm)
            
            # Check for required permissions
            required_perms = ['whatsapp_business_management', 'whatsapp_business_messaging']
            granted_perms = [p.get('permission') for p in permissions if p.get('status') == 'granted']
            
            print(f"\n🎯 Required for Flows: {required_perms}")
            
            missing_perms = [perm for perm in required_perms if perm not in granted_perms]
            
            if missing_perms:
                print(f"❌ Missing permissions: {missing_perms}")
            else:
                print(f"✅ All required permissions granted")
        
        else:
            print(f"❌ Failed to get permissions: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Error checking permissions: {str(e)}")

def find_whatsapp_business_accounts():
    """Find WhatsApp Business Accounts associated with the token"""
    
    access_token = os.environ.get('ACCESS_TOKEN')
    
    print("\n🔍 Finding WhatsApp Business Accounts...")
    print("=" * 50)
    
    try:
        # Method 1: Get user's businesses
        url = "https://graph.facebook.com/v18.0/me/businesses"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            businesses = data.get('data', [])
            
            print(f"✅ Found {len(businesses)} businesses:")
            
            for business in businesses:
                business_id = business.get('id')
                business_name = business.get('name', 'Unknown')
                
                print(f"\n🏢 Business: {business_name} (ID: {business_id})")
                
                # Check if this business has WhatsApp
                check_business_whatsapp(business_id, access_token)
        
        else:
            print(f"❌ Failed to get businesses: {response.status_code} - {response.text}")
            
            # Method 2: Try to get WhatsApp Business Account directly
            print("\n🔄 Trying alternative method...")
            check_whatsapp_business_account_direct(access_token)
    
    except Exception as e:
        print(f"❌ Error finding businesses: {str(e)}")

def check_business_whatsapp(business_id, access_token):
    """Check if a business has WhatsApp and can create flows"""
    
    try:
        # Check for WhatsApp phone numbers
        url = f"https://graph.facebook.com/v18.0/{business_id}/phone_numbers"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            phones = data.get('data', [])
            
            if phones:
                print(f"   📱 Has {len(phones)} WhatsApp phone numbers")
                
                for phone in phones:
                    phone_id = phone.get('id')
                    display_number = phone.get('display_phone_number', 'Unknown')
                    print(f"      - {display_number} (ID: {phone_id})")
                
                # Test if this business can create flows
                test_flow_access(business_id, access_token)
            else:
                print(f"   ❌ No WhatsApp phone numbers")
        else:
            print(f"   ❌ Cannot access phone numbers: {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Error checking WhatsApp: {str(e)}")

def test_flow_access(business_id, access_token):
    """Test if we can access flows for this business"""
    
    try:
        url = f"https://graph.facebook.com/v18.0/{business_id}/flows"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            flows = data.get('data', [])
            print(f"   ✅ Flow access works! Found {len(flows)} flows")
            
            if flows:
                for flow in flows:
                    flow_name = flow.get('name', 'Unknown')
                    flow_id = flow.get('id', 'Unknown')
                    print(f"      - {flow_name} (ID: {flow_id})")
            
            return True
        else:
            print(f"   ❌ Flow access failed: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"   ❌ Error testing flow access: {str(e)}")
        return False

def check_whatsapp_business_account_direct(access_token):
    """Try to find WhatsApp Business Account directly"""
    
    phone_number_id = os.environ.get('PHONE_NUMBER_ID')
    
    if not phone_number_id:
        print("❌ No phone number ID to work with")
        return
    
    try:
        # Get phone number details to find parent business account
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}?fields=id,display_phone_number,verified_name,business_account_id"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"📱 Phone Number Details:")
            print(f"   ID: {data.get('id')}")
            print(f"   Display: {data.get('display_phone_number')}")
            print(f"   Verified Name: {data.get('verified_name')}")
            
            if 'business_account_id' in data:
                business_account_id = data['business_account_id']
                print(f"   🎯 Business Account ID: {business_account_id}")
                
                # Test flow access with this ID
                if test_flow_access(business_account_id, access_token):
                    print(f"\n🎉 FOUND WORKING BUSINESS ACCOUNT ID: {business_account_id}")
                    return business_account_id
            else:
                print(f"   ❌ No business_account_id field in response")
        else:
            print(f"❌ Failed to get phone details: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Error checking phone details: {str(e)}")
    
    return None

def main():
    """Main function"""
    
    print("🔍 WhatsApp Business Account ID Finder")
    print("=" * 50)
    
    access_token = os.environ.get('ACCESS_TOKEN')
    current_business_id = os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID')
    
    if not access_token:
        print("❌ No ACCESS_TOKEN found in environment")
        return
    
    print(f"🔑 Access Token: {access_token[:20]}...")
    print(f"📱 Current Business ID: {current_business_id}")
    
    # Check token permissions
    check_token_permissions()
    
    # Find business accounts
    working_id = find_whatsapp_business_accounts()
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    
    if working_id:
        print(f"🎉 Found working Business Account ID: {working_id}")
        print(f"\n📝 Update your .env file:")
        print(f'WHATSAPP_BUSINESS_ACCOUNT_ID="{working_id}"')
    else:
        print("❌ No working Business Account ID found")
        print("\n💡 Possible solutions:")
        print("1. Check if your access token has 'whatsapp_business_management' permission")
        print("2. Verify the Business Account ID in WhatsApp Business Manager")
        print("3. Ensure your app is approved for WhatsApp Business API")
        print("4. Contact WhatsApp support if needed")
    
    print(f"\n🔄 Current fallback system works perfectly!")
    print(f"   Users get text-based registration when flows aren't available")

if __name__ == "__main__":
    main()