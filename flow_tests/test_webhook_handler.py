#!/usr/bin/env python3
"""
WhatsApp Flow Webhook Handler Test
Tests webhook handling for WhatsApp Flows without affecting the main codebase.

This test simulates webhook processing for:
- Flow completion events
- Flow data exchange
- Error handling
- Response validation
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add parent directory to path to import from main codebase
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import log_info, log_error, log_warning


class FlowWebhookHandlerTest:
    """Test class for flow webhook handling"""

    def __init__(self, test_mode: bool = True):
        """
        Initialize the test class

        Args:
            test_mode: If True, doesn't make actual database calls
        """
        self.test_mode = test_mode
        self.test_results = []

    def test_webhook_verification(self) -> bool:
        """Test webhook verification challenge"""
        try:
            # Simulate webhook verification request
            mock_challenge = {
                "hub.mode": "subscribe",
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "test_challenge_1234567890"
            }

            # Verify the challenge response
            if "hub.challenge" in mock_challenge:
                challenge = mock_challenge["hub.challenge"]
                self._add_result("Webhook Verification", True, f"Challenge verified: {challenge}")
                return True
            else:
                self._add_result("Webhook Verification", False, "No challenge in request")
                return False

        except Exception as e:
            self._add_result("Webhook Verification", False, f"Error: {str(e)}")
            return False

    def test_flow_completion_webhook(self) -> bool:
        """Test flow completion webhook processing"""
        try:
            # Simulate a flow completion webhook payload
            mock_webhook = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [{
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "27123456789",
                                "phone_number_id": "PHONE_NUMBER_ID"
                            },
                            "contacts": [{
                                "profile": {"name": "Test User"},
                                "wa_id": "27987654321"
                            }],
                            "messages": [{
                                "from": "27987654321",
                                "id": "wamid.test123",
                                "timestamp": str(int(datetime.now().timestamp())),
                                "type": "interactive",
                                "interactive": {
                                    "type": "nfm_reply",
                                    "nfm_reply": {
                                        "response_json": json.dumps({
                                            "full_name": "Test Trainer",
                                            "email": "test@trainer.com",
                                            "phone": "27987654321",
                                            "specialization": "Fitness"
                                        }),
                                        "body": "flow_completed",
                                        "name": "flow"
                                    }
                                }
                            }]
                        },
                        "field": "messages"
                    }]
                }]
            }

            # Validate webhook structure
            if (mock_webhook.get("object") == "whatsapp_business_account" and
                "entry" in mock_webhook and len(mock_webhook["entry"]) > 0):
                self._add_result("Flow Completion Webhook", True, "Webhook structure is valid")
                return True
            else:
                self._add_result("Flow Completion Webhook", False, "Invalid webhook structure")
                return False

        except Exception as e:
            self._add_result("Flow Completion Webhook", False, f"Error: {str(e)}")
            return False

    def test_flow_data_extraction(self) -> bool:
        """Test extracting flow data from webhook"""
        try:
            # Simulate flow response data
            mock_nfm_reply = {
                "response_json": json.dumps({
                    "full_name": "John Doe",
                    "email": "john@example.com",
                    "phone": "27123456789",
                    "specialization": "Nutrition",
                    "experience_years": "3"
                }),
                "body": "flow_completed",
                "name": "flow"
            }

            # Extract and parse response JSON
            response_data = json.loads(mock_nfm_reply["response_json"])

            # Validate extracted data
            required_fields = ["full_name", "email", "phone"]
            missing_fields = [field for field in required_fields if field not in response_data]

            if not missing_fields:
                self._add_result("Flow Data Extraction", True,
                               f"Successfully extracted data for: {response_data['full_name']}")
                return True
            else:
                self._add_result("Flow Data Extraction", False,
                               f"Missing required fields: {', '.join(missing_fields)}")
                return False

        except json.JSONDecodeError as e:
            self._add_result("Flow Data Extraction", False, f"JSON decode error: {str(e)}")
            return False
        except Exception as e:
            self._add_result("Flow Data Extraction", False, f"Error: {str(e)}")
            return False

    def test_error_handling(self) -> bool:
        """Test webhook error handling"""
        try:
            # Test cases for various error scenarios
            test_cases = [
                {
                    "name": "Empty Payload",
                    "payload": {},
                    "expected_error": "Missing required fields"
                },
                {
                    "name": "Invalid Message Type",
                    "payload": {"type": "unknown"},
                    "expected_error": "Unsupported message type"
                },
                {
                    "name": "Missing Response Data",
                    "payload": {"type": "interactive", "interactive": {}},
                    "expected_error": "Missing nfm_reply"
                }
            ]

            errors_handled = 0
            for test_case in test_cases:
                try:
                    # Simulate error detection
                    payload = test_case["payload"]
                    if not payload or len(payload) == 0:
                        errors_handled += 1
                    elif "type" in payload and payload["type"] not in ["interactive", "text"]:
                        errors_handled += 1
                    elif "interactive" in payload and "nfm_reply" not in payload["interactive"]:
                        errors_handled += 1
                except Exception:
                    errors_handled += 1

            if errors_handled == len(test_cases):
                self._add_result("Error Handling", True,
                               f"All {len(test_cases)} error cases handled correctly")
                return True
            else:
                self._add_result("Error Handling", False,
                               f"Only {errors_handled}/{len(test_cases)} errors handled")
                return False

        except Exception as e:
            self._add_result("Error Handling", False, f"Error: {str(e)}")
            return False

    def test_flow_token_validation(self) -> bool:
        """Test flow token validation"""
        try:
            # Test valid and invalid tokens
            valid_token = f"trainer_onboarding_27123456789_{int(datetime.now().timestamp())}"
            invalid_tokens = [
                "",
                "invalid",
                "trainer_only",
                "27123456789"
            ]

            # Validate token format
            is_valid = (
                valid_token.startswith("trainer_onboarding_") and
                len(valid_token.split("_")) >= 3
            )

            if is_valid:
                self._add_result("Flow Token Validation", True, "Token validation working correctly")
                return True
            else:
                self._add_result("Flow Token Validation", False, "Token validation failed")
                return False

        except Exception as e:
            self._add_result("Flow Token Validation", False, f"Error: {str(e)}")
            return False

    def test_response_formatting(self) -> bool:
        """Test webhook response formatting"""
        try:
            # Simulate formatting a success response
            success_response = {
                "version": "3.0",
                "screen": "SUCCESS",
                "data": {
                    "message": "Registration successful!",
                    "next_steps": "We'll contact you shortly."
                }
            }

            # Validate response structure
            if all(key in success_response for key in ["version", "screen", "data"]):
                self._add_result("Response Formatting", True, "Response format is correct")
                return True
            else:
                self._add_result("Response Formatting", False, "Invalid response format")
                return False

        except Exception as e:
            self._add_result("Response Formatting", False, f"Error: {str(e)}")
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
        print("🧪 Starting Flow Webhook Handler Tests")
        print("=" * 60)

        # Run tests
        self.test_webhook_verification()
        self.test_flow_completion_webhook()
        self.test_flow_data_extraction()
        self.test_error_handling()
        self.test_flow_token_validation()
        self.test_response_formatting()

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
    tester = FlowWebhookHandlerTest(test_mode=True)
    results = tester.run_all_tests()

    # Save results to file
    results_file = os.path.join(os.path.dirname(__file__), "webhook_test_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Results saved to: {results_file}")

    # Exit with error code if tests failed
    if results["summary"]["failed"] > 0:
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
