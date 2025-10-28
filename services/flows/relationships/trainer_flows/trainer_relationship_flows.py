"""
Trainer Relationship Flow Coordinator
Main coordinator for trainer relationship flows - maintains backward compatibility
"""
from typing import Dict
from utils.logger import log_info, log_error
from .invitation_flow import InvitationFlow
from .creation_flow import CreationFlow
from .removal_flow import RemovalFlow


class TrainerRelationshipFlows:
    """Main coordinator for trainer relationship flows"""
    
    def __init__(self, db, whatsapp, task_service, reg_service=None):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.reg_service = reg_service
        
        # Initialize specialized flow handlers
        self.invitation_flow = InvitationFlow(db, whatsapp, task_service)
        self.creation_flow = CreationFlow(db, whatsapp, task_service, reg_service)
        self.removal_flow = RemovalFlow(db, whatsapp, task_service)
    
    def continue_invite_trainee(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle invite existing client flow - delegates to InvitationFlow"""
        return self.invitation_flow.continue_invite_trainee(phone, message, trainer_id, task)
    
    def continue_create_trainee(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle create new client flow - delegates to CreationFlow"""
        return self.creation_flow.continue_create_trainee(phone, message, trainer_id, task)
    
    def continue_remove_trainee(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle remove client flow - delegates to RemovalFlow"""
        return self.removal_flow.continue_remove_trainee(phone, message, trainer_id, task)