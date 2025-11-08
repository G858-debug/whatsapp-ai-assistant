#!/usr/bin/env python3
"""
Trainer Onboarding Flow Test Script

This script provides comprehensive testing for the trainer onboarding flow including:
- Flow message creation with proper WhatsApp structure
- Local flow simulation without sending to WhatsApp
- Data validation for South African context
- Complete logging of all test actions
- Standalone runnable test functions

Flow Details:
- Flow Name: trainer_onboarding_flow
- Flow ID: 775047838492907
- Context: South African (ZA phone numbers, Rand currency)
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List

# Add parent directory to path to import from main codebase
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import from main codebase, fallback to print if not available
try:
    from utils.logger import log_info, log_error, log_warning
except ImportError:
    # Fallback logger functions if main codebase logger is not available
    def log_info(msg):
        print(f"[INFO] {msg}")

    def log_error(msg):
        print(f"[ERROR] {msg}")

    def log_warning(msg):
        print(f"[WARNING] {msg}")

# Constants
FLOW_ID = "775047838492907"
FLOW_NAME = "trainer_onboarding_flow"
TEST_LOG_FILE = "flow_tests/logs/trainer_onboarding_test.log"
TEST_RESULTS_FILE = "flow_tests/logs/trainer_onboarding_results.json"

# Ensure log directory exists
os.makedirs(os.path.dirname(TEST_LOG_FILE), exist_ok=True)

# Configure file logging
file_handler = logging.FileHandler(TEST_LOG_FILE)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Get logger
test_logger = logging.getLogger('trainer_onboarding_test')
test_logger.setLevel(logging.INFO)
test_logger.addHandler(file_handler)


def log_test_action(action: str, details: str = "", level: str = "INFO"):
    """
    Log test action to both console and file

    Args:
        action: The action being performed
        details: Additional details about the action
        level: Log level (INFO, WARNING, ERROR)
    """
    message = f"{action}"
    if details:
        message += f": {details}"

    if level == "INFO":
        test_logger.info(message)
        log_info(message)
    elif level == "WARNING":
        test_logger.warning(message)
        log_warning(message)
    elif level == "ERROR":
        test_logger.error(message)
        log_error(message)


def create_test_flow_message(phone_number: str, flow_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a WhatsApp Flow message for trainer onboarding

    Args:
        phone_number: South African phone number (format: 27XXXXXXXXX)
        flow_token: Optional flow token (auto-generated if not provided)

    Returns:
        Dictionary containing the complete WhatsApp Flow message structure
    """
    log_test_action("Creating flow message", f"Phone: {phone_number}")

    # Format phone number (ensure ZA format)
    if not phone_number.startswith('27'):
        if phone_number.startswith('0'):
            phone_number = '27' + phone_number[1:]
        else:
            phone_number = '27' + phone_number

    # Generate flow token if not provided
    if not flow_token:
        timestamp = int(datetime.now().timestamp())
        flow_token = f"trainer_onboarding_{phone_number}_{timestamp}"

    log_test_action("Generated flow token", flow_token)

    # Create message with proper WhatsApp Flow structure
    message = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "header": {
                "type": "text",
                "text": "🚀 Trainer Onboarding"
            },
            "body": {
                "text": "Welcome to Refiloe! Let's get you set up as a trainer. This will take about 2 minutes."
            },
            "footer": {
                "text": "Complete your profile setup"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    "flow_token": flow_token,
                    "flow_id": FLOW_ID,
                    "flow_name": FLOW_NAME,
                    "flow_cta": "Start Setup",
                    "flow_action": "navigate",
                    "flow_action_payload": {
                        "screen": "welcome",
                        "data": {}
                    }
                }
            }
        }
    }

    log_test_action("Flow message created successfully", f"Flow ID: {FLOW_ID}")

    return message


def validate_trainer_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate trainer onboarding data with South African context

    Args:
        data: Dictionary containing trainer information

    Returns:
        Dictionary with validation results
    """
    log_test_action("Validating trainer data", f"Data keys: {list(data.keys())}")

    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "validated_data": {}
    }

    # Required fields
    required_fields = {
        "full_name": str,
        "email": str,
        "phone": str,
    }

    # Optional fields
    optional_fields = {
        "specialization": str,
        "experience_years": (str, int),
        "bio": str,
        "certifications": str,
        "rate_per_session": (str, int, float),
        "currency": str,
        "location": str,
        "availability": str
    }

    # Check required fields
    for field, expected_type in required_fields.items():
        if field not in data:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Missing required field: {field}")
            log_test_action("Validation error", f"Missing required field: {field}", "ERROR")
        elif not isinstance(data[field], expected_type):
            validation_result["valid"] = False
            validation_result["errors"].append(
                f"Invalid type for {field}: expected {expected_type.__name__}, got {type(data[field]).__name__}"
            )
            log_test_action("Validation error", f"Invalid type for {field}", "ERROR")
        else:
            validation_result["validated_data"][field] = data[field]

    # Validate phone number (South African format)
    if "phone" in data:
        phone = str(data["phone"])
        if not phone.startswith("27"):
            validation_result["warnings"].append(
                f"Phone number should start with 27 for South Africa, got: {phone}"
            )
            log_test_action("Validation warning", f"Phone format: {phone}", "WARNING")
        elif len(phone) != 11:
            validation_result["warnings"].append(
                f"Phone number should be 11 digits (27XXXXXXXXX), got {len(phone)} digits"
            )
            log_test_action("Validation warning", f"Phone length: {len(phone)}", "WARNING")

    # Validate email format
    if "email" in data:
        email = data["email"]
        if "@" not in email or "." not in email:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Invalid email format: {email}")
            log_test_action("Validation error", f"Invalid email: {email}", "ERROR")

    # Check optional fields
    for field, expected_type in optional_fields.items():
        if field in data:
            if isinstance(expected_type, tuple):
                if not isinstance(data[field], expected_type):
                    validation_result["warnings"].append(
                        f"Unexpected type for {field}: expected one of {expected_type}, got {type(data[field]).__name__}"
                    )
                    log_test_action("Validation warning", f"Type mismatch for {field}", "WARNING")
            elif not isinstance(data[field], expected_type):
                validation_result["warnings"].append(
                    f"Unexpected type for {field}: expected {expected_type.__name__}, got {type(data[field]).__name__}"
                )
                log_test_action("Validation warning", f"Type mismatch for {field}", "WARNING")

            validation_result["validated_data"][field] = data[field]

    # Validate currency (should be ZAR for South Africa)
    if "currency" in data:
        if data["currency"].upper() != "ZAR":
            validation_result["warnings"].append(
                f"Currency should be ZAR for South Africa, got: {data['currency']}"
            )
            log_test_action("Validation warning", f"Currency: {data['currency']}", "WARNING")

    # Validate rate format
    if "rate_per_session" in data:
        try:
            rate = float(data["rate_per_session"])
            if rate < 0:
                validation_result["errors"].append("Rate per session cannot be negative")
                validation_result["valid"] = False
                log_test_action("Validation error", "Negative rate", "ERROR")
            elif rate > 0 and rate < 50:
                validation_result["warnings"].append(
                    f"Rate per session (R{rate}) seems unusually low for South Africa"
                )
                log_test_action("Validation warning", f"Low rate: R{rate}", "WARNING")
        except (ValueError, TypeError):
            validation_result["errors"].append(
                f"Rate per session must be numeric, got: {data['rate_per_session']}"
            )
            validation_result["valid"] = False
            log_test_action("Validation error", f"Invalid rate format", "ERROR")

    log_test_action(
        "Validation completed",
        f"Valid: {validation_result['valid']}, Errors: {len(validation_result['errors'])}, Warnings: {len(validation_result['warnings'])}"
    )

    return validation_result


def simulate_flow_response(test_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Simulate a flow response from WhatsApp with trainer onboarding data

    Args:
        test_data: Optional test data to simulate. If None, uses default South African test data

    Returns:
        Dictionary with simulation results including the validated data
    """
    log_test_action("Simulating flow response")

    # Use provided test data or create default South African test data
    if test_data is None:
        test_data = {
            "full_name": "Thabo Mbeki",
            "email": "thabo.mbeki@refiloe.co.za",
            "phone": "27821234567",
            "specialization": "Strength & Conditioning",
            "experience_years": "8",
            "bio": "Certified personal trainer specializing in strength training and athletic conditioning. Based in Johannesburg.",
            "certifications": "NASM-CPT, ISSA Strength Coach",
            "rate_per_session": "350",
            "currency": "ZAR",
            "location": "Johannesburg, Gauteng",
            "availability": "Mon-Fri: 6am-8pm, Sat: 8am-2pm"
        }
        log_test_action("Using default test data", "South African trainer profile")
    else:
        log_test_action("Using provided test data", f"Keys: {list(test_data.keys())}")

    # Simulate webhook payload structure
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "27600000000",
                        "phone_number_id": "PHONE_NUMBER_ID"
                    },
                    "contacts": [{
                        "profile": {
                            "name": test_data.get("full_name", "Test User")
                        },
                        "wa_id": test_data.get("phone", "27821234567")
                    }],
                    "messages": [{
                        "from": test_data.get("phone", "27821234567"),
                        "id": f"wamid.test_{int(datetime.now().timestamp())}",
                        "timestamp": str(int(datetime.now().timestamp())),
                        "type": "interactive",
                        "interactive": {
                            "type": "nfm_reply",
                            "nfm_reply": {
                                "name": FLOW_NAME,
                                "body": json.dumps(test_data),
                                "response_json": json.dumps(test_data)
                            }
                        }
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    log_test_action("Created webhook payload", "WhatsApp Business API format")

    # Validate the data
    validation_result = validate_trainer_data(test_data)

    # Create response
    response = {
        "success": validation_result["valid"],
        "data": test_data,
        "validation": validation_result,
        "webhook_payload": webhook_payload,
        "timestamp": datetime.now().isoformat()
    }

    if validation_result["valid"]:
        log_test_action("Flow response simulation successful", "All validations passed")
    else:
        log_test_action(
            "Flow response simulation completed with errors",
            f"Errors: {len(validation_result['errors'])}",
            "WARNING"
        )

    return response


def test_flow_locally(phone_number: str = "27821234567", custom_data: Optional[Dict] = None):
    """
    Test the complete flow locally without sending to WhatsApp

    Args:
        phone_number: Test phone number (South African format)
        custom_data: Optional custom trainer data to test with
    """
    print("\n" + "="*80)
    print("🧪 LOCAL TRAINER ONBOARDING FLOW TEST")
    print("="*80)

    log_test_action("Starting local flow test", f"Phone: {phone_number}")

    test_results = {
        "test_name": "Trainer Onboarding Flow - Local Test",
        "timestamp": datetime.now().isoformat(),
        "phone_number": phone_number,
        "flow_id": FLOW_ID,
        "flow_name": FLOW_NAME,
        "steps": []
    }

    # Step 1: Create flow message
    print("\n📝 Step 1: Creating Flow Message")
    print("-" * 80)
    try:
        flow_message = create_test_flow_message(phone_number)
        print(f"✅ Flow message created successfully")
        print(f"   To: {flow_message['to']}")
        print(f"   Flow ID: {flow_message['interactive']['action']['parameters']['flow_id']}")
        print(f"   Flow Token: {flow_message['interactive']['action']['parameters']['flow_token']}")

        test_results["steps"].append({
            "step": "create_flow_message",
            "status": "success",
            "message": flow_message
        })
    except Exception as e:
        print(f"❌ Failed to create flow message: {str(e)}")
        log_test_action("Flow message creation failed", str(e), "ERROR")
        test_results["steps"].append({
            "step": "create_flow_message",
            "status": "failed",
            "error": str(e)
        })
        return test_results

    # Step 2: Simulate flow response
    print("\n📥 Step 2: Simulating Flow Response")
    print("-" * 80)
    try:
        response = simulate_flow_response(custom_data)
        print(f"✅ Flow response simulated successfully")
        print(f"   Valid: {response['success']}")
        print(f"   Trainer: {response['data'].get('full_name', 'N/A')}")
        print(f"   Email: {response['data'].get('email', 'N/A')}")
        print(f"   Phone: {response['data'].get('phone', 'N/A')}")
        print(f"   Specialization: {response['data'].get('specialization', 'N/A')}")
        print(f"   Rate: R{response['data'].get('rate_per_session', 'N/A')} {response['data'].get('currency', 'ZAR')}")

        test_results["steps"].append({
            "step": "simulate_flow_response",
            "status": "success",
            "response": response
        })
    except Exception as e:
        print(f"❌ Failed to simulate flow response: {str(e)}")
        log_test_action("Flow response simulation failed", str(e), "ERROR")
        test_results["steps"].append({
            "step": "simulate_flow_response",
            "status": "failed",
            "error": str(e)
        })
        return test_results

    # Step 3: Display validation results
    print("\n✓ Step 3: Validation Results")
    print("-" * 80)
    validation = response["validation"]

    if validation["errors"]:
        print(f"❌ Errors ({len(validation['errors'])}):")
        for error in validation["errors"]:
            print(f"   • {error}")
    else:
        print("✅ No errors found")

    if validation["warnings"]:
        print(f"\n⚠️  Warnings ({len(validation['warnings'])}):")
        for warning in validation["warnings"]:
            print(f"   • {warning}")
    else:
        print("✅ No warnings")

    # Step 4: Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)

    all_success = all(step["status"] == "success" for step in test_results["steps"])
    test_results["overall_status"] = "success" if all_success else "failed"
    test_results["validation_passed"] = response["success"]

    if all_success and response["success"]:
        print("🎉 All tests passed! Flow is working correctly.")
        log_test_action("Local flow test completed", "All tests passed")
    elif all_success:
        print("⚠️  Tests completed but validation has issues.")
        log_test_action("Local flow test completed", "Validation issues found", "WARNING")
    else:
        print("❌ Some tests failed. Check the logs for details.")
        log_test_action("Local flow test completed", "Some tests failed", "ERROR")

    print(f"\n📝 Logs saved to: {TEST_LOG_FILE}")
    print(f"📄 Results saved to: {TEST_RESULTS_FILE}")

    # Save results to file
    with open(TEST_RESULTS_FILE, 'w') as f:
        json.dump(test_results, f, indent=2)

    log_test_action("Test results saved", TEST_RESULTS_FILE)

    return test_results


class TrainerOnboardingFlowTest:
    """Test class for trainer onboarding flow with comprehensive testing capabilities"""

    def __init__(self, test_mode: bool = True):
        """
        Initialize the test class

        Args:
            test_mode: If True, doesn't make actual API calls (default: True)
        """
        self.test_mode = test_mode
        self.flow_data = None
        self.test_results = []
        log_test_action("Initialized TrainerOnboardingFlowTest", f"Test mode: {test_mode}")

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

    def test_message_creation(self) -> bool:
        """Test flow message creation"""
        try:
            test_phone = "27821234567"
            message = create_test_flow_message(test_phone)

            # Validate message structure
            required_keys = ["messaging_product", "to", "type", "interactive"]
            if all(key in message for key in required_keys):
                self._add_result("Message Creation", True, f"Message created for {test_phone}")
                return True
            else:
                self._add_result("Message Creation", False, "Invalid message structure")
                return False

        except Exception as e:
            self._add_result("Message Creation", False, f"Error: {str(e)}")
            return False

    def test_data_validation(self) -> bool:
        """Test trainer data validation"""
        try:
            # Test with valid South African data
            valid_data = {
                "full_name": "Sipho Ndlovu",
                "email": "sipho@example.co.za",
                "phone": "27823456789",
                "specialization": "Yoga & Pilates",
                "rate_per_session": "250",
                "currency": "ZAR"
            }

            result = validate_trainer_data(valid_data)

            if result["valid"]:
                self._add_result("Data Validation", True, "Validation successful")
                return True
            else:
                self._add_result("Data Validation", False, f"Validation failed: {result['errors']}")
                return False

        except Exception as e:
            self._add_result("Data Validation", False, f"Error: {str(e)}")
            return False

    def test_flow_simulation(self) -> bool:
        """Test flow response simulation"""
        try:
            response = simulate_flow_response()

            if response["success"]:
                self._add_result("Flow Simulation", True, "Simulation successful")
                return True
            else:
                self._add_result("Flow Simulation", False, "Simulation failed validation")
                return False

        except Exception as e:
            self._add_result("Flow Simulation", False, f"Error: {str(e)}")
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
        log_test_action(f"Test: {test_name}", f"{'Passed' if passed else 'Failed'} - {message}")

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results"""
        print("\n🧪 Starting Trainer Onboarding Flow Tests")
        print("=" * 80)
        log_test_action("Starting test suite", "Trainer Onboarding Flow")

        # Run tests
        self.load_flow_data()
        self.validate_flow_structure()
        self.test_message_creation()
        self.test_data_validation()
        self.test_flow_simulation()

        # Calculate summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests

        print("\n" + "=" * 80)
        print(f"📊 Test Summary:")
        print(f"   Total: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")

        summary = {
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests/total_tests if total_tests > 0 else 0
            },
            "results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }

        log_test_action(
            "Test suite completed",
            f"Passed: {passed_tests}/{total_tests}"
        )

        return summary


def main():
    """Main test function"""
    print("\n🚀 Trainer Onboarding Flow Test Suite")
    print("Flow ID: " + FLOW_ID)
    print("Flow Name: " + FLOW_NAME)
    log_test_action("Test suite started", f"Flow: {FLOW_NAME}")

    # Run comprehensive local test
    print("\n" + "="*80)
    print("Running Local Flow Test...")
    print("="*80)
    test_flow_locally()

    # Run unit tests
    print("\n" + "="*80)
    print("Running Unit Tests...")
    print("="*80)
    tester = TrainerOnboardingFlowTest(test_mode=True)
    results = tester.run_all_tests()

    # Final summary
    print("\n" + "="*80)
    print("📋 FINAL SUMMARY")
    print("="*80)

    if results["summary"]["failed"] > 0:
        print("❌ Some tests failed. Please check the logs.")
        print(f"📝 Log file: {TEST_LOG_FILE}")
        print(f"📄 Results file: {TEST_RESULTS_FILE}")
        log_test_action("Test suite finished", "Some tests failed", "ERROR")
        sys.exit(1)
    else:
        print("🎉 All tests passed!")
        print(f"📝 Log file: {TEST_LOG_FILE}")
        print(f"📄 Results file: {TEST_RESULTS_FILE}")
        log_test_action("Test suite finished", "All tests passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
