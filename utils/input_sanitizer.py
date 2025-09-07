"""Input sanitization utilities"""
import re
from typing import Tuple

class InputSanitizer:
    """Sanitize user input for security"""
    
    def __init__(self, config):
        self.config = config
        # Patterns to block
        self.sql_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)',
            r'(--|#|\/\*|\*\/)',
        ]
        self.script_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
    
    def sanitize_message(self, message: str, sender: str) -> Tuple[str, bool, list]:
        """
        Sanitize message text
        Returns: (sanitized_text, is_safe, warnings)
        """
        warnings = []
        is_safe = True
        sanitized = message
        
        # Check for SQL injection attempts
        for pattern in self.sql_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                warnings.append("Potential SQL injection detected")
                is_safe = False
        
        # Check for script injection
        for pattern in self.script_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                warnings.append("Script injection detected")
                is_safe = False
        
        # Remove potentially harmful characters
        if not is_safe:
            # Remove special characters that could be harmful
            sanitized = re.sub(r'[<>\"\'`;]', '', message)
        
        # Limit message length
        max_length = 4096
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            warnings.append("Message truncated due to length")
        
        return sanitized, is_safe, warnings
    
    def sanitize_phone(self, phone: str) -> str:
        """Sanitize phone number"""
        # Remove all non-numeric characters
        cleaned = re.sub(r'\D', '', phone)
        
        # Handle South African format
        if cleaned.startswith('27'):
            return f"+{cleaned}"
        elif cleaned.startswith('0'):
            return f"+27{cleaned[1:]}"
        else:
            return f"+27{cleaned}"