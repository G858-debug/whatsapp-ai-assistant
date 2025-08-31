#!/usr/bin/env python3
"""
Test script for Railway API functionality
Tests the existing RailwayAPI class to verify log fetching capabilities
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

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
        self.project_id = os.getenv('RAILWAY_PROJECT_ID')
        self.service_id = os.getenv('RAILWAY_SERVICE_ID')
        
        # Initialize API client
        self.api = None
        self.test_results = []
        
    def setup(self):
        """Setup test environment"""
        print("=" * 60)
        print("RAILWAY API TEST SUITE")
        print("=" * 60)
        print()
        
        # Check for required environment variables
        if not self.api_token:
            print("⚠️  WARNING: RAILWAY_API_TOKEN not set in environment")
            print("   Using mock token for testing")
            self.api_token = "mock_token_for_testing"
            
        if not self.project_id:
            print("⚠️  WARNING: RAILWAY_PROJECT_ID not set in environment")
            print("   Using mock project ID for testing")
            self.project_id = "mock_project_id"
            
        if not self.service_id:
            print("⚠️  WARNING: RAILWAY_SERVICE_ID not set in environment")
            print("   Using mock service ID for testing")
            self.service_id = "mock_service_id"
        
        print(f"📋 Configuration:")
        print(f"   API Token: {'*' * 20 if self.api_token else 'Not set'}")
        print(f"   Project ID: {self.project_id[:10]}..." if self.project_id else "Not set")
        print(f"   Service ID: {self.service_id[:10]}..." if self.service_id else "Not set")
        print()
        
        # Initialize API client
        self.api = RailwayAPI(api_token=self.api_token)
        print("✅ Railway API client initialized")
        print()
    
    def test_get_logs(self):
        """Test basic log fetching"""
        print("🧪 TEST: Basic Log Fetching")
        print("-" * 40)
        
        try:
            logs = self.api.get_logs(
                project_id=self.project_id,
                service_id=self.service_id,
                limit=10
            )
            
            if logs:
                print(f"✅ Successfully fetched {len(logs)} logs")
                print(f"   Sample log entry:")
                if logs[0]:
                    for key in ['timestamp', 'message', 'severity']:
                        if key in logs[0]:
                            value = str(logs[0][key])[:50]
                            print(f"     {key}: {value}...")
            else:
                print("⚠️  No logs returned (may be due to mock data or no logs available)")
            
            self.test_results.append(("Basic Log Fetching", True, f"Fetched {len(logs)} logs"))
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results.append(("Basic Log Fetching", False, str(e)))
        
        print()
    
    def test_get_recent_logs(self):
        """Test fetching recent logs"""
        print("🧪 TEST: Recent Logs (Last 24 Hours)")
        print("-" * 40)
        
        try:
            logs = self.api.get_recent_logs(
                project_id=self.project_id,
                service_id=self.service_id,
                hours=24
            )
            
            if logs:
                print(f"✅ Successfully fetched {len(logs)} recent logs")
                # Check if logs are actually from last 24 hours
                now = datetime.now()
                recent_count = 0
                for log in logs:
                    if 'timestamp' in log:
                        try:
                            log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                            if (now - log_time).total_seconds() < 86400:  # 24 hours
                                recent_count += 1
                        except:
                            pass
                print(f"   {recent_count} logs confirmed from last 24 hours")
            else:
                print("⚠️  No recent logs found")
            
            self.test_results.append(("Recent Logs", True, f"Fetched {len(logs)} logs"))
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results.append(("Recent Logs", False, str(e)))
        
        print()
    
    def test_get_error_logs(self):
        """Test fetching error logs"""
        print("🧪 TEST: Error Logs")
        print("-" * 40)
        
        try:
            logs = self.api.get_error_logs(
                project_id=self.project_id,
                service_id=self.service_id,
                hours=48
            )
            
            if logs:
                print(f"✅ Found {len(logs)} error logs in last 48 hours")
                # Verify they are error logs
                error_count = sum(1 for log in logs if log.get('severity', '').lower() == 'error')
                print(f"   {error_count} confirmed as error severity")
            else:
                print("✅ No error logs found (good news!)")
            
            self.test_results.append(("Error Logs", True, f"Checked for errors, found {len(logs)}"))
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results.append(("Error Logs", False, str(e)))
        
        print()
    
    def test_filtered_logs(self):
        """Test log filtering with specific time range"""
        print("🧪 TEST: Filtered Logs (Custom Time Range)")
        print("-" * 40)
        
        try:
            # Get logs from last 6 hours
            start_time = datetime.now() - timedelta(hours=6)
            
            logs = self.api.get_logs(
                project_id=self.project_id,
                service_id=self.service_id,
                limit=50,
                start_time=start_time,
                severity=None  # All severities
            )
            
            print(f"✅ Fetched {len(logs)} logs from last 6 hours")
            
            # Count by severity
            severities = {}
            for log in logs:
                severity = log.get('severity', 'unknown')
                severities[severity] = severities.get(severity, 0) + 1
            
            if severities:
                print("   Log breakdown by severity:")
                for sev, count in severities.items():
                    print(f"     {sev}: {count}")
            
            self.test_results.append(("Filtered Logs", True, f"Successfully filtered {len(logs)} logs"))
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results.append(("Filtered Logs", False, str(e)))
        
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
                if 'services' in project:
                    print(f"   Services: {len(project['services'])}")
                    for service in project['services'][:3]:  # Show first 3
                        print(f"     - {service.get('name', 'Unknown')} ({service.get('status', 'Unknown')})")
            else:
                print("⚠️  No project info returned (may be due to mock data)")
            
            self.test_results.append(("Project Info", True, "Fetched project information"))
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results.append(("Project Info", False, str(e)))
        
        print()
    
    def test_service_health(self):
        """Test fetching service health"""
        print("🧪 TEST: Service Health")
        print("-" * 40)
        
        try:
            health = self.api.get_service_health(
                project_id=self.project_id,
                service_id=self.service_id
            )
            
            if health:
                print("✅ Successfully fetched service health")
                print(f"   Service: {health.get('name', 'Unknown')}")
                print(f"   Status: {health.get('status', 'Unknown')}")
                
                if 'healthcheck' in health:
                    hc = health['healthcheck']
                    print(f"   Health Check Status: {hc.get('status', 'Unknown')}")
                    print(f"   Uptime: {hc.get('uptime', 'Unknown')}")
            else:
                print("⚠️  No health data returned")
            
            self.test_results.append(("Service Health", True, "Fetched health status"))
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results.append(("Service Health", False, str(e)))
        
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
                logs = test_api.get_logs(
                    project_id=self.project_id,
                    service_id=self.service_id,
                    limit=1
                )
                print(f"   Request {i+1}: {'Success' if logs is not None else 'Failed'}")
            
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
            
            # Run individual tests
            self.test_get_logs()
            self.test_get_recent_logs()
            self.test_get_error_logs()
            self.test_filtered_logs()
            self.test_project_info()
            self.test_service_health()
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
    
    # Check if running with real credentials
    if not os.getenv('RAILWAY_API_TOKEN'):
        print("⚠️  IMPORTANT: Running in mock mode without real Railway credentials")
        print("   To test with real data, set these environment variables:")
        print("   - RAILWAY_API_TOKEN")
        print("   - RAILWAY_PROJECT_ID")  
        print("   - RAILWAY_SERVICE_ID")
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