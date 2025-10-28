"""
Message History Manager
Handles saving and retrieving message history for context
"""
from typing import List, Dict
from utils.logger import log_error


class MessageHistoryManager:
    """Manages message history for chat context"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
    
    def get_chat_history(self, phone: str, limit: int = 10) -> List[Dict]:
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
    
    def save_message(self, phone: str, message: str, sender: str) -> bool:
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
    
    def clear_history(self, phone: str, days_old: int = 30) -> bool:
        """Clear old message history"""
        try:
            from datetime import datetime, timedelta
            import pytz
            sa_tz = pytz.timezone('Africa/Johannesburg')
            
            cutoff_date = datetime.now(sa_tz) - timedelta(days=days_old)
            
            self.db.table('message_history').delete().eq(
                'phone_number', phone
            ).lt('created_at', cutoff_date.isoformat()).execute()
            
            return True
            
        except Exception as e:
            log_error(f"Error clearing message history: {str(e)}")
            return False