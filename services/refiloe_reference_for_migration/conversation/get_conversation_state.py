"""
Get Conversation State
Get current conversation state for user
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def get_conversation_state(self, phone: str) -> Dict:
    """Get current conversation state for user"""
    try:
        result = self.db.table('conversation_states').select('*').eq(
            'phone_number', phone
        ).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        # Create new state
        return self.create_conversation_state(phone)
        
    except Exception as e:
        log_error(f"Error getting conversation state: {str(e)}")
        return {'state': self.STATES['IDLE']}
