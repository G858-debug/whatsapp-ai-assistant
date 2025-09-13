"""Handlers for editing registration data"""
from typing import Dict, Optional
from utils.logger import log_error, log_info

class EditHandlers:
    """Handle editing of registration information"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
    
    def handle_edit_request(self, session_id: str, field_to_edit: str) -> Dict:
        """Handle request to edit a specific field"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': 'Session not found'
                }
            
            # Map edit keywords to fields
            field_map = {
                'name': 'name',
                'email': 'email',
                'phone': 'phone',
                'business': 'business_name',
                'location': 'location',
                'specialization': 'specialization',
                'price': 'pricing',
                'trainer': 'trainer_choice'
            }
            
            # Find which field to edit
            field = None
            for key, value in field_map.items():
                if key in field_to_edit.lower():
                    field = value
                    break
            
            if not field:
                return {
                    'success': False,
                    'message': "I'm not sure which field you want to edit. You can edit: name, email, phone, business name, location, specialization, or price."
                }
            
            # Update session to go back to that step
            step_map = {
                'name': 'name',
                'email': 'email',
                'phone': 'phone',
                'business_name': 'business',
                'location': 'location',
                'specialization': 'specialization',
                'pricing': 'pricing',
                'trainer_choice': 'trainer_selection'
            }
            
            new_step = step_map.get(field, 'name')
            
            # Update session step
            self.db.table('registration_sessions').update({
                'step': new_step
            }).eq('id', session_id).execute()
            
            # Get prompt for the field
            prompts = {
                'name': "What's your full name?",
                'email': "What's your email address?",
                'phone': "What's your phone number?",
                'business_name': "What's your business name? (or 'skip' if you don't have one)",
                'location': "Where are you located? (area/suburb)",
                'specialization': "What's your training specialization?",
                'pricing': "What's your rate per session? (e.g., R350)",
                'trainer_choice': "Would you like me to find trainers in your area? Reply YES or NO"
            }
            
            return {
                'success': True,
                'message': f"Let's update that. {prompts.get(field, 'Please provide the new value:')}"
            }
            
        except Exception as e:
            log_error(f"Error handling edit request: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing edit request'
            }
    
    def validate_edit(self, field: str, value: str) -> Dict:
        """Validate edited field value"""
        try:
            if field == 'email':
                from services.helpers.validation_helpers import ValidationHelpers
                validator = ValidationHelpers()
                if not validator.validate_email(value):
                    return {
                        'valid': False,
                        'message': 'Please provide a valid email address'
                    }
            
            elif field == 'phone':
                from services.helpers.validation_helpers import ValidationHelpers
                validator = ValidationHelpers()
                formatted = validator.format_phone_number(value)
                if not formatted:
                    return {
                        'valid': False,
                        'message': 'Please provide a valid South African phone number'
                    }
                return {
                    'valid': True,
                    'formatted_value': formatted
                }
            
            elif field == 'pricing':
                from services.helpers.validation_helpers import ValidationHelpers
                validator = ValidationHelpers()
                price = validator.extract_price(value)
                if not price:
                    return {
                        'valid': False,
                        'message': 'Please provide a valid price (e.g., R350)'
                    }
                return {
                    'valid': True,
                    'formatted_value': price
                }
            
            return {'valid': True}
            
        except Exception as e:
            log_error(f"Error validating edit: {str(e)}")
            return {
                'valid': False,
                'message': 'Error validating input'
            }