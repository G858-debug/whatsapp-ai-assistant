"""
Client Addition Validator
Comprehensive input validation and error handling for the add-client flow.

Features:
- South African phone number format validation (+27, 27, 0)
- Name validation (2-100 characters, reasonable length)
- Email validation (valid format if provided)
- Price validation (positive numbers, R50-R5000 range)
- Package deal validation using AI
- Retry logic (max 3 attempts for invalid input)
- Friendly, helpful error messages
- vCard edge case handling
- Comprehensive logging
"""

from typing import Dict, Tuple, Optional, List
import re
from utils.logger import log_info, log_error, log_warning, log_debug
from services.openai_service import get_openai_response


class ClientAdditionValidator:
    """Handles comprehensive validation for client addition flow"""

    # Constants
    MAX_RETRY_ATTEMPTS = 3
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 100
    MIN_PRICE = 50
    MAX_PRICE = 5000

    # SA phone number patterns
    SA_PHONE_PATTERNS = {
        'with_plus': re.compile(r'^\+27\d{9}$'),  # +27730564882
        'without_plus': re.compile(r'^27\d{9}$'),  # 27730564882
        'with_zero': re.compile(r'^0\d{9}$'),      # 0730564882
    }

    # Email pattern (basic but effective)
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def __init__(self):
        """Initialize the validator"""
        self.retry_counts = {}  # Track retry attempts per user per field
        log_info("ClientAdditionValidator initialized")

    # ==================== PHONE NUMBER VALIDATION ====================

    def validate_phone_number(self, phone: str, user_id: str = None) -> Tuple[bool, str, Optional[str]]:
        """
        Validate South African phone number format.

        Args:
            phone: Phone number to validate
            user_id: User ID for retry tracking (optional)

        Returns:
            Tuple of (is_valid, error_message, cleaned_phone)
            - is_valid: True if valid, False otherwise
            - error_message: Friendly error message if invalid, empty string if valid
            - cleaned_phone: Cleaned phone number in format 27XXXXXXXXX, or None if invalid
        """
        try:
            log_debug(f"Validating phone number: {phone}")

            # Check if empty
            if not phone or not phone.strip():
                error_msg = (
                    "📱 Oops! You didn't enter a phone number.\n\n"
                    "Please provide the client's WhatsApp number."
                )
                return False, error_msg, None

            # Clean the phone number
            cleaned = self._clean_phone_number(phone)

            # Check if it's all digits after cleaning
            if not cleaned.isdigit():
                error_msg = self._get_phone_error_message(phone, user_id, "non_digit")
                return False, error_msg, None

            # Validate length
            if len(cleaned) < 10:
                error_msg = self._get_phone_error_message(phone, user_id, "too_short")
                return False, error_msg, None

            if len(cleaned) > 15:
                error_msg = self._get_phone_error_message(phone, user_id, "too_long")
                return False, error_msg, None

            # Check if it's a valid SA number format
            is_valid_format = False
            normalized_phone = None

            # Try to normalize to SA format (27XXXXXXXXX)
            if len(cleaned) == 10 and cleaned.startswith('0'):
                # Format: 0730564882 -> 27730564882
                normalized_phone = '27' + cleaned[1:]
                is_valid_format = True
            elif len(cleaned) == 11 and cleaned.startswith('27'):
                # Format: 27730564882 (already correct)
                normalized_phone = cleaned
                is_valid_format = True
            elif len(cleaned) == 9:
                # Format: 730564882 -> 27730564882
                normalized_phone = '27' + cleaned
                is_valid_format = True
            else:
                # Check if it has +27 prefix with correct length
                original = phone.strip()
                if original.startswith('+27') and len(cleaned) == 11:
                    normalized_phone = cleaned
                    is_valid_format = True

            if not is_valid_format or not normalized_phone:
                error_msg = self._get_phone_error_message(phone, user_id, "invalid_format")
                return False, error_msg, None

            # Validate it's a mobile number (SA mobile numbers start with certain prefixes)
            # SA mobile prefixes: 6, 7, 8 (after country code)
            mobile_prefix = normalized_phone[2]  # Third digit after '27'
            if mobile_prefix not in ['6', '7', '8']:
                error_msg = (
                    "📱 Hmm, that doesn't look like a South African mobile number.\n\n"
                    "SA mobile numbers usually start with 06, 07, or 08.\n\n"
                    "*Examples:*\n"
                    "• 0730564882\n"
                    "• +27730564882\n"
                    "• 27730564882"
                )
                log_warning(f"Invalid SA mobile prefix: {phone} -> {normalized_phone}")
                return False, error_msg, None

            log_info(f"Phone number validated successfully: {phone} -> {normalized_phone}")

            # Reset retry count on success
            if user_id:
                self._reset_retry_count(user_id, 'phone')

            return True, "", normalized_phone

        except Exception as e:
            log_error(f"Error validating phone number: {str(e)}")
            error_msg = (
                "❌ Oops! Something went wrong while checking that phone number.\n\n"
                "Please try again."
            )
            return False, error_msg, None

    def _clean_phone_number(self, phone: str) -> str:
        """Remove all non-digit characters from phone number"""
        return re.sub(r'[^\d]', '', phone.strip())

    def _get_phone_error_message(self, phone: str, user_id: str, error_type: str) -> str:
        """
        Generate friendly, helpful error message for phone validation.
        Includes retry count and examples.
        """
        # Track retry count
        retry_count = 0
        if user_id:
            retry_count = self._increment_retry_count(user_id, 'phone')

        log_warning(f"Phone validation error ({error_type}): {phone} | Attempt {retry_count}/{self.MAX_RETRY_ATTEMPTS}")

        # Base error messages by type
        error_messages = {
            'non_digit': (
                "📱 That doesn't look quite right!\n\n"
                "Please enter only numbers (spaces, dashes, and + are okay)."
            ),
            'too_short': (
                "📱 That number seems too short!\n\n"
                "SA phone numbers have 10 digits (starting with 0) or 11 digits (starting with 27)."
            ),
            'too_long': (
                "📱 That number seems too long!\n\n"
                "SA phone numbers have 10 digits (starting with 0) or 11 digits (starting with 27)."
            ),
            'invalid_format': (
                "📱 Hmm, I'm having trouble with that format.\n\n"
                "Please try one of these South African formats:"
            )
        }

        base_message = error_messages.get(error_type, error_messages['invalid_format'])

        # Add examples
        examples = (
            "\n\n*Valid formats:*\n"
            "• 0730564882\n"
            "• +27730564882\n"
            "• 27730564882\n"
            "• 073 056 4882\n"
            "• +27 73 056 4882"
        )

        message = base_message + examples

        # Add retry count info
        if retry_count > 0:
            attempts_left = self.MAX_RETRY_ATTEMPTS - retry_count
            if attempts_left > 0:
                message += f"\n\n💡 *Attempts remaining:* {attempts_left}"
            else:
                message += (
                    "\n\n⚠️ *Maximum attempts reached!*\n"
                    "Type */stop* to cancel, or */start-over* to try again from the beginning."
                )

        return message

    # ==================== NAME VALIDATION ====================

    def validate_name(self, name: str, user_id: str = None) -> Tuple[bool, str]:
        """
        Validate client name.

        Args:
            name: Name to validate
            user_id: User ID for retry tracking (optional)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            log_debug(f"Validating name: {name}")

            # Check if empty
            if not name or not name.strip():
                error_msg = (
                    "✍️ Oops! You didn't enter a name.\n\n"
                    "Please provide your client's full name."
                )
                return False, error_msg

            cleaned_name = name.strip()

            # Check minimum length
            if len(cleaned_name) < self.MIN_NAME_LENGTH:
                error_msg = (
                    f"✍️ That name seems too short!\n\n"
                    f"Please enter at least {self.MIN_NAME_LENGTH} characters.\n\n"
                    f"💡 *Tip:* Use the client's full name (e.g., 'John Smith')"
                )
                log_warning(f"Name too short: {name} ({len(cleaned_name)} chars)")
                return False, error_msg

            # Check maximum length
            if len(cleaned_name) > self.MAX_NAME_LENGTH:
                error_msg = (
                    f"✍️ That name is too long!\n\n"
                    f"Please keep it under {self.MAX_NAME_LENGTH} characters.\n\n"
                    f"💡 *Tip:* Use first and last name only"
                )
                log_warning(f"Name too long: {name} ({len(cleaned_name)} chars)")
                return False, error_msg

            # Check if name contains at least some letters
            if not re.search(r'[a-zA-Z]', cleaned_name):
                error_msg = (
                    "✍️ Hmm, that doesn't look like a name.\n\n"
                    "Please use letters for the name.\n\n"
                    "*Example:* John Smith"
                )
                log_warning(f"Name has no letters: {name}")
                return False, error_msg

            # Check if name has excessive numbers (more than 2)
            digit_count = sum(c.isdigit() for c in cleaned_name)
            if digit_count > 2:
                error_msg = (
                    "✍️ That looks unusual for a name!\n\n"
                    "Names should mostly contain letters.\n\n"
                    "*Example:* John Smith Jr."
                )
                log_warning(f"Name has too many digits: {name} ({digit_count} digits)")
                return False, error_msg

            log_info(f"Name validated successfully: {name}")

            # Reset retry count on success
            if user_id:
                self._reset_retry_count(user_id, 'name')

            return True, ""

        except Exception as e:
            log_error(f"Error validating name: {str(e)}")
            error_msg = (
                "❌ Oops! Something went wrong while checking that name.\n\n"
                "Please try again."
            )
            return False, error_msg

    # ==================== EMAIL VALIDATION ====================

    def validate_email(self, email: str, required: bool = False, user_id: str = None) -> Tuple[bool, str]:
        """
        Validate email address.

        Args:
            email: Email to validate
            required: Whether email is required
            user_id: User ID for retry tracking (optional)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            log_debug(f"Validating email: {email} (required={required})")

            # Check if empty
            if not email or not email.strip():
                if required:
                    error_msg = (
                        "📧 Oops! You didn't enter an email address.\n\n"
                        "Please provide your client's email."
                    )
                    return False, error_msg
                else:
                    # Optional field - allow empty/skip
                    return True, ""

            cleaned_email = email.strip().lower()

            # Allow 'skip' for optional fields
            if cleaned_email in ['skip', 'none', 'n/a', 'na'] and not required:
                log_info(f"Email skipped by user")
                return True, ""

            # Check basic format
            if '@' not in cleaned_email:
                error_msg = (
                    "📧 Hmm, that doesn't look like an email address.\n\n"
                    "Email addresses need an @ symbol.\n\n"
                    "*Example:* john@gmail.com"
                )
                log_warning(f"Email missing @ symbol: {email}")
                return False, error_msg

            # Check for domain
            parts = cleaned_email.split('@')
            if len(parts) != 2:
                error_msg = (
                    "📧 That email format looks unusual.\n\n"
                    "Please use this format: name@domain.com\n\n"
                    "*Example:* john.smith@gmail.com"
                )
                log_warning(f"Email has multiple @ symbols: {email}")
                return False, error_msg

            local_part, domain = parts

            # Check if parts are not empty
            if not local_part or not domain:
                error_msg = (
                    "📧 That email seems incomplete.\n\n"
                    "Please provide a complete email address.\n\n"
                    "*Example:* john@example.com"
                )
                log_warning(f"Email has empty parts: {email}")
                return False, error_msg

            # Check domain has a dot
            if '.' not in domain:
                error_msg = (
                    "📧 That domain doesn't look quite right.\n\n"
                    "Email domains need a dot (e.g., gmail.com, yahoo.co.za)\n\n"
                    "*Examples:*\n"
                    "• john@gmail.com\n"
                    "• sarah@company.co.za"
                )
                log_warning(f"Email domain missing dot: {email}")
                return False, error_msg

            # Use regex for more thorough validation
            if not self.EMAIL_PATTERN.match(cleaned_email):
                error_msg = (
                    "📧 That email format isn't quite right.\n\n"
                    "Please check for typos and try again.\n\n"
                    "*Valid formats:*\n"
                    "• john@gmail.com\n"
                    "• sarah.jones@company.co.za\n"
                    "• mike_smith123@yahoo.com"
                )
                log_warning(f"Email failed regex validation: {email}")
                return False, error_msg

            log_info(f"Email validated successfully: {email}")

            # Reset retry count on success
            if user_id:
                self._reset_retry_count(user_id, 'email')

            return True, ""

        except Exception as e:
            log_error(f"Error validating email: {str(e)}")
            error_msg = (
                "❌ Oops! Something went wrong while checking that email.\n\n"
                "Please try again."
            )
            return False, error_msg

    # ==================== PRICE VALIDATION ====================

    def validate_price(self, price_str: str, user_id: str = None) -> Tuple[bool, str, Optional[float]]:
        """
        Validate price per session.

        Args:
            price_str: Price as string
            user_id: User ID for retry tracking (optional)

        Returns:
            Tuple of (is_valid, error_message, price_float)
        """
        try:
            log_debug(f"Validating price: {price_str}")

            # Check if empty
            if not price_str or not price_str.strip():
                error_msg = (
                    "💰 Oops! You didn't enter a price.\n\n"
                    "Please provide the price per session in Rands.\n\n"
                    "*Example:* 300"
                )
                return False, error_msg, None

            # Clean the price string (remove R, r, spaces, commas)
            cleaned = price_str.strip().upper()
            cleaned = cleaned.replace('R', '').replace(',', '').replace(' ', '').strip()

            # Try to convert to float
            try:
                price_value = float(cleaned)
            except ValueError:
                error_msg = (
                    "💰 Hmm, that doesn't look like a valid price.\n\n"
                    "Please enter a number (Rands).\n\n"
                    "*Examples:*\n"
                    "• 300\n"
                    "• R350\n"
                    "• 250.50"
                )
                log_warning(f"Price not a valid number: {price_str}")
                return False, error_msg, None

            # Check if positive
            if price_value <= 0:
                error_msg = (
                    "💰 Price must be greater than zero!\n\n"
                    "Please enter a positive amount.\n\n"
                    "*Example:* 300"
                )
                log_warning(f"Price not positive: {price_str} -> {price_value}")
                return False, error_msg, None

            # Check reasonable range (R50 - R5000)
            if price_value < self.MIN_PRICE:
                error_msg = (
                    f"💰 That price seems quite low!\n\n"
                    f"We recommend at least R{self.MIN_PRICE} per session.\n\n"
                    f"💡 *Tip:* This helps maintain quality training services.\n\n"
                    f"Please enter a price of at least R{self.MIN_PRICE}."
                )
                log_warning(f"Price below minimum: {price_str} -> {price_value}")
                return False, error_msg, None

            if price_value > self.MAX_PRICE:
                error_msg = (
                    f"💰 Wow, that's quite high!\n\n"
                    f"Our system supports prices up to R{self.MAX_PRICE} per session.\n\n"
                    f"💡 *Tip:* For premium packages, consider using package deals.\n\n"
                    f"Please enter a price under R{self.MAX_PRICE}."
                )
                log_warning(f"Price above maximum: {price_str} -> {price_value}")
                return False, error_msg, None

            # Round to 2 decimal places
            price_value = round(price_value, 2)

            log_info(f"Price validated successfully: {price_str} -> R{price_value}")

            # Reset retry count on success
            if user_id:
                self._reset_retry_count(user_id, 'price')

            return True, "", price_value

        except Exception as e:
            log_error(f"Error validating price: {str(e)}")
            error_msg = (
                "❌ Oops! Something went wrong while checking that price.\n\n"
                "Please try again."
            )
            return False, error_msg, None

    # ==================== PACKAGE DEAL VALIDATION ====================

    def validate_package_deal(self, package_description: str, price_per_session: float) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate package deal using AI to check if structure makes sense.

        Args:
            package_description: Description of the package deal
            price_per_session: Base price per session

        Returns:
            Tuple of (is_valid, error_message, parsed_package_info)
        """
        try:
            log_debug(f"Validating package deal: {package_description}")

            # Check if empty
            if not package_description or not package_description.strip():
                error_msg = (
                    "📦 Please describe your package deal.\n\n"
                    "*Example:* 10 sessions for R2500 (save R500)"
                )
                return False, error_msg, None

            # Use AI to validate and parse the package deal
            prompt = f"""
You are validating a fitness trainer's package deal offer. Analyze if the package makes business sense.

Base price per session: R{price_per_session}
Package description: "{package_description}"

Check:
1. Does it mention number of sessions?
2. Does it mention a total price or discount?
3. Does the package offer value (discount or benefit) to the client?
4. Is the math reasonable (not too good to be true, not worse than regular pricing)?

Respond in JSON format:
{{
    "is_valid": true/false,
    "reason": "brief explanation",
    "extracted_sessions": number or null,
    "extracted_price": number or null,
    "discount_percentage": number or null,
    "friendly_error": "user-friendly error message if invalid, or empty if valid"
}}

Be helpful - if it's close to valid but missing info, mark invalid and ask for clarification in friendly_error.
"""

            response = get_openai_response(prompt, max_tokens=300)

            if not response:
                # Fallback validation if AI fails
                log_warning("AI validation failed, using fallback validation")
                return self._fallback_package_validation(package_description, price_per_session)

            try:
                import json
                result = json.loads(response)

                is_valid = result.get('is_valid', False)

                if is_valid:
                    package_info = {
                        'description': package_description,
                        'sessions': result.get('extracted_sessions'),
                        'total_price': result.get('extracted_price'),
                        'discount_percentage': result.get('discount_percentage'),
                        'base_price_per_session': price_per_session
                    }
                    log_info(f"Package deal validated by AI: {package_info}")
                    return True, "", package_info
                else:
                    error_msg = result.get('friendly_error', (
                        "💡 I'm having trouble understanding that package deal.\n\n"
                        "Please include:\n"
                        "• Number of sessions\n"
                        "• Total price or discount amount\n\n"
                        "*Example:* 10 sessions for R2500 (save R500)"
                    ))
                    log_warning(f"Package deal validation failed: {result.get('reason')}")
                    return False, error_msg, None

            except json.JSONDecodeError:
                log_error(f"Failed to parse AI response as JSON: {response}")
                return self._fallback_package_validation(package_description, price_per_session)

        except Exception as e:
            log_error(f"Error validating package deal: {str(e)}")
            return self._fallback_package_validation(package_description, price_per_session)

    def _fallback_package_validation(self, package_description: str, price_per_session: float) -> Tuple[bool, str, Optional[Dict]]:
        """Fallback validation if AI is unavailable"""
        log_info("Using fallback package validation")

        # Basic checks for numbers
        numbers = re.findall(r'\d+', package_description)

        if len(numbers) < 2:
            error_msg = (
                "💡 Please include both:\n"
                "• Number of sessions\n"
                "• Total price\n\n"
                "*Example:* 10 sessions for R2500"
            )
            return False, error_msg, None

        # Assume valid if has reasonable structure
        package_info = {
            'description': package_description,
            'sessions': None,
            'total_price': None,
            'discount_percentage': None,
            'base_price_per_session': price_per_session,
            'validated_by': 'fallback'
        }

        log_info(f"Package deal validated by fallback: {package_info}")
        return True, "", package_info

    # ==================== vCARD EDGE CASE HANDLING ====================

    def handle_vcard_edge_cases(self, vcard_data: Dict) -> Dict:
        """
        Handle edge cases in vCard data and return appropriate prompts.

        Args:
            vcard_data: Parsed vCard data

        Returns:
            Dict with:
            - status: 'valid', 'missing_phone', 'multiple_phones', 'missing_name'
            - message: User-friendly message
            - data: Cleaned/processed data
            - action_required: What action the user should take
        """
        try:
            log_debug(f"Handling vCard edge cases: {vcard_data}")

            result = {
                'status': 'valid',
                'message': '',
                'data': vcard_data,
                'action_required': None
            }

            # Edge Case 1: Missing phone number
            phones = vcard_data.get('phones', [])
            if not phones or all(not p for p in phones):
                result['status'] = 'missing_phone'
                result['message'] = (
                    "📇 I got the contact, but there's no phone number!\n\n"
                    "Please provide your client's WhatsApp number manually.\n\n"
                    "*Example:* 0730564882"
                )
                result['action_required'] = 'ask_phone'
                log_warning(f"vCard missing phone number")
                return result

            # Edge Case 2: Multiple phone numbers
            if len(phones) > 1:
                result['status'] = 'multiple_phones'

                # Format phone options
                phone_list = '\n'.join([f"{i+1}. {phone}" for i, phone in enumerate(phones)])

                result['message'] = (
                    f"📇 This contact has {len(phones)} phone numbers:\n\n"
                    f"{phone_list}\n\n"
                    f"Which one is their WhatsApp number?\n\n"
                    f"Reply with the number (1, 2, etc.)"
                )
                result['action_required'] = 'choose_phone'
                result['data']['phone_options'] = phones
                log_info(f"vCard has {len(phones)} phone numbers, asking user to choose")
                return result

            # Edge Case 3: Missing or incomplete name
            name = vcard_data.get('name', '').strip()
            first_name = vcard_data.get('first_name', '').strip()
            last_name = vcard_data.get('last_name', '').strip()

            if not name and not first_name:
                result['status'] = 'missing_name'
                result['message'] = (
                    "📇 I got the contact, but there's no name!\n\n"
                    "Please provide your client's full name.\n\n"
                    "*Example:* John Smith"
                )
                result['action_required'] = 'ask_name'
                log_warning(f"vCard missing name")
                return result

            # If name is missing but we have parts, construct it
            if not name and (first_name or last_name):
                constructed_name = f"{first_name} {last_name}".strip()
                result['data']['name'] = constructed_name
                log_info(f"Constructed name from parts: {constructed_name}")

            # Edge Case 4: Phone number format validation
            phone = phones[0]
            is_valid, error_msg, cleaned_phone = self.validate_phone_number(phone)

            if not is_valid:
                result['status'] = 'invalid_phone'
                result['message'] = (
                    f"📇 I got the contact, but the phone number looks unusual:\n\n"
                    f"*From contact:* {phone}\n\n"
                    f"{error_msg}\n\n"
                    f"Please provide the correct WhatsApp number."
                )
                result['action_required'] = 'ask_phone'
                log_warning(f"vCard phone number invalid: {phone}")
                return result

            # Update with cleaned phone
            result['data']['phone'] = cleaned_phone
            result['data']['phones'] = [cleaned_phone]

            log_info(f"vCard data validated successfully")
            return result

        except Exception as e:
            log_error(f"Error handling vCard edge cases: {str(e)}")
            return {
                'status': 'error',
                'message': (
                    "❌ Sorry, I had trouble reading that contact.\n\n"
                    "Let's try adding the client manually instead.\n\n"
                    "Please provide their WhatsApp number."
                ),
                'data': {},
                'action_required': 'ask_phone'
            }

    # ==================== RETRY LOGIC ====================

    def _increment_retry_count(self, user_id: str, field: str) -> int:
        """Increment and return retry count for a user's field"""
        key = f"{user_id}_{field}"
        if key not in self.retry_counts:
            self.retry_counts[key] = 0
        self.retry_counts[key] += 1
        return self.retry_counts[key]

    def _reset_retry_count(self, user_id: str, field: str):
        """Reset retry count for a user's field"""
        key = f"{user_id}_{field}"
        if key in self.retry_counts:
            del self.retry_counts[key]
            log_debug(f"Reset retry count for {key}")

    def get_retry_count(self, user_id: str, field: str) -> int:
        """Get current retry count for a user's field"""
        key = f"{user_id}_{field}"
        return self.retry_counts.get(key, 0)

    def has_exceeded_max_retries(self, user_id: str, field: str) -> bool:
        """Check if user has exceeded maximum retry attempts"""
        return self.get_retry_count(user_id, field) >= self.MAX_RETRY_ATTEMPTS

    def get_restart_prompt(self, field: str) -> str:
        """Get friendly prompt for when user exceeds max retries"""
        return (
            f"😔 I see you're having trouble with the {field}.\n\n"
            f"*Options:*\n"
            f"• Type */stop* to cancel this process\n"
            f"• Type */start-over* to begin again from scratch\n"
            f"• Try entering the {field} one more time\n\n"
            f"💡 Need help? Make sure you're following the format shown in the examples!"
        )

    # ==================== UTILITY METHODS ====================

    def format_validation_summary(self, validated_data: Dict) -> str:
        """
        Format a friendly summary of validated client data.

        Args:
            validated_data: Dict of validated client information

        Returns:
            Formatted string summary
        """
        try:
            summary = "📋 *Client Information Summary*\n\n"

            if 'name' in validated_data:
                summary += f"*Name:* {validated_data['name']}\n"

            if 'phone' in validated_data:
                # Format phone number nicely
                phone = validated_data['phone']
                if len(phone) == 11 and phone.startswith('27'):
                    formatted_phone = f"+{phone[:2]} {phone[2:5]} {phone[5:8]} {phone[8:]}"
                else:
                    formatted_phone = phone
                summary += f"*Phone:* {formatted_phone}\n"

            if 'email' in validated_data and validated_data['email']:
                summary += f"*Email:* {validated_data['email']}\n"

            if 'price' in validated_data:
                price = validated_data['price']
                summary += f"*Price per session:* R{price:.2f}\n"

            if 'package_deal' in validated_data and validated_data['package_deal']:
                package = validated_data['package_deal']
                summary += f"*Package:* {package.get('description', 'Custom package')}\n"

            summary += "\n✅ Everything looks good!"

            return summary

        except Exception as e:
            log_error(f"Error formatting validation summary: {str(e)}")
            return "✅ Client information validated!"


# Singleton instance
_validator_instance = None

def get_validator() -> ClientAdditionValidator:
    """Get singleton validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ClientAdditionValidator()
    return _validator_instance
