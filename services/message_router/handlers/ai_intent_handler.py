"""
AI Intent Handler
Uses AI to determine user intent and respond when no specific command or task is running
"""
from typing import Dict
from utils.logger import log_error


class AIIntentHandler:
    """Uses AI to determine user intent and respond"""
    
    def __init__(self, supabase_client, whatsapp_service, task_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.task_service = task_service
    
    def handle_ai_intent(self, phone: str, message: str, role: str, user_id: str) -> Dict:
        """Use AI to determine user intent and respond"""
        try:
            # Get recent tasks and chat history for context
            recent_tasks = self.task_service.get_recent_completed_tasks(user_id, role, limit=5)
            
            # Get chat history from message_history table
            chat_history = self._get_chat_history(phone, limit=10)
            
            # Save current message to history
            self._save_message(phone, message, 'user')
            
            # Use AI to determine intent
            from services.ai_intent import AIIntentHandler as AIIntentHandlerPhase1
            ai_handler = AIIntentHandlerPhase1(self.db, self.whatsapp)
            
            result = ai_handler.handle_intent(
                phone, message, role, user_id,
                recent_tasks, chat_history
            )
            
            # Save bot response to history
            if result.get('response'):
                self._save_message(phone, result['response'], 'bot')
            
            return result
            
        except Exception as e:
            log_error(f"Error handling AI intent: {str(e)}")
            return {
                'success': True,
                'response': (
                    "I'm here to help! Here are some things you can do:\n\n"
                    "• Type /help to see all commands\n"
                    "• Type /view-profile to see your profile\n"
                    "• Type /edit-profile to update your information\n\n"
                    "What would you like to do?"
                ),
                'handler': 'ai_intent_fallback'
            }
    
    def _get_chat_history(self, phone: str, limit: int = 10) -> list:
        """Get recent chat history"""
        try:
            result = self.db.table('message_history').select('*').eq(
                'phone_number', phone
            ).order('created_at', desc=True).limit(limit).execute()
            
            if result.data:
                # Reverse to get chronological order
                return list(reversed(result.data))
            return []
            
        except Exception as e:
            log_error(f"Error getting chat history: {str(e)}")
            return []
    
    def _save_message(self, phone: str, message: str, sender: str) -> bool:
        """Save message to history"""
        try:
            from datetime import datetime
            import pytz
            sa_tz = pytz.timezone('Africa/Johannesburg')
            
            message_data = {
                'phone_number': phone,
                'message': message[:1000],  # Limit message length
                'sender': sender,  # 'user' or 'bot'
                'created_at': datetime.now(sa_tz).isoformat()
            }
            
            self.db.table('message_history').insert(message_data).execute()
            return True
            
        except Exception as e:
            log_error(f"Error saving message: {str(e)}")
            return False