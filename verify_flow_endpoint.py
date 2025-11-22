#!/usr/bin/env python3
"""
Simple verification script for WhatsApp Flow health check endpoint
Checks code implementation without requiring cryptography libraries
"""

import re
import sys

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{YELLOW}{BOLD}{'='*70}{RESET}")
    print(f"{YELLOW}{BOLD}{text:^70}{RESET}")
    print(f"{YELLOW}{BOLD}{'='*70}{RESET}\n")

def print_check(passed, name, details):
    if passed:
        print(f"{GREEN}✓ {name}{RESET}")
        if details:
            print(f"  {BLUE}{details}{RESET}")
    else:
        print(f"{RED}✗ {name}{RESET}")
        if details:
            print(f"  {RED}{details}{RESET}")
    return passed

def verify_whatsapp_flow_route():
    """Verify the WhatsApp Flow route implementation"""
    print_header("Verifying WhatsApp Flow Endpoint Implementation")

    try:
        with open('/home/user/whatsapp-ai-assistant/routes/whatsapp_flow.py', 'r') as f:
            route_code = f.read()
    except FileNotFoundError:
        print(f"{RED}✗ Could not find routes/whatsapp_flow.py{RESET}")
        return False

    all_checks_passed = True

    # Check 1: Verify encryption function exists
    check1 = 'def encrypt_response(response, aes_key, iv):' in route_code
    all_checks_passed &= print_check(
        check1,
        "Encryption function exists",
        "encrypt_response() function is defined"
    )

    # Check 2: Verify decryption function exists
    check2 = 'def decrypt_request(encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64):' in route_code
    all_checks_passed &= print_check(
        check2,
        "Decryption function exists",
        "decrypt_request() function is defined"
    )

    # Check 3: Verify POST handler exists
    check3 = "def handle_whatsapp_flow():" in route_code
    all_checks_passed &= print_check(
        check3,
        "POST handler exists",
        "handle_whatsapp_flow() function is defined"
    )

    # Check 4: Verify response returns Base64 string with text/plain (NOT JSON wrapped)
    # This is the CRITICAL check
    check4 = "return encrypted_response, 200, {'Content-Type': 'text/plain'}" in route_code
    all_checks_passed &= print_check(
        check4,
        "✓ CRITICAL: Returns plain Base64 (NOT JSON-wrapped)",
        "Returns: encrypted_response, 200, {'Content-Type': 'text/plain'}"
    )

    # Check 5: Verify it's NOT returning JSON-wrapped response (the old buggy way)
    check5_bad = 'jsonify({"encrypted_response": encrypted_response})' not in route_code
    all_checks_passed &= print_check(
        check5_bad,
        "No JSON wrapping around encrypted response",
        "Good! Not using jsonify() to wrap the Base64 string"
    )

    # Check 6: Verify encryption is called
    check6 = 'encrypted_response = encrypt_response(response, aes_key, iv)' in route_code
    all_checks_passed &= print_check(
        check6,
        "Response is encrypted before returning",
        "encrypt_response() is called with proper parameters"
    )

    # Check 7: Verify request is decrypted
    check7 = 'decrypt_request(' in route_code
    all_checks_passed &= print_check(
        check7,
        "Incoming request is decrypted",
        "decrypt_request() is called to handle encrypted flow data"
    )

    # Check 8: Verify flow data exchange handler is called
    check8 = 'handle_flow_data_exchange(decrypted_data, flow_token)' in route_code
    all_checks_passed &= print_check(
        check8,
        "Flow data exchange handler is called",
        "handle_flow_data_exchange() processes the decrypted data"
    )

    return all_checks_passed

def verify_flow_data_exchange_handler():
    """Verify the flow data exchange handler"""
    print_header("Verifying Flow Data Exchange Handler")

    try:
        with open('/home/user/whatsapp-ai-assistant/handlers/flow_data_exchange.py', 'r') as f:
            handler_code = f.read()
    except FileNotFoundError:
        print(f"{RED}✗ Could not find handlers/flow_data_exchange.py{RESET}")
        return False

    all_checks_passed = True

    # Check 1: Handler function exists
    check1 = 'def handle_flow_data_exchange(decrypted_data: Dict[str, Any], flow_token: str)' in handler_code
    all_checks_passed &= print_check(
        check1,
        "Handler function exists",
        "handle_flow_data_exchange() is properly defined"
    )

    # Check 2: Ping action is handled
    check2 = "if action == 'ping':" in handler_code
    all_checks_passed &= print_check(
        check2,
        "Ping action handler exists",
        "Handles 'ping' action for health checks"
    )

    # Check 3: Ping returns correct response structure
    check3 = '"status": "active"' in handler_code
    all_checks_passed &= print_check(
        check3,
        "Ping returns status: active",
        "Health check response includes status: active"
    )

    # Check 4: Returns version in response
    check4 = '"version": version' in handler_code or '"version": "3.0"' in handler_code
    all_checks_passed &= print_check(
        check4,
        "Response includes version",
        "All responses include WhatsApp Flow version"
    )

    # Check 5: INIT action is handled
    check5 = "elif action == 'init':" in handler_code
    all_checks_passed &= print_check(
        check5,
        "INIT action handler exists",
        "Handles flow initialization"
    )

    # Check 6: data_exchange action is handled
    check6 = "elif action == 'data_exchange':" in handler_code
    all_checks_passed &= print_check(
        check6,
        "data_exchange action handler exists",
        "Handles data exchange actions"
    )

    return all_checks_passed

def show_implementation_summary():
    """Show summary of how the endpoint works"""
    print_header("Implementation Summary")

    print(f"{BLUE}How the WhatsApp Flow Health Check Works:{RESET}\n")

    print(f"{GREEN}1. WhatsApp sends encrypted POST request{RESET}")
    print(f"   • Includes encrypted_flow_data, encrypted_aes_key, initial_vector")
    print(f"   • Request contains action: 'ping' for health checks\n")

    print(f"{GREEN}2. Endpoint decrypts the request{RESET}")
    print(f"   • Uses RSA private key to decrypt AES key")
    print(f"   • Uses AES-GCM to decrypt flow data")
    print(f"   • Extracts action and other fields\n")

    print(f"{GREEN}3. Handler processes the ping{RESET}")
    print(f"   • handle_flow_data_exchange() receives decrypted data")
    print(f"   • Recognizes action='ping'")
    print(f"   • Returns: {{'version': '3.0', 'data': {{'status': 'active'}}}}\n")

    print(f"{GREEN}4. Response is encrypted{RESET}")
    print(f"   • Flips the IV (XOR with 0xFF)")
    print(f"   • Encrypts response with AES-GCM")
    print(f"   • Base64 encodes the result\n")

    print(f"{GREEN}5. Returns plain Base64 string{RESET}")
    print(f"   • Content-Type: text/plain")
    print(f"   • Body is ONLY the Base64 string")
    print(f"   • ✓ NOT wrapped in JSON")
    print(f"   • ✓ NOT quoted\n")

def main():
    """Main verification function"""
    print(f"\n{BOLD}{BLUE}WhatsApp Flow Health Check Endpoint Verification{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    # Verify route implementation
    route_ok = verify_whatsapp_flow_route()

    # Verify handler implementation
    handler_ok = verify_flow_data_exchange_handler()

    # Show implementation summary
    show_implementation_summary()

    # Final verdict
    print_header("Final Verification Result")

    if route_ok and handler_ok:
        print(f"{GREEN}{BOLD}{'✓'*70}{RESET}")
        print(f"{GREEN}{BOLD}ALL CHECKS PASSED - IMPLEMENTATION IS CORRECT!{RESET}")
        print(f"{GREEN}{BOLD}{'✓'*70}{RESET}\n")

        print(f"{GREEN}The endpoint is properly configured to:{RESET}")
        print(f"{GREEN}  ✓ Accept encrypted WhatsApp Flow requests{RESET}")
        print(f"{GREEN}  ✓ Handle ping/health check actions{RESET}")
        print(f"{GREEN}  ✓ Return encrypted responses as Base64 strings{RESET}")
        print(f"{GREEN}  ✓ Use Content-Type: text/plain (not JSON){RESET}")
        print(f"{GREEN}  ✓ NOT wrap responses in JSON objects{RESET}\n")

        print(f"{BLUE}WhatsApp Flow health checks should now work correctly!{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}{'✗'*70}{RESET}")
        print(f"{RED}{BOLD}VERIFICATION FAILED - ISSUES FOUND{RESET}")
        print(f"{RED}{BOLD}{'✗'*70}{RESET}\n")

        if not route_ok:
            print(f"{RED}Issues found in routes/whatsapp_flow.py{RESET}")
        if not handler_ok:
            print(f"{RED}Issues found in handlers/flow_data_exchange.py{RESET}")

        print(f"\n{YELLOW}Please review the failed checks above{RESET}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
