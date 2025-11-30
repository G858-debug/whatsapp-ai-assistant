"""
Field Manager
Handles field configuration and management for registration
"""
from typing import Dict, Optional, List, Any, Tuple
import json
import os
from utils.logger import log_info, log_error


class FieldManager:
    """Manages registration field configuration and operations"""
    
    def __init__(self):
        # Load registration input configurations
        self.client_fields = self._load_registration_config('client')
    
    def _load_registration_config(self, role: str) -> Dict:
        """Load registration field configuration from JSON"""
        try:
            config_file = f'config/{role}_registration_inputs.json'
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                log_error(f"Registration config not found: {config_file}")
                return {'fields': [], 'showable_fields': []}
        except Exception as e:
            log_error(f"Error loading registration config: {str(e)}")
            return {'fields': [], 'showable_fields': []}
    
    def get_trainer_add_client_fields(self) -> List[Dict]:
        """Get fields for trainer adding client (includes phone number)"""
        try:
            config_file = 'config/trainer_add_client_inputs.json'
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('fields', [])
            else:
                log_error(f"Trainer add client config not found: {config_file}")
                return []
        except Exception as e:
            log_error(f"Error loading trainer add client config: {str(e)}")
            return []
    
    def get_registration_fields(self, role: str) -> List[Dict]:
        """Get list of fields for registration"""
        if role == 'client':
            return self.client_fields.get('fields', [])
        return []
    
    def get_next_field(self, role: str, current_index: int) -> Optional[Dict]:
        """Get next field in registration flow"""
        fields = self.get_registration_fields(role)
        if 0 <= current_index < len(fields):
            return fields[current_index]
        return None
    
    def parse_field_value(self, field: Dict, value: str) -> Any:
        """
        Parse and format field value based on field type
        """
        try:
            field_type = field.get('type', 'text')
            
            # Handle skip for optional fields
            if not field.get('required', False) and value.strip().lower() == 'skip':
                return None
            
            if field_type == 'number':
                return float(value)
            
            elif field_type == 'choice':
                options = field.get('options', [])
                choice_num = int(value)
                return options[choice_num - 1] if 1 <= choice_num <= len(options) else value
            
            elif field_type == 'multi_choice':
                options = field.get('options', [])
                choices = [int(c.strip()) for c in value.split(',')]
                selected = [options[c - 1] for c in choices if 1 <= c <= len(options)]
                return selected
            
            else:
                return value.strip()
            
        except Exception as e:
            log_error(f"Error parsing field value: {str(e)}")
            return value
    
    def map_field_to_db_column(self, field_name: str, role: str) -> str:
        """
        Map config field name to database column name
        Some fields have different names in config vs database
        """
        # Client field mappings
        if role == 'client':
            field_mapping = {
                'full_name': 'name',
                'preferred_training_type': 'preferred_training_times',
                'phone_number': 'whatsapp'
            }
            return field_mapping.get(field_name, field_name)
        
        # Trainer field mappings
        # elif role == 'trainer':
        #     field_mapping = {
        #         # Handle potential reverse mappings for compatibility
        #         'location': 'city',  # If someone somehow edits location, map to city
        #         'years_experience': 'experience_years'  # If someone edits years_experience, map to experience_years
        #     }
        #     return field_mapping.get(field_name, field_name)
        
        return field_name