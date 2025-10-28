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

from .new_user_handler import NewUserHandler
from .trainer_registration import TrainerRegistrationHandler
from .client_registration import ClientRegistrationHandler
from .completion_handler import RegistrationCompletionHandler


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
        self.new_user_handler = NewUserHandler(whatsapp, self.message_builder)
        self.trainer_handler = TrainerRegistrationHandler(
            db, whatsapp, reg_service, self.validator, self.message_builder, self.task_manager
        )
        self.client_handler = ClientRegistrationHandler(
            db, whatsapp, reg_service, self.validator, self.message_builder, self.task_manager
        )
        self.completion_handler = RegistrationCompletionHandler(
            db, whatsapp, auth_service, reg_service, self.message_builder, self.task_manager
        )
    
    def handle_new_user(self, phone: str, message: str) -> Dict:
        """Handle first message from new user"""
        try:
            # Check if this is a direct role selection
            msg_lower = message.lower().strip()
            
            if msg_lower in ['register_trainer', 'register as trainer', 'trainer', '💪 register as trainer']:
                return self.start_registration(phone, 'trainer')
            
            elif msg_lower in ['register_client', 'register as client', 'client', '🏃 register as client']:
                return self.start_registration(phone, 'client')
            
            # First time user - show welcome and options
            return self.new_user_handler.show_welcome_message(phone)
            
        except Exception as e:
            return self.handle_flow_error(phone, None, e, 'new_user', 'new user handling')
    
    def start_registration(self, phone: str, role: str) -> Dict:
        """Start registration process for selected role"""
        try:
            log_info(f"Starting {role} registration for {phone}")
            
            # Get registration fields for this role
            fields = self.reg.get_registration_fields(role)
            
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
                    'fields': fields
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
            if role == 'trainer':
                return self.trainer_handler.start_trainer_registration(phone, fields, task_id)
            else:
                return self.client_handler.start_client_registration(phone, fields, task_id)
                
        except Exception as e:
            return self.handle_flow_error(phone, None, e, role, 'registration start')
    
    def continue_registration(self, phone: str, message: str, role: str, task: Dict) -> Dict:
        """Continue registration process"""
        try:
            task_data = task.get('task_data', {})
            reg_role = task_data.get('role', role)
            
            # Route to appropriate handler
            if reg_role == 'trainer':
                return self.trainer_handler.continue_trainer_registration(phone, message, task)
            else:
                return self.client_handler.continue_client_registration(phone, message, task)
                
        except Exception as e:
            return self.handle_flow_error(phone, task, e, role, 'registration continuation')