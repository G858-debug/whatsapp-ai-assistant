"""Validation helper functions"""
import re
from typing import Dict, Optional, Tuple
from datetime import datetime, date
from utils.logger import log_info, log_error
from datetime import datetime, date, timedelta

class ValidationHelpers:
    """Helper functions for data validation"""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """Validate email format"""
        if not email:
            return False, "Email is required"
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email.strip()):
            return False, "Invalid email format"
        
        return True, None
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """Validate South African phone number"""
        if not phone:
            return False, "Phone number is required"
        
        # Remove all non-digits
        phone_digits = re.sub(r'\D', '', phone)
        
        # Check length
        if len(phone_digits) < 9:
            return False, "Phone number too short"
        
        if len(phone_digits) > 12:
            return False, "Phone number too long"
        
        # Check if it's a valid SA number
        if phone_digits.startswith('27'):
            if len(phone_digits) != 11:
                return False, "Invalid South African phone number"
        elif phone_digits.startswith('0'):
            if len(phone_digits) != 10:
                return False, "Invalid South African phone number"
        
        return True, None
    
    @staticmethod
    def validate_price(price_str: str) -> Tuple[bool, Optional[float], Optional[str]]:
        """Validate and parse price"""
        if not price_str:
            return False, None, "Price is required"
        
        # Extract numbers
        numbers = re.findall(r'\d+(?:\.\d{2})?', price_str)
        
        if not numbers:
            return False, None, "No valid price found"
        
        try:
            price = float(numbers[0])
            
            if price <= 0:
                return False, None, "Price must be greater than 0"
            
            if price > 10000:
                return False, None, "Price seems too high. Please check."
            
            return True, price, None
            
        except ValueError:
            return False, None, "Invalid price format"
    
    @staticmethod
    def validate_date(date_str: str) -> Tuple[bool, Optional[date], Optional[str]]:
        """Validate and parse date"""
        if not date_str:
            return False, None, "Date is required"
        
        # Try different date formats
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d %B %Y',
            '%d %b %Y'
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt).date()
                
                # Check if date is not in the past
                if parsed_date < date.today():
                    return False, None, "Date cannot be in the past"
                
                # Check if date is not too far in future (1 year)
                max_future = date.today() + timedelta(days=365)
                if parsed_date > max_future:
                    return False, None, "Date is too far in the future"
                
                return True, parsed_date, None
                
            except ValueError:
                continue
        
        return False, None, "Invalid date format. Use DD/MM/YYYY"
    
    @staticmethod
    def validate_time(time_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate and parse time"""
        if not time_str:
            return False, None, "Time is required"
        
        # Remove spaces and convert to lowercase
        time_str = time_str.strip().lower()
        
        # Handle am/pm format
        time_pattern = r'^(\d{1,2}):?(\d{2})?\s*(am|pm)?$'
        match = re.match(time_pattern, time_str)
        
        if not match:
            return False, None, "Invalid time format. Use HH:MM or HH:MM AM/PM"
        
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)
        
        # Convert to 24-hour format if AM/PM specified
        if period:
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
        
        # Validate hour and minute
        if hour < 0 or hour > 23:
            return False, None, "Invalid hour"
        
        if minute < 0 or minute > 59:
            return False, None, "Invalid minute"
        
        # Format as HH:MM
        formatted_time = f"{hour:02d}:{minute:02d}"
        
        return True, formatted_time, None
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 500) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remove potentially harmful characters (basic sanitization)
        # Keep alphanumeric, spaces, and common punctuation
        text = re.sub(r'[^\w\s\-.,!?@#()\'":/]', '', text)
        
        return text
