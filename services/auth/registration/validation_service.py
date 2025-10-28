"""
Validation Service
Handles input validation for registration fields
"""
from typing import Dict, Tuple
import re
from utils.logger import log_info, log_error


class ValidationService:
    """Handles validation of registration field inputs"""
    
    def validate_field_value(self, field: Dict, value: str) -> Tuple[bool, str]:
        """
        Validate field value against field rules
        Returns: (is_valid, error_message)
        """
        try:
            # Check if field is required
            if field.get('required', False):
                if not value or value.strip().lower() in ['', 'skip']:
                    return False, f"{field['label']} is required. Please provide a value."
            
            # Allow skip for optional fields
            if not field.get('required', False) and value.strip().lower() == 'skip':
                return True, ""
            
            # Type-specific validation
            field_type = field.get('type', 'text')
            validation = field.get('validation', {})
            
            if field_type == 'email':
                if value and '@' not in value:
                    return False, "Please provide a valid email address."
            
            elif field_type == 'number':
                try:
                    num_value = float(value)
                    if 'min' in validation and num_value < validation['min']:
                        return False, f"Value must be at least {validation['min']}"
                    if 'max' in validation and num_value > validation['max']:
                        return False, f"Value must be at most {validation['max']}"
                except ValueError:
                    return False, "Please provide a valid number."
            
            elif field_type in ['text', 'textarea']:
                if 'min_length' in validation and len(value) < validation['min_length']:
                    return False, f"Must be at least {validation['min_length']} characters."
                if 'max_length' in validation and len(value) > validation['max_length']:
                    return False, f"Must be at most {validation['max_length']} characters."
            
            elif field_type == 'choice':
                # Validate choice selection
                options = field.get('options', [])
                try:
                    choice_num = int(value)
                    if choice_num < 1 or choice_num > len(options):
                        return False, f"Please select a number between 1 and {len(options)}"
                except ValueError:
                    return False, "Please provide a valid number."
            
            elif field_type == 'multi_choice':
                # Validate multiple choice selections
                options = field.get('options', [])
                try:
                    choices = [int(c.strip()) for c in value.split(',')]
                    for choice in choices:
                        if choice < 1 or choice > len(options):
                            return False, f"Please select numbers between 1 and {len(options)}"
                except ValueError:
                    return False, "Please provide valid numbers separated by commas (e.g., 1,3,5)"
            
            return True, ""
            
        except Exception as e:
            log_error(f"Error validating field: {str(e)}")
            return False, "Validation error occurred."
    
    def clean_phone_number(self, phone: str) -> str:
        """
        Clean phone number by removing +, -, spaces, and other non-digit characters
        Returns only digits
        """
        # Remove all non-digit characters
        cleaned = re.sub(r'[^\d]', '', phone)
        return cleaned