"""
Login Status Manager
Handles login status management operations
"""
from typing import Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error


class LoginStatusManager:
    """Handles login status operations"""
    
    def __init__(self, supabase_client, user_manager):
        self.db = supabase_client
        self.user_manager = user_manager
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def get_login_status(self, phone: str) -> Optional[str]:
        """
        Get current login status for user
        Returns: 'trainer', 'client', or None
        """
        try:
            user = self.user_manager.check_user_exists(phone)
            if user:
                return user.get('login_status')
            return None
            
        except Exception as e:
            log_error(f"Error getting login status: {str(e)}")
            return None
    
    def set_login_status(self, phone: str, status: Optional[str]) -> bool:
        """
        Set login status for user
        status: 'trainer', 'client', or None (for logout)
        """
        try:
            # Validate status
            if status not in ['trainer', 'client', None]:
                log_error(f"Invalid login status: {status}")
                return False
            
            # Update users table
            result = self.db.table('users').update({
                'login_status': status,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('phone_number', phone).execute()
            
            # Also update conversation_states for consistency
            self.db.table('conversation_states').update({
                'login_status': status,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('phone_number', phone).execute()
            
            log_info(f"Login status set to '{status}' for {phone}")
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error setting login status: {str(e)}")
            return False