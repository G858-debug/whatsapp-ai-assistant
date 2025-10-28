"""
Fallback Response Handler
Provides fallback responses when AI is unavailable
"""
from typing import Dict
from utils.logger import log_error


class FallbackResponseHandler:
    """Handles fallback responses when AI is unavailable"""
    
    def get_fallback_response(self, phone: str, message: str, role: str, whatsapp_service) -> Dict:
        """Provide fallback response when AI is unavailable"""
        try:
            msg = self._get_fallback_message(role)
            whatsapp_service.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'ai_intent_fallback'
            }
            
        except Exception as e:
            log_error(f"Error in fallback response: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error.",
                'handler': 'ai_intent_error'
            }
    
    def _get_fallback_message(self, role: str) -> str:
        """Get appropriate fallback message for role"""
        if role == 'trainer':
            return (
                "I'm here to help! Here are some things you can do:\n\n"
                "• /view-profile - View your profile\n"
                "• /view-trainees - View your clients\n"
                "• /create-habit - Create new habits\n"
                "• /help - Show all commands\n\n"
                "What would you like to do?"
            )
        elif role == 'client':
            return (
                "I'm here to help! Here are some things you can do:\n\n"
                "• /view-profile - View your profile\n"
                "• /view-my-habits - View your habits\n"
                "• /log-habits - Log your habits\n"
                "• /help - Show all commands\n\n"
                "What would you like to do?"
            )
        else:
            return (
                "I'm here to help! Here are some things you can do:\n\n"
                "• /view-profile - View your profile\n"
                "• /edit-profile - Edit your information\n"
                "• /help - Show all commands\n\n"
                "What would you like to do?"
            )