# utils/input_sanitizer.py
"""
Input Sanitization and Validation for WhatsApp Messages
Protects against injection attacks, malicious content, and invalid data
"""

import re
import unicodedata
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import pytz

from utils.logger import log_warning, log_error, log_info

class InputSanitizer:
    """
    Comprehensive input sanitization for WhatsApp messages
    """
    
    def __init__(self, config):
        """Initialize sanitizer with configuration"""
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Message limits
        self.MAX_MESSAGE_LENGTH = 4096  # WhatsApp limit
        self.MAX_PHONE_LENGTH = 20
        self.MAX_NAME_LENGTH = 100
        self.MAX_AMOUNT_VALUE = 100000  # R100,000 max payment
        
        # Dangerous patterns to block
        self.SQL_PATTERNS = [
            r'(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute|script|javascript|eval)',
            r'(?i)(from\s+information_schema)',
            r'(?i)(or\s+1\s*=\s*1)',
            r'(?i)(;\s*drop\s+table)',
            r'(?i)(--\s*$)',  # SQL comments
            r'(?i)(xp_cmdshell)',
            r'(?i)(waitfor\s+delay)',
        ]
        
        self.SCRIPT_PATTERNS = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',  # onclick, onload, etc.
            r'<iframe',
            r'<embed',
            r'<object',
            r'document\.',
            r'window\.',
            r'eval\s*\(',
            r'Function\s*\(',
        ]
        
        self.COMMAND_PATTERNS = [
            r'(?i)(rm\s+-rf)',
            r'(?i)(sudo\s+)',
            r'(?i)(chmod\s+)',
            r'(?i)(curl\s+.*\|.*sh)',
            r'(?i)(wget\s+.*\|.*sh)',
            r'&&',
            r'\|\|',
            r'`.*`',  # Command substitution
            r'\$\(.*\)',  # Command substitution
        ]
        
        # Suspicious content patterns
        self.SUSPICIOUS_PATTERNS = {
            'phishing': [
                r'(?i)(verify\s+your\s+account)',
                r'(?i)(suspended\s+account)',
                r'(?i)(click\s+here\s+immediately)',
                r'(?i)(confirm\s+your\s+identity)',
                r'(?i)(update\s+payment\s+information)',
            ],
            'scam': [
                r'(?i)(you\s+have\s+won)',
                r'(?i)(claim\s+your\s+prize)',
                r'(?i)(limited\s+time\s+offer)',
                r'(?i)(act\s+now)',
                r'(?i)(100%\s+guaranteed)',
            ],
            'malicious_urls': [
                r'bit\.ly/',
                r'tinyurl\.com/',
                r'goo\.gl/',
                r'ow\.ly/',
                r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
            ]
        }
        
        # Valid patterns
        self.VALID_PATTERNS = {
            'phone': r'^\+?[0-9\s\-\(\)]+$',
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'amount': r'^[0-9]+(\.[0-9]{1,2})?$',
            'date': r'^\d{4}-\d{2}-\d{2}$',
            'time': r'^\d{2}:\d{2}$',
        }
        
        # Track sanitization stats
        self.stats = {
            'total_processed': 0,
            'blocked_sql': 0,
            'blocked_script': 0,
            'blocked_command': 0,
            'suspicious_detected': 0,
            'truncated': 0,
        }
    
    def sanitize_message(self, message: str, phone_number: str) -> Tuple[str, bool, List[str]]:
        """
        Main sanitization function for incoming messages
        Returns: (sanitized_message, is_safe, warnings)
        """
        try:
            self.stats['total_processed'] += 1
            warnings = []
            
            # Step 1: Basic validation
            if not message:
                return "", True, ["Empty message"]
            
            # Step 2: Length check
            if len(message) > self.MAX_MESSAGE_LENGTH:
                message = message[:self.MAX_MESSAGE_LENGTH]
                self.stats['truncated'] += 1
                warnings.append(f"Message truncated to {self.MAX_MESSAGE_LENGTH} characters")
                log_warning(f"Message from {phone_number} truncated - too long")
            
            # Step 3: Normalize unicode
            message = self._normalize_unicode(message)
            
            # Step 4: Check for SQL injection
            if self._contains_sql_injection(message):
                self.stats['blocked_sql'] += 1
                log_warning(f"SQL injection attempt from {phone_number}: {message[:100]}")
                return "", False, ["SQL injection detected"]
            
            # Step 5: Check for script injection
            if self._contains_script_injection(message):
                self.stats['blocked_script'] += 1
                log_warning(f"Script injection attempt from {phone_number}: {message[:100]}")
                return "", False, ["Script injection detected"]
            
            # Step 6: Check for command injection
            if self._contains_command_injection(message):
                self.stats['blocked_command'] += 1
                log_warning(f"Command injection attempt from {phone_number}: {message[:100]}")
                return "", False, ["Command injection detected"]
            
            # Step 7: Check for suspicious content
            suspicious_type = self._check_suspicious_content(message)
            if suspicious_type:
                self.stats['suspicious_detected'] += 1
                warnings.append(f"Suspicious content detected: {suspicious_type}")
                log_warning(f"Suspicious {suspicious_type} from {phone_number}")
            
            # Step 8: Clean the message
            sanitized = self._clean_message(message)
            
            # Step 9: Validate based on context
            if self._is_payment_message(sanitized):
                sanitized = self._sanitize_payment_message(sanitized)
            
            return sanitized, True, warnings
            
        except Exception as e:
            log_error(f"Error sanitizing message: {str(e)}")
            return "", False, ["Sanitization error"]
    
    def sanitize_phone_number(self, phone: str) -> Tuple[str, bool]:
        """
        Sanitize and validate phone numbers
        Returns: (sanitized_phone, is_valid)
        """
        try:
            # Remove all non-numeric except +
            cleaned = re.sub(r'[^\d+]', '', phone)
            
            # Check length
            if len(cleaned) > self.MAX_PHONE_LENGTH:
                return "", False
            
            # Ensure South African format
            if not cleaned.startswith('+'):
                if cleaned.startswith('0'):
                    cleaned = '+27' + cleaned[1:]
                elif cleaned.startswith('27'):
                    cleaned = '+' + cleaned
                else:
                    cleaned = '+27' + cleaned
            
            # Validate format
            if not re.match(r'^\+27[0-9]{9}$', cleaned):
                return "", False
            
            return cleaned, True
            
        except Exception as e:
            log_error(f"Error sanitizing phone: {str(e)}")
            return "", False
    
    def sanitize_amount(self, amount_str: str) -> Tuple[Optional[float], bool]:
        """
        Sanitize and validate payment amounts
        Returns: (amount, is_valid)
        """
        try:
            # Remove currency symbols and spaces
            cleaned = re.sub(r'[R$,\s]', '', amount_str)
            
            # Check if valid number format
            if not re.match(self.VALID_PATTERNS['amount'], cleaned):
                return None, False
            
            amount = float(cleaned)
            
            # Check reasonable limits
            if amount <= 0 or amount > self.MAX_AMOUNT_VALUE:
                return None, False
            
            # Round to 2 decimal places
            amount = round(amount, 2)
            
            return amount, True
            
        except Exception as e:
            log_error(f"Error sanitizing amount: {str(e)}")
            return None, False
    
    def sanitize_name(self, name: str) -> Tuple[str, bool]:
        """
        Sanitize and validate names
        Returns: (sanitized_name, is_valid)
        """
        try:
            # Remove potentially dangerous characters
            cleaned = re.sub(r'[<>\"\';&]', '', name)
            
            # Truncate if too long
            if len(cleaned) > self.MAX_NAME_LENGTH:
                cleaned = cleaned[:self.MAX_NAME_LENGTH]
            
            # Must have at least one letter
            if not re.search(r'[a-zA-Z]', cleaned):
                return "", False
            
            # Title case
            cleaned = cleaned.title()
            
            return cleaned, True
            
        except Exception as e:
            log_error(f"Error sanitizing name: {str(e)}")
            return "", False
    
    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters to prevent homograph attacks"""
        # Normalize to NFKC form
        normalized = unicodedata.normalize('NFKC', text)
        
        # Remove zero-width characters
        zero_width_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\ufeff',  # Zero-width no-break space
        ]
        for char in zero_width_chars:
            normalized = normalized.replace(char, '')
        
        return normalized
    
    def _contains_sql_injection(self, text: str) -> bool:
        """Check for SQL injection patterns"""
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, text):
                return True
        return False
    
    def _contains_script_injection(self, text: str) -> bool:
        """Check for script injection patterns"""
        for pattern in self.SCRIPT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return True
        return False
    
    def _contains_command_injection(self, text: str) -> bool:
        """Check for command injection patterns"""
        for pattern in self.COMMAND_PATTERNS:
            if re.search(pattern, text):
                return True
        return False
    
    def _check_suspicious_content(self, text: str) -> Optional[str]:
        """Check for suspicious content patterns"""
        for category, patterns in self.SUSPICIOUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return category
        return None
    
    def _clean_message(self, message: str) -> str:
        """Clean and normalize message text"""
        # Remove excessive whitespace
        cleaned = ' '.join(message.split())
        
        # Remove control characters except newlines
        cleaned = ''.join(
            char for char in cleaned 
            if char == '\n' or not unicodedata.category(char).startswith('C')
        )
        
        # Limit consecutive newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Escape special characters for database storage
        cleaned = cleaned.replace("'", "''")  # SQL escape
        
        return cleaned.strip()
    
    def _is_payment_message(self, message: str) -> bool:
        """Check if message is payment-related"""
        payment_keywords = ['pay', 'payment', 'invoice', 'amount', 'owe', 'charge']
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in payment_keywords)
    
    def _sanitize_payment_message(self, message: str) -> str:
        """Extra sanitization for payment messages"""
        # Remove any potential card numbers
        message = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD_REMOVED]', message)
        
        # Remove CVV patterns
        message = re.sub(r'\b\d{3,4}\b', '[CVV_REMOVED]', message)
        
        return message
    
    def validate_booking_time(self, time_str: str) -> Tuple[str, bool]:
        """
        Validate and sanitize booking time
        Returns: (sanitized_time, is_valid)
        """
        try:
            # Remove spaces and convert to standard format
            cleaned = time_str.strip().replace(' ', '')
            
            # Try different formats
            formats = ['%H:%M', '%I:%M%p', '%I%p']
            
            for fmt in formats:
                try:
                    time_obj = datetime.strptime(cleaned, fmt)
                    # Convert to 24-hour format
                    return time_obj.strftime('%H:%M'), True
                except ValueError:
                    continue
            
            return "", False
            
        except Exception as e:
            log_error(f"Error validating time: {str(e)}")
            return "", False
    
    def get_sanitization_stats(self) -> Dict:
        """Get sanitization statistics"""
        return {
            'total_processed': self.stats['total_processed'],
            'blocked_total': sum([
                self.stats['blocked_sql'],
                self.stats['blocked_script'],
                self.stats['blocked_command']
            ]),
            'blocked_sql': self.stats['blocked_sql'],
            'blocked_script': self.stats['blocked_script'],
            'blocked_command': self.stats['blocked_command'],
            'suspicious_detected': self.stats['suspicious_detected'],
            'truncated': self.stats['truncated'],
            'block_rate': (
                (self.stats['blocked_sql'] + self.stats['blocked_script'] + 
                 self.stats['blocked_command']) / max(self.stats['total_processed'], 1)
            ) * 100
        }
    
    def reset_stats(self):
        """Reset sanitization statistics"""
        for key in self.stats:
            self.stats[key] = 0
