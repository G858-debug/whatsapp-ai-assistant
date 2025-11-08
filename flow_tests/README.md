# Trainer Onboarding Flow Test Suite

## Overview

### What This Test Suite Does
This test suite allows you to safely test the WhatsApp trainer onboarding flow **before** making it live. Think of it as a practice area where you can:
- Test how the onboarding form works
- Make sure all the data fields are captured correctly
- Check that the flow responds properly when trainers submit their information
- Catch any issues before real trainers use the system

### Why It's Separate From Main Code
The test files are kept in their own `flow_tests/` folder to ensure:
- **Safety**: Tests don't accidentally change real data or affect live users
- **Speed**: You can test quickly without waiting for the whole system to start
- **Independence**: Tests work offline and don't need API keys or database connections
- **Cost-free**: No charges for WhatsApp API calls during testing
- **Flexibility**: You can experiment and break things without consequences

---

## Files

### `integration_test.py`
Comprehensive integration test that validates the complete WhatsApp Business API setup including:
- Connection to Meta's WhatsApp Business API
- Flow verification (confirms flow ID 775047838492907 exists)
- Webhook endpoint accessibility and configuration
- Flow JSON data structure validation
- Encryption setup verification

**Usage:**
```bash
python3 flow_tests/integration_test.py
```

**Features:**
- ✅ API connection testing with detailed error messages
- ✅ Flow existence and status verification
- ✅ Webhook endpoint testing (GET and POST)
- ✅ Flow JSON structure validation
- ✅ Private key and encryption setup verification
- ✅ Comprehensive troubleshooting guide
- ✅ Detailed configuration validation
- ✅ Warning system for potential issues
- 📁 Saves detailed results to `integration_test_results.json`

**What it tests:**
1. **API Connection**: Validates ACCESS_TOKEN and connects to Meta's Graph API
2. **Flow Verification**: Checks if flow 775047838492907 exists and is published
3. **Webhook Endpoint**: Tests if your webhook at `/webhooks/whatsapp-flow` is accessible
4. **Flow Structure**: Validates all flow JSON files match Meta's requirements
5. **Encryption**: Verifies WHATSAPP_FLOW_PRIVATE_KEY is properly configured

**Required Environment Variables:**
- `ACCESS_TOKEN`: Your WhatsApp Business API access token
- `WHATSAPP_BUSINESS_ACCOUNT_ID`: Your Business Account ID
- `PHONE_NUMBER_ID`: Your WhatsApp phone number ID
- `BASE_URL`: Your deployed application URL
- `WHATSAPP_FLOW_PRIVATE_KEY`: Private key for flow encryption (optional but recommended)

**When to use:**
- Before deploying changes to production
- After updating flow configurations
- When troubleshooting flow issues
- To verify your setup is complete

**What to do if tests fail:**
The script provides detailed troubleshooting instructions for each failure type:
- API Connection failures → Check token validity and permissions
- Flow verification failures → Verify flow ID and access permissions
- Webhook failures → Check server deployment and BASE_URL
- Structure validation failures → Review flow JSON files
- Encryption failures → Generate and configure private key

### `test_webhook_handler.py`
**Live Flask webhook handler** for testing trainer onboarding flow webhooks from WhatsApp.

This creates a test Flask server with real webhook endpoints that:
- Receives actual WhatsApp Flow webhook data
- Extracts all trainer onboarding fields
- Logs responses to `test_flow_responses.json`
- Does NOT interact with the database (testing only)
- Returns proper responses to WhatsApp

**Quick Start:**
```bash
# Run the test webhook server
python3 flow_tests/test_webhook_handler.py

# Server starts on http://0.0.0.0:5001
# Main webhook endpoint: POST /test/flow/trainer-onboarding
```

**Available Endpoints:**
- `POST /test/flow/trainer-onboarding` - Main webhook endpoint
- `GET /test/flow/trainer-onboarding` - Get endpoint info
- `GET /test/flow/responses` - View all logged responses
- `POST /test/flow/clear` - Clear logged responses
- `GET /test/flow` - Service information

**Testing with cURL:**
```bash
# Test with sample payload
curl -X POST http://localhost:5001/test/flow/trainer-onboarding \
  -H "Content-Type: application/json" \
  -d @flow_tests/sample_webhook_payload.json

# View logged responses
curl http://localhost:5001/test/flow/responses

# Clear responses
curl -X POST http://localhost:5001/test/flow/clear
```

**Extracted Fields:**
- ✅ `full_name` - Trainer's full name
- ✅ `email` - Email address
- ✅ `phone` - Phone number (formatted to South African format)
- ✅ `city` - City location
- ✅ `specialization` - Training specialization
- ✅ `experience_years` - Years of experience
- ✅ `pricing_per_session` - Session pricing in Rand
- ✅ `terms_accepted` - Terms acceptance status

**Features:**
- 🚀 Live Flask server for real webhook testing
- 📝 Detailed logging to console and JSON file
- ✅ Field validation and error handling
- 🇿🇦 South African phone number formatting
- 📊 Complete webhook payload logging
- 🔍 Metadata extraction (phone, message ID, timestamp)
- 🛡️ No database interaction (safe for testing)
- 📁 Saves all responses to `test_flow_responses.json`
### `trainer_onboarding_test.py`
**What it does**: Tests the trainer onboarding flow structure and validation

**What it checks**:
- The flow JSON file loads correctly from `whatsapp_flows/trainer_onboarding_flow.json`
- All required screens and fields are present
- Flow tokens are generated in the correct format
- The message sent to trainers has the right structure
- Response data from trainers can be validated properly

**When to use it**: Run this test whenever you make changes to the trainer onboarding flow design or add new fields.

---

### `test_webhook_handler.py`
**What it does**: Tests how the system processes responses when trainers complete the onboarding flow

**What it checks**:
- Webhook verification works (WhatsApp's way of confirming it's really them)
- Flow completion events are processed correctly
- Trainer data is extracted from webhook responses
- Error cases are handled gracefully (missing data, invalid formats, etc.)
- Flow tokens are validated properly
- Success responses are formatted correctly

**When to use it**: Run this test before deploying webhook handlers or when changing how flow responses are processed.

---

```bash
# Integration test (validates complete setup)
python3 flow_tests/integration_test.py

# Test trainer onboarding flow
python3 flow_tests/trainer_onboarding_test.py
### `__init__.py`
**What it does**: Makes `flow_tests/` a proper Python package so tests can import code from the main system.

**You don't need to edit this file** - it's just technical plumbing.

---

## How to Run Tests

Before running tests, make sure you're in the main project directory:
```bash
# Run all test files
python3 flow_tests/integration_test.py && \
python3 flow_tests/trainer_onboarding_test.py && \
python3 flow_tests/test_webhook_handler.py
cd /home/user/whatsapp-ai-assistant
```

### 1. Test the Flow Structure
Tests the trainer onboarding flow JSON and message creation:
```bash
# From project root
python3 -m flow_tests.integration_test
python3 -m flow_tests.trainer_onboarding_test
python3 -m flow_tests.test_webhook_handler
```

### Recommended Testing Workflow

1. **Start with Integration Test**: Run `integration_test.py` first to validate your complete setup
2. **Fix any issues**: Follow the troubleshooting guide if any tests fail
3. **Run specific tests**: Use individual test files to test specific components
4. **Before deployment**: Always run the integration test to ensure everything is ready

## Test Output

Tests provide colorful emoji-based output:
- ✅ Green checkmark for passed tests
- ❌ Red X for failed tests
- 📊 Summary statistics
- 🎉 Success celebration
python flow_tests/trainer_onboarding_test.py
```

**What you'll see**:
- ✅ Green checkmarks for passed tests
- ❌ Red X marks for failed tests
- A summary showing how many tests passed

**Example output**:
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

---

### 2. Test Webhook Processing
Tests how the system handles responses from WhatsApp when trainers complete the flow:
```bash
python flow_tests/test_webhook_handler.py
```

**What you'll see**:
- Test results for webhook verification
- Validation of flow completion events
- Data extraction tests
- Error handling verification
- A JSON file saved with detailed results: `webhook_test_results.json`

**Example output**:
```
🧪 Starting Flow Webhook Handler Tests
============================================================
✅ Webhook Verification: Challenge verified: test_challenge_1234567890
✅ Flow Completion Webhook: Webhook structure is valid
✅ Flow Data Extraction: Successfully extracted data for: John Doe
✅ Error Handling: All 3 error cases handled correctly
✅ Flow Token Validation: Token validation working correctly
✅ Response Formatting: Response format is correct

============================================================
📊 Test Summary:
   Total: 6
   Passed: 6
   Failed: 0
   Success Rate: 100.0%

📁 Results saved to: flow_tests/webhook_test_results.json
🎉 All tests passed!
```

---

### 3. Run All Tests Together
To run both test files in sequence:
```bash
python flow_tests/trainer_onboarding_test.py && python flow_tests/test_webhook_handler.py
```

The `&&` means "run the second test only if the first one passes."

---

## Test Data Format

### Example Flow Response Data
When a trainer completes the onboarding flow, WhatsApp sends data in this format:

```json
{
  "first_name": "Thabo",
  "surname": "Mokoena",
  "email": "thabo@example.com",
  "phone": "27823456789",
  "city": "Johannesburg",
  "business_name": "Thabo's Fitness Studio",
  "specializations": ["personal_training", "strength_training"],
  "experience_years": "4-5",
  "pricing_per_session": "350",
  "available_days": ["monday", "wednesday", "friday"],
  "preferred_time_slots": "morning",
  "subscription_plan": "premium",
  "services_offered": ["in_person_training", "online_training"],
  "pricing_flexibility": ["package_discounts"],
  "notification_preferences": ["whatsapp", "email"],
  "marketing_consent": true,
  "terms_accepted": true,
  "additional_notes": "Specializing in beginner fitness"
}
```

### Field Validation Rules

**Required fields** (trainer cannot submit without these):
- `first_name` - Text, at least 1 character
- `surname` - Text, at least 1 character
- `email` - Valid email format (name@domain.com)
- `city` - Text, location in South Africa
- `specializations` - At least one specialty selected
- `experience_years` - Selected from dropdown options
- `pricing_per_session` - Numeric value (in ZAR)
- `available_days` - At least one day selected
- `preferred_time_slots` - One time slot selected
- `subscription_plan` - One plan selected
- `terms_accepted` - Must be true

**Optional fields**:
- `business_name` - Can be blank
- `services_offered` - Can be empty array
- `pricing_flexibility` - Can be empty array
- `notification_preferences` - Can be empty array
- `marketing_consent` - Can be false
- `additional_notes` - Can be blank

### South African Context

**Phone number format**:
- Always starts with country code: `27` (South Africa)
- Followed by 9 digits
- Example: `27823456789` (not `0823456789`)
- **Important**: Remove the leading `0` and add `27`

**Currency**:
- All prices are in South African Rand (ZAR)
- Examples: `350` (R350 per session), `500` (R500 per session)
- No currency symbol needed in the data, just the number

**Locations**:
- Cities include: Johannesburg, Cape Town, Pretoria, Durban, etc.
- Can be neighborhoods too: Sandton, Rosebank, Bellville, etc.

---

## Moving to Production

Once testing is complete and you're ready to make the trainer onboarding flow live, follow these steps:

### 1. Upload the Flow to Meta Business Manager
1. Log into [Meta Business Manager](https://business.facebook.com/)
2. Go to **WhatsApp Manager** → **Flows**
3. Click **Create Flow**
4. Upload the file: `whatsapp_flows/trainer_onboarding_flow.json`
5. Test the flow in **Draft Mode**
6. When ready, click **Publish**
7. Copy the **Flow ID** (looks like: `123456789012345`)

### 2. Add the Flow Handler to Main Code
Create a new file: `handlers/trainer_onboarding_flow_handler.py`

Use this template:
```python
#!/usr/bin/env python3
"""
Trainer Onboarding Flow Handler
Processes trainer onboarding flow completions
"""

from utils.logger import log_info, log_error
from utils.whatsapp_utils import send_message
from datetime import datetime
import json

def handle_trainer_onboarding_flow(flow_data: dict, phone_number: str) -> bool:
    """
    Process trainer onboarding flow completion

    Args:
        flow_data: Dictionary with trainer information
        phone_number: Trainer's WhatsApp number

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract required fields
        first_name = flow_data.get('first_name')
        surname = flow_data.get('surname')
        email = flow_data.get('email')

        # Validate required fields
        if not all([first_name, surname, email]):
            log_error(f"Missing required fields for {phone_number}")
            return False

        # TODO: Save to database (see step 3)

        # Send confirmation message
        send_message(
            phone_number,
            f"Welcome to Refiloe, {first_name}! Your trainer profile is now active. 🎉"
        )

        log_info(f"Trainer onboarding completed: {first_name} {surname}")
        return True

    except Exception as e:
        log_error(f"Error in trainer onboarding: {str(e)}")
        return False
```

### 3. Database Integration Points

Add database operations in `handle_trainer_onboarding_flow()`:

```python
# Import database utilities
from database.db_utils import create_trainer, get_or_create_user

# Create user account
user = get_or_create_user(phone_number)

# Create trainer profile
trainer_id = create_trainer(
    user_id=user.id,
    first_name=flow_data.get('first_name'),
    surname=flow_data.get('surname'),
    email=flow_data.get('email'),
    city=flow_data.get('city'),
    business_name=flow_data.get('business_name'),
    specializations=json.dumps(flow_data.get('specializations', [])),
    experience_years=flow_data.get('experience_years'),
    pricing_per_session=float(flow_data.get('pricing_per_session', 0)),
    available_days=json.dumps(flow_data.get('available_days', [])),
    preferred_time_slots=flow_data.get('preferred_time_slots'),
    subscription_plan=flow_data.get('subscription_plan'),
    services_offered=json.dumps(flow_data.get('services_offered', [])),
    created_at=datetime.now()
)
```

### 4. Connect to Webhook Processor

In `handlers/webhook_handler.py`, add:

```python
from handlers.trainer_onboarding_flow_handler import handle_trainer_onboarding_flow

# Inside process_flow_response() function:
if flow_name == "trainer_onboarding":
    success = handle_trainer_onboarding_flow(flow_data, phone_number)
    if success:
        log_info(f"Trainer onboarding processed for {phone_number}")
    else:
        log_error(f"Failed to process trainer onboarding for {phone_number}")
```

### 5. Update Flow Configuration

In `whatsapp_flows/flow_config.json`, add:

```json
{
  "trainer_onboarding": {
    "flow_id": "YOUR_FLOW_ID_FROM_META",
    "flow_name": "trainer_onboarding",
    "version": "3.0",
    "handler": "handlers.trainer_onboarding_flow_handler.handle_trainer_onboarding_flow"
  }
}
```

### 6. Test in Production

1. Send yourself a test flow message
2. Complete the onboarding as a trainer
3. Check logs to verify data was saved
4. Confirm the welcome message was sent
5. Verify database entry was created

---

## Troubleshooting

### Common Issues and Solutions

#### ❌ "Flow file not found"
**Problem**: The test can't find `whatsapp_flows/trainer_onboarding_flow.json`

**Solution**:
```bash
# Check if file exists
ls -la whatsapp_flows/trainer_onboarding_flow.json

# If missing, check you're in the right directory
pwd  # Should show: /home/user/whatsapp-ai-assistant
```

---

#### ❌ "Import Error: No module named 'utils'"
**Problem**: Python can't find the main codebase utilities

**Solution**:
```bash
# Always run from project root
cd /home/user/whatsapp-ai-assistant
python flow_tests/trainer_onboarding_test.py

# Don't run from inside flow_tests/
```

---

#### ❌ "JSON Decode Error"
**Problem**: The flow JSON file has invalid syntax

**Solution**:
1. Open the flow file in a JSON validator: https://jsonlint.com/
2. Paste the contents and click "Validate JSON"
3. Fix any syntax errors (missing commas, brackets, quotes)
4. Common issues:
   - Trailing commas: `"field": "value",]` ← remove comma before `]`
   - Missing quotes: `{field: value}` ← should be `{"field": "value"}`
   - Unclosed brackets: `{"screens": [` ← missing closing `]}`

---

#### ❌ Tests Pass But Real Flow Doesn't Work
**Problem**: Tests succeed but the flow fails with real WhatsApp users

**Possible causes**:
1. **Flow not published in Meta Business Manager**
   - Go to WhatsApp Manager → Flows
   - Check status is "Published" (not "Draft")

2. **Wrong Flow ID**
   - Copy the Flow ID from Meta Business Manager
   - Update `flow_config.json` with the correct ID

3. **Webhook not configured**
   - In Meta Business Manager → WhatsApp → Configuration
   - Add webhook URL: `https://yourdomain.com/webhook`
   - Subscribe to "messages" events

---

#### ❌ "Phone number format invalid"
**Problem**: Phone number validation fails

**Solution**:
- **Correct format**: `27823456789` (country code + 9 digits)
- **Wrong formats**:
  - `0823456789` ← missing country code
  - `+27823456789` ← remove the `+` sign
  - `27 82 345 6789` ← remove spaces

**How to convert**:
```python
# Remove leading zero and add country code
phone = "0823456789"
international = "27" + phone[1:]  # Result: "27823456789"
```

---

### How to Check Logs

**During testing** (test mode):
- Logs appear directly in the terminal with emoji indicators
- Green ✅ means success
- Red ❌ means failure

**In production**:
```bash
# View recent logs
tail -f logs/app.log

# Search for specific errors
grep "ERROR" logs/app.log

# Search for trainer onboarding events
grep "trainer_onboarding" logs/app.log
```

---

### Meta Business Manager Setup Tips

#### Setting Up WhatsApp Flows

1. **Create a Business Account**
   - Go to https://business.facebook.com/
   - Click "Create Account"
   - Add your business details

2. **Add WhatsApp Business Account**
   - Business Settings → Accounts → WhatsApp Accounts
   - Click "Add" → Create a new WhatsApp Business Account
   - Verify your phone number

3. **Enable Flows**
   - WhatsApp Manager → Flows
   - Click "Get Started"
   - Create your first flow

4. **Test in Draft Mode**
   - Upload your flow JSON
   - Click "Test Flow"
   - Complete the flow on your phone
   - Check all fields work correctly
   - Fix any issues before publishing

5. **Publish Flow**
   - Once testing is done, click "Publish"
   - Note: You cannot edit a published flow, only create new versions

6. **Get Flow ID**
   - After publishing, click on the flow
   - Copy the Flow ID (long number)
   - Add it to `flow_config.json`

#### Common Meta Setup Issues

**"Flow validation failed"**
- Check JSON syntax in a validator
- Ensure all required fields are present
- Verify version is compatible (use "7.3" or latest)

**"Cannot test flow"**
- Make sure your WhatsApp number is added as a tester
- Business Settings → WhatsApp Accounts → Phone Numbers → Add Testers

**"Webhook verification failed"**
- Ensure your webhook URL is publicly accessible (not localhost)
- Check the verify token matches your configuration
- Must use HTTPS (not HTTP)

---

## Need More Help?

### Documentation Resources
- WhatsApp Flows Guide: https://developers.facebook.com/docs/whatsapp/flows
- Meta Business Manager: https://business.facebook.com/
- WhatsApp API Reference: https://developers.facebook.com/docs/whatsapp

### Testing Best Practices
1. Always test in draft mode first
2. Run both test files before deploying
3. Test with multiple phone number formats
4. Try incomplete forms (skip optional fields)
5. Test error cases (invalid email, etc.)
6. Verify all specializations appear correctly
7. Check all dropdown options work

### Quick Checklist Before Going Live
- [ ] Flow JSON validates without errors
- [ ] Both test files pass 100%
- [ ] Flow published in Meta Business Manager
- [ ] Flow ID added to `flow_config.json`
- [ ] Webhook URL configured and verified
- [ ] Database tables created for trainer data
- [ ] Handler function integrated
- [ ] Tested with real WhatsApp number
- [ ] Confirmation message sends correctly
- [ ] Data saves to database
- [ ] Logs show successful completion

---

**Last Updated**: 2025-11-08
**Version**: 1.0
**Maintained by**: WhatsApp AI Assistant Team
