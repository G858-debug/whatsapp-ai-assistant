#!/usr/bin/env python3
"""
Trainer Onboarding Flow Test
Tests the trainer onboarding flow without affecting the main codebase.

This test simulates the trainer onboarding process including:
- Flow message creation
- Flow token generation
- Flow data validation
- Response handling
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Optional, Any

# Add parent directory to path to import from main codebase
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import log_info, log_error, log_warning


class TrainerOnboardingFlowTest:
    """Test class for trainer onboarding flow"""

    def __init__(self, test_mode: bool = True):
        """
        Initialize the test class

        Args:
            test_mode: If True, doesn't make actual API calls
        """
        self.test_mode = test_mode
        self.flow_data = None
        self.test_results = []

    def load_flow_data(self) -> bool:
        """Load the trainer onboarding flow JSON"""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            flow_path = os.path.join(project_root, 'whatsapp_flows', 'trainer_onboarding_flow.json')

            if not os.path.exists(flow_path):
                self._add_result("Flow File Check", False, f"Flow file not found at {flow_path}")
                return False

            with open(flow_path, 'r', encoding='utf-8') as f:
                self.flow_data = json.load(f)

            self._add_result("Flow File Check", True, "Flow file loaded successfully")
            return True

        except json.JSONDecodeError as e:
            self._add_result("Flow File Check", False, f"Invalid JSON: {str(e)}")
            return False
        except Exception as e:
            self._add_result("Flow File Check", False, f"Error loading flow: {str(e)}")
            return False

    def validate_flow_structure(self) -> bool:
        """Validate the flow JSON structure"""
        if not self.flow_data:
            self._add_result("Flow Structure", False, "No flow data loaded")
            return False

        required_keys = ['version', 'screens']
        missing_keys = [key for key in required_keys if key not in self.flow_data]

        if missing_keys:
            self._add_result("Flow Structure", False, f"Missing keys: {', '.join(missing_keys)}")
            return False

        self._add_result("Flow Structure", True, "Flow structure is valid")
        return True

    def test_flow_token_generation(self) -> bool:
        """Test flow token generation"""
        try:
            test_phone = "27123456789"
            timestamp = int(datetime.now().timestamp())
            token = f"trainer_onboarding_{test_phone}_{timestamp}"

            if len(token) > 0 and "trainer_onboarding_" in token:
                self._add_result("Token Generation", True, f"Generated token: {token}")
                return True
            else:
                self._add_result("Token Generation", False, "Invalid token format")
                return False

        except Exception as e:
            self._add_result("Token Generation", False, f"Error: {str(e)}")
            return False

    def test_flow_message_structure(self) -> bool:
        """Test the flow message structure"""
        try:
            test_phone = "27123456789"
            flow_token = f"test_token_{int(datetime.now().timestamp())}"

            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": test_phone,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "Complete Your Profile"
                    },
                    "body": {
                        "text": "Please provide your trainer details to get started."
                    },
                    "footer": {
                        "text": "This will only take a minute"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": "FLOW_ID_PLACEHOLDER",
                            "flow_cta": "Start",
                            "flow_action": "navigate",
                            "mode": "draft"
                        }
                    }
                }
            }

            # Validate message structure
            if all(key in message for key in ["to", "type", "interactive"]):
                self._add_result("Message Structure", True, "Flow message structure is valid")
                return True
            else:
                self._add_result("Message Structure", False, "Invalid message structure")
                return False

        except Exception as e:
            self._add_result("Message Structure", False, f"Error: {str(e)}")
            return False

    def simulate_flow_response(self) -> bool:
        """Simulate a flow response from WhatsApp"""
        try:
            # Simulate a trainer onboarding response
            mock_response = {
                "full_name": "Test Trainer",
                "email": "test@example.com",
                "phone": "27123456789",
                "specialization": "Fitness",
                "experience_years": "5",
                "bio": "Experienced fitness trainer"
            }

            # Validate required fields
            required_fields = ["full_name", "email", "phone"]
            missing_fields = [field for field in required_fields if field not in mock_response]

            if missing_fields:
                self._add_result("Flow Response", False, f"Missing fields: {', '.join(missing_fields)}")
                return False

            self._add_result("Flow Response", True, "Flow response validation successful")
            return True

        except Exception as e:
            self._add_result("Flow Response", False, f"Error: {str(e)}")
            return False

    def _add_result(self, test_name: str, passed: bool, message: str):
        """Add a test result to the results list"""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)

        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {message}")

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results"""
        print("🧪 Starting Trainer Onboarding Flow Tests")
        print("=" * 60)

        # Run tests
        self.load_flow_data()
        self.validate_flow_structure()
        self.test_flow_token_generation()
        self.test_flow_message_structure()
        self.simulate_flow_response()

        # Calculate summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests

        print("\n" + "=" * 60)
        print(f"📊 Test Summary:")
        print(f"   Total: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")

        return {
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests/total_tests if total_tests > 0 else 0
            },
            "results": self.test_results
        }


def main():
    """Main test function"""
    tester = TrainerOnboardingFlowTest(test_mode=True)
    results = tester.run_all_tests()

    # Exit with error code if tests failed
    if results["summary"]["failed"] > 0:
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
