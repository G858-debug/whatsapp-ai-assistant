"""
Client Relationship Flow Coordinator
Main coordinator for client relationship flows - maintains backward compatibility
"""
from typing import Dict
from utils.logger import log_info, log_error
from .search_flow import SearchFlow
from .invitation_flow import InvitationFlow
from .removal_flow import RemovalFlow


class ClientRelationshipFlows:
    """Main coordinator for client relationship flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        
        # Initialize specialized flow handlers
        self.search_flow = SearchFlow(db, whatsapp, task_service)
        self.invitation_flow = InvitationFlow(db, whatsapp, task_service)
        self.removal_flow = RemovalFlow(db, whatsapp, task_service)
    
    def continue_search_trainer(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle search trainer flow - delegates to SearchFlow"""
        return self.search_flow.continue_search_trainer(phone, message, client_id, task)
    
    def continue_invite_trainer(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle invite trainer flow - delegates to InvitationFlow"""
        return self.invitation_flow.continue_invite_trainer(phone, message, client_id, task)
    
    def continue_remove_trainer(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle remove trainer flow - delegates to RemovalFlow"""
        return self.removal_flow.continue_remove_trainer(phone, message, client_id, task)