"""
Get Conversation History
Get recent conversation history
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def get_conversation_history(self, phone: str, limit: int = 10) -> List[Dict]:
    """Get recent conversation history"""
    try:
        result = self.db.table('message_history').select('*').eq(
            'phone_number', phone
        ).order('created_at', desc=True).limit(limit).execute()
        
        # Reverse to get chronological order
        return list(reversed(result.data)) if result.data else []
        
    except Exception as e:
        log_error(f"Error getting conversation history: {str(e)}")
        return []
