"""
Authentication Service - Enhanced Structure
Main coordinator for authentication with delegation to specialized managers
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

# Import specialized managers
from .core.login_status_manager import LoginStatusManager
from .core.user_manager import UserManager
from .core.role_manager import RoleManager


class AuthenticationService:
    """
    Main authentication service coordinator.
    Delegates to specialized managers while maintaining backward compatibility.
    """
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize specialized managers
        self.user_manager = UserManager(supabase_client)
        self.role_manager = RoleManager(supabase_client, self.user_manager)
        self.login_status_manager = LoginStatusManager(supabase_client, self.user_manager)
    
    # Delegate to UserManager
    def check_user_exists(self, phone: str) -> Optional[Dict]:
        """Check if user exists in users table"""
        return self.user_manager.check_user_exists(phone)
    
    def create_user_entry(self, phone: str, role: str, role_id: str) -> bool:
        """Create or update user entry in users table"""
        return self.user_manager.create_user_entry(phone, role, role_id)
    
    def get_user_id_by_role(self, phone: str, role: str) -> Optional[str]:
        """Get trainer_id or client_id for user based on role"""
        return self.user_manager.get_user_id_by_role(phone, role)
    
    def delete_user_role(self, phone: str, role: str) -> bool:
        """Delete user's role data (for account deletion)"""
        return self.user_manager.delete_user_role(phone, role)
    
    # Delegate to RoleManager
    def get_user_roles(self, phone: str) -> Dict[str, bool]:
        """Check which roles user has (trainer, client, or both)"""
        return self.role_manager.get_user_roles(phone)
    
    def verify_role_exists(self, phone: str, role: str) -> bool:
        """Verify that user has the specified role in the respective table"""
        return self.role_manager.verify_role_exists(phone, role)
    
    def generate_unique_id(self, name: str, role: str) -> str:
        """Generate unique ID based on name and role"""
        return self.role_manager.generate_unique_id(name, role)
    
    def auto_login_single_role(self, phone: str) -> Tuple[bool, Optional[str], str]:
        """Automatically login user if they have only one role"""
        return self.role_manager.auto_login_single_role(phone, self)
    
    # Delegate to LoginStatusManager
    def get_login_status(self, phone: str) -> Optional[str]:
        """Get current login status for user"""
        return self.login_status_manager.get_login_status(phone)
    
    def set_login_status(self, phone: str, status: Optional[str]) -> bool:
        """Set login status for user"""
        return self.login_status_manager.set_login_status(phone, status)
    

