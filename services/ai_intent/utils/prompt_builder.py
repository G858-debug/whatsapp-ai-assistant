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
- "stop" → {{"intent": "stop", "confidence": 0.95, "needs_action": true, "suggested_command": "/stop"}}
- "cancel" → {{"intent": "stop", "confidence": 0.9, "needs_action": true, "suggested_command": "/stop"}}
- "quit" → {{"intent": "stop", "confidence": 0.85, "needs_action": true, "suggested_command": "/stop"}}
- "show my clients" (trainer) → {{"intent": "view_trainees", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainees"}}
- "view my trainers" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "assign habit to client" (trainer) → {{"intent": "assign_habit", "confidence": 0.9, "needs_action": true, "suggested_command": "/assign-habit"}}
- "remove habit from trainee" (trainer) → {{"intent": "unassign_habit", "confidence": 0.9, "needs_action": true, "suggested_command": "/unassign-habit"}}
- "unassign habit" (trainer) → {{"intent": "unassign_habit", "confidence": 0.9, "needs_action": true, "suggested_command": "/unassign-habit"}}
- "list my trainees" (trainer) → {{"intent": "view_trainees", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainees"}}
- "see trainer list" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "view trainer" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "view trainers" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "show trainers" (client) → {{"intent": "view_trainers", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-trainers"}}
- "show my dashboard" (trainer) → {{"intent": "view_dashboard", "confidence": 0.9, "needs_action": true, "suggested_command": "/trainer-dashboard"}}
- "trainer dashboard" (trainer) → {{"intent": "view_dashboard", "confidence": 0.9, "needs_action": true, "suggested_command": "/trainer-dashboard"}}
- "dashboard" (trainer) → {{"intent": "view_dashboard", "confidence": 0.85, "needs_action": true, "suggested_command": "/trainer-dashboard"}}
- "client progress dashboard" (trainer) → {{"intent": "view_client_progress", "confidence": 0.9, "needs_action": true, "suggested_command": "/client-progress"}}
- "view client progress" (trainer) → {{"intent": "view_client_progress", "confidence": 0.9, "needs_action": true, "suggested_command": "/client-progress"}}
- "show trainee progress" (trainer) → {{"intent": "view_client_progress", "confidence": 0.9, "needs_action": true, "suggested_command": "/client-progress"}}
- "set up reminders" (client) → {{"intent": "reminder_settings", "confidence": 0.9, "needs_action": true, "suggested_command": "/reminder-settings"}}
- "change reminder time" (client) → {{"intent": "reminder_settings", "confidence": 0.9, "needs_action": true, "suggested_command": "/reminder-settings"}}
- "disable reminders" (client) → {{"intent": "reminder_settings", "confidence": 0.9, "needs_action": true, "suggested_command": "/reminder-settings"}}
- "reminder settings" (client) → {{"intent": "reminder_settings", "confidence": 0.9, "needs_action": true, "suggested_command": "/reminder-settings"}}
- "test my reminder" (client) → {{"intent": "test_reminder", "confidence": 0.9, "needs_action": true, "suggested_command": "/test-reminder"}}
- "send test reminder" (client) → {{"intent": "test_reminder", "confidence": 0.9, "needs_action": true, "suggested_command": "/test-reminder"}}
- "create new client" (trainer) → {{"intent": "create_trainee", "confidence": 0.95, "needs_action": true, "suggested_command": "/create-trainee"}}
- "I'd like to add a client" (trainer) → {{"intent": "create_trainee", "confidence": 0.95, "needs_action": true, "suggested_command": "/create-trainee"}}
- "add a client" (trainer) → {{"intent": "create_trainee", "confidence": 0.95, "needs_action": true, "suggested_command": "/create-trainee"}}
- "add client" (trainer) → {{"intent": "create_trainee", "confidence": 0.95, "needs_action": true, "suggested_command": "/create-trainee"}}
- "I want to add a client" (trainer) → {{"intent": "create_trainee", "confidence": 0.95, "needs_action": true, "suggested_command": "/create-trainee"}}
- "can I add a client" (trainer) → {{"intent": "create_trainee", "confidence": 0.9, "needs_action": true, "suggested_command": "/create-trainee"}}
- "how do I add a client" (trainer) → {{"intent": "create_trainee", "confidence": 0.9, "needs_action": true, "suggested_command": "/create-trainee"}}
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
- Help (/help)
- Stop current task (/stop)

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
- Unassign habits from clients (/unassign-habit)
- View all habits (/view-habits)
- View client progress (/view-trainee-progress)
- Client progress dashboard (/client-progress)
- Generate client reports (/trainee-weekly-report, /trainee-monthly-report)

Available Features (Dashboard):
- Main trainer dashboard (/trainer-dashboard)
- Client progress dashboard (/client-progress)
"""
        else:
            return """
Available Features (Phase 1):
- View profile (/view-profile)
- Edit profile (/edit-profile)
- Delete account (/delete-account)
- Help (/help)
- Stop current task (/stop)

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

Available Features (Reminders):
- Configure reminder settings (/reminder-settings)
- Test reminder message (/test-reminder)
"""