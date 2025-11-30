"""
Update Conversation State
Update or create conversation state
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def update_conversation_state(self, phone: str, state: str, 
                                context: Dict = None) -> bool:
    """Update or create conversation state"""
    try:
        # First try to get existing state
        existing = self.db.table('conversation_states').select('id').eq(
            'phone_number', phone
        ).execute()
        
        update_data = {
            'phone_number': phone,  # Include phone for insert
            'state': state,
            'context': context or {},
            'updated_at': datetime.now(self.sa_tz).isoformat()
        }
        
        if existing.data:
            # Update existing row
            result = self.db.table('conversation_states').update(
                update_data
            ).eq('phone_number', phone).execute()
            log_info(f"Updated conversation state for {phone}: {state}")
        else:
            # Insert new row
            update_data['created_at'] = datetime.now(self.sa_tz).isoformat()
            result = self.db.table('conversation_states').insert(
                update_data
            ).execute()
            log_info(f"Created new conversation state for {phone}: {state}")
        
        return bool(result.data)
        
    except Exception as e:
        log_error(f"Error updating conversation state: {str(e)}")
        return False
