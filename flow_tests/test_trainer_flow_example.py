#!/usr/bin/env python3
"""
Example usage of the trainer onboarding test functions

This demonstrates how to use the test functions individually
with custom data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flow_tests.trainer_onboarding_test import (
    create_test_flow_message,
    simulate_flow_response,
    validate_trainer_data,
    test_flow_locally
)

def example_1_create_message():
    """Example: Create a flow message for a specific phone number"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Create Flow Message")
    print("="*80)

    phone = "27821234567"
    message = create_test_flow_message(phone)

    print(f"\nFlow message created for: {message['to']}")
    print(f"Flow ID: {message['interactive']['action']['parameters']['flow_id']}")
    print(f"Flow Token: {message['interactive']['action']['parameters']['flow_token']}")


def example_2_validate_data():
    """Example: Validate custom trainer data"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Validate Trainer Data")
    print("="*80)

    # Custom trainer data
    trainer_data = {
        "full_name": "Nomsa Dlamini",
        "email": "nomsa.dlamini@gmail.com",
        "phone": "27834567890",
        "specialization": "CrossFit",
        "experience_years": "3",
        "rate_per_session": "400",
        "currency": "ZAR",
        "location": "Cape Town"
    }

    result = validate_trainer_data(trainer_data)

    print(f"\nValidation Result: {'✅ VALID' if result['valid'] else '❌ INVALID'}")
    print(f"Errors: {len(result['errors'])}")
    print(f"Warnings: {len(result['warnings'])}")

    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  • {error}")

    if result['warnings']:
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  • {warning}")


def example_3_simulate_response():
    """Example: Simulate flow response with custom data"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Simulate Flow Response")
    print("="*80)

    custom_data = {
        "full_name": "Zanele Mkhize",
        "email": "zanele@fitness.co.za",
        "phone": "27823456789",
        "specialization": "Pilates & Yoga",
        "experience_years": "5",
        "bio": "Passionate about holistic wellness",
        "rate_per_session": "300",
        "currency": "ZAR"
    }

    response = simulate_flow_response(custom_data)

    print(f"\nSimulation Success: {response['success']}")
    print(f"Trainer Name: {response['data']['full_name']}")
    print(f"Specialization: {response['data']['specialization']}")
    print(f"Rate: R{response['data']['rate_per_session']} {response['data']['currency']}")


def example_4_invalid_data():
    """Example: Test with invalid data to see validation errors"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Test Invalid Data")
    print("="*80)

    # Invalid data - missing required fields, wrong formats
    invalid_data = {
        "full_name": "Test Trainer",
        "email": "invalid-email",  # Invalid email format
        "phone": "0821234567",  # Wrong format (should start with 27)
        "rate_per_session": "-100",  # Negative rate
        "currency": "USD"  # Wrong currency for SA
    }

    result = validate_trainer_data(invalid_data)

    print(f"\nValidation Result: {'✅ VALID' if result['valid'] else '❌ INVALID'}")

    if result['errors']:
        print(f"\n❌ Errors ({len(result['errors'])}):")
        for error in result['errors']:
            print(f"  • {error}")

    if result['warnings']:
        print(f"\n⚠️  Warnings ({len(result['warnings'])}):")
        for warning in result['warnings']:
            print(f"  • {warning}")


def example_5_complete_test():
    """Example: Run complete local test with custom data"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Complete Local Test")
    print("="*80)

    custom_data = {
        "full_name": "Sizwe Nkosi",
        "email": "sizwe@trainers.co.za",
        "phone": "27823334444",
        "specialization": "Bodybuilding",
        "experience_years": "10",
        "bio": "Professional bodybuilder and trainer",
        "certifications": "IFBB Pro, NASM",
        "rate_per_session": "500",
        "currency": "ZAR",
        "location": "Durban, KZN",
        "availability": "Mon-Sat: 5am-9pm"
    }

    # Run complete test with custom data
    test_flow_locally(phone_number="27823334444", custom_data=custom_data)


def main():
    """Run all examples"""
    print("\n🚀 TRAINER ONBOARDING TEST - USAGE EXAMPLES")
    print("="*80)

    # Run examples
    example_1_create_message()
    example_2_validate_data()
    example_3_simulate_response()
    example_4_invalid_data()
    example_5_complete_test()

    print("\n" + "="*80)
    print("✅ All examples completed!")
    print("="*80)


if __name__ == "__main__":
    main()
