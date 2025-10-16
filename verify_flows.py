#!/usr/bin/env python3
"""
Verify WhatsApp Flow JSON files are properly formatted
"""

import json
import os
from pathlib import Path

def verify_flow_files():
    """Verify all flow JSON files are valid"""
    flows_dir = Path("whatsapp_flows")
    
    if not flows_dir.exists():
        print("❌ whatsapp_flows directory not found")
        return False
    
    flow_files = [f for f in flows_dir.glob("*.json") if not f.name.startswith('flow_config')]
    
    if not flow_files:
        print("❌ No JSON files found in whatsapp_flows directory")
        return False
    
    print(f"🔍 Checking {len(flow_files)} flow files...\n")
    
    all_valid = True
    
    for flow_file in flow_files:
        try:
            with open(flow_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Basic validation
            if 'screens' in data or 'version' in data:
                print(f"✅ {flow_file.name} - Valid JSON structure")
            else:
                print(f"⚠️  {flow_file.name} - Missing required fields (screens/version)")
                all_valid = False
                
        except json.JSONDecodeError as e:
            print(f"❌ {flow_file.name} - Invalid JSON: {str(e)}")
            all_valid = False
        except Exception as e:
            print(f"❌ {flow_file.name} - Error: {str(e)}")
            all_valid = False
    
    print(f"\n{'✅ All flows are valid!' if all_valid else '❌ Some flows have issues'}")
    return all_valid

def check_endpoint_health():
    """Check if the webhook endpoint is healthy"""
    try:
        import requests
        
        url = "https://web-production-26de5.up.railway.app/webhooks/whatsapp-flow"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print("✅ Webhook endpoint health check passed")
                return True
        
        print(f"❌ Webhook endpoint health check failed: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"❌ Could not check endpoint health: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 WhatsApp Flows Verification\n")
    
    # Check flow files
    flows_valid = verify_flow_files()
    
    print("\n" + "="*50 + "\n")
    
    # Check endpoint health
    endpoint_healthy = check_endpoint_health()
    
    print("\n" + "="*50 + "\n")
    
    if flows_valid and endpoint_healthy:
        print("🎉 Everything looks good! You're ready to add flows to Facebook Business Manager.")
    else:
        print("⚠️  Please fix the issues above before proceeding.")