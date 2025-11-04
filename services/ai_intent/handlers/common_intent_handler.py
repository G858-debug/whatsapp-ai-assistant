"""
Common Intent Handler
Handles intents that are available to both trainers and clients
"""
from typing import Dict, List
from utils.logger import log_error


class CommonIntentHandler:
    """Handles common intents for both roles"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported common intents"""
        return [
            'view_profile',
            'edit_profile',
            'delete_account',
            'logout',
            'switch_role',
            'help',
            'stop'
        ]
    
    def handle_intent(self, phone: str, intent_type: str, intent: Dict, context: Dict) -> Dict:
        """Handle common intent"""
        try:
            name = context.get('name', 'there')
            
            if intent_type == 'view_profile':
                return self._handle_view_profile(phone, name, intent, context)
            elif intent_type == 'edit_profile':
                return self._handle_edit_profile(phone, name, intent, context)
            elif intent_type == 'delete_account':
                return self._handle_delete_account(phone, name, intent, context)
            elif intent_type == 'logout':
                return self._handle_logout(phone, name, intent, context)
            elif intent_type == 'switch_role':
                return self._handle_switch_role(phone, name, intent, context)
            elif intent_type == 'help':
                return self._handle_help(phone, name, intent, context)
            elif intent_type == 'stop':
                return self._handle_stop(phone, name, intent, context)
            else:
                return self._unknown_common_intent(phone, name, intent_type)
                
        except Exception as e:
            log_error(f"Error handling common intent: {str(e)}")
            return self._error_response(phone)
    
    def _handle_view_profile(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle view profile intent"""
        msg = (
            f"Sure {name}! I can show you your profile.\n\n"
            f"Click the button below or type /view-profile"
        )
        buttons = [{'id': '/view-profile', 'title': '👤 View Profile'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_view_profile'
        }
    
    def _handle_edit_profile(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle edit profile intent"""
        msg = (
            f"I can help you update your profile, {name}!\n\n"
            f"Click the button below or type /edit-profile"
        )
        buttons = [{'id': '/edit-profile', 'title': '✏️ Edit Profile'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_edit_profile'
        }
    
    def _handle_delete_account(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle delete account intent"""
        msg = (
            f"I understand you want to delete your account.\n\n"
            f"⚠️ This is a permanent action. Are you sure?\n\n"
            f"Click the button below or type /delete-account"
        )
        buttons = [{'id': '/delete-account', 'title': '🗑️ Delete Account'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_delete_account'
        }
    
    def _handle_logout(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle logout intent"""
        msg = (
            f"Ready to logout, {name}?\n\n"
            f"Click the button below or type /logout"
        )
        buttons = [{'id': '/logout', 'title': '🚪 Logout'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_logout'
        }
    
    def _handle_switch_role(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle switch role intent"""
        msg = (
            f"I can help you switch roles, {name}!\n\n"
            f"Click the button below or type /switch-role"
        )
        buttons = [{'id': '/switch-role', 'title': '🔄 Switch Role'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_switch_role'
        }
    
    def _handle_help(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle help intent"""
        msg = (
            f"I'm here to help, {name}!\n\n"
            f"Click the button below to see all available commands."
        )
        buttons = [{'id': '/help', 'title': '📚 Show Help'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_help'
        }
    
    def _handle_stop(self, phone: str, name: str, intent: Dict, context: Dict) -> Dict:
        """Handle stop intent"""
        msg = (
            f"I'll stop any current task, {name}.\n\n"
            f"Click the button below or type /stop"
        )
        buttons = [{'id': '/stop', 'title': '🛑 Stop Task'}]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_stop'
        }
    
    def _unknown_common_intent(self, phone: str, name: str, intent_type: str) -> Dict:
        """Handle unknown common intent"""
        msg = (
            f"I'm not sure how to help with that, {name}.\n\n"
            f"Here are some things I can do:"
        )
        buttons = [
            {'id': '/view-profile', 'title': '👤 View Profile'},
            {'id': '/help', 'title': '📚 Show Help'}
        ]
        self.whatsapp.send_button_message(phone, msg, buttons)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'ai_intent_unknown_common'
        }
    
    def _error_response(self, phone: str) -> Dict:
        """Handle error response"""
        msg = "Sorry, I encountered an error processing your request."
        self.whatsapp.send_message(phone, msg)
        
        return {
            'success': False,
            'response': msg,
            'handler': 'ai_intent_common_error'
        }