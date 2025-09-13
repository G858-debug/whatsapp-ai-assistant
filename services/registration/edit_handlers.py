"""Edit handlers for registration flow"""
from typing import Dict
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from services.helpers.validation_helpers import ValidationHelpers

class EditHandlers:
    """Handle editing of registration fields"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.validation = ValidationHelpers()
    
    def process_edit_value(self, session_id: str, field_name: str, new_value: str) -> Dict:
        """Process edited field value"""
        try:
            # Get session
            from services.registration.registration_state import RegistrationStateManager
            state_manager = RegistrationStateManager(self.db, self.config)
            
            session = state_manager.get_session(session_id)
            if not session:
                return {
                    'success': False,
                    'message': 'Session expired. Please start over.'
                }
            
            # Validate new value based on field
            validation_result = self._validate_field(field_name, new_value, session['user_type'])
            
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': validation_result['message']
                }
            
            # Update session data
            update_result = state_manager.update_session(
                session_id,
                step='confirmation',  # Go back to confirmation
                data_update={field_name: validation_result['value']}
            )
            
            if update_result['success']:
                return {
                    'success': True,
                    'message': f"✅ {field_name.replace('_', ' ').title()} updated successfully!"
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to update. Please try again.'
                }
                
        except Exception as e:
            log_error(f"Error processing edit: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred while updating.'
            }
    
    def _validate_field(self, field_name: str, value: str, user_type: str) -> Dict:
        """Validate field value based on field name and user type"""
        value = value.strip()
        
        # Common fields
        if field_name == 'name':
            if len(value) < 2:
                return {'valid': False, 'message': 'Name must be at least 2 characters.'}
            return {'valid': True, 'value': value}
        
        elif field_name == 'email':
            if not self.validation.validate_email(value):
                return {'valid': False, 'message': 'Please enter a valid email address.'}
            return {'valid': True, 'value': value.lower()}
        
        # Trainer-specific fields
        elif user_type == 'trainer':
            if field_name == 'business':
                if len(value) < 2:
                    return {'valid': False, 'message': 'Business name must be at least 2 characters.'}
                return {'valid': True, 'value': value}
            
            elif field_name == 'location':
                if len(value) < 2:
                    return {'valid': False, 'message': 'Location must be at least 2 characters.'}
                return {'valid': True, 'value': value}
            
            elif field_name == 'price':
                price = self.validation.extract_price(value)
                if not price or price < 50 or price > 5000:
                    return {'valid': False, 'message': 'Price must be between R50 and R5000.'}
                return {'valid': True, 'value': price}
            
            elif field_name == 'specialties':
                if len(value) < 3:
                    return {'valid': False, 'message': 'Please describe your specialties.'}
                return {'valid': True, 'value': value}
        
        # Client-specific fields
        elif user_type == 'client':
            if field_name == 'emergency_contact':
                if len(value) < 2:
                    return {'valid': False, 'message': 'Emergency contact name required.'}
                return {'valid': True, 'value': value}
            
            elif field_name == 'emergency_phone':
                phone = self.validation.format_phone_number(value)
                if not phone:
                    return {'valid': False, 'message': 'Please enter a valid phone number.'}
                return {'valid': True, 'value': phone}
            
            elif field_name == 'goals':
                if len(value) < 5:
                    return {'valid': False, 'message': 'Please describe your goals.'}
                return {'valid': True, 'value': value}
        
        # Default validation
        return {'valid': True, 'value': value}