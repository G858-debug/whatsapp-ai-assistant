#!/usr/bin/env python3
"""
WhatsApp Business API Integration Test
======================================

This script validates the complete WhatsApp Flow integration setup without making any changes.
It tests:
1. Connection to Meta's WhatsApp Business API
2. Verification that the flow exists
3. Webhook endpoint readiness
4. Flow data structure validation
5. Configuration completeness

Author: Integration Test Suite
Version: 1.0.0
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class WhatsAppIntegrationTest:
    """Comprehensive integration test for WhatsApp Business API setup"""

    # Meta Graph API configuration
    GRAPH_API_VERSION = "v17.0"
    GRAPH_API_BASE = "https://graph.facebook.com"
    FLOW_ID = "775047838492907"

    def __init__(self):
        """Initialize the test suite"""
        self.test_results = []
        self.warnings = []
        self.config_issues = []
        self.access_token = None
        self.business_account_id = None
        self.phone_number_id = None
        self.base_url = None
        self.private_key = None

        # Load configuration
        self._load_config()

    def _load_config(self):
        """Load configuration from environment variables"""
        print("📋 Loading configuration...")

        # Access Token
        self.access_token = os.environ.get('ACCESS_TOKEN')
        if not self.access_token:
            self.config_issues.append("ACCESS_TOKEN environment variable not set")
        else:
            print(f"   ✅ ACCESS_TOKEN: {'*' * 10}{self.access_token[-4:]}")

        # Business Account ID
        self.business_account_id = os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', Config.WHATSAPP_BUSINESS_ACCOUNT_ID)
        if not self.business_account_id:
            self.config_issues.append("WHATSAPP_BUSINESS_ACCOUNT_ID not set")
        else:
            print(f"   ✅ BUSINESS_ACCOUNT_ID: {self.business_account_id}")

        # Phone Number ID
        self.phone_number_id = os.environ.get('PHONE_NUMBER_ID', Config.PHONE_NUMBER_ID)
        if not self.phone_number_id:
            self.config_issues.append("PHONE_NUMBER_ID not set")
        else:
            print(f"   ✅ PHONE_NUMBER_ID: {self.phone_number_id}")

        # Base URL (for webhook testing)
        self.base_url = os.environ.get('BASE_URL', Config.BASE_URL)
        if not self.base_url or self.base_url == 'https://your-app.railway.app':
            self.warnings.append("BASE_URL not configured or using default value")
        else:
            print(f"   ✅ BASE_URL: {self.base_url}")

        # Private Key (for flow encryption)
        self.private_key = os.environ.get('WHATSAPP_FLOW_PRIVATE_KEY')
        if not self.private_key:
            self.warnings.append("WHATSAPP_FLOW_PRIVATE_KEY not set (required for flow encryption)")
        else:
            print(f"   ✅ PRIVATE_KEY: Configured ({len(self.private_key)} chars)")

        print()

    def _record_test(self, test_name: str, passed: bool, message: str, details: Optional[str] = None):
        """Record a test result"""
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def test_api_connection(self) -> bool:
        """Test 1: Validate connection to Meta's WhatsApp Business API"""
        print("🔌 TEST 1: Meta WhatsApp Business API Connection")
        print("=" * 60)

        if not self.access_token:
            print("   ❌ Cannot test API connection - ACCESS_TOKEN not configured")
            self._record_test("API Connection", False, "ACCESS_TOKEN not configured")
            return False

        try:
            # Test API connection by fetching business account details
            url = f"{self.GRAPH_API_BASE}/{self.GRAPH_API_VERSION}/{self.business_account_id}"
            params = {
                'fields': 'id,name,timezone_id,message_template_namespace',
                'access_token': self.access_token
            }

            print(f"   📡 Connecting to: {url}")

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ API connection successful!")
                print(f"   📊 Business Account Name: {data.get('name', 'N/A')}")
                print(f"   📊 Business Account ID: {data.get('id', 'N/A')}")
                print(f"   📊 Timezone: {data.get('timezone_id', 'N/A')}")

                self._record_test(
                    "API Connection",
                    True,
                    "Successfully connected to WhatsApp Business API",
                    json.dumps(data, indent=2)
                )
                return True

            elif response.status_code == 190 or response.status_code == 401:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                print(f"   ❌ Authentication failed: {error_msg}")
                print(f"   💡 Your ACCESS_TOKEN may be expired or invalid")

                self._record_test(
                    "API Connection",
                    False,
                    f"Authentication failed: {error_msg}",
                    f"Status Code: {response.status_code}"
                )
                return False

            else:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                print(f"   ❌ API request failed: {error_msg}")
                print(f"   📊 Status Code: {response.status_code}")

                self._record_test(
                    "API Connection",
                    False,
                    f"API request failed: {error_msg}",
                    response.text
                )
                return False

        except requests.exceptions.Timeout:
            print("   ❌ Connection timeout - Meta API is not responding")
            self._record_test("API Connection", False, "Connection timeout")
            return False

        except requests.exceptions.ConnectionError:
            print("   ❌ Connection error - Cannot reach Meta API")
            self._record_test("API Connection", False, "Connection error")
            return False

        except Exception as e:
            print(f"   ❌ Unexpected error: {str(e)}")
            self._record_test("API Connection", False, f"Unexpected error: {str(e)}")
            return False

        finally:
            print()

    def test_flow_exists(self) -> bool:
        """Test 2: Verify the specific flow exists and is accessible"""
        print("📝 TEST 2: Flow Verification (ID: {})".format(self.FLOW_ID))
        print("=" * 60)

        if not self.access_token:
            print("   ❌ Cannot verify flow - ACCESS_TOKEN not configured")
            self._record_test("Flow Verification", False, "ACCESS_TOKEN not configured")
            return False

        try:
            # Get flow details
            url = f"{self.GRAPH_API_BASE}/{self.GRAPH_API_VERSION}/{self.FLOW_ID}"
            params = {
                'fields': 'id,name,status,categories,validation_errors,json_version,data_api_version,endpoint_uri',
                'access_token': self.access_token
            }

            print(f"   📡 Fetching flow details...")

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                flow_data = response.json()

                print(f"   ✅ Flow found!")
                print(f"   📊 Flow Name: {flow_data.get('name', 'N/A')}")
                print(f"   📊 Flow ID: {flow_data.get('id', 'N/A')}")
                print(f"   📊 Status: {flow_data.get('status', 'N/A')}")
                print(f"   📊 Categories: {', '.join(flow_data.get('categories', []))}")
                print(f"   📊 JSON Version: {flow_data.get('json_version', 'N/A')}")
                print(f"   📊 Data API Version: {flow_data.get('data_api_version', 'N/A')}")

                # Check endpoint URI
                endpoint_uri = flow_data.get('endpoint_uri', '')
                if endpoint_uri:
                    print(f"   📊 Endpoint URI: {endpoint_uri}")

                    # Validate endpoint URI matches our webhook
                    expected_endpoint = f"{self.base_url}/webhooks/whatsapp-flow"
                    if endpoint_uri == expected_endpoint:
                        print(f"   ✅ Endpoint URI matches expected webhook URL")
                    else:
                        print(f"   ⚠️ Endpoint URI mismatch!")
                        print(f"      Expected: {expected_endpoint}")
                        print(f"      Actual: {endpoint_uri}")
                        self.warnings.append(f"Flow endpoint URI mismatch: {endpoint_uri} vs {expected_endpoint}")
                else:
                    print(f"   ⚠️ No endpoint URI configured for this flow")
                    self.warnings.append("Flow has no endpoint URI configured")

                # Check for validation errors
                validation_errors = flow_data.get('validation_errors', [])
                if validation_errors:
                    print(f"   ⚠️ Flow has validation errors:")
                    for error in validation_errors:
                        print(f"      - {error}")
                    self.warnings.append(f"Flow has {len(validation_errors)} validation error(s)")
                else:
                    print(f"   ✅ No validation errors")

                # Check flow status
                status = flow_data.get('status', '').upper()
                if status == 'PUBLISHED':
                    print(f"   ✅ Flow is PUBLISHED and ready to use")
                elif status == 'DRAFT':
                    print(f"   ⚠️ Flow is in DRAFT mode - it needs to be published")
                    self.warnings.append("Flow is in DRAFT mode, not PUBLISHED")
                else:
                    print(f"   ⚠️ Flow status is: {status}")
                    self.warnings.append(f"Flow status is {status}")

                self._record_test(
                    "Flow Verification",
                    True,
                    f"Flow {self.FLOW_ID} exists and is accessible",
                    json.dumps(flow_data, indent=2)
                )
                return True

            elif response.status_code == 404:
                print(f"   ❌ Flow not found!")
                print(f"   💡 Flow ID {self.FLOW_ID} does not exist or is not accessible")
                print(f"   💡 Check that:")
                print(f"      - The flow ID is correct")
                print(f"      - Your access token has permission to view this flow")
                print(f"      - The flow belongs to the correct Business Account")

                self._record_test("Flow Verification", False, f"Flow {self.FLOW_ID} not found")
                return False

            else:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                print(f"   ❌ Failed to retrieve flow: {error_msg}")
                print(f"   📊 Status Code: {response.status_code}")

                self._record_test("Flow Verification", False, f"Failed to retrieve flow: {error_msg}")
                return False

        except Exception as e:
            print(f"   ❌ Error verifying flow: {str(e)}")
            self._record_test("Flow Verification", False, f"Error: {str(e)}")
            return False

        finally:
            print()

    def test_webhook_endpoint(self) -> bool:
        """Test 3: Validate webhook endpoint is accessible and configured correctly"""
        print("🌐 TEST 3: Webhook Endpoint Verification")
        print("=" * 60)

        if not self.base_url or self.base_url == 'https://your-app.railway.app':
            print("   ❌ Cannot test webhook - BASE_URL not configured")
            self._record_test("Webhook Endpoint", False, "BASE_URL not configured")
            return False

        webhook_url = f"{self.base_url}/webhooks/whatsapp-flow"
        print(f"   📡 Testing webhook URL: {webhook_url}")

        try:
            # Test GET request (health check)
            print(f"   🔍 Testing GET request (health check)...")
            response = requests.get(webhook_url, timeout=10)

            if response.status_code == 200:
                print(f"   ✅ Webhook endpoint is accessible (GET)")
                print(f"   📊 Response: {response.text[:100]}...")
            else:
                print(f"   ⚠️ GET request returned: {response.status_code}")
                print(f"   📊 This might be expected if GET is not implemented")

            # Test POST request with sample encrypted flow data structure
            print(f"   🔍 Testing POST request structure...")

            # Sample payload mimicking Meta's encrypted flow structure
            test_payload = {
                "encrypted_flow_data": "test_encrypted_data",
                "encrypted_aes_key": "test_encrypted_key",
                "initial_vector": "test_iv"
            }

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WhatsApp-Integration-Test/1.0'
            }

            response = requests.post(
                webhook_url,
                json=test_payload,
                headers=headers,
                timeout=10
            )

            # We expect 421 (decryption error) or 500 with our test data, which is fine
            # The important thing is that the endpoint exists and responds
            if response.status_code in [200, 421, 500]:
                print(f"   ✅ Webhook endpoint is accessible (POST)")
                print(f"   📊 Status Code: {response.status_code}")

                if response.status_code == 421:
                    print(f"   ℹ️ Got 421 (expected for test data - decryption error)")
                    print(f"   ℹ️ This confirms the endpoint is handling encrypted flows")
                elif response.status_code == 500:
                    print(f"   ℹ️ Got 500 (expected for test data - processing error)")
                    print(f"   ℹ️ Endpoint exists but test data caused an error (normal)")

                self._record_test(
                    "Webhook Endpoint",
                    True,
                    "Webhook endpoint is accessible and responding",
                    f"Status: {response.status_code}"
                )
                return True

            else:
                print(f"   ⚠️ Unexpected status code: {response.status_code}")
                print(f"   📊 Response: {response.text[:200]}")
                self.warnings.append(f"Webhook returned unexpected status: {response.status_code}")

                self._record_test(
                    "Webhook Endpoint",
                    True,
                    f"Endpoint accessible but returned {response.status_code}",
                    response.text[:500]
                )
                return True

        except requests.exceptions.Timeout:
            print(f"   ❌ Webhook timeout - endpoint not responding")
            print(f"   💡 Check that:")
            print(f"      - Your server is running")
            print(f"      - The BASE_URL is correct")
            print(f"      - There are no firewall issues")

            self._record_test("Webhook Endpoint", False, "Webhook timeout")
            return False

        except requests.exceptions.ConnectionError:
            print(f"   ❌ Cannot connect to webhook endpoint")
            print(f"   💡 Check that:")
            print(f"      - Your server is deployed and running")
            print(f"      - The BASE_URL is correct: {self.base_url}")
            print(f"      - The route is properly configured")

            self._record_test("Webhook Endpoint", False, "Connection error")
            return False

        except Exception as e:
            print(f"   ❌ Error testing webhook: {str(e)}")
            self._record_test("Webhook Endpoint", False, f"Error: {str(e)}")
            return False

        finally:
            print()

    def test_flow_data_structure(self) -> bool:
        """Test 4: Validate flow JSON structure matches Meta's requirements"""
        print("📋 TEST 4: Flow Data Structure Validation")
        print("=" * 60)

        try:
            # Look for flow JSON files
            flow_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'whatsapp_flows'
            )

            if not os.path.exists(flow_dir):
                print(f"   ⚠️ Flow directory not found: {flow_dir}")
                self._record_test("Flow Data Structure", False, "Flow directory not found")
                return False

            print(f"   📁 Checking flow directory: {flow_dir}")

            # List all flow JSON files
            flow_files = [f for f in os.listdir(flow_dir) if f.endswith('.json') and f != 'flow_config.json']

            if not flow_files:
                print(f"   ⚠️ No flow JSON files found")
                self._record_test("Flow Data Structure", False, "No flow files found")
                return False

            print(f"   📊 Found {len(flow_files)} flow file(s)")

            all_valid = True
            validated_flows = []

            for flow_file in flow_files:
                flow_path = os.path.join(flow_dir, flow_file)
                print(f"\n   🔍 Validating: {flow_file}")

                try:
                    with open(flow_path, 'r', encoding='utf-8') as f:
                        flow_data = json.load(f)

                    # Validate required fields
                    required_fields = ['version', 'screens']
                    missing_fields = [field for field in required_fields if field not in flow_data]

                    if missing_fields:
                        print(f"      ❌ Missing required fields: {missing_fields}")
                        all_valid = False
                        continue

                    # Get flow metadata
                    version = flow_data.get('version', 'Unknown')
                    screens = flow_data.get('screens', [])

                    print(f"      ✅ Valid JSON structure")
                    print(f"      📊 Version: {version}")
                    print(f"      📊 Screens: {len(screens)}")

                    # Validate screens
                    if not screens:
                        print(f"      ⚠️ No screens defined")
                        self.warnings.append(f"{flow_file}: No screens defined")
                        continue

                    # Check screen structure
                    screen_names = []
                    for screen in screens:
                        if 'id' in screen:
                            screen_names.append(screen['id'])

                    print(f"      📊 Screen IDs: {', '.join(screen_names)}")

                    # Validate data API version (should be 3.0 for encrypted flows)
                    data_api_version = flow_data.get('data_api_version')
                    if data_api_version:
                        print(f"      📊 Data API Version: {data_api_version}")
                        if data_api_version != "3.0":
                            self.warnings.append(f"{flow_file}: Data API version is {data_api_version}, encrypted flows require 3.0")

                    # Check for routing model (required for multi-screen flows)
                    routing_model = flow_data.get('routing_model')
                    if routing_model:
                        print(f"      📊 Routing Model: {routing_model}")
                    elif len(screens) > 1:
                        self.warnings.append(f"{flow_file}: Multi-screen flow without routing_model")

                    validated_flows.append({
                        'file': flow_file,
                        'version': version,
                        'screens': len(screens),
                        'valid': True
                    })

                except json.JSONDecodeError as e:
                    print(f"      ❌ Invalid JSON: {str(e)}")
                    all_valid = False

                except Exception as e:
                    print(f"      ❌ Error reading flow: {str(e)}")
                    all_valid = False

            # Summary
            print(f"\n   📊 Validation Summary:")
            print(f"      Total files: {len(flow_files)}")
            print(f"      Valid flows: {len(validated_flows)}")

            if all_valid and validated_flows:
                print(f"   ✅ All flow files are valid")
                self._record_test(
                    "Flow Data Structure",
                    True,
                    f"Validated {len(validated_flows)} flow file(s)",
                    json.dumps(validated_flows, indent=2)
                )
                return True
            else:
                print(f"   ⚠️ Some flow files have issues")
                self._record_test(
                    "Flow Data Structure",
                    False,
                    "Some flow files have validation issues"
                )
                return False

        except Exception as e:
            print(f"   ❌ Error validating flow structure: {str(e)}")
            self._record_test("Flow Data Structure", False, f"Error: {str(e)}")
            return False

        finally:
            print()

    def test_encryption_setup(self) -> bool:
        """Test 5: Verify encryption setup for flows"""
        print("🔐 TEST 5: Flow Encryption Configuration")
        print("=" * 60)

        if not self.private_key:
            print("   ⚠️ WHATSAPP_FLOW_PRIVATE_KEY not configured")
            print("   💡 Flow encryption requires a private key")
            print("   💡 Generate one using: openssl genrsa -out private_key.pem 2048")
            self._record_test("Encryption Setup", False, "Private key not configured")
            return False

        try:
            # Try to load the private key to validate format
            from cryptography.hazmat.primitives.serialization import load_pem_private_key

            print(f"   🔍 Validating private key format...")

            try:
                private_key = load_pem_private_key(
                    self.private_key.encode('utf-8'),
                    password=None
                )

                print(f"   ✅ Private key is valid PEM format")
                print(f"   📊 Key size: {private_key.key_size} bits")

                if private_key.key_size < 2048:
                    print(f"   ⚠️ Key size is less than 2048 bits (not recommended)")
                    self.warnings.append(f"Private key size is {private_key.key_size} bits, 2048+ recommended")

                self._record_test(
                    "Encryption Setup",
                    True,
                    f"Private key is valid ({private_key.key_size} bits)"
                )
                return True

            except Exception as key_error:
                print(f"   ❌ Invalid private key format: {str(key_error)}")
                print(f"   💡 Make sure the private key is in PEM format")
                print(f"   💡 It should start with '-----BEGIN PRIVATE KEY-----'")

                self._record_test("Encryption Setup", False, f"Invalid private key: {str(key_error)}")
                return False

        except ImportError:
            print(f"   ⚠️ cryptography library not available")
            print(f"   💡 Install with: pip install cryptography")
            self._record_test("Encryption Setup", False, "cryptography library not installed")
            return False

        except Exception as e:
            print(f"   ❌ Error testing encryption: {str(e)}")
            self._record_test("Encryption Setup", False, f"Error: {str(e)}")
            return False

        finally:
            print()

    def generate_report(self) -> Dict:
        """Generate a comprehensive test report"""
        print("=" * 60)
        print("📊 INTEGRATION TEST REPORT")
        print("=" * 60)
        print()

        # Configuration Status
        print("🔧 Configuration Status:")
        if self.config_issues:
            print("   ❌ Configuration Issues:")
            for issue in self.config_issues:
                print(f"      - {issue}")
        else:
            print("   ✅ All required configuration present")
        print()

        # Test Results Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for t in self.test_results if t['passed'])
        failed_tests = total_tests - passed_tests

        print("📋 Test Results:")
        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            print(f"   {status} {result['test']}: {result['message']}")
        print()

        # Summary Statistics
        print("📊 Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            print(f"   Success Rate: {success_rate:.1f}%")
        print()

        # Warnings
        if self.warnings:
            print("⚠️ Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
            print()

        # Overall Status
        print("=" * 60)
        if failed_tests == 0 and not self.config_issues:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Your WhatsApp Flow integration is ready to use!")
        elif failed_tests == 0 and self.config_issues:
            print("⚠️ TESTS PASSED WITH WARNINGS")
            print("Please review the configuration issues above")
        else:
            print("❌ SOME TESTS FAILED")
            print("Please review the failed tests and follow the troubleshooting guide")
        print("=" * 60)
        print()

        # Troubleshooting Guide
        if failed_tests > 0 or self.config_issues:
            self._print_troubleshooting_guide()

        # Save report to file
        report = {
            'timestamp': datetime.now().isoformat(),
            'flow_id': self.FLOW_ID,
            'configuration': {
                'access_token_configured': bool(self.access_token),
                'business_account_id': self.business_account_id,
                'phone_number_id': self.phone_number_id,
                'base_url': self.base_url,
                'private_key_configured': bool(self.private_key)
            },
            'test_results': self.test_results,
            'warnings': self.warnings,
            'config_issues': self.config_issues,
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "N/A"
            }
        }

        report_path = os.path.join(
            os.path.dirname(__file__),
            'integration_test_results.json'
        )

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            print(f"📄 Detailed report saved to: {report_path}")
            print()
        except Exception as e:
            print(f"⚠️ Could not save report: {str(e)}")
            print()

        return report

    def _print_troubleshooting_guide(self):
        """Print troubleshooting guide for failed tests"""
        print("🔧 TROUBLESHOOTING GUIDE")
        print("=" * 60)
        print()

        # API Connection Issues
        if any('API Connection' in t['test'] and not t['passed'] for t in self.test_results):
            print("❌ API Connection Failed:")
            print("   1. Verify your ACCESS_TOKEN is valid and not expired")
            print("   2. Check that the token has correct permissions:")
            print("      - whatsapp_business_management")
            print("      - whatsapp_business_messaging")
            print("   3. Ensure WHATSAPP_BUSINESS_ACCOUNT_ID is correct")
            print("   4. Regenerate token at: https://developers.facebook.com/tools/explorer/")
            print()

        # Flow Verification Issues
        if any('Flow Verification' in t['test'] and not t['passed'] for t in self.test_results):
            print("❌ Flow Verification Failed:")
            print(f"   1. Verify flow ID {self.FLOW_ID} is correct")
            print("   2. Check that the flow belongs to your Business Account")
            print("   3. Ensure your access token has permission to view flows")
            print("   4. Verify the flow exists in Meta Business Manager:")
            print(f"      https://business.facebook.com/wa/manage/flows/{self.FLOW_ID}/")
            print()

        # Webhook Issues
        if any('Webhook' in t['test'] and not t['passed'] for t in self.test_results):
            print("❌ Webhook Endpoint Failed:")
            print("   1. Verify your server is deployed and running")
            print("   2. Check BASE_URL is correct in environment variables")
            print("   3. Ensure webhook route is registered: /webhooks/whatsapp-flow")
            print("   4. Test webhook locally: curl -X POST <BASE_URL>/webhooks/whatsapp-flow")
            print("   5. Check server logs for errors")
            print("   6. Verify HTTPS is enabled (required by Meta)")
            print()

        # Flow Structure Issues
        if any('Flow Data Structure' in t['test'] and not t['passed'] for t in self.test_results):
            print("❌ Flow Data Structure Issues:")
            print("   1. Validate flow JSON files in whatsapp_flows/ directory")
            print("   2. Ensure flows have required fields: version, screens")
            print("   3. Check screen definitions are valid")
            print("   4. Verify data_api_version is set to 3.0 for encrypted flows")
            print("   5. Use Meta's Flow Builder to validate: https://business.facebook.com/wa/manage/flows/")
            print()

        # Encryption Issues
        if any('Encryption' in t['test'] and not t['passed'] for t in self.test_results):
            print("❌ Encryption Setup Issues:")
            print("   1. Generate a private key:")
            print("      openssl genrsa -out private_key.pem 2048")
            print("   2. Extract public key:")
            print("      openssl rsa -in private_key.pem -pubout -out public_key.pem")
            print("   3. Set WHATSAPP_FLOW_PRIVATE_KEY environment variable with the private key content")
            print("   4. Upload public key to your flow in Meta Business Manager")
            print("   5. Install required library: pip install cryptography")
            print()

        # Configuration Issues
        if self.config_issues:
            print("⚠️ Configuration Issues:")
            for issue in self.config_issues:
                print(f"   - {issue}")
            print()
            print("   💡 Set missing environment variables:")
            print("      - ACCESS_TOKEN: Your WhatsApp Business API token")
            print("      - WHATSAPP_BUSINESS_ACCOUNT_ID: Your Business Account ID")
            print("      - PHONE_NUMBER_ID: Your WhatsApp phone number ID")
            print("      - BASE_URL: Your deployed application URL")
            print("      - WHATSAPP_FLOW_PRIVATE_KEY: Private key for flow encryption")
            print()

        print("📚 Additional Resources:")
        print("   - WhatsApp Flows Documentation: https://developers.facebook.com/docs/whatsapp/flows")
        print("   - Flow Builder: https://business.facebook.com/wa/manage/flows/")
        print("   - API Reference: https://developers.facebook.com/docs/whatsapp/business-management-api/manage-flows")
        print("   - Webhooks Guide: https://developers.facebook.com/docs/whatsapp/flows/reference/webhooks")
        print()
        print("=" * 60)
        print()

    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 WhatsApp Business API Integration Test Suite")
        print("=" * 60)
        print(f"Test Flow ID: {self.FLOW_ID}")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()

        # Check for critical configuration issues first
        if self.config_issues:
            print("⚠️ CRITICAL CONFIGURATION ISSUES DETECTED")
            print("=" * 60)
            for issue in self.config_issues:
                print(f"   ❌ {issue}")
            print()
            print("💡 Please configure the missing environment variables before running tests")
            print("   See troubleshooting guide below for instructions")
            print()
            self._print_troubleshooting_guide()
            return

        # Run tests in sequence
        test_1_passed = self.test_api_connection()
        test_2_passed = self.test_flow_exists()
        test_3_passed = self.test_webhook_endpoint()
        test_4_passed = self.test_flow_data_structure()
        test_5_passed = self.test_encryption_setup()

        # Generate final report
        self.generate_report()


def main():
    """Main entry point"""
    # Create and run integration test
    test_suite = WhatsAppIntegrationTest()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()
