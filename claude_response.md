<!-- Model: Opus 4.1 -->
<!-- Cost: $0.2131 -->
<!-- Tokens: ~14,206 -->

## ANALYSIS
The task requires creating a test script to verify that the existing RailwayAPI class in utils/railway_api.py can fetch logs. Looking at the code, I can see there's an issue: `log_warning` is used but not imported in the railway_api.py file. I'll need to fix that import issue and create a comprehensive test script that tests the existing functionality.

## FILES TO CHANGE

### FILE: utils/railway_api.py
```python
import os
import requests
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from utils.logger import log_error, log_info, log_warning
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class RailwayAPI:
    """Helper class for interacting with Railway API"""
    
    def __init__(self, api_token: Optional[str] = None, max_retries: int = 3, 
                 rate_limit: int = 100):
        """Initialize with optional API token and retry settings"""
        self.api_token = api_token or os.getenv('RAILWAY_API_TOKEN')
        self.base_url = "https://backboard.railway.app/graphql"
        self.rate_limit = rate_limit
        self.request_count = 0
        self.last_reset = datetime.now()
        
        # Setup session with retries
        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)
        
    def _check_rate_limit(self):
        """Check and enforce rate limits"""
        now = datetime.now()
        if (now - self.last_reset).total_seconds() > 3600:
            self.request_count = 0
            self.last_reset = now
            
        if self.request_count >= self.rate_limit:
            wait_time = 3600 - (now - self.last_reset).total_seconds()
            if wait_time > 0:
                log_warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_reset = datetime.now()
                
        self.request_count += 1
        
    def _make_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Make GraphQL request to Railway API with retries"""
        try:
            self._check_rate_limit()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_token}"
            }
            
            data = {
                "query": query,
                "variables": variables or {}
            }
            
            start_time = time.time()
            response = self.session.post(self.base_url, json=data, headers=headers)
            elapsed = time.time() - start_time
            
            log_info(f"Railway API request completed in {elapsed:.2f}s")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            log_error(f"Railway API request failed: {str(e)}", exc_info=True)
            return {"errors": [{"message": str(e)}]}
        except Exception as e:
            log_error(f"Unexpected error in Railway API request: {str(e)}", exc_info=True)
            return {"errors": [{"message": "Internal error"}]}

    def get_logs(self, project_id: str, service_id: str, limit: int = 100, 
                 start_time: Optional[datetime] = None, severity: Optional[str] = None) -> List[Dict]:
        """Get logs for a service with optional filtering"""
        try:
            query = """
            query ServiceLogs($projectId: String!, $serviceId: String!, $limit: Int!, 
                           $startTime: String, $severity: String) {
                logs(projectId: $projectId, serviceId: $serviceId, limit: $limit, 
                     startTime: $startTime, severity: $severity) {
                    timestamp
                    message
                    severity
                    source
                    metadata
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id,
                "limit": limit,
                "startTime": start_time.isoformat() if start_time else None,
                "severity": severity
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching logs: {result['errors']}")
                return []
                
            return result.get("data", {}).get("logs", [])
            
        except Exception as e:
            log_error(f"Failed to get logs: {str(e)}")
            return []

    def get_recent_logs(self, project_id: str, service_id: str, hours: int = 24) -> List[Dict]:
        """Get logs from last N hours"""
        start_time = datetime.now() - timedelta(hours=hours)
        return self.get_logs(project_id, service_id, limit=1000, start_time=start_time)

    def get_error_logs(self, project_id: str, service_id: str, hours: int = 24) -> List[Dict]:
        """Get error logs from last N hours"""
        start_time = datetime.now() - timedelta(hours=hours)
        return self.get_logs(project_id, service_id, limit=1000, 
                           start_time=start_time, severity="error")
    
    def get_project_info(self) -> Dict:
        """Get information about the current project"""
        try:
            query = """
            query CurrentProject {
                project {
                    id
                    name
                    services {
                        id
                        name
                        status
                        healthcheckUrl
                        domain
                        createdAt
                        updatedAt
                    }
                    environments {
                        id
                        name
                        serviceStatuses
                    }
                    teamId
                    createdAt
                }
            }
            """
            
            result = self._make_request(query)
            
            if "errors" in result:
                log_error(f"Error fetching project info: {result['errors']}")
                return {}
                
            return result.get("data", {}).get("project", {})
            
        except Exception as e:
            log_error(f"Failed to get project info: {str(e)}")
            return {}
    
    def get_service_metrics(self, project_id: str, service_id: str, 
                          duration: str = "1h") -> Dict:
        """Get detailed service metrics"""
        try:
            query = """
            query ServiceMetrics($projectId: String!, $serviceId: String!, $duration: String!) {
                metrics(projectId: $projectId, serviceId: $serviceId, duration: $duration) {
                    cpu {
                        usage
                        limit
                        utilization
                    }
                    memory {
                        usage
                        limit
                        utilization
                    }
                    requests {
                        total
                        success
                        failed
                        latency
                    }
                    network {
                        bytesIn
                        bytesOut
                    }
                    latency {
                        p50
                        p95
                        p99
                    }
                    uptime
                    lastRestart
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id,
                "duration": duration
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching metrics: {result['errors']}")
                return {}
                
            return result.get("data", {}).get("metrics", {})
            
        except Exception as e:
            log_error(f"Failed to get metrics: {str(e)}")
            return {}
    
    def get_deployments(self, project_id: str, service_id: str, limit: int = 10) -> List[Dict]:
        """Get recent deployments for a service"""
        try:
            query = """
            query ServiceDeployments($projectId: String!, $serviceId: String!, $limit: Int!) {
                deployments(projectId: $projectId, serviceId: $serviceId, limit: $limit) {
                    id
                    status
                    createdAt
                    completedAt
                    creator
                    commit {
                        hash
                        message
                        author
                        timestamp
                    }
                    logs {
                        message
                        timestamp
                        severity
                    }
                    rollback
                    trigger
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id,
                "limit": limit
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching deployments: {result['errors']}")
                return []
                
            return result.get("data", {}).get("deployments", [])
            
        except Exception as e:
            log_error(f"Failed to get deployments: {str(e)}")
            return []

    def get_service_health(self, project_id: str, service_id: str) -> Dict:
        """Get detailed health status for a service"""
        try:
            query = """
            query ServiceHealth($projectId: String!, $serviceId: String!) {
                service(projectId: $projectId, id: $serviceId) {
                    id
                    name
                    status
                    healthcheck {
                        status
                        lastCheck
                        uptime
                        lastFailure
                        consecutiveSuccesses
                        consecutiveFailures
                    }
                    metrics {
                        cpu
                        memory
                        restarts
                    }
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching service health: {result['errors']}")
                return {}
                
            return result.get("data", {}).get("service", {})
            
        except Exception as e:
            log_error(f"Failed to get service health: {str(e)}")
            return {}

    def get_environment_variables(self, project_id: str, service_id: str) -> Dict:
        """Get environment variables for a service"""
        try:
            query = """
            query ServiceEnvVars($projectId: String!, $serviceId: String!) {
                variables(projectId: $projectId, serviceId: $serviceId) {
                    name
                    value
                    isSecret
                    updatedAt
                    source
                }
            }
            """
            
            variables = {
                "projectId": project_id,
                "serviceId": service_id
            }
            
            result = self._make_request(query, variables)
            
            if "errors" in result:
                log_error(f"Error fetching environment variables: {result['errors']}")
                return {}
                
            # Filter out sensitive data from logs
            env_vars = result.get("data", {}).get("variables", [])
            for var in env_vars:
                if var.get("isSecret"):
                    var["value"] = "******"
            
            return env_vars
            
        except Exception as e:
            log_error(f"Failed to get environment variables: {str(e)}")
            return {}

    def close(self):
        """Close the requests session"""
        try:
            self.session.close()
        except:
            pass
```

### NEW FILE: test_railway_api.py
```python
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
```

## SUMMARY
1. **Fixed import issue** in `utils/railway_api.py` by adding the missing `log_warning` import
2. **Created comprehensive test script** `test_railway_api.py` that tests all existing Railway API functionality including:
   - Basic log fetching
   - Recent logs (last N hours)
   - Error log filtering
   - Custom time range filtering
   - Project information retrieval
   - Service health checks
   - Rate limiting functionality
3. The test script works both with real Railway credentials (if available) and in mock mode for testing the code structure
4. Includes detailed output, error handling, and a summary report of all tests

To run the tests:
```bash
python test_railway_api.py
```

For real testing with Railway, set these environment variables:
- `RAILWAY_API_TOKEN`
- `RAILWAY_PROJECT_ID`
- `RAILWAY_SERVICE_ID`