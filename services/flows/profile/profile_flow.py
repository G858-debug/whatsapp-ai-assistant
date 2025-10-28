"""
Profile Flow Handler - Refactored
Main coordinator for profile management flows
"""
from typing import Dict
from utils.logger import log_info, log_error

from ..core.flow_coordinator import FlowCoordinator
from ..core.field_validator import FieldValidator
from ..core.message_builder import MessageBuilder
from ..core.task_manager import FlowTaskManager

from .edit_handler import ProfileEditHandler
from .deletion_handler import AccountDeletionHandler


class ProfileFlowHandler(FlowCoordinator):
    """Main coordinator for profile management flows"""
    
    def __init__(self, db, whatsapp, reg_service, task_service):
        super().__init__(db, whatsapp, task_service)
        self.reg = reg_service
        
        # Initialize components
        self.validator = FieldValidator()
        self.message_builder = MessageBuilder()
        self.task_manager = FlowTaskManager(task_service)
        
        # Initialize handlers
        self.edit_handler = ProfileEditHandler(
            db, whatsapp, reg_service, self.validator, self.message_builder, self.task_manager
        )
        self.deletion_handler = AccountDeletionHandler(
            db, whatsapp, self.message_builder, self.task_manager
        )
    
    def continue_edit_profile(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Continue profile editing flow"""
        try:
            return self.edit_handler.continue_edit_profile(phone, message, role, user_id, task)
        except Exception as e:
            return self.handle_flow_error(phone, task, e, role, 'profile editing')
    
    def continue_delete_account(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Continue account deletion flow"""
        try:
            return self.deletion_handler.continue_delete_account(phone, message, role, user_id, task)
        except Exception as e:
            return self.handle_flow_error(phone, task, e, role, 'account deletion')