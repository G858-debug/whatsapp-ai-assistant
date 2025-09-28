#!/usr/bin/env python3
"""
Deployment Verification Script
Tests basic imports and configuration to ensure deployment will work
"""

import sys
import os

def test_basic_imports():
    """Test that all basic imports work"""
    print("Testing basic imports...")
    
    try:
        import flask
        print("✅ Flask imported successfully")
    except ImportError as e:
        print(f"❌ Flask import failed: {e}")
        return False
    
    try:
        import supabase
        print("✅ Supabase imported successfully")
    except ImportError as e:
        print(f"❌ Supabase import failed: {e}")
        return False
    
    try:
        import anthropic
        print("✅ Anthropic imported successfully")
    except ImportError as e:
        print(f"❌ Anthropic import failed: {e}")
        return False
    
    try:
        import pandas
        print("✅ Pandas imported successfully")
    except ImportError as e:
        print(f"❌ Pandas import failed: {e}")
        return False
    
    return True

def test_config_loading():
    """Test that configuration loads without errors"""
    print("\nTesting configuration loading...")
    
    try:
        from config import Config
        print("✅ Config imported successfully")
        
        # Test that we can access config values
        print(f"  - Timezone: {Config.TIMEZONE}")
        print(f"  - AI Model: {Config.AI_MODEL}")
        print(f"  - Secret Key set: {'Yes' if Config.SECRET_KEY else 'No'}")
        print(f"  - Supabase URL set: {'Yes' if Config.SUPABASE_URL else 'No'}")
        
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def test_app_imports():
    """Test that app modules can be imported"""
    print("\nTesting app module imports...")
    
    try:
        from app_core import setup_app_core
        print("✅ app_core imported successfully")
    except Exception as e:
        print(f"❌ app_core import failed: {e}")
        return False
    
    try:
        from app_routes import setup_routes
        print("✅ app_routes imported successfully")
    except Exception as e:
        print(f"❌ app_routes import failed: {e}")
        return False
    
    return True

def test_services_imports():
    """Test that service modules can be imported"""
    print("\nTesting service imports...")
    
    try:
        from services.whatsapp import WhatsAppService
        print("✅ WhatsApp service imported successfully")
    except Exception as e:
        print(f"❌ WhatsApp service import failed: {e}")
        return False
    
    try:
        from services.ai_intent_handler import AIIntentHandler
        print("✅ AI intent handler imported successfully")
    except Exception as e:
        print(f"❌ AI intent handler import failed: {e}")
        return False
    
    return True

def main():
    """Run all deployment checks"""
    print("🚀 Starting deployment verification...")
    print("=" * 50)
    
    all_passed = True
    
    # Run all tests
    tests = [
        test_basic_imports,
        test_config_loading,
        test_app_imports,
        test_services_imports
    ]
    
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All deployment checks passed! Ready for deployment.")
        return 0
    else:
        print("❌ Some deployment checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
