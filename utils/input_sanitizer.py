"""Input sanitization utilities"""
import re
from typing import Optional, Any
from utils.logger import log_warning

class InputSanitizer:
    """Sanitize user inputs for security"""
    
    def __init__(self, config):
        self.config = config
        self.max_length = 1000
        
        # Patterns to remove
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                 # JavaScript protocol
            r'on\w+\s*=',                  # Event handlers
            r'<iframe[^>]*>.*?</iframe>',  # Iframes
            r'DROP\s+TABLE',               # SQL injection
            r'DELETE\s+FROM',              # SQL injection
            r'INSERT\s+INTO',              # SQL injection
            r'UPDATE\s+SET',               # SQL injection
        ]
    
    def sanitize(self, text: Any) -> str:
        """
        Sanitize input text
        
        Args:
            text: Input text to sanitize
            
        Returns:
            Sanitized text string
        """
        if text is None:
            return ""
        
        # Convert to string
        text = str(text)
        
        # Truncate if too long
        if len(text) > self.max_length:
            text = text[:self.max_length]
            log_warning(f"Input truncated to {self.max_length} characters")
        
        # Remove dangerous patterns
        for pattern in self.dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove control characters except newlines
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def sanitize_phone(self, phone: str) -> Optional[str]:
        """
        Sanitize and validate phone number
        
        Args:
            phone: Phone number to sanitize
            
        Returns:
            Sanitized phone number or None if invalid
        """
        # Remove all non-digits
        phone = re.sub(r'\D', '', str(phone))
        
        # South African phone number validation
        if len(phone) == 10 and phone.startswith('0'):
            # Local format: 0821234567 -> 27821234567
            return '27' + phone[1:]
        elif len(phone) == 11 and phone.startswith('27'):
            # International format: 27821234567
            return phone
        elif len(phone) == 9:
            # Missing leading 0: 821234567 -> 27821234567
            return '27' + phone
        
        log_warning(f"Invalid phone number format: {phone}")
        return None
    
    def sanitize_email(self, email: str) -> Optional[str]:
        """
        Sanitize and validate email
        
        Args:
            email: Email to sanitize
            
        Returns:
            Sanitized email or None if invalid
        """
        email = str(email).strip().lower()
        
        # Basic email pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(pattern, email):
            return email
        
        log_warning(f"Invalid email format: {email}")
        return None
    
    def sanitize_name(self, name: str) -> str:
        """
        Sanitize name input
        
        Args:
            name: Name to sanitize
            
        Returns:
            Sanitized name
        """
        name = self.sanitize(name)
        
        # Remove numbers and special characters except spaces, hyphens, apostrophes
        name = re.sub(r'[^a-zA-Z\s\-\']', '', name)
        
        # Normalize multiple spaces
        name = re.sub(r'\s+', ' ', name)
        
        # Title case
        name = name.title()
        
        return name.strip()
    
    def sanitize_amount(self, amount: Any) -> Optional[float]:
        """
        Sanitize and validate currency amount
        
        Args:
            amount: Amount to sanitize
            
        Returns:
            Sanitized amount or None if invalid
        """
        try:
            # Remove currency symbols and spaces
            amount_str = re.sub(r'[Rr$,\s]', '', str(amount))
            
            # Convert to float
            amount_float = float(amount_str)
            
            # Validate reasonable range
            if 0 < amount_float < 100000:
                return round(amount_float, 2)
            
            log_warning(f"Amount outside valid range: {amount_float}")
            return None
            
        except (ValueError, TypeError):
            log_warning(f"Invalid amount format: {amount}")
            return None