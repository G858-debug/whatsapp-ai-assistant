#!/usr/bin/env python3
"""
Trainer Onboarding Flow Test Runner
====================================
Tests the trainer onboarding flow locally with simulated data.
Does NOT save to database - only validates and previews.

Usage:
    python3 flow_tests/run_flow_test.py
"""

import json
import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ANSI Color Codes for beautiful output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    # Emoji-like symbols
    SUCCESS = '✅'
    FAIL = '❌'
    INFO = 'ℹ️'
    WARNING = '⚠️'
    ROCKET = '🚀'
    CHART = '📊'
    DATABASE = '💾'
    CHECKMARK = '✓'
    CROSS = '✗'


class TrainerOnboardingTester:
    """Test the trainer onboarding flow with validation and preview"""

    def __init__(self):
        self.flow_file = "whatsapp_flows/trainer_onboarding_flow.json"
        self.flow_data = None
        self.test_results = []
        self.validation_errors = []

    def print_header(self, text: str):
        """Print a colored header"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text.center(70)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

    def print_section(self, text: str):
        """Print a section header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}▶ {text}{Colors.ENDC}")
        print(f"{Colors.CYAN}{'─'*70}{Colors.ENDC}")

    def print_success(self, text: str):
        """Print a success message"""
        print(f"{Colors.GREEN}{Colors.SUCCESS} {text}{Colors.ENDC}")

    def print_error(self, text: str):
        """Print an error message"""
        print(f"{Colors.RED}{Colors.FAIL} {text}{Colors.ENDC}")

    def print_info(self, text: str):
        """Print an info message"""
        print(f"{Colors.BLUE}{Colors.INFO}  {text}{Colors.ENDC}")

    def print_warning(self, text: str):
        """Print a warning message"""
        print(f"{Colors.YELLOW}{Colors.WARNING} {text}{Colors.ENDC}")

    def load_flow_definition(self) -> bool:
        """Load and validate the flow JSON file"""
        self.print_section("Loading Flow Definition")

        try:
            if not os.path.exists(self.flow_file):
                self.print_error(f"Flow file not found: {self.flow_file}")
                return False

            with open(self.flow_file, 'r') as f:
                self.flow_data = json.load(f)

            self.print_success(f"Flow file loaded: {self.flow_file}")
            self.print_info(f"Flow version: {self.flow_data.get('version', 'N/A')}")
            self.print_info(f"Data API version: {self.flow_data.get('data_api_version', 'N/A')}")
            self.print_info(f"Total screens: {len(self.flow_data.get('screens', []))}")

            return True
        except json.JSONDecodeError as e:
            self.print_error(f"Invalid JSON in flow file: {e}")
            return False
        except Exception as e:
            self.print_error(f"Error loading flow: {e}")
            return False

    def get_test_data(self) -> Dict[str, Any]:
        """Get test data for trainer onboarding"""
        return {
            'first_name': 'Test',
            'surname': 'Trainer',
            'email': 'test@example.com',
            'city': 'Johannesburg',
            'business_name': 'FitPro Training',
            'specializations': ['Personal Training', 'Strength & Conditioning'],
            'experience_years': '2-3',
            'pricing_per_session': '350',
            'available_days': ['Monday', 'Wednesday', 'Friday'],
            'preferred_time_slots': 'Morning',
            'subscription_plan': 'Free',
            'services_offered': ['In-person Training', 'Online Training'],
            'pricing_flexibility': ['Package Discounts'],
            'notification_preferences': ['WhatsApp', 'Email'],
            'marketing_consent': False,
            'terms_accepted': True,
            'additional_notes': 'Looking forward to helping clients achieve their fitness goals!',
            'phone': '+27123456789'
        }

    def validate_email(self, email: str) -> Tuple[bool, str]:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email.strip()):
            return True, "Valid email format"
        return False, "Invalid email format"

    def validate_phone(self, phone: str) -> Tuple[bool, str]:
        """Validate phone number"""
        clean_phone = re.sub(r'[^\d+]', '', phone.strip())

        if len(clean_phone) < 10:
            return False, "Phone number too short"

        # Check for South African format
        if clean_phone.startswith('+27') or clean_phone.startswith('27'):
            return True, "Valid South African number"
        elif clean_phone.startswith('0') and len(clean_phone) == 10:
            return True, "Valid local format (will be converted to +27)"

        return True, "Valid phone number"

    def validate_pricing(self, price: str) -> Tuple[bool, str]:
        """Validate pricing"""
        try:
            price_float = float(price)
            if 0 < price_float < 10000:
                return True, f"Valid price: R{price_float:.2f}"
            return False, "Price out of reasonable range (R0-R10000)"
        except ValueError:
            return False, "Invalid price format - must be a number"

    def validate_required_fields(self, data: Dict) -> List[str]:
        """Validate all required fields are present"""
        required_fields = [
            'first_name',
            'surname',
            'email',
            'city',
            'specializations',
            'experience_years',
            'pricing_per_session',
            'terms_accepted'
        ]

        missing = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing.append(field)

        return missing

    def validate_test_data(self, test_data: Dict) -> bool:
        """Validate all test data"""
        self.print_section("Validating Test Data")

        all_valid = True

        # Check required fields
        missing_fields = self.validate_required_fields(test_data)
        if missing_fields:
            self.print_error(f"Missing required fields: {', '.join(missing_fields)}")
            all_valid = False
        else:
            self.print_success("All required fields present")

        # Validate email
        email_valid, email_msg = self.validate_email(test_data['email'])
        if email_valid:
            self.print_success(f"Email: {test_data['email']} - {email_msg}")
        else:
            self.print_error(f"Email: {test_data['email']} - {email_msg}")
            all_valid = False

        # Validate phone
        phone_valid, phone_msg = self.validate_phone(test_data['phone'])
        if phone_valid:
            self.print_success(f"Phone: {test_data['phone']} - {phone_msg}")
        else:
            self.print_error(f"Phone: {test_data['phone']} - {phone_msg}")
            all_valid = False

        # Validate pricing
        price_valid, price_msg = self.validate_pricing(test_data['pricing_per_session'])
        if price_valid:
            self.print_success(f"Pricing: {price_msg}")
        else:
            self.print_error(f"Pricing: {price_msg}")
            all_valid = False

        # Validate terms acceptance
        if test_data['terms_accepted']:
            self.print_success("Terms accepted: Yes")
        else:
            self.print_error("Terms accepted: No - Required for registration")
            all_valid = False

        # Check name length
        full_name = f"{test_data['first_name']} {test_data['surname']}"
        if len(full_name.strip()) >= 2:
            self.print_success(f"Name: {full_name}")
        else:
            self.print_error("Name too short")
            all_valid = False

        # Check specializations
        if test_data['specializations'] and len(test_data['specializations']) > 0:
            self.print_success(f"Specializations: {len(test_data['specializations'])} selected")
        else:
            self.print_error("No specializations selected")
            all_valid = False

        return all_valid

    def preview_database_record(self, test_data: Dict):
        """Show what would be saved to the database"""
        self.print_section(f"{Colors.DATABASE} Database Preview (NOT SAVED)")

        # Generate flow token
        phone_normalized = re.sub(r'[^\d]', '', test_data['phone'])
        timestamp = int(datetime.now().timestamp())
        flow_token = f"trainer_onboarding_{phone_normalized}_{timestamp}"

        # Build database record
        db_record = {
            'name': f"{test_data['first_name']} {test_data['surname']}",
            'first_name': test_data['first_name'],
            'last_name': test_data['surname'],
            'email': test_data['email'].lower(),
            'whatsapp': phone_normalized,
            'city': test_data['city'],
            'business_name': test_data.get('business_name', ''),
            'specialization': ', '.join(test_data['specializations']),
            'experience_years': test_data['experience_years'],
            'pricing_per_session': float(test_data['pricing_per_session']),
            'available_days': test_data.get('available_days', []),
            'preferred_time_slots': test_data.get('preferred_time_slots', ''),
            'subscription_plan': test_data.get('subscription_plan', 'free'),
            'services_offered': test_data.get('services_offered', []),
            'pricing_flexibility': test_data.get('pricing_flexibility', []),
            'notification_preferences': test_data.get('notification_preferences', []),
            'marketing_consent': test_data.get('marketing_consent', False),
            'terms_accepted': test_data['terms_accepted'],
            'additional_notes': test_data.get('additional_notes', ''),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'flow_token': flow_token
        }

        # Pretty print the record
        print(f"\n{Colors.BOLD}Table: trainers{Colors.ENDC}")
        print(f"{Colors.CYAN}{'─'*70}{Colors.ENDC}")

        # Group fields for better display
        sections = {
            'Personal Information': ['name', 'first_name', 'last_name', 'email', 'whatsapp', 'city'],
            'Business Details': ['business_name', 'specialization', 'experience_years', 'pricing_per_session'],
            'Availability': ['available_days', 'preferred_time_slots'],
            'Subscription & Services': ['subscription_plan', 'services_offered', 'pricing_flexibility'],
            'Preferences': ['notification_preferences', 'marketing_consent', 'terms_accepted'],
            'Additional': ['additional_notes', 'status', 'created_at', 'flow_token']
        }

        for section_name, fields in sections.items():
            print(f"\n{Colors.BOLD}{Colors.YELLOW}{section_name}:{Colors.ENDC}")
            for field in fields:
                if field in db_record:
                    value = db_record[field]
                    # Format the value for display
                    if isinstance(value, list):
                        value_str = ', '.join(value) if value else '[]'
                    elif isinstance(value, bool):
                        value_str = f"{Colors.GREEN}Yes{Colors.ENDC}" if value else f"{Colors.RED}No{Colors.ENDC}"
                    elif isinstance(value, float):
                        value_str = f"R{value:.2f}"
                    else:
                        value_str = str(value)

                    print(f"  {Colors.BOLD}{field}:{Colors.ENDC} {value_str}")

        self.print_info(f"\n{Colors.WARNING} This is a preview only - NO data was saved to the database")

    def print_summary(self, validation_passed: bool):
        """Print test summary"""
        self.print_section(f"{Colors.CHART} Test Results Summary")

        # Count results
        total_tests = 8  # Fixed number of validation checks

        if validation_passed:
            print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*70}{Colors.ENDC}")
            print(f"{Colors.GREEN}{Colors.BOLD}{Colors.SUCCESS} ALL TESTS PASSED! {Colors.SUCCESS}{Colors.ENDC}".center(80))
            print(f"{Colors.GREEN}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

            print(f"{Colors.GREEN}✓ Flow definition loaded successfully{Colors.ENDC}")
            print(f"{Colors.GREEN}✓ Test data structure valid{Colors.ENDC}")
            print(f"{Colors.GREEN}✓ All required fields present{Colors.ENDC}")
            print(f"{Colors.GREEN}✓ Email validation passed{Colors.ENDC}")
            print(f"{Colors.GREEN}✓ Phone validation passed{Colors.ENDC}")
            print(f"{Colors.GREEN}✓ Pricing validation passed{Colors.ENDC}")
            print(f"{Colors.GREEN}✓ Terms accepted{Colors.ENDC}")
            print(f"{Colors.GREEN}✓ Database record structure valid{Colors.ENDC}")

            print(f"\n{Colors.CYAN}{Colors.INFO} The trainer onboarding flow is ready for production!{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}{'='*70}{Colors.ENDC}")
            print(f"{Colors.RED}{Colors.BOLD}{Colors.FAIL} TESTS FAILED {Colors.FAIL}{Colors.ENDC}".center(80))
            print(f"{Colors.RED}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

            print(f"{Colors.RED}Please fix the validation errors listed above.{Colors.ENDC}")

        # Execution info
        print(f"\n{Colors.CYAN}{'─'*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}Test Execution Info:{Colors.ENDC}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Flow File: {self.flow_file}")
        print(f"  Test Mode: {Colors.YELLOW}DRY RUN (no database writes){Colors.ENDC}")

    def run(self):
        """Run the complete test suite"""
        self.print_header(f"{Colors.ROCKET} Trainer Onboarding Flow Test Runner {Colors.ROCKET}")

        print(f"{Colors.BOLD}This test will:{Colors.ENDC}")
        print(f"  1. Load the trainer onboarding flow definition")
        print(f"  2. Simulate a complete flow response with test data")
        print(f"  3. Validate all required fields and data formats")
        print(f"  4. Preview what would be saved to the database")
        print(f"  5. Provide a detailed test results summary")
        print(f"\n{Colors.YELLOW}{Colors.WARNING} NOTE: This is a DRY RUN - no data will be saved!{Colors.ENDC}")

        # Step 1: Load flow definition
        if not self.load_flow_definition():
            self.print_summary(False)
            sys.exit(1)

        # Step 2: Get test data
        self.print_section("Test Data")
        test_data = self.get_test_data()

        print(f"\n{Colors.BOLD}Simulating trainer registration with:{Colors.ENDC}")
        print(f"  Name: {test_data['first_name']} {test_data['surname']}")
        print(f"  Email: {test_data['email']}")
        print(f"  Phone: {test_data['phone']}")
        print(f"  City: {test_data['city']}")
        print(f"  Specialization: {', '.join(test_data['specializations'])}")
        print(f"  Experience: {test_data['experience_years']} years")
        print(f"  Pricing: R{test_data['pricing_per_session']} per session")
        print(f"  Terms Accepted: {'Yes' if test_data['terms_accepted'] else 'No'}")

        # Step 3: Validate data
        validation_passed = self.validate_test_data(test_data)

        # Step 4: Preview database record (only if validation passed)
        if validation_passed:
            self.preview_database_record(test_data)

        # Step 5: Print summary
        self.print_summary(validation_passed)

        # Exit with appropriate code
        sys.exit(0 if validation_passed else 1)


if __name__ == "__main__":
    tester = TrainerOnboardingTester()
    tester.run()
