"""Validation helper functions"""
import re
from typing import Optional

class ValidationHelpers:
    """Helper functions for input validation"""
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    def normalize_phone_number(self, phone: str) -> Optional[str]:
        """Normalize phone number to format WITHOUT + prefix (for tests)"""
        if not phone:
            return None
        
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Handle different formats
        if len(digits) == 10 and digits.startswith('0'):
            # Local format: 0821234567 -> 27821234567
            return '27' + digits[1:]
        elif len(digits) == 11 and digits.startswith('27'):
            # International format: 27821234567
            return digits
        elif len(digits) == 9:
            # Missing leading 0: 821234567 -> 27821234567
            return '27' + digits
        elif len(digits) == 12 and digits.startswith('27'):
            # With country code prefix: +27821234567 -> 27821234567
            return digits
        
        # Return WITHOUT the + prefix (tests expect this)
        return digits if digits else None
    
    def format_phone_number(self, phone: str) -> Optional[str]:
        """Format and validate South African phone number (legacy method)"""
        # Just call normalize_phone_number for consistency
        return self.normalize_phone_number(phone)
    
    def extract_price(self, text: str) -> Optional[float]:
        """Extract price from text - handles South African currency formats"""
        # Clean the input
        text = str(text).strip()
        
        # Remove currency indicators (R, Rands, ZAR, etc.)
        text = re.sub(r'(?i)\b(rands?|zar)\b', '', text)  # Remove word "rand/rands/ZAR"
        text = re.sub(r'[Rr](?![a-zA-Z])', '', text)  # Remove R symbol (but not if part of word)
        text = re.sub(r'[,$]', '', text)  # Remove commas and dollar signs
        text = re.sub(r'(?i)per\s+(session|hour|class|month)', '', text)  # Remove "per session" etc
        
        # Clean up spaces
        text = text.strip()
        
        # Find numbers (including decimals)
        numbers = re.findall(r'\d+(?:\.\d{1,2})?', text)
        
        if numbers:
            try:
                price = float(numbers[0])
                # Sanity check for reasonable training prices
                if 0 < price < 10000:  # More reasonable upper limit
                    return price
            except ValueError:
                pass
        
        return None
    
    def validate_date(self, date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        # Check if valid date
        try:
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def validate_time(self, time_str: str) -> bool:
        """Validate time format (HH:MM or informal like 9am)"""
        # First try HH:MM format
        pattern_24hr = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        if re.match(pattern_24hr, time_str.strip()):
            return True
        
        # Also accept informal formats like 9am, 2:30pm
        return self.validate_time_format(time_str)
    
    def validate_time_format(self, time_str: str) -> bool:
        """Validate various time formats (9am, 14:00, 2:30pm, etc)"""
        patterns = [
            r'^\d{1,2}(am|pm)$',  # 9am, 10pm
            r'^\d{1,2}:\d{2}(am|pm)?$',  # 9:00, 14:30, 9:00am
            r'^\d{1,2}\s*(am|pm)$',  # 9 am, 10 pm (with space)
        ]
        
        time_lower = time_str.lower().strip()
        for pattern in patterns:
            if re.match(pattern, time_lower):
                return True
        return False
    
    def parse_time(self, time_str: str) -> Optional[str]:
        """Parse various time formats to HH:MM format"""
        time_lower = time_str.lower().strip()
        
        # Handle formats like "9am", "10pm"
        match = re.match(r'^(\d{1,2})(am|pm)$', time_lower)
        if match:
            hour = int(match.group(1))
            is_pm = match.group(2) == 'pm'
            
            if is_pm and hour != 12:
                hour += 12
            elif not is_pm and hour == 12:
                hour = 0
            
            return f"{hour:02d}:00"
        
        # Handle formats like "9:30am", "2:45pm"
        match = re.match(r'^(\d{1,2}):(\d{2})(am|pm)?$', time_lower)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            is_pm = match.group(3) == 'pm' if match.group(3) else hour >= 12
            
            if match.group(3):  # If am/pm specified
                if is_pm and hour != 12:
                    hour += 12
                elif not is_pm and hour == 12:
                    hour = 0
            
            return f"{hour:02d}:{minute:02d}"
        
        # Return as-is if already in HH:MM format
        if re.match(r'^\d{2}:\d{2}$', time_str):
            return time_str
        
        return None
    
    def sanitize_input(self, text: str) -> str:
        """Basic input sanitization"""
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        # Limit length
        text = text[:1000]
        # Strip whitespace
        text = text.strip()
        return text
    
    def is_empty_or_skip(self, text: str) -> bool:
        """Check if user wants to skip a field"""
        skip_words = ['skip', 'none', 'na', 'n/a', '-', '--', 'nil', 'nothing']
        return text.lower().strip() in skip_words or len(text.strip()) == 0
