"""
Field Validator
Handles validation of user inputs for flow fields
"""
from typing import Dict, Tuple, Any
import re
from utils.logger import log_error


class FieldValidator:
    """Validates user inputs for flow fields"""
    
    def validate_field_value(self, field: Dict, value: str) -> Tuple[bool, str]:
        """
        Validate field value based on field configuration
        Returns: (is_valid, error_message)
        """
        try:
            field_type = field.get('type', 'text')
            field_name = field.get('name', 'field')
            validation = field.get('validation', {})
            
            # Handle optional fields
            if not field.get('required', True) and value.strip().lower() in ['skip', 'no', 'none', '']:
                return True, ""
            
            # Required field check
            if field.get('required', True) and not value.strip():
                return False, f"{field_name} is required."
            
            # Type-specific validation
            if field_type == 'number':
                return self._validate_number_field(value, validation)
            elif field_type == 'email':
                return self._validate_email_field(value, validation)
            elif field_type == 'phone':
                return self._validate_phone_field(value, validation)
            elif field_type == 'choice':
                return self._validate_choice_field(value, field.get('options', []))
            elif field_type == 'text':
                return self._validate_text_field(value, validation)
            else:
                return True, ""  # Unknown type, allow it
                
        except Exception as e:
            log_error(f"Error validating field: {str(e)}")
            return False, "Validation error occurred."
    
    def _validate_number_field(self, value: str, validation: Dict) -> Tuple[bool, str]:
        """Validate number field"""
        try:
            num_value = float(value.strip())
            
            if 'min' in validation and num_value < validation['min']:
                return False, f"Value must be at least {validation['min']}."
            
            if 'max' in validation and num_value > validation['max']:
                return False, f"Value must be at most {validation['max']}."
            
            return True, ""
            
        except ValueError:
            return False, "Please enter a valid number."
    
    def _validate_email_field(self, value: str, validation: Dict) -> Tuple[bool, str]:
        """Validate email field"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, value.strip()):
            return False, "Please enter a valid email address."
        
        return True, ""
    
    def _validate_phone_field(self, value: str, validation: Dict) -> Tuple[bool, str]:
        """Validate phone field"""
        # Remove common phone formatting
        clean_phone = re.sub(r'[^\d+]', '', value.strip())
        
        if len(clean_phone) < 10:
            return False, "Please enter a valid phone number."
        
        return True, ""
    
    def _validate_choice_field(self, value: str, options: list) -> Tuple[bool, str]:
        """Validate choice field"""
        if not options:
            return True, ""
        
        valid_values = [opt.get('value', '').lower() if isinstance(opt, dict) else str(opt).lower() 
                       for opt in options]
        
        if value.strip().lower() not in valid_values:
            option_labels = [opt.get('label', opt.get('value', '')) if isinstance(opt, dict) else str(opt) 
                           for opt in options]
            return False, f"Please choose from: {', '.join(option_labels)}"
        
        return True, ""
    
    def _validate_text_field(self, value: str, validation: Dict) -> Tuple[bool, str]:
        """Validate text field"""
        text_value = value.strip()
        
        if 'min_length' in validation and len(text_value) < validation['min_length']:
            return False, f"Must be at least {validation['min_length']} characters."
        
        if 'max_length' in validation and len(text_value) > validation['max_length']:
            return False, f"Must be at most {validation['max_length']} characters."
        
        if 'pattern' in validation:
            if not re.match(validation['pattern'], text_value):
                return False, validation.get('pattern_message', 'Invalid format.')
        
        return True, ""
    
    def parse_field_value(self, field: Dict, value: str) -> Any:
        """Parse field value to appropriate type"""
        try:
            field_type = field.get('type', 'text')
            
            # Handle optional fields
            if not field.get('required', True) and value.strip().lower() in ['skip', 'no', 'none', '']:
                return None
            
            if field_type == 'number':
                return float(value.strip())
            elif field_type == 'choice':
                return value.strip().lower()
            else:
                return value.strip()
                
        except Exception as e:
            log_error(f"Error parsing field value: {str(e)}")
            return value.strip()