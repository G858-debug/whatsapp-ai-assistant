"""Input sanitization utilities for Refiloe"""
import re
import html
from typing import Tuple, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class InputSanitizer:
    """Sanitize and validate user inputs"""
    
    def __init__(self, config):
        self.config = config
        
        # Define patterns for common malicious inputs
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE)\b)",
            r"(--|#|\/\*|\*\/)",
            r"(\bOR\b.*=.*)",
            r"(\bAND\b.*=.*)",
            r"(';|\";\s*--)"
        ]
        
        self.script_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>"
        ]
        
        # Max message length
        self.max_message_length = 4096
        
        # Profanity list (basic - expand as needed)
        self.profanity_list = []  # Add words as needed
        
        # Suspicious patterns that might indicate spam
        self.spam_patterns = [
            r"(viagra|cialis|casino|lottery|winner)",
            r"(click here|buy now|limited offer)",
            r"(http[s]?://[^\s]+){3,}",  # Multiple URLs
            r"(\$\d+[\d,]*\.?\d*){3,}",  # Multiple dollar amounts
            r"(call now|whatsapp me)"
        ]
    
    def sanitize_message(self, message: str, sender_phone: str) -> Tuple[str, bool, List[str]]:
        """
        Sanitize a message from WhatsApp
        
        Returns:
            Tuple of (sanitized_message, is_safe, warnings)
        """
        if not message:
            return "", True, []
        
        warnings = []
        is_safe = True
        
        # Check length
        if len(message) > self.max_message_length:
            message = message[:self.max_message_length]
            warnings.append("Message truncated due to length")
        
        # Check for SQL injection attempts
        for pattern in self.sql_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                warnings.append("Potential SQL injection detected")
                is_safe = False
                logger.warning(f"SQL injection attempt from {sender_phone}: {message[:100]}")
        
        # Check for script injection
        for pattern in self.script_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                warnings.append("Script injection detected")
                is_safe = False
                logger.warning(f"Script injection attempt from {sender_phone}: {message[:100]}")
        
        # Check for spam patterns
        spam_count = 0
        for pattern in self.spam_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                spam_count += 1
        
        if spam_count >= 2:
            warnings.append("Message appears to be spam")
            is_safe = False
        
        # HTML escape the message
        sanitized = html.escape(message)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Remove zero-width characters and other invisible Unicode
        invisible_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\ufeff',  # Zero-width no-break space
            '\u2060',  # Word joiner
        ]
        for char in invisible_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized, is_safe, warnings
    
    def sanitize_phone_number(self, phone: str) -> Optional[str]:
        """
        Sanitize and validate phone number
        
        Returns:
            Sanitized phone number or None if invalid
        """
        if not phone:
            return None
        
        # Remove all non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        
        # Check for South African format
        if phone_digits.startswith('27'):
            if len(phone_digits) == 11:  # International format
                return f"+{phone_digits}"
        elif phone_digits.startswith('0'):
            if len(phone_digits) == 10:  # Local format
                return f"+27{phone_digits[1:]}"
        elif len(phone_digits) == 9:  # Missing leading 0
            return f"+27{phone_digits}"
        
        return None
    
    def sanitize_email(self, email: str) -> Optional[str]:
        """
        Sanitize and validate email address
        
        Returns:
            Sanitized email or None if invalid
        """
        if not email:
            return None
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        email = email.strip().lower()
        
        if re.match(email_pattern, email):
            return email
        
        return None
    
    def sanitize_name(self, name: str) -> str:
        """
        Sanitize a person's name
        
        Returns:
            Sanitized name
        """
        if not name:
            return ""
        
        # Remove numbers and special characters except spaces, hyphens, and apostrophes
        sanitized = re.sub(r'[^a-zA-Z\s\-\']', '', name)
        
        # Remove excessive spaces
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        # Title case
        sanitized = sanitized.title()
        
        return sanitized
    
    def sanitize_amount(self, amount: str) -> Optional[float]:
        """
        Sanitize and validate currency amount
        
        Returns:
            Float amount or None if invalid
        """
        if not amount:
            return None
        
        # Remove currency symbols and spaces
        amount = re.sub(r'[R$,\s]', '', amount)
        
        try:
            # Convert to float
            amount_float = float(amount)
            
            # Check reasonable bounds (R1 to R100,000)
            if 1 <= amount_float <= 100000:
                return round(amount_float, 2)
            
        except ValueError:
            pass
        
        return None
    
    def sanitize_date(self, date_str: str) -> Optional[str]:
        """
        Sanitize and validate date string
        
        Returns:
            ISO format date string or None if invalid
        """
        if not date_str:
            return None
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d %B %Y',
            '%d %b %Y',
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                return parsed_date.date().isoformat()
            except ValueError:
                continue
        
        return None
    
    def sanitize_time(self, time_str: str) -> Optional[str]:
        """
        Sanitize and validate time string
        
        Returns:
            24-hour format time string or None if invalid
        """
        if not time_str:
            return None
        
        # Remove spaces
        time_str = time_str.strip()
        
        # Common time formats
        time_formats = [
            '%H:%M',
            '%H:%M:%S',
            '%I:%M %p',
            '%I:%M%p',
            '%I %p',
            '%I%p',
        ]
        
        for fmt in time_formats:
            try:
                parsed_time = datetime.strptime(time_str, fmt)
                return parsed_time.strftime('%H:%M')
            except ValueError:
                continue
        
        # Try to handle simple formats like "9am" or "3pm"
        simple_match = re.match(r'^(\d{1,2})\s*(am|pm)$', time_str.lower())
        if simple_match:
            hour = int(simple_match.group(1))
            meridiem = simple_match.group(2)
            
            if meridiem == 'pm' and hour != 12:
                hour += 12
            elif meridiem == 'am' and hour == 12:
                hour = 0
            
            if 0 <= hour <= 23:
                return f"{hour:02d}:00"
        
        return None
    
    def sanitize_url(self, url: str) -> Optional[str]:
        """
        Sanitize and validate URL
        
        Returns:
            Sanitized URL or None if invalid
        """
        if not url:
            return None
        
        # Basic URL validation
        url_pattern = r'^https?://[^\s<>"{}|\\^`\[\]]+$'
        
        url = url.strip()
        
        if re.match(url_pattern, url):
            # Additional checks for malicious URLs
            suspicious_domains = [
                'bit.ly', 'tinyurl', 'goo.gl',  # URL shorteners
                'phishing', 'malware', 'virus'
            ]
            
            for domain in suspicious_domains:
                if domain in url.lower():
                    return None
            
            return url
        
        return None
    
    def detect_language(self, text: str) -> str:
        """
        Detect if text contains South African languages
        
        Returns:
            Language code (en, af, zu, xh, etc.)
        """
        # Basic detection for South African languages
        afrikaans_words = ['jy', 'ek', 'is', 'die', 'en', 'van', 'vir', 'met']
        zulu_words = ['ngiyabonga', 'sawubona', 'yebo', 'cha', 'mina']
        xhosa_words = ['molo', 'enkosi', 'ewe', 'hayi']
        
        text_lower = text.lower()
        words = text_lower.split()
        
        # Count occurrences
        af_count = sum(1 for word in words if word in afrikaans_words)
        zu_count = sum(1 for word in words if word in zulu_words)
        xh_count = sum(1 for word in words if word in xhosa_words)
        
        if af_count > 2:
            return 'af'
        elif zu_count > 0:
            return 'zu'
        elif xh_count > 0:
            return 'xh'
        else:
            return 'en'
    
    def is_command(self, message: str) -> bool:
        """
        Check if message appears to be a command
        
        Returns:
            True if message looks like a command
        """
        command_prefixes = ['/', '!', '#', '.']
        
        message = message.strip()
        
        if message and message[0] in command_prefixes:
            return True
        
        # Check for common command keywords at start
        command_starts = [
            'add', 'remove', 'delete', 'show', 'list', 
            'view', 'cancel', 'book', 'schedule', 'send'
        ]
        
        first_word = message.lower().split()[0] if message else ""
        
        return first_word in command_starts