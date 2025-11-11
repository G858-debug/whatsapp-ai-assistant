# Client Addition Validator

Comprehensive input validation and error handling for the add-client flow.

## Features

### ✅ Input Validation
- **Phone Numbers**: South African format validation (+27, 27, 0), 10 digits
- **Names**: 2-100 characters, reasonable length checking
- **Emails**: Valid format validation if provided (optional)
- **Prices**: Positive numbers, R50-R5000 range
- **Package Deals**: AI-powered validation to check if structure makes sense

### 🔄 Retry Logic
- Maximum 3 attempts for invalid inputs
- Helpful error messages with examples
- Option to start over after reaching max retries
- User-friendly prompts showing remaining attempts

### 📱 vCard Edge Case Handling
- **Missing phone number** → Ask manually
- **Multiple phone numbers** → Ask which one to use
- **No name** → Ask manually
- **Invalid phone format** → Validate and provide helpful feedback

### 💬 Friendly Error Messages
- Clear, non-technical language
- Examples of valid formats
- Emoji indicators for better UX
- Contextual help based on mobile users and South African formats

### 📝 Comprehensive Logging
- Debug-level validation attempts
- Warning-level validation failures
- Error-level exceptions
- Info-level successful validations

## Usage

### Basic Usage

```python
from services.validation import get_validator

# Get validator instance (singleton)
validator = get_validator()

# Validate phone number
is_valid, error_msg, cleaned_phone = validator.validate_phone_number(
    phone="0730564882",
    user_id="27730564882"  # For retry tracking
)

if is_valid:
    print(f"Valid phone: {cleaned_phone}")  # Output: 27730564882
else:
    print(f"Error: {error_msg}")

# Validate name
is_valid, error_msg = validator.validate_name(
    name="John Smith",
    user_id="27730564882"
)

# Validate email
is_valid, error_msg = validator.validate_email(
    email="john@example.com",
    required=False,  # Optional field
    user_id="27730564882"
)

# Validate price
is_valid, error_msg, price_value = validator.validate_price(
    price_str="R350",
    user_id="27730564882"
)

if is_valid:
    print(f"Valid price: R{price_value:.2f}")  # Output: R350.00
```

### Advanced Usage

#### Retry Tracking

```python
validator = get_validator()

# Check retry count
retry_count = validator.get_retry_count("27730564882", "phone")
print(f"Attempts: {retry_count}/3")

# Check if max retries exceeded
if validator.has_exceeded_max_retries("27730564882", "phone"):
    restart_prompt = validator.get_restart_prompt("phone number")
    print(restart_prompt)
```

#### vCard Edge Case Handling

```python
validator = get_validator()

# Parse vCard data (from contact_share_handler)
vcard_data = {
    'name': 'John Smith',
    'phones': ['0730564882', '0829876543'],  # Multiple phones
    'emails': ['john@example.com']
}

# Handle edge cases
result = validator.handle_vcard_edge_cases(vcard_data)

print(result['status'])  # 'valid', 'missing_phone', 'multiple_phones', etc.
print(result['message'])  # User-friendly message
print(result['action_required'])  # 'ask_phone', 'choose_phone', 'ask_name'
```

#### Package Deal Validation (AI-Powered)

```python
validator = get_validator()

# Validate package deal
is_valid, error_msg, package_info = validator.validate_package_deal(
    package_description="10 sessions for R2500 (save R500)",
    price_per_session=300.0
)

if is_valid:
    print(package_info)
    # Output: {
    #   'description': '10 sessions for R2500 (save R500)',
    #   'sessions': 10,
    #   'total_price': 2500,
    #   'discount_percentage': 16.67,
    #   'base_price_per_session': 300.0
    # }
```

#### Validation Summary

```python
validator = get_validator()

validated_data = {
    'name': 'John Smith',
    'phone': '27730564882',
    'email': 'john@example.com',
    'price': 350.0
}

summary = validator.format_validation_summary(validated_data)
print(summary)
# Output:
# 📋 *Client Information Summary*
#
# *Name:* John Smith
# *Phone:* +27 730 564 882
# *Email:* john@example.com
# *Price per session:* R350.00
#
# ✅ Everything looks good!
```

## Integration Points

### 1. Contact Share Handler
**File**: `services/message_handlers/contact_share_handler.py`

Handles vCard edge cases when trainers share contacts:
- Missing phone → asks manually
- Multiple phones → asks which one
- Invalid phone → validates and provides feedback
- Missing name → asks manually

### 2. Creation Flow
**File**: `services/flows/relationships/trainer_flows/creation_flow.py`

Validates fields during text-based client creation:
- Phone number validation with SA formats
- Name validation with length checks
- Email validation (optional)
- Price validation with range checks
- Retry logic with max 3 attempts

### 3. vCard Edge Case Handler
**File**: `services/message_router/handlers/tasks/contact_tasks.py`

Processes vCard edge cases as tasks:
- Collects missing information
- Validates user inputs
- Handles retry attempts
- Creates confirmation tasks

## Phone Number Formats

The validator supports these South African phone formats:

| Format | Example | Result |
|--------|---------|--------|
| With + | +27730564882 | 27730564882 |
| Without + | 27730564882 | 27730564882 |
| With 0 | 0730564882 | 27730564882 |
| With spaces | 073 056 4882 | 27730564882 |
| With dashes | 073-056-4882 | 27730564882 |

All formats are normalized to `27XXXXXXXXX` (11 digits).

### Mobile Number Validation

The validator ensures:
- Phone number is SA mobile (starts with 27 + 6/7/8)
- Exactly 11 digits after normalization
- No invalid characters
- Proper country code

## Error Messages

### Phone Number Errors

**Too short:**
```
📱 That number seems too short!

SA phone numbers have 10 digits (starting with 0) or 11 digits (starting with 27).

*Valid formats:*
• 0730564882
• +27730564882
• 27730564882
• 073 056 4882
• +27 73 056 4882
```

**Invalid format:**
```
📱 Hmm, I'm having trouble with that format.

Please try one of these South African formats:

*Valid formats:*
• 0730564882
• +27730564882
• 27730564882
• 073 056 4882
• +27 73 056 4882
```

### Name Errors

**Too short:**
```
✍️ That name seems too short!

Please enter at least 2 characters.

💡 *Tip:* Use the client's full name (e.g., 'John Smith')
```

### Email Errors

**Missing @ symbol:**
```
📧 Hmm, that doesn't look like an email address.

Email addresses need an @ symbol.

*Example:* john@gmail.com
```

### Price Errors

**Below minimum:**
```
💰 That price seems quite low!

We recommend at least R50 per session.

💡 *Tip:* This helps maintain quality training services.

Please enter a price of at least R50.
```

**Above maximum:**
```
💰 Wow, that's quite high!

Our system supports prices up to R5000 per session.

💡 *Tip:* For premium packages, consider using package deals.

Please enter a price under R5000.
```

## Retry Logic

The validator tracks retry attempts per user per field:

```python
# First attempt
is_valid, error_msg, _ = validator.validate_phone_number("abc", user_id)
# Error message includes: "💡 *Attempts remaining:* 2"

# Second attempt
is_valid, error_msg, _ = validator.validate_phone_number("123", user_id)
# Error message includes: "💡 *Attempts remaining:* 1"

# Third attempt (max)
is_valid, error_msg, _ = validator.validate_phone_number("456", user_id)
# Error message includes: "⚠️ *Maximum attempts reached!*
# Type */stop* to cancel, or */start-over* to try again."

# Check if exceeded
if validator.has_exceeded_max_retries(user_id, "phone"):
    restart_msg = validator.get_restart_prompt("phone number")
    # Returns friendly prompt with options
```

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_RETRY_ATTEMPTS` | 3 | Maximum retry attempts per field |
| `MIN_NAME_LENGTH` | 2 | Minimum characters for name |
| `MAX_NAME_LENGTH` | 100 | Maximum characters for name |
| `MIN_PRICE` | 50 | Minimum price in Rands |
| `MAX_PRICE` | 5000 | Maximum price in Rands |

## Testing

To test the validator:

```bash
# Run Python interactive shell
python3

# Import validator
from services.validation import get_validator
validator = get_validator()

# Test phone validation
validator.validate_phone_number("0730564882", "test_user")
# Expected: (True, '', '27730564882')

validator.validate_phone_number("123", "test_user")
# Expected: (False, 'error message', None)

# Test name validation
validator.validate_name("John Smith", "test_user")
# Expected: (True, '')

validator.validate_name("A", "test_user")
# Expected: (False, 'error message')

# Test price validation
validator.validate_price("R350", "test_user")
# Expected: (True, '', 350.0)

validator.validate_price("10", "test_user")
# Expected: (False, 'error message', None)
```

## Design Decisions

### Why Singleton Pattern?

The validator uses a singleton pattern (`get_validator()`) to:
- Maintain retry counts across the session
- Avoid recreating instances
- Provide consistent validation behavior

### Why Separate Retry Tracking?

Retry counts are tracked per `user_id` and `field` to:
- Allow different retry counts for different fields
- Support multiple users simultaneously
- Reset counts on successful validation

### Why AI for Package Deals?

Package deal validation uses AI because:
- Structure varies greatly (free text input)
- Need to understand intent and math
- Fallback to basic validation if AI unavailable
- Provides helpful feedback for corrections

## Logging

The validator logs at different levels:

```python
# Debug level - validation attempts
log_debug(f"Validating phone number: {phone}")

# Info level - successful validations
log_info(f"Phone number validated successfully: {phone} -> {normalized_phone}")

# Warning level - validation failures
log_warning(f"Phone validation error ({error_type}): {phone} | Attempt {retry_count}/{MAX_RETRY}")

# Error level - exceptions
log_error(f"Error validating phone number: {str(e)}")
```

## Future Enhancements

- [ ] Support for international phone numbers
- [ ] Custom validation rules per trainer
- [ ] Validation analytics dashboard
- [ ] Machine learning for better package deal parsing
- [ ] Multi-language error messages
- [ ] Integration with CRM systems for duplicate checking

## Contributing

When adding new validators:
1. Follow the existing pattern (validate_X method)
2. Return tuple: `(is_valid, error_message, [parsed_value])`
3. Add retry tracking for user inputs
4. Provide friendly error messages with examples
5. Add comprehensive logging
6. Update this README with usage examples

## Support

For issues or questions:
- Check logs for detailed error messages
- Review error messages sent to users
- Verify field types and validation rules
- Test with various input formats
