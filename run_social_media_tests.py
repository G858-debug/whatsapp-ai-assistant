#!/usr/bin/env python3
"""
Social Media System Test Runner

Simple script to run the social media system tests with proper environment setup.

Usage:
    python run_social_media_tests.py

This script will:
1. Check for required environment variables
2. Run all social media system tests
3. Display results in a clear format
"""

import os
import sys
import subprocess
from pathlib import Path

def check_environment():
    """Check if required environment variables are set"""
    required_vars = {
        'SUPABASE_URL': 'Supabase database URL',
        'SUPABASE_ANON_KEY': 'Supabase anonymous key',
        'ANTHROPIC_API_KEY': 'Anthropic Claude API key',
        'REPLICATE_API_TOKEN': 'Replicate API token for image generation'
    }
    
    optional_vars = {
        'FACEBOOK_PAGE_ACCESS_TOKEN': 'Facebook page access token (optional for full testing)',
        'FACEBOOK_PAGE_ID': 'Facebook page ID (optional for full testing)'
    }
    
    print("🔍 Checking environment variables...")
    print()
    
    missing_required = []
    missing_optional = []
    
    for var, description in required_vars.items():
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Missing - {description}")
            missing_required.append(var)
    
    for var, description in optional_vars.items():
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"⚠️  {var}: Missing - {description}")
            missing_optional.append(var)
    
    print()
    
    if missing_required:
        print("❌ Missing required environment variables!")
        print("Please set the following variables before running tests:")
        for var in missing_required:
            print(f"   export {var}=your_value_here")
        print()
        return False
    
    if missing_optional:
        print("⚠️  Some optional variables are missing.")
        print("Tests for Facebook integration will be skipped.")
        print()
    
    return True

def run_tests():
    """Run the social media system tests"""
    print("🚀 Running Social Media System Tests...")
    print("=" * 50)
    
    try:
        # Change to the project root directory
        project_root = Path(__file__).parent
        os.chdir(project_root)
        
        # Run the test script
        result = subprocess.run([
            'python3', 
            'social_media/test_system.py'
        ], capture_output=True, text=True)
        
        # Print the output
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Return the exit code
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running tests: {str(e)}")
        return False

def main():
    """Main function"""
    print("🧪 Social Media System Test Runner")
    print("=" * 40)
    print()
    
    # Check environment
    if not check_environment():
        print("Please set up your environment variables and try again.")
        sys.exit(1)
    
    # Run tests
    success = run_tests()
    
    print()
    if success:
        print("🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()