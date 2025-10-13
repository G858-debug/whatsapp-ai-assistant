#!/usr/bin/env python3
"""
WhatsApp Flow Manager Script
Checks if flows exist and creates them if needed
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from utils.logger import log_info, log_error, log_warning

class WhatsAppFlowManager:
    """Manages WhatsApp Flows via API"""
    
    def __init__(self):
        self.access_token = Config.WHATSAPP_ACCESS_TOKEN
        self.business_account_id = Config.WHATSAPP_BUSINESS_ACCOUNT_ID
        self.base_url = Config.BASE_URL
        
        # Validate configuration
        if not self.access_token:
            raise ValueError("WHATSAPP_ACCESS_TOKEN not configured")
        if not self.business_account_id:
            raise ValueError("WHATSAPP_BUSINESS_ACCOUNT_ID not configured")
    
    def list_existing_flows(self) -> dict:
        """List all existing flows"""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.business_account_id}/flows"
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            print(f"📋 Listing flows for business account: {self.business_account_id}")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                flows_data = response.json()
                flows = flows_data.get('data', [])
                
                print(f"✅ Found {len(flows)} existing flows:")
                for flow in flows:
                    print(f"   - {flow.get('name')} (ID: {flow.get('id')}) - Status: {flow.get('status', 'unknown')}")
                
                return {'success': True, 'flows': flows}
            else:
                print(f"❌ Failed to list flows: {response.status_code} - {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            print(f"❌ Error listing flows: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_flow_exists(self, flow_name: str) -> dict:
        """Check if a specific flow exists"""
        try:
            flows_result = self.list_existing_flows()
            
            if flows_result.get('success'):
                flows = flows_result.get('flows', [])
                
                for flow in flows:
                    if flow.get('name') == flow_name:
                        return {
                            'exists': True,
                            'flow_id': flow.get('id'),
                            'status': flow.get('status'),
                            'flow_data': flow
                        }
                
                return {'exists': False}
            else:
                return {'exists': False, 'error': flows_result.get('error')}
                
        except Exception as e:
            print(f"❌ Error checking flow existence: {str(e)}")
            return {'exists': False, 'error': str(e)}
    
    def create_trainer_onboarding_flow(self) -> dict:
        """Create the trainer onboarding flow"""
        try:
            # Load flow JSON
            flow_json_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'whatsapp_flows', 
                'trainer_onboarding_flow.json'
            )
            
            if not os.path.exists(flow_json_path):
                return {'success': False, 'error': f'Flow JSON not found: {flow_json_path}'}
            
            with open(flow_json_path, 'r', encoding='utf-8') as f:
                flow_json = json.load(f)
            
            # Create flow via API
            url = f"https://graph.facebook.com/v18.0/{self.business_account_id}/flows"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            api_payload = {
                "name": "trainer_onboarding_flow",
                "categories": ["UTILITY"],
                "endpoint_uri": f"{self.base_url}/flow/webhook/flow"
            }
            
            print(f"🚀 Creating trainer onboarding flow...")
            print(f"   API URL: {url}")
            print(f"   Payload: {json.dumps(api_payload, indent=2)}")
            
            response = requests.post(url, headers=headers, json=api_payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                flow_id = result.get('id')
                
                print(f"✅ Flow created successfully with ID: {flow_id}")
                
                # Publish flow JSON
                publish_result = self.publish_flow_json(flow_id, flow_json)
                
                if publish_result.get('success'):
                    print(f"✅ Flow JSON published successfully")
                    return {
                        'success': True,
                        'flow_id': flow_id,
                        'message': 'Flow created and published successfully'
                    }
                else:
                    print(f"⚠️ Flow created but JSON publishing failed: {publish_result.get('error')}")
                    return {
                        'success': False,
                        'flow_id': flow_id,
                        'error': f'JSON publishing failed: {publish_result.get("error")}'
                    }
            else:
                error_text = response.text
                print(f"❌ Flow creation failed: {response.status_code} - {error_text}")
                
                # Check if it's a duplicate error
                if response.status_code == 400 and ('already exists' in error_text.lower() or 'duplicate' in error_text.lower()):
                    print("ℹ️ Flow might already exist, checking...")
                    existing = self.check_flow_exists("trainer_onboarding_flow")
                    
                    if existing.get('exists'):
                        flow_id = existing.get('flow_id')
                        print(f"✅ Using existing flow: {flow_id}")
                        return {
                            'success': True,
                            'flow_id': flow_id,
                            'message': 'Using existing flow'
                        }
                
                return {
                    'success': False,
                    'error': f'API Error: {response.status_code} - {error_text}'
                }
                
        except Exception as e:
            print(f"❌ Error creating flow: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def publish_flow_json(self, flow_id: str, flow_json: dict) -> dict:
        """Publish flow JSON to existing flow"""
        try:
            url = f"https://graph.facebook.com/v18.0/{flow_id}/assets"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "name": "flow.json",
                "asset_type": "FLOW_JSON",
                "flow_json": json.dumps(flow_json)
            }
            
            print(f"📤 Publishing flow JSON to flow {flow_id}...")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Flow JSON published successfully")
                return {'success': True}
            else:
                print(f"❌ Flow JSON publishing failed: {response.status_code} - {response.text}")
                return {'success': False, 'error': f'{response.status_code} - {response.text}'}
                
        except Exception as e:
            print(f"❌ Error publishing flow JSON: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_flow(self, flow_id: str) -> dict:
        """Delete a flow (for testing)"""
        try:
            url = f"https://graph.facebook.com/v18.0/{flow_id}"
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            print(f"🗑️ Deleting flow {flow_id}...")
            
            response = requests.delete(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Flow deleted successfully")
                return {'success': True}
            else:
                print(f"❌ Flow deletion failed: {response.status_code} - {response.text}")
                return {'success': False, 'error': f'{response.status_code} - {response.text}'}
                
        except Exception as e:
            print(f"❌ Error deleting flow: {str(e)}")
            return {'success': False, 'error': str(e)}

def main():
    """Main script execution"""
    print("🔧 WhatsApp Flow Manager")
    print("=" * 50)
    
    try:
        manager = WhatsAppFlowManager()
        
        print(f"📱 Business Account ID: {manager.business_account_id}")
        print(f"🔑 Access Token: {manager.access_token[:20]}...")
        print(f"🌐 Base URL: {manager.base_url}")
        print()
        
        # List existing flows
        print("1️⃣ Checking existing flows...")
        flows_result = manager.list_existing_flows()
        print()
        
        # Check if trainer onboarding flow exists
        print("2️⃣ Checking trainer onboarding flow...")
        flow_check = manager.check_flow_exists("trainer_onboarding_flow")
        
        if flow_check.get('exists'):
            flow_id = flow_check.get('flow_id')
            status = flow_check.get('status')
            print(f"✅ Trainer onboarding flow exists: {flow_id} (Status: {status})")
        else:
            print("❌ Trainer onboarding flow does not exist")
            
            # Create the flow
            print("\n3️⃣ Creating trainer onboarding flow...")
            create_result = manager.create_trainer_onboarding_flow()
            
            if create_result.get('success'):
                print(f"🎉 Success! Flow ID: {create_result.get('flow_id')}")
            else:
                print(f"💥 Failed: {create_result.get('error')}")
        
        print("\n" + "=" * 50)
        print("✅ Flow management complete!")
        
    except ValueError as e:
        print(f"⚙️ Configuration Error: {str(e)}")
        print("\nPlease check your .env file and ensure these variables are set:")
        print("- ACCESS_TOKEN (WhatsApp Access Token)")
        print("- WHATSAPP_BUSINESS_ACCOUNT_ID (Business Account ID)")
        return 1
    except Exception as e:
        print(f"💥 Unexpected Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)