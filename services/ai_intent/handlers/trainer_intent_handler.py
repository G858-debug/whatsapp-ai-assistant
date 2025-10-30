"""
Trainer Intent Handler
Handles trainer-specific intents (Phase 2 & 3)
"""
from typing import Dict, List
from utils.logger import log_error


class TrainerIntentHandler:
    """Handles trainer-specific intents"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported trainer intents"""
        return [
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
    
    def handle_intent(self, phone: str, intent_type: str, intent: Dict, context: Dict) -> Dict:
        """Handle trainer intent"""
        try:
            name = context.get('name', 'there')
            
            # Phase 2: Relationship intents
            if intent_type == 'invite_trainee':
                return self._handle_invite_trainee(phone, name, intent, context)
            elif intent_type == 'create_trainee':
                return self._handle_create_trainee(phone, name, intent, context)
            elif intent_type == 'view_trainees':
                return self._handle_view_trainees(phone, name, intent, context)
            elif intent_type == 'remove_trainee':
                return self._handle_remove_trainee(phone, name, intent, context)
            
            # Phase 3: Habit intents
            elif intent_type == 'create_habit':
                return self._handle_create_habit(phone, name, intent, context)
            elif intent_type == 'edit_habit':
                return self._handle_edit_habit(phone, name, intent, context)
            elif intent_type == 'delete_habit':
                return self._handle_delete_habit(phone, name, intent, context)
            elif intent_type == 'assign_habit':
                return self._handle_assign_habit(phone, name, intent, context)
            elif intent_type == 'view_habits':
                return self._handle_view_habits(phone, name, intent, context)
            elif intent_type == 'view_trainee_progress':
                return self._handle_view_trainee_progress(phone, name, intent, context)
            elif intent_type == 'trainee_report':
                return self._handle_trainee_report(phone, name, intent, context)
            
            else:
                return self._unknown_trainer_intent(phone, name, intent_type)
                
        except Exception as e:
            log_error(f"Error handling trainer intent: {str(e)}")
            return self._error_response(phone)
    
    # Phase 2: Relationship Intent Handlers
    
    def _handle_invite_trainee(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle invite trainee intent"""
        msg = (
            f"Sure {name}! I can help you invite a client.\n\n"
            f"Click the button below or type /invite-trainee"
        )
        buttons = [{'id': '/invite-trainee', 'title': '📨 Invite Client'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_invite_trainee'
        }
    
    def _handle_create_trainee(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle create trainee intent"""
        msg = (
            f"I can help you create a new client account, {name}!\n\n"
            f"Click the button below or type /create-trainee"
        )
        buttons = [{'id': '/create-trainee', 'title': '➕ Create Client'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_create_trainee'
        }
    
    def _handle_view_trainees(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view trainees intent"""
        msg = (
            f"Let me show you your clients, {name}!\n\n"
            f"Click the button below or type /view-trainees"
        )
        buttons = [{'id': '/view-trainees', 'title': '👥 View Trainees'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_trainees'
        }
    
    def _handle_remove_trainee(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle remove trainee intent"""
        msg = (
            f"I can help you remove a client, {name}.\n\n"
            f"Click the button below or type /remove-trainee"
        )
        buttons = [{'id': '/remove-trainee', 'title': '🗑️ Remove Client'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_remove_trainee'
        }
    
    # Phase 3: Habit Intent Handlers
    
    def _handle_create_habit(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle create habit intent"""
        msg = (
            f"Great idea, {name}! I can help you create a new habit.\n\n"
            f"Click the button below or type /create-habit"
        )
        buttons = [{'id': '/create-habit', 'title': '🎯 Create Habit'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_create_habit'
        }
    
    def _handle_edit_habit(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle edit habit intent"""
        msg = (
            f"I can help you edit a habit, {name}!\n\n"
            f"Click the button below or type /edit-habit"
        )
        buttons = [{'id': '/edit-habit', 'title': '✏️ Edit Habit'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_edit_habit'
        }
    
    def _handle_delete_habit(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle delete habit intent"""
        msg = (
            f"I can help you delete a habit, {name}.\n\n"
            f"Click the button below or type /delete-habit"
        )
        buttons = [{'id': '/delete-habit', 'title': '🗑️ Delete Habit'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_delete_habit'
        }
    
    def _handle_assign_habit(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle assign habit intent"""
        msg = (
            f"I can help you assign a habit to a client, {name}!\n\n"
            f"Click the button below or type /assign-habit"
        )
        buttons = [{'id': '/assign-habit', 'title': '📋 Assign Habit'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_assign_habit'
        }
    
    def _handle_view_habits(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view habits intent"""
        msg = (
            f"Let me show you all your habits, {name}!\n\n"
            f"Click the button below or type /view-habits"
        )
        buttons = [{'id': '/view-habits', 'title': '📋 View Habits'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_habits'
        }
    
    def _handle_view_trainee_progress(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view trainee progress intent"""
        msg = (
            f"I can show you client progress, {name}!\n\n"
            f"Click the button below or type /view-trainee-progress"
        )
        buttons = [{'id': '/view-trainee-progress', 'title': '📊 View Progress'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_trainee_progress'
        }
    
    def _handle_trainee_report(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle trainee report intent"""
        msg = (
            f"I can generate client reports, {name}!\n\n"
            f"Choose a report type:"
        )
        buttons = [
            {'id': '/trainee-weekly-report', 'title': '📅 Weekly Report'},
            {'id': '/trainee-monthly-report', 'title': '📊 Monthly Report'}
        ]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_trainee_report'
        }
    
    def _unknown_trainer_intent(self, phone: str, name: str, intent_type: str) -> Dict:
        """Handle unknown trainer intent"""
        msg = (
            f"I'm not sure how to help with that, {name}.\n\n"
            f"Here are some trainer features:"
        )
        buttons = [
            {'id': '/view-trainees', 'title': '👥 View Trainees'},
            {'id': '/view-habits', 'title': '📋 View Habits'},
            {'id': '/help', 'title': '📚 Show Help'}
        ]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_unknown_trainer'
        }
    
    def _error_response(self, phone: str) -> Dict:
        """Handle error response"""
        msg = "Sorry, I encountered an error processing your trainer request."
        self.whatsapp.send_message(phone, msg)
        
        return {
            'success': False,
            'response': msg,
            'handler': 'ai_intent_trainer_error'
        }