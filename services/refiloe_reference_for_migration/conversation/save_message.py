"""
Save Message
Save message to history
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def save_message(self, phone: str, message: str, sender: str, 
                intent: str = None) -> bool:
    """Save message to history"""
    try:
        message_data = {
            'phone_number': phone,
            'message': message,
            'sender': sender,  # 'user' or 'bot'
            'intent': intent,
            'created_at': datetime.now(self.sa_tz).isoformat()
        }
        
        result = self.db.table('message_history').insert(
            message_data
        ).execute()
        
        return bool(result.data)
        
    except Exception as e:
        log_error(f"Error saving message: {str(e)}")
        return False
