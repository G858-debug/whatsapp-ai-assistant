"""
Create Conversation State
Create new conversation state
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def create_conversation_state(self, phone: str) -> Dict:
    """Create new conversation state"""
    try:
        state_data = {
            'phone_number': phone,
            'state': self.STATES['IDLE'],
            'context': {},
            'created_at': datetime.now(self.sa_tz).isoformat(),
            'updated_at': datetime.now(self.sa_tz).isoformat()
        }
        
        result = self.db.table('conversation_states').insert(
            state_data
        ).execute()
        
        return result.data[0] if result.data else state_data
        
    except Exception as e:
        log_error(f"Error creating conversation state: {str(e)}")
        return {'state': self.STATES['IDLE']}
