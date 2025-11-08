# Flow Tests

This directory contains isolated tests for WhatsApp Flows that can be run without affecting the main codebase or production database.

## Overview

The flow tests provide a safe environment to:
- Test flow message creation and structure
- Validate flow JSON configurations
- Simulate webhook handling
- Test error scenarios
- Verify data extraction and validation

## Test Files

### `__init__.py`
Package initialization file that makes flow_tests a Python package.

### `trainer_onboarding_test.py`
Tests the trainer onboarding flow including:
- Flow data loading and validation
- Flow token generation
- Message structure creation
- Response simulation and validation

**Usage:**
```bash
python3 flow_tests/trainer_onboarding_test.py
```

**Features:**
- ✅ Flow JSON validation
- ✅ Token generation testing
- ✅ Message structure validation
- ✅ Response data validation
- ✅ Comprehensive test reporting

### `test_webhook_handler.py`
Tests webhook handling for WhatsApp Flows including:
- Webhook verification
- Flow completion events
- Data extraction from webhooks
- Error handling
- Response formatting

**Usage:**
```bash
python3 flow_tests/test_webhook_handler.py
```

**Features:**
- ✅ Webhook verification testing
- ✅ Flow completion webhook processing
- ✅ Data extraction and validation
- ✅ Error scenario handling
- ✅ Token validation
- ✅ Response formatting verification
- 📁 Saves results to `webhook_test_results.json`

## Running Tests

### Run Individual Tests

```bash
# Test trainer onboarding flow
python3 flow_tests/trainer_onboarding_test.py

# Test webhook handler
python3 flow_tests/test_webhook_handler.py
```

### Run All Tests

```bash
# Run both test files
python3 flow_tests/trainer_onboarding_test.py && python3 flow_tests/test_webhook_handler.py
```

### Using Python Module Syntax

```bash
# From project root
python3 -m flow_tests.trainer_onboarding_test
python3 -m flow_tests.test_webhook_handler
```

## Test Output

Tests provide colorful emoji-based output:
- ✅ Green checkmark for passed tests
- ❌ Red X for failed tests
- 📊 Summary statistics
- 🎉 Success celebration

Example output:
```
🧪 Starting Trainer Onboarding Flow Tests
============================================================
✅ Flow File Check: Flow file loaded successfully
✅ Flow Structure: Flow structure is valid
✅ Token Generation: Generated token: trainer_onboarding_27123456789_1699456789
✅ Message Structure: Flow message structure is valid
✅ Flow Response: Flow response validation successful

============================================================
📊 Test Summary:
   Total: 5
   Passed: 5
   Failed: 0
   Success Rate: 100.0%

🎉 All tests passed!
```

## Test Mode

All tests run in `test_mode=True` by default, which means:
- No actual API calls are made
- No database operations are performed
- No external services are contacted
- All operations are simulated

This ensures tests are:
- ⚡ Fast
- 🔒 Safe
- 🌐 Work offline
- 💰 Cost-free

## Integration with Main Codebase

The tests import from the main codebase but don't modify it:

```python
# Tests can import utilities
from utils.logger import log_info, log_error, log_warning

# Tests load actual flow configurations
flow_path = os.path.join(project_root, 'whatsapp_flows', 'trainer_onboarding_flow.json')
```

This allows tests to:
- Use real flow configurations
- Validate against actual data structures
- Test with production-like scenarios
- Catch configuration issues early

## Adding New Tests

To add a new test file:

1. Create a new Python file in `flow_tests/`
2. Add proper headers and documentation
3. Import necessary modules from main codebase
4. Implement test class with `test_mode` parameter
5. Add comprehensive test methods
6. Include result tracking and reporting
7. Update `__init__.py` if needed

Example structure:
```python
#!/usr/bin/env python3
"""
Your Test Description
What this test covers
"""

import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class YourTestClass:
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.test_results = []

    def your_test_method(self) -> bool:
        # Test implementation
        pass

    def run_all_tests(self):
        # Run all tests
        pass

if __name__ == "__main__":
    main()
```

## Best Practices

1. **Always use test_mode=True** for automated tests
2. **Validate all data structures** before processing
3. **Handle exceptions gracefully** and report them
4. **Provide clear test output** with emoji indicators
5. **Save results to files** for review and debugging
6. **Don't modify production data** or make real API calls
7. **Keep tests independent** - each test should work standalone
8. **Document test purpose** clearly in docstrings

## Troubleshooting

### Import Errors
If you get import errors, ensure you're running from the project root:
```bash
cd /home/user/whatsapp-ai-assistant
python3 flow_tests/trainer_onboarding_test.py
```

### Flow File Not Found
Ensure the flow JSON files exist in `whatsapp_flows/` directory:
```bash
ls -la whatsapp_flows/trainer_onboarding_flow.json
```

### Test Failures
Check the detailed output for specific failure messages. Tests will indicate:
- Which test failed
- Why it failed
- What was expected vs. what was received

## Future Enhancements

Potential additions to the test suite:
- [ ] Client onboarding flow tests
- [ ] Habit logging flow tests
- [ ] Profile edit flow tests
- [ ] Integration tests with mock API
- [ ] Performance benchmarking
- [ ] Load testing simulations
- [ ] Multi-flow scenario testing

## Contributing

When adding new tests:
1. Follow the existing code style
2. Include comprehensive documentation
3. Add test cases for both success and failure scenarios
4. Update this README with new test descriptions
5. Ensure tests run in isolation without side effects

## License

Part of the WhatsApp AI Assistant project.
