"""
Registration Flow Handler - Refactored
Main coordinator for new user registration flows
"""
from typing import Dict
from utils.logger import log_info, log_error

from ..core.flow_coordinator import FlowCoordinator
from ..core.field_validator import FieldValidator
from ..core.message_builder import MessageBuilder
from ..core.task_manager import FlowTaskManager

from .client_registration import ClientRegistrationHandler


class RegistrationFlowHandler(FlowCoordinator):
    """Main coordinator for registration flows"""
    
    def __init__(self, db, whatsapp, auth_service, reg_service, task_service):
        super().__init__(db, whatsapp, task_service)
        self.auth = auth_service
        self.reg = reg_service
        
        # Initialize components
        self.validator = FieldValidator()
        self.message_builder = MessageBuilder()
        self.task_manager = FlowTaskManager(task_service)
        
        # Initialize handlers
        self.client_handler = ClientRegistrationHandler(
            db, whatsapp, reg_service, self.validator, self.message_builder, self.task_manager
        )
    
    def handle_new_user(self, phone: str, message: str) -> Dict:
        """
        Handle first message from new user
        
        NOTE: This method is deprecated and should not be called for new users.
        New users should be handled by message_router/handlers/new_user_handler.py
        This is kept only for backward compatibility with in-progress registrations.
        """
        try:
            # Check if this is a direct role selection
            msg_lower = message.lower().strip()
            
            
            if msg_lower in ['register_client', 'Register as Trainee', 'client', '🏃 Register as Trainee']:
                return self.start_registration(phone, 'client')
            
            # This should not be reached for new users
            log_error(f"RegistrationFlowHandler.handle_new_user() called unexpectedly for {phone}")
            return {
                'success': False,
                'response': "Please start registration by typing 'trainer' or 'client'",
                'handler': 'deprecated_new_user_handler'
            }
            
        except Exception as e:
            return self.handle_flow_error(phone, None, e, 'new_user', 'new user handling')
    
    def start_registration(self, phone: str, role: str, created_by_trainer: bool = False, trainer_id: str = None) -> Dict:
        """Start registration process for selected role"""
        try:
            log_info(f"Starting {role} registration for {phone}")
            
            # Get registration fields for this role
            if role == 'client' and created_by_trainer:
                # Use trainer-add-client fields (includes phone number)
                fields = self.reg.get_trainer_add_client_fields()
            
            
            if not fields:
                error_msg = "Sorry, registration is not available right now. Please try again later."
                self.whatsapp.send_message(phone, error_msg)
                return {
                    'success': False,
                    'response': error_msg,
                    'handler': 'registration_error'
                }
            
            # Create registration task
            task_id = self.task_manager.create_flow_task(
                user_id=phone,  # Use phone as temp ID until we have user_id
                role=role,
                task_type='registration',
                initial_data={
                    'current_field_index': 0,
                    'collected_data': {},
                    'role': role,
                    'fields': fields,
                    'created_by_trainer': created_by_trainer,
                    'trainer_id': trainer_id
                }
            )
            
            if not task_id:
                error_msg = "Sorry, I couldn't start the registration process. Please try again."
                self.whatsapp.send_message(phone, error_msg)
                return {
                    'success': False,
                    'response': error_msg,
                    'handler': 'registration_task_error'
                }
            
            # Send intro message and first field
            
                return self.client_handler.start_client_registration(phone, fields, task_id)
                
        except Exception as e:
            return self.handle_flow_error(phone, None, e, role, 'registration start')
    
    def continue_registration(self, phone: str, message: str, role: str, task: Dict) -> Dict:
        """Continue registration process"""
        try:
            task_data = task.get('task_data', {})
            reg_role = task_data.get('role', role)
            
            # Route to appropriate handler
            
            return self.client_handler.continue_client_registration(phone, message, task)
                
        except Exception as e:
            return self.handle_flow_error(phone, task, e, role, 'registration continuation')