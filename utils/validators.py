"""Validation utilities for Refiloe"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, date
import re
import pytz

class Validators:
    """Data validation utilities"""
    
    def __init__(self, config=None):
        self.config = config
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    # ============= PHONE VALIDATION =============
    
    def normalize_phone_number(phone):
        """Normalize phone number to format WITHOUT + prefix for tests"""
        if not phone:
            return None
        
        # Remove all non-digit characters including +
        phone = ''.join(filter(str.isdigit, str(phone)))
        
        # Handle South African numbers
        if phone.startswith('0'):
            phone = '27' + phone[1:]
        elif not phone.startswith('27') and len(phone) == 9:
            phone = '27' + phone
        
        # Return WITHOUT the + prefix (tests expect this format)
        return phone  # Not '+' + phone
    
    def validate_phone_number(self, phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate South African phone number
        
        Returns:
            Tuple of (is_valid, formatted_number, error_message)
        """
        if not phone:
            return False, None, "Phone number is required"
        
        # Remove all non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        
        # Check for valid South African mobile number patterns
        valid_prefixes = ['60', '61', '62', '63', '64', '65', '66', '67', '68', '69',
                         '71', '72', '73', '74', '76', '78', '79',
                         '81', '82', '83', '84', '85']
        
        # International format (27XXXXXXXXX)
        if phone_digits.startswith('27'):
            if len(phone_digits) != 11:
                return False, None, "Invalid phone number length"
            
            prefix = phone_digits[2:4]
            if prefix not in valid_prefixes:
                return False, None, "Invalid mobile number prefix"
            
            return True, phone_digits, None
        
        # Local format (0XXXXXXXXX)
        elif phone_digits.startswith('0'):
            if len(phone_digits) != 10:
                return False, None, "Invalid phone number length"
            
            prefix = phone_digits[1:3]
            if prefix not in valid_prefixes:
                return False, None, "Invalid mobile number prefix"
            
            return True, f"27{phone_digits[1:]}", None
        
        # Without leading 0 (XXXXXXXXX)
        elif len(phone_digits) == 9:
            prefix = phone_digits[0:2]
            if prefix not in valid_prefixes:
                return False, None, "Invalid mobile number prefix"
            
            return True, phone_digits, None
        
        return False, None, "Invalid South African phone number format"
    
    # ============= EMAIL VALIDATION =============
    
    def validate_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email address
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"
        
        # RFC 5322 compliant email regex (simplified)
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        email = email.strip().lower()
        
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        # Check for common typos
        if email.endswith('.con') or email.endswith('.cpm'):
            return False, "Invalid email domain (did you mean .com?)"
        
        # Check length
        if len(email) > 254:  # RFC 5321
            return False, "Email address too long"
        
        return True, None
    
    # ============= NAME VALIDATION =============
    
    def validate_name(self, name: str, field_name: str = "Name") -> Tuple[bool, Optional[str]]:
        """
        Validate person's name
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name or not name.strip():
            return False, f"{field_name} is required"
        
        name = name.strip()
        
        # Check length
        if len(name) < 2:
            return False, f"{field_name} is too short"
        
        if len(name) > 100:
            return False, f"{field_name} is too long"
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-\'\.]+$", name):
            return False, f"{field_name} contains invalid characters"
        
        # Check for excessive spaces
        if '  ' in name:
            return False, f"{field_name} contains excessive spaces"
        
        return True, None
    
    # ============= DATE/TIME VALIDATION =============
    
    def validate_date(self, date_str: str, 
                     min_date: Optional[date] = None,
                     max_date: Optional[date] = None) -> Tuple[bool, Optional[date], Optional[str]]:
        """
        Validate date string
        
        Returns:
            Tuple of (is_valid, parsed_date, error_message)
        """
        if not date_str:
            return False, None, "Date is required"
        
        # Try to parse the date
        try:
            if isinstance(date_str, date):
                parsed_date = date_str
            else:
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return False, None, "Invalid date format (use YYYY-MM-DD)"
        
        # Check bounds
        if min_date and parsed_date < min_date:
            return False, None, f"Date cannot be before {min_date}"
        
        if max_date and parsed_date > max_date:
            return False, None, f"Date cannot be after {max_date}"
        
        return True, parsed_date, None
    
    def validate_time(self, time_str: str,
                     min_time: Optional[str] = None,
                     max_time: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate and parse time string into standard format
        Returns: (is_valid, formatted_time, error_message)
        """
        import re
        from datetime import datetime
        
        if not time_str:
            return False, None, "Time is required"
        
        # Clean and normalize the input
        original = time_str
        time_str = time_str.strip()

        print(f"DEBUG 1: Checking '{time_str}'")  # ADD THIS FOR DEBUGGING
        
        # Handle special case: "9am" or "9pm" (no space, no colon)
        simple_am_pm = re.match(r'^(\d{1,2})(am|pm)$', time_str.lower())
        print(f"DEBUG 2: simple_am_pm match = {simple_am_pm}")  # ADD THIS FOR DEBUGGING
        print(f"DEBUG 3: bool(simple_am_pm) = {bool(simple_am_pm)}")  # ADD THIS FOR DEBUGGING
                         
        if simple_am_pm:
            print(f"DEBUG 4: Inside if block!")  # ADD THIS FOR DEBUGGING
            hour = int(simple_am_pm.group(1))
            is_pm = simple_am_pm.group(2) == 'pm'
            print(f"DEBUG 5: hour={hour}, is_pm={is_pm}")  # ADD THIS FOR DEBUGGING
            
            # Convert to 24-hour format
            if is_pm and hour != 12:
                hour += 12
            elif not is_pm and hour == 12:
                hour = 0
                
            formatted = f"{hour:02d}:00"
            print(f"DEBUG 6: formatted={formatted}")  # ADD THIS FOR DEBUGGING
            
            # Check bounds
            if min_time and formatted < min_time:
                print(f"DEBUG 7: Failed min_time check")  # ADD THIS FOR DEBUGGING
                return False, None, f"Time cannot be before {min_time}"
            if max_time and formatted > max_time:
                print(f"DEBUG 8: Failed max_time check")  # ADD THIS FOR DEBUGGING
                return False, None, f"Time cannot be after {max_time}"

            print(f"DEBUG 9: Returning True, {formatted}, None")  # ADD THIS FOR DEBUGGING
            return True, formatted, None

        print(f"DEBUG 10: simple_am_pm did not match, continuing...")  # ADD THIS FOR DEBUGGING
        
        # Handle "9 am" or "9 pm" or "9 AM" or "9 PM" (with space, any case)
        space_am_pm = re.match(r'^(\d{1,2})\s+(am|pm)$', time_str.lower())
        if space_am_pm:
            hour = int(space_am_pm.group(1))
            is_pm = space_am_pm.group(2) == 'pm'
            
            if is_pm and hour != 12:
                hour += 12
            elif not is_pm and hour == 12:
                hour = 0
                        
            formatted = f"{hour:02d}:00"
            
            # Check bounds
            if min_time and formatted < min_time:
                return False, None, f"Time cannot be before {min_time}"
            if max_time and formatted > max_time:
                return False, None, f"Time cannot be after {max_time}"
                
            return True, formatted, None
        
        # Handle "9 o'clock"
        oclock = re.match(r'^(\d{1,2})\s*o[\'']?clock$', time_str.lower())
        if oclock:
            hour = int(oclock.group(1))
            
            formatted = f"{hour:02d}:00"
            
            # Check bounds
            if min_time and formatted < min_time:
                return False, None, f"Time cannot be before {min_time}"
            if max_time and formatted > max_time:
                return False, None, f"Time cannot be after {max_time}"
                
            return True, formatted, None
        
        # Try standard datetime parsing for other formats (9:00, 09:00, 9:00am, etc.)
        formats_to_try = [
            '%H:%M',      # 14:30, 09:00
            '%H:%M:%S',   # 14:30:00
            '%I:%M %p',   # 2:30 PM
            '%I:%M%p',    # 2:30PM
            '%I:%M %P',   # 2:30 pm
            '%I:%M%P',    # 2:30pm
        ]
        
        for fmt in formats_to_try:
            try:
                # Try both original case and uppercase for AM/PM
                for test_str in [time_str, time_str.upper(), time_str.lower()]:
                    try:
                        parsed_time = datetime.strptime(test_str, fmt)
                        formatted = parsed_time.strftime('%H:%M')
                        
                        # Check bounds
                        if min_time and formatted < min_time:
                            return False, None, f"Time cannot be before {min_time}"
                        if max_time and formatted > max_time:
                            return False, None, f"Time cannot be after {max_time}"
                        
                        return True, formatted, None
                    except ValueError:
                        continue
            except:
                continue
        
        return False, None, "Invalid time format"

    def validate_time_format(self, time_str: str) -> tuple:
        """
        Validate time format (wrapper for validate_time)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        from typing import Tuple, Optional
        is_valid, formatted_time, error = self.validate_time(time_str)
        return is_valid, error
    
    def validate_business_hours(self, time_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that time is within business hours
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        is_valid, formatted_time, error = self.validate_time(time_str)
        
        if not is_valid:
            return False, error
        
        # Check if within business hours (6:00 - 20:00)
        hour = int(formatted_time.split(':')[0])
        
        if hour < 6 or hour >= 20:
            return False, "Time must be between 6:00 AM and 8:00 PM"
        
        return True, None
    
    # ============= AMOUNT VALIDATION =============
    
    def validate_amount(self, amount: Any,
                       min_amount: float = 0,
                       max_amount: float = 100000) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Validate currency amount
        
        Returns:
            Tuple of (is_valid, parsed_amount, error_message)
        """
        if amount is None or amount == '':
            return False, None, "Amount is required"
        
        # Convert to string and clean
        amount_str = str(amount)
        
        # Remove currency symbols and spaces
        amount_str = re.sub(r'[R$,\s]', '', amount_str)
        
        try:
            amount_float = float(amount_str)
        except ValueError:
            return False, None, "Invalid amount format"
        
        # Check bounds
        if amount_float < min_amount:
            return False, None, f"Amount cannot be less than R{min_amount}"
        
        if amount_float > max_amount:
            return False, None, f"Amount cannot exceed R{max_amount}"
        
        # Round to 2 decimal places
        amount_float = round(amount_float, 2)
        
        return True, amount_float, None
    
    # ============= PACKAGE VALIDATION =============
    
    def validate_package_type(self, package: str) -> Tuple[bool, Optional[str]]:
        """
        Validate training package type
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_packages = ['single', 'weekly_4', 'weekly_8', 'monthly_12', 'monthly_16']
        
        if not package:
            return False, "Package type is required"
        
        if package not in valid_packages:
            return False, f"Invalid package. Must be one of: {', '.join(valid_packages)}"
        
        return True, None
    
    # ============= SESSION VALIDATION =============
    
    def validate_session_type(self, session_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate session type
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_types = ['standard', 'assessment', 'consultation', 'group', 'online']
        
        if not session_type:
            return False, "Session type is required"
        
        if session_type not in valid_types:
            return False, f"Invalid session type. Must be one of: {', '.join(valid_types)}"
        
        return True, None
    
    # ============= HABIT VALIDATION =============
    
    def validate_habit_type(self, habit_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate habit tracking type
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_habits = [
            'water_intake', 'sleep_hours', 'steps', 'calories',
            'workout_completed', 'meals_logged', 'weight', 'mood'
        ]
        
        if not habit_type:
            return False, "Habit type is required"
        
        if habit_type not in valid_habits:
            return False, f"Invalid habit type. Must be one of: {', '.join(valid_habits)}"
        
        return True, None
    
    def validate_habit_value(self, habit_type: str, value: Any) -> Tuple[bool, Any, Optional[str]]:
        """
        Validate habit tracking value based on type
        
        Returns:
            Tuple of (is_valid, parsed_value, error_message)
        """
        if value is None or value == '':
            return False, None, "Value is required"
        
        try:
            if habit_type == 'water_intake':
                # Expect liters (0-10)
                val = float(value)
                if not 0 <= val <= 10:
                    return False, None, "Water intake must be between 0 and 10 liters"
                return True, val, None
            
            elif habit_type == 'sleep_hours':
                # Expect hours (0-24)
                val = float(value)
                if not 0 <= val <= 24:
                    return False, None, "Sleep hours must be between 0 and 24"
                return True, val, None
            
            elif habit_type == 'steps':
                # Expect integer (0-100000)
                val = int(value)
                if not 0 <= val <= 100000:
                    return False, None, "Steps must be between 0 and 100,000"
                return True, val, None
            
            elif habit_type == 'calories':
                # Expect integer (0-10000)
                val = int(value)
                if not 0 <= val <= 10000:
                    return False, None, "Calories must be between 0 and 10,000"
                return True, val, None
            
            elif habit_type == 'workout_completed':
                # Expect boolean (0 or 1)
                if str(value).lower() in ['yes', 'true', '1', 'done', 'completed']:
                    return True, 1, None
                elif str(value).lower() in ['no', 'false', '0', 'skip', 'missed']:
                    return True, 0, None
                return False, None, "Workout status must be yes/no"
            
            elif habit_type == 'weight':
                # Expect kg (20-300)
                val = float(value)
                if not 20 <= val <= 300:
                    return False, None, "Weight must be between 20 and 300 kg"
                return True, val, None
            
            elif habit_type == 'mood':
                # Expect 1-10 scale
                val = int(value)
                if not 1 <= val <= 10:
                    return False, None, "Mood must be between 1 and 10"
                return True, val, None
            
            else:
                # Default: accept as string
                return True, str(value), None
                
        except (ValueError, TypeError) as e:
            return False, None, f"Invalid value format for {habit_type}"
    
    # ============= PASSWORD VALIDATION =============
    
    def validate_password(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        if not password:
            return False, ["Password is required"]
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
        
        return len(issues) == 0, issues
    
    # ============= COMPOSITE VALIDATION =============
    
    def validate_booking_request(self, data: Dict) -> Tuple[bool, Dict[str, str]]:
        """
        Validate a complete booking request
        
        Returns:
            Tuple of (is_valid, dict_of_errors)
        """
        errors = {}
        
        # Validate date
        if 'session_date' in data:
            is_valid, parsed_date, error = self.validate_date(
                data['session_date'],
                min_date=datetime.now().date(),
                max_date=datetime.now().date() + timedelta(days=90)
            )
            if not is_valid:
                errors['session_date'] = error
        else:
            errors['session_date'] = "Session date is required"
        
        # Validate time
        if 'session_time' in data:
            is_valid, error = self.validate_business_hours(data['session_time'])
            if not is_valid:
                errors['session_time'] = error
        else:
            errors['session_time'] = "Session time is required"
        
        # Validate session type
        if 'session_type' in data:
            is_valid, error = self.validate_session_type(data['session_type'])
            if not is_valid:
                errors['session_type'] = error
        
        return len(errors) == 0, errors
    
    def validate_client_registration(self, data: Dict) -> Tuple[bool, Dict[str, str]]:
        """
        Validate client registration data
        
        Returns:
            Tuple of (is_valid, dict_of_errors)
        """
        errors = {}
        
        # Validate name
        if 'name' in data:
            is_valid, error = self.validate_name(data['name'])
            if not is_valid:
                errors['name'] = error
        else:
            errors['name'] = "Name is required"
        
        # Validate phone
        if 'phone' in data:
            is_valid, formatted, error = self.validate_phone_number(data['phone'])
            if not is_valid:
                errors['phone'] = error
        else:
            errors['phone'] = "Phone number is required"
        
        # Validate email (optional)
        if 'email' in data and data['email']:
            is_valid, error = self.validate_email(data['email'])
            if not is_valid:
                errors['email'] = error
        
        # Validate package
        if 'package' in data:
            is_valid, error = self.validate_package_type(data['package'])
            if not is_valid:
                errors['package'] = error
        
        return len(errors) == 0, errors
