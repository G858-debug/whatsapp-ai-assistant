"""Validation helper functions"""
import re
from typing import Optional

class ValidationHelpers:
    """Helper functions for input validation"""
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    def format_phone_number(self, phone: str) -> Optional[str]:
        """Format and validate South African phone number"""
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
            # With country code prefix: +27821234567
            return digits[2:] if digits.startswith('27') else None
        
        return None
    
    def extract_price(self, text: str) -> Optional[float]:
        """Extract price from text"""
        # Remove currency symbols and text
        text = re.sub(r'[Rr](?:and)?s?\.?', '', text)
        text = re.sub(r'per\s+(session|hour|class|month)', '', text, flags=re.IGNORECASE)
        
        # Find numbers (including decimals)
        numbers = re.findall(r'\d+(?:\.\d{2})?', text)
        
        if numbers:
            try:
                price = float(numbers[0])
                # Sanity check for reasonable prices
                if 0 < price < 10000:
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
        """Validate time format (HH:MM)"""
        pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        return bool(re.match(pattern, time_str.strip()))
    
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