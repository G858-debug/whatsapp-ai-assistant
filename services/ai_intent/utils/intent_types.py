"""
Intent Types
Defines available intent types for different roles
"""
from typing import List


class IntentTypes:
    """Defines and manages intent types"""
    
    def __init__(self):
        self.common_intents = [
            'view_profile',
            'edit_profile', 
            'delete_account',
            'logout',
            'switch_role',
            'help'
        ]
        
        self.trainer_intents = [
            # Phase 2: Relationship intents
            'invite_trainee',
            'create_trainee',
            'view_trainees',
            'remove_trainee',
            # Phase 3: Habit intents
            'create_habit',
            'edit_habit',
            'delete_habit',
            'assign_habit',
            'view_habits',
            'view_trainee_progress',
            'trainee_report'
        ]
        
        self.client_intents = [
            # Phase 2: Relationship intents
            'search_trainer',
            'invite_trainer',
            'view_trainers',
            'remove_trainer',
            # Phase 3: Habit intents
            'view_my_habits',
            'log_habits',
            'view_progress',
            'weekly_report',
            'monthly_report'
        ]
        
        self.universal_intents = [
            'general_conversation',
            'unclear'
        ]
    
    def get_intents_for_role(self, role: str) -> List[str]:
        """Get all available intents for a role"""
        intents = self.common_intents + self.universal_intents
        
        if role == 'trainer':
            intents.extend(self.trainer_intents)
        elif role == 'client':
            intents.extend(self.client_intents)
        
        return intents
    
    def get_common_intents(self) -> List[str]:
        """Get common intents available to both roles"""
        return self.common_intents
    
    def get_trainer_intents(self) -> List[str]:
        """Get trainer-specific intents"""
        return self.trainer_intents
    
    def get_client_intents(self) -> List[str]:
        """Get client-specific intents"""
        return self.client_intents
    
    def is_valid_intent(self, intent: str, role: str) -> bool:
        """Check if intent is valid for role"""
        return intent in self.get_intents_for_role(role)