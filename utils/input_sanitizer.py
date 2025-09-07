"""Input sanitization utility"""
import re
from typing import Tuple

class InputSanitizer:
    """Sanitize user inputs"""
    
    def __init__(self, config):
        self.config = config
        self.max_message_length = 5000
        self.blocked_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
    
    def sanitize_message(self, message: str, sender: str) -> Tuple[str, bool, list]:
        """Sanitize incoming message"""
        warnings = []
        
        # Check length
        if len(message) > self.max_message_length:
            message = message[:self.max_message_length]
            warnings.append("Message truncated")
        
        # Remove dangerous patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                message = re.sub(pattern, '', message, flags=re.IGNORECASE)
                warnings.append("Potentially harmful content removed")
        
        # Basic XSS prevention
        message = message.replace('<', '&lt;').replace('>', '&gt;')
        
        # Check if message is safe
        is_safe = len(warnings) == 0 or (len(warnings) == 1 and warnings[0] == "Message truncated")
        
        return message, is_safe, warnings