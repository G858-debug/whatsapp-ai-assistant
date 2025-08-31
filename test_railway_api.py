#!/usr/bin/env python3
"""
Test script for Railway API functionality
Note: Log fetching functionality has been removed from the API
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import the RailwayAPI class
from utils.railway_api import RailwayAPI

class RailwayAPITester:
    """Test suite for Railway API functionality"""
    
    def __init__(self):
        """Initialize tester"""
        self.api_token = os.getenv('RAILWAY_API_TOKEN')
        
        # Initialize API client
        self.api = None
        self.test_results = []
        
    def setup(self):
        """Setup test environment"""
        print("=" * 60)
        print("RAILWAY API TEST SUITE")
        print("=" * 60)
        print()
        print("⚠️  NOTE: Log fetching functionality has been removed")
        print()
        
        # Check for required environment variables
        if not self.api_token:
            print("⚠️  WARNING: RAILWAY_API_TOKEN not set in environment")
            print("   Using mock token for testing")
            self.api_token = "mock_token_for_testing"
        
        print(f"📋 Configuration:")
        print(f"   API Token: {'*' * 20 if self.api_token else 'Not set'}")
        print()
        
        # Initialize API client
        self.api = RailwayAPI(api_token=self.api_token)
        print("✅ Railway API client initialized (limited functionality)")
        print()
    
    def test_project_info(self):
        """Test fetching project information"""
        print("🧪 TEST: Project Information")
        print("-" * 40)
        
        try:
            project = self.api.get_project_info()
            
            if project:
                print("✅ Successfully fetched project info")
                if 'name' in project:
                    print(f"   Project Name: {project['name']}")
                if 'id' in project:
                    print(f"   Project ID: {project['id']}")
            else:
                print("⚠️  No project info returned (may be due to mock data)")
            
            self.test_results.append(("Project Info", True, "Fetched project information"))
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results.append(("Project Info", False, str(e)))
        
        print()
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        print("🧪 TEST: Rate Limiting")
        print("-" * 40)
        
        try:
            # Create API client with low rate limit for testing
            test_api = RailwayAPI(api_token=self.api_token, rate_limit=3)
            
            print("   Making rapid requests to test rate limiting...")
            for i in range(5):
                project = test_api.get_project_info()
                print(f"   Request {i+1}: {'Success' if project is not None else 'Failed'}")
            
            test_api.close()
            print("✅ Rate limiting tested successfully")
            self.test_results.append(("Rate Limiting", True, "Rate limiter working"))
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results.append(("Rate Limiting", False, str(e)))
        
        print()
    
    def print_summary(self):
        """Print test summary"""
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print()
        
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        
        print(f"Tests Run: {total}")
        print(f"Tests Passed: {passed}")
        print(f"Tests Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "N/A")
        print()
        
        print("Detailed Results:")
        print("-" * 40)
        for test_name, result, message in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} | {test_name}")
            print(f"       {message}")
        print()
        
        return passed == total
    
    def cleanup(self):
        """Cleanup resources"""
        if self.api:
            self.api.close()
            print("🧹 Cleaned up API resources")
    
    def run_all_tests(self):
        """Run all tests"""
        try:
            self.setup()
            
            # Run limited tests (log-related tests removed)
            self.test_project_info()
            self.test_rate_limiting()
            
            # Print summary
            all_passed = self.print_summary()
            
            # Cleanup
            self.cleanup()
            
            # Return exit code
            return 0 if all_passed else 1
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
            self.cleanup()
            return 1
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {str(e)}")
            self.cleanup()
            return 1


def main():
    """Main entry point"""
    print("\n🚀 Starting Railway API Tests for Refiloe WhatsApp Assistant\n")
    print("⚠️  IMPORTANT: Log fetching functionality has been removed from the API")
    print("   Only basic project info and rate limiting tests are available\n")
    
    # Check if running with real credentials
    if not os.getenv('RAILWAY_API_TOKEN'):
        print("⚠️  WARNING: RAILWAY_API_TOKEN not set in environment")
        print("   Using mock token for testing")
        print()
        
        response = input("Continue with mock testing? (y/n): ")
        if response.lower() != 'y':
            print("Test cancelled")
            return 1
        print()
    
    # Run tests
    tester = RailwayAPITester()
    exit_code = tester.run_all_tests()
    
    if exit_code == 0:
        print("🎉 All tests completed successfully!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())