#!/usr/bin/env python3
"""
Basic test to verify the social media test system can be imported and run
without requiring all external dependencies.
"""

import os
import sys

def test_imports():
    """Test basic imports"""
    print("🔍 Testing basic imports...")
    
    try:
        # Test basic Python modules
        import yaml
        import json
        import time
        import uuid
        from datetime import datetime, timedelta
        print("✅ Basic Python modules imported successfully")
        
        # Test if we can find the social media directory
        social_media_path = os.path.join(os.path.dirname(__file__), 'social_media')
        if os.path.exists(social_media_path):
            print("✅ Social media directory found")
        else:
            print("❌ Social media directory not found")
            return False
        
        # Test if config file exists
        config_path = os.path.join(social_media_path, 'config.yaml')
        if os.path.exists(config_path):
            print("✅ Config file found")
        else:
            print("❌ Config file not found")
            return False
        
        # Test config loading
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        if config and 'ai_influencer_settings' in config:
            print("✅ Config file loads successfully")
            print(f"   AI Name: {config.get('ai_influencer_settings', {}).get('name', 'Unknown')}")
        else:
            print("❌ Config file structure invalid")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {str(e)}")
        return False

def test_environment():
    """Test environment variables"""
    print("\n🔍 Testing environment variables...")
    
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY', 
        'ANTHROPIC_API_KEY',
        'REPLICATE_API_TOKEN'
    ]
    
    optional_vars = [
        'FACEBOOK_PAGE_ACCESS_TOKEN',
        'FACEBOOK_PAGE_ID'
    ]
    
    all_good = True
    
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Missing (REQUIRED)")
            all_good = False
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"⚠️  {var}: Missing (optional)")
    
    return all_good

def main():
    """Main test function"""
    print("🧪 Basic Social Media Test System Check")
    print("=" * 40)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test environment
    env_ok = test_environment()
    
    print("\n" + "=" * 40)
    
    if imports_ok and env_ok:
        print("🎉 Basic tests passed! System is ready for full testing.")
        print("\nTo run full tests:")
        print("  python3 social_media/test_system.py")
        print("  or")
        print("  python3 run_social_media_tests.py")
    else:
        print("❌ Basic tests failed. Please fix issues before running full tests.")
        
        if not imports_ok:
            print("\nFix import issues:")
            print("  pip install -r requirements.txt")
        
        if not env_ok:
            print("\nSet required environment variables:")
            print("  export SUPABASE_URL=your_url")
            print("  export SUPABASE_ANON_KEY=your_key")
            print("  export ANTHROPIC_API_KEY=your_key")
            print("  export REPLICATE_API_TOKEN=your_token")

if __name__ == "__main__":
    main()