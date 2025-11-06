"""
Client Intent Handler
Handles client-specific intents (Phase 2 & 3)
"""
from typing import Dict, List
from utils.logger import log_error


class ClientIntentHandler:
    """Handles client-specific intents"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported client intents"""
        return [
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
            'monthly_report',
            # Reminder intents
            'reminder_settings',
            'test_reminder'
        ]
    
    def handle_intent(self, phone: str, intent_type: str, intent: Dict, context: Dict) -> Dict:
        """Handle client intent"""
        try:
            name = context.get('name', 'there')
            
            # Phase 2: Relationship intents
            if intent_type == 'search_trainer':
                return self._handle_search_trainer(phone, name, intent, context)
            elif intent_type == 'invite_trainer':
                return self._handle_invite_trainer(phone, name, intent, context)
            elif intent_type == 'view_trainers':
                return self._handle_view_trainers(phone, name, intent, context)
            elif intent_type == 'remove_trainer':
                return self._handle_remove_trainer(phone, name, intent, context)
            
            # Phase 3: Habit intents
            elif intent_type == 'view_my_habits':
                return self._handle_view_my_habits(phone, name, intent, context)
            elif intent_type == 'log_habits':
                return self._handle_log_habits(phone, name, intent, context)
            elif intent_type == 'view_progress':
                return self._handle_view_progress(phone, name, intent, context)
            elif intent_type == 'weekly_report':
                return self._handle_weekly_report(phone, name, intent, context)
            elif intent_type == 'monthly_report':
                return self._handle_monthly_report(phone, name, intent, context)
            
            # Reminder intents
            elif intent_type == 'reminder_settings':
                return self._handle_reminder_settings(phone, name, intent, context)
            elif intent_type == 'test_reminder':
                return self._handle_test_reminder(phone, name, intent, context)
            
            else:
                return self._unknown_client_intent(phone, name, intent_type)
                
        except Exception as e:
            log_error(f"Error handling client intent: {str(e)}")
            return self._error_response(phone)
    
    # Phase 2: Relationship Intent Handlers
    
    def _handle_search_trainer(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle search trainer intent"""
        msg = (
            f"I can help you search for trainers, {name}!\n\n"
            f"Click the button below or type /search-trainer"
        )
        buttons = [{'id': '/search-trainer', 'title': '🔍 Search Trainers'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_search_trainer'
        }
    
    def _handle_invite_trainer(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle invite trainer intent"""
        msg = (
            f"Sure {name}! I can help you invite a trainer.\n\n"
            f"Click the button below or type /invite-trainer"
        )
        buttons = [{'id': '/invite-trainer', 'title': '📨 Invite Trainer'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_invite_trainer'
        }
    
    def _handle_view_trainers(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view trainers intent"""
        msg = (
            f"Let me show you your trainers, {name}!\n\n"
            f"Click the button below or type /view-trainers"
        )
        buttons = [{'id': '/view-trainers', 'title': '👥 View Trainers'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_trainers'
        }
    
    def _handle_remove_trainer(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle remove trainer intent"""
        msg = (
            f"I can help you remove a trainer, {name}.\n\n"
            f"Click the button below or type /remove-trainer"
        )
        buttons = [{'id': '/remove-trainer', 'title': '🗑️ Remove Trainer'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_remove_trainer'
        }
    
    # Phase 3: Habit Intent Handlers
    
    def _handle_view_my_habits(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view my habits intent"""
        msg = (
            f"Let me show you your habits, {name}!\n\n"
            f"Click the button below or type /view-my-habits"
        )
        buttons = [{'id': '/view-my-habits', 'title': '📋 View My Habits'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_my_habits'
        }
    
    def _handle_log_habits(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle log habits intent"""
        msg = (
            f"Great! I can help you log your habits, {name}!\n\n"
            f"Click the button below or type /log-habits"
        )
        buttons = [{'id': '/log-habits', 'title': '✅ Log Habits'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_log_habits'
        }
    
    def _handle_view_progress(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view progress intent"""
        msg = (
            f"I can show you your progress, {name}!\n\n"
            f"Click the button below or type /view-progress"
        )
        buttons = [{'id': '/view-progress', 'title': '📊 View Progress'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_progress'
        }
    
    def _handle_weekly_report(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle weekly report intent"""
        msg = (
            f"I can generate your weekly report, {name}!\n\n"
            f"Click the button below or type /weekly-report"
        )
        buttons = [{'id': '/weekly-report', 'title': '📅 Weekly Report'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_weekly_report'
        }
    
    def _handle_monthly_report(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle monthly report intent"""
        msg = (
            f"I can generate your monthly report, {name}!\n\n"
            f"Click the button below or type /monthly-report"
        )
        buttons = [{'id': '/monthly-report', 'title': '📊 Monthly Report'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_monthly_report'
        }
    
    # Reminder Intent Handlers
    
    def _handle_reminder_settings(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle reminder settings intent"""
        msg = (
            f"I can help you configure your habit reminders, {name}!\n\n"
            f"Click the button below or type /reminder-settings"
        )
        buttons = [{'id': '/reminder-settings', 'title': '⚙️ Reminder Settings'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_reminder_settings'
        }
    
    def _handle_test_reminder(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle test reminder intent"""
        msg = (
            f"I can send you a test reminder, {name}!\n\n"
            f"Click the button below or type /test-reminder"
        )
        buttons = [{'id': '/test-reminder', 'title': '🧪 Test Reminder'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_test_reminder'
        }
    
    def _unknown_client_intent(self, phone: str, name: str, intent_type: str) -> Dict:
        """Handle unknown client intent"""
        msg = (
            f"I'm not sure how to help with that, {name}.\n\n"
            f"Here are some client features:"
        )
        buttons = [
            {'id': '/view-my-habits', 'title': '📋 View Habits'},
            {'id': '/view-trainers', 'title': '👥 View Trainers'},
            {'id': '/help', 'title': '📚 Show Help'}
        ]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_unknown_client'
        }
    
    def _error_response(self, phone: str) -> Dict:
        """Handle error response"""
        msg = "Sorry, I encountered an error processing your client request."
        self.whatsapp.send_message(phone, msg)
        
        return {
            'success': False,
            'response': msg,
            'handler': 'ai_intent_client_error'
        }