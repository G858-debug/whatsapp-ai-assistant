"""
Clear Conversation State
Clear conversation state (reset to idle)
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def clear_conversation_state(self, phone: str) -> bool:
    """Clear conversation state (reset to idle)"""
    try:
        return self.update_conversation_state(phone, self.STATES['IDLE'], {})
        
    except Exception as e:
        log_error(f"Error clearing conversation state: {str(e)}")
        return False
