"""
Registration Service - Enhanced Structure
Main coordinator for registration with delegation to specialized managers
"""
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from services.auth.authentication_service import AuthenticationService

# Import specialized managers
from .registration.data_saver import DataSaver
from .registration.field_manager import FieldManager
from .registration.validation_service import ValidationService


class RegistrationService:
    """
    Main registration service coordinator.
    Delegates to specialized managers while maintaining backward compatibility.
    """
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        self.auth_service = AuthenticationService(supabase_client)
        
        # Initialize specialized managers
        self.field_manager = FieldManager()
        self.validation_service = ValidationService()
        self.data_saver = DataSaver(supabase_client, self.auth_service)
    
    # Delegate to FieldManager
    def get_registration_fields(self, role: str) -> List[Dict]:
        """Get list of fields for registration"""
        return self.field_manager.get_registration_fields(role)
    
    def get_next_field(self, role: str, current_index: int) -> Optional[Dict]:
        """Get next field in registration flow"""
        return self.field_manager.get_next_field(role, current_index)
    
    def parse_field_value(self, field: Dict, value: str) -> Any:
        """Parse and format field value based on field type"""
        return self.field_manager.parse_field_value(field, value)
    
    def map_field_to_db_column(self, field_name: str, role: str) -> str:
        """Map config field name to database column name"""
        return self.field_manager.map_field_to_db_column(field_name, role)
    
    # Delegate to ValidationService
    def validate_field_value(self, field: Dict, value: str) -> Tuple[bool, str]:
        """Validate field value against field rules"""
        return self.validation_service.validate_field_value(field, value)
    
    def clean_phone_number(self, phone: str) -> str:
        """Clean phone number by removing non-digit characters"""
        return self.validation_service.clean_phone_number(phone)
    
    # Delegate to DataSaver
    def save_trainer_registration(self, phone: str, data: Dict) -> Tuple[bool, str, Optional[str]]:
        """Save trainer registration data"""
        return self.data_saver.save_trainer_registration(phone, data)
    
    def save_client_registration(self, phone: str, data: Dict, created_by_trainer: bool = False, trainer_id: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Save client registration data"""
        return self.data_saver.save_client_registration(phone, data, created_by_trainer, trainer_id)
    
    def _create_trainer_client_relationship(self, trainer_id: str, client_id: str, invited_by: str) -> bool:
        """Create bidirectional trainer-client relationship"""
        return self.data_saver._create_trainer_client_relationship(trainer_id, client_id, invited_by)
