"""
Prompt Builder
Constructs AI prompts for intent detection
"""
from typing import Dict
from .intent_types import IntentTypes


class PromptBuilder:
    """Builds prompts for AI intent detection"""
    
    def __init__(self):
        self.intent_types = IntentTypes()
    
    def build_intent_prompt(self, message: str, role: str, context: Dict) -> str:
        """Build intent detection prompt"""
        
        # Get available features for role
        available_features = self._get_available_features(role)
        
        # Get available intents for role
        available_intents = self.intent_types.get_intents_for_role(role)
        
        prompt = f"""You are Refiloe, an AI fitness assistant. Analyze this message from a {role}.

USER: {context.get('name', 'User')} ({role})
MESSAGE: "{message}"

CONTEXT:
- Recent tasks: {', '.join(context.get('recent_tasks', [])) or 'None'}
- Recent chat: {context.get('chat_history', [])}

{available_features}

Analyze the message and return ONLY valid JSON with:
{{
    "intent": "one of: {', '.join(available_intents)}",
    "confidence": 0.0-1.0,
    "needs_action": true/false,
    "suggested_command": "/command or null",
    "user_sentiment": "positive/neutral/negative/frustrated"
}}

Examples:
- "show me my profile" → {{"intent": "view_profile", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-profile"}}
- "I want to change my email" → {{"intent": "edit_profile", "confidence": 0.85, "needs_action": true, "suggested_command": "/edit-profile"}}
- "show my clients" (trainer) → {{"intent": "view_trainees", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainees"}}
- "view my trainers" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "list my trainees" (trainer) → {{"intent": "view_trainees", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainees"}}
- "see trainer list" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "view trainer" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "view trainers" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "show trainers" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "how do I add clients?" → {{"intent": "general_conversation", "confidence": 0.8, "needs_action": false, "is_asking_about_phase2": true}}
- "hi" → {{"intent": "general_conversation", "confidence": 0.9, "needs_action": false}}

Return ONLY the JSON, no other text."""
        
        return prompt
    
    def _get_available_features(self, role: str) -> str:
        """Get available features description for role"""
        if role == 'trainer':
            return """
Available Features (Phase 1):
- View profile (/view-profile)
- Edit profile (/edit-profile)
- Delete account (/delete-account)
- Logout (/logout)
- Switch role (/switch-role if has both roles)
- Help (/help)

Available Features (Phase 2):
- Invite existing client (/invite-trainee)
- Create new client (/create-trainee)
- View client list or manage clients (/view-trainees)
- Remove client from list (/remove-trainee)

Available Features (Phase 3):
- Create habits (/create-habit)
- Edit habits (/edit-habit)
- Delete habits (/delete-habit)
- Assign habits to clients (/assign-habit)
- View all habits (/view-habits)
- View client progress (/view-trainee-progress)
- Generate client reports (/trainee-weekly-report, /trainee-monthly-report)
"""
        else:
            return """
Available Features (Phase 1):
- View profile (/view-profile)
- Edit profile (/edit-profile)
- Delete account (/delete-account)
- Logout (/logout)
- Switch role (/switch-role if has both roles)
- Help (/help)

Available Features (Phase 2):
- Search trainers (/search-trainer)
- Invite trainer (/invite-trainer)
- View trainer list or manage trainers (/view-trainers)
- Remove trainer from list (/remove-trainer)

Available Features (Phase 3):
- View assigned habits (/view-my-habits)
- Log habits (/log-habits)
- View progress (/view-progress)
- Generate reports (/weekly-report, /monthly-report)
"""