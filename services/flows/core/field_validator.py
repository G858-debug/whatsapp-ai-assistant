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
            elif field_type == 'multi_choice':
                return self._validate_multi_choice_field(value, field.get('options', []))
            elif field_type == 'text' or field_type == 'textarea':
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
        
        try:
            # Try to parse as number (option index)
            choice_num = int(value.strip())
            if 1 <= choice_num <= len(options):
                return True, ""
            else:
                return False, f"Please choose a number between 1 and {len(options)}."
        except ValueError:
            # Not a number, check if it's a valid option text
            valid_values = [str(opt).lower() for opt in options]
            if value.strip().lower() not in valid_values:
                return False, f"Please choose from: {', '.join(options)}"
            return True, ""
    
    def _validate_multi_choice_field(self, value: str, options: list) -> Tuple[bool, str]:
        """Validate multi-choice field"""
        if not options:
            return True, ""
        
        # Parse comma-separated values
        choices = [choice.strip() for choice in value.split(',')]
        
        for choice in choices:
            try:
                # Try to parse as number (option index)
                choice_num = int(choice)
                if not (1 <= choice_num <= len(options)):
                    return False, f"Choice {choice_num} is not valid. Please choose numbers between 1 and {len(options)}."
            except ValueError:
                # Not a number, check if it's a valid option text
                valid_values = [str(opt).lower() for opt in options]
                if choice.lower() not in valid_values:
                    return False, f"'{choice}' is not a valid option. Please choose from: {', '.join(options)}"
        
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
            options = field.get('options', [])
            
            # Handle optional fields
            if not field.get('required', True) and value.strip().lower() in ['skip', 'no', 'none', '']:
                return None
            
            if field_type == 'number':
                return float(value.strip())
            elif field_type == 'choice':
                # Try to parse as number (option index)
                try:
                    choice_num = int(value.strip())
                    if 1 <= choice_num <= len(options):
                        return options[choice_num - 1]  # Convert to actual option value
                except ValueError:
                    pass
                return value.strip()
            elif field_type == 'multi_choice':
                # Parse comma-separated values
                choices = [choice.strip() for choice in value.split(',')]
                parsed_choices = []
                
                for choice in choices:
                    try:
                        # Try to parse as number (option index)
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(options):
                            parsed_choices.append(options[choice_num - 1])
                    except ValueError:
                        # Not a number, use as-is
                        parsed_choices.append(choice)
                
                return parsed_choices
            else:
                return value.strip()
                
        except Exception as e:
            log_error(f"Error parsing field value: {str(e)}")
            return value.strip()