"""
 Store Profile Edit Token
Store profile edit flow token for tracking
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _store_profile_edit_token(self, phone: str, flow_token: str, user_type: str):
    """Store profile edit flow token for tracking"""
    try:
        from datetime import datetime
        
        token_data = {
            'phone_number': phone,
            'flow_token': flow_token,
            'flow_type': f'{user_type}_profile_edit',
            'created_at': datetime.now().isoformat()
        }
        
        self.db.table('flow_tokens').insert(token_data).execute()
        log_info(f"Stored profile edit flow token for {phone}")
        
    except Exception as e:
        log_error(f"Error storing profile edit flow token: {str(e)}")
