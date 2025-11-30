"""
Login Flow Handler - Refactored
Main coordinator for user login flows
"""
from typing import Dict
from utils.logger import log_info, log_error

from ..core.flow_coordinator import FlowCoordinator
from ..core.message_builder import MessageBuilder

from .role_selector import RoleSelector
from .auto_login import AutoLoginHandler


class LoginFlowHandler(FlowCoordinator):
    """Main coordinator for login flows"""
    
    def __init__(self, db, whatsapp, auth_service, task_service):
        super().__init__(db, whatsapp, task_service)
        self.auth = auth_service
        
        # Initialize components
        self.message_builder = MessageBuilder()
        
        # Initialize handlers
        self.role_selector = RoleSelector(db, whatsapp, auth_service, self.message_builder)
        self.auto_login = AutoLoginHandler(db, whatsapp, auth_service, self.message_builder)
    
    def handle_login(self, phone: str, message: str) -> Dict:
        """Handle login for existing user"""
        try:
            # Check if user is responding to role selection
            msg_lower = message.lower().strip()
            
            if msg_lower in ['login_trainer', 'login as trainer', 'trainer', '💪 login as trainer']:
                return self.role_selector.login_as_role(phone, 'trainer')
            
            elif msg_lower in ['login_client', 'login as client', 'client', '🏃 login as client']:
                return self.role_selector.login_as_role(phone, 'client')
            
            # First time - check roles and auto-login or show selection
            return self.auto_login.handle_auto_login(phone)
                
        except Exception as e:
            return self.handle_flow_error(phone, None, e, 'login', 'login handling')
    
    def handle_role_selection(self, phone: str, role: str) -> Dict:
        """Handle role selection from button clicks"""
        try:
            log_info(f"Role selection from button: {role} for {phone}")
            return self.role_selector.login_as_role(phone, role)
                
        except Exception as e:
            return self.handle_flow_error(phone, None, e, 'login', f'role selection for {role}')