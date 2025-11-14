"""
Trainer Intent Handler
Handles trainer-specific intents (Phase 2 & 3)
"""
from typing import Dict, List
from utils.logger import log_error


class TrainerIntentHandler:
    """Handles trainer-specific intents"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
    
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
            'unassign_habit',
            'view_habits',
            'view_trainee_progress',
            'trainee_report',
            # Dashboard intents
            'view_dashboard',
            'view_client_progress'
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
            elif intent_type == 'unassign_habit':
                return self._handle_unassign_habit(phone, name, intent, context)
            elif intent_type == 'view_habits':
                return self._handle_view_habits(phone, name, intent, context)
            elif intent_type == 'view_trainee_progress':
                return self._handle_view_trainee_progress(phone, name, intent, context)
            elif intent_type == 'trainee_report':
                return self._handle_trainee_report(phone, name, intent, context)
            
            # Dashboard intents
            elif intent_type == 'view_dashboard':
                return self._handle_view_dashboard(phone, name, intent, context)
            elif intent_type == 'view_client_progress':
                return self._handle_view_client_progress(phone, name, intent, context)
            elif intent_type == 'view_progress':
                return self._handle_view_progress(phone, name, intent, context)
            elif intent_type == 'dashboard':
                return self._handle_dashboard(phone, name, intent, context)
            
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
        # Create the add_client_choice task before sending buttons
        task_id = self.task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='add_client_choice',
            task_data={
                'step': 'choose_input_method',
                'trainer_id': context.get('user_id')
            }
        )

        # Check if task creation failed
        if not task_id:
            msg = "❌ I couldn't start the process. Please try again."
            self.whatsapp.send_message(phone, msg)
            return {
                'success': False,
                'response': msg,
                'handler': 'ai_intent_create_trainee_task_failed'
            }

        # Send the button message
        msg = (
            f"Perfect! Let's add your new client, {name}! 💪\n\n"
            f"Would you like to:\n"
            f"1️⃣ Type in their contact details manually\n"
            f"2️⃣ Share their contact from your phone"
        )
        buttons = [
            {'id': 'add_client_type', 'title': 'Type Details'},
            {'id': 'add_client_share', 'title': 'Share Contact'}
        ]
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
        # Check if user already has a running create_habit task (only if task_service is available)
        user_id = context.get('user_id')
        if user_id and self.task_service:
            running_task = self.task_service.get_running_task(phone, 'trainer')
            if running_task and running_task.get('task_type') == 'create_habit':
                # Don't send another create habit message if already in progress
                return {
                    'success': True,
                    'response': "You already have a habit creation in progress. Please complete it or type /stop to cancel.",
                    'handler': 'ai_intent_create_habit_already_running'
                }
        
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
    
    def _handle_unassign_habit(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle unassign habit intent"""
        msg = (
            f"I can help you unassign a habit from a client, {name}!\n\n"
            f"Click the button below or type /unassign-habit"
        )
        buttons = [{'id': '/unassign-habit', 'title': '🗑️ Unassign Habit'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_unassign_habit'
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
        buttons = [{'id': '/view-trainee-progress', 'title': '📊 Trainee Progress'}]
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
    
    # Dashboard Intent Handlers
    
    def _handle_view_dashboard(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view dashboard intent"""
        msg = (
            f"Here's your trainer dashboard, {name}!\n\n"
            f"Click the button below or type /trainer-dashboard"
        )
        buttons = [{'id': '/trainer-dashboard', 'title': '🎯 Trainer Dashboard'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_dashboard'
        }
    
    def _handle_view_client_progress(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view client progress intent"""
        msg = (
            f"I can show you detailed trainee progress, {name}!\n\n"
            f"Click the button below or type /view-trainee-progress"
        )
        buttons = [{'id': '/view-trainee-progress', 'title': '📊 Trainee Progress'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_client_progress'
        }
    
    def _handle_view_progress(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view progress intent for trainers"""
        msg = (
            f"Great! I can help you view trainee progress, {name}!\n\n"
            f"Click the button below or type /view-trainee-progress"
        )
        buttons = [{'id': '/view-trainee-progress', 'title': '📊 Trainee Progress'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_progress'
        }
    
    def _handle_dashboard(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle dashboard intent for trainers"""
        msg = (
            f"Perfect! I can show you your trainer dashboard, {name}!\n\n"
            f"Click the button below or type /trainer-dashboard"
        )
        buttons = [{'id': '/trainer-dashboard', 'title': '📊 Trainer Dashboard'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_dashboard'
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