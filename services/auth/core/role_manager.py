"""
Role Manager
Handles role management, verification, and role-based operations
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
import pytz
import random
import string
from utils.logger import log_info, log_error


class RoleManager:
    """Manages user roles and role-based operations"""
    
    def __init__(self, supabase_client, user_manager):
        self.db = supabase_client
        self.user_manager = user_manager
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def get_user_roles(self, phone: str) -> Dict[str, bool]:
        """
        Check which roles user has (trainer, client, or both)
        Returns: {'trainer': bool, 'client': bool}
        """
        try:
            user = self.user_manager.check_user_exists(phone)
            if not user:
                return {'trainer': False, 'client': False}
            
            return {
                'trainer': user.get('trainer_id') is not None,
                'client': user.get('client_id') is not None
            }
            
        except Exception as e:
            log_error(f"Error getting user roles: {str(e)}")
            return {'trainer': False, 'client': False}
    
    def verify_role_exists(self, phone: str, role: str) -> bool:
        """
        Verify that user has the specified role in the respective table
        """
        try:
            user = self.user_manager.check_user_exists(phone)
            if not user:
                return False
            
            if role == 'trainer':
                trainer_id = user.get('trainer_id')
                if not trainer_id:
                    return False
                
                result = self.db.table('trainers').select('id').eq(
                    'trainer_id', trainer_id
                ).execute()
                
                return bool(result.data and len(result.data) > 0)
            
            elif role == 'client':
                client_id = user.get('client_id')
                if not client_id:
                    return False
                
                result = self.db.table('clients').select('id').eq(
                    'client_id', client_id
                ).execute()
                
                return bool(result.data and len(result.data) > 0)
            
            return False
            
        except Exception as e:
            log_error(f"Error verifying role: {str(e)}")
            return False
    
    def generate_unique_id(self, name: str, role: str) -> str:
        """
        Generate unique 5-7 character ID based on name and date
        Format: first3-4 letters of name + 2-3 numbers
        Ensures uniqueness by checking database
        """
        try:
            # Clean name (remove spaces, special chars, convert to lowercase)
            clean_name = ''.join(c for c in name if c.isalnum()).lower()
            
            # Take first 3-4 characters
            name_part = clean_name[:4] if len(clean_name) >= 4 else clean_name[:3]
            
            # Determine which table to check
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            # Try to generate unique ID (max 10 attempts)
            for attempt in range(10):
                # Generate random numbers (2-3 digits)
                num_digits = 2 if len(name_part) == 4 else 3
                numbers = ''.join(random.choices(string.digits, k=num_digits))
                
                generated_id = f"{name_part}{numbers}"
                
                # Check if ID already exists
                result = self.db.table(table).select('id').eq(
                    id_column, generated_id
                ).execute()
                
                if not result.data or len(result.data) == 0:
                    log_info(f"Generated unique {role} ID: {generated_id}")
                    return generated_id
            
            # If all attempts failed, add timestamp
            timestamp = datetime.now(self.sa_tz).strftime('%S')
            generated_id = f"{name_part[:3]}{timestamp}"
            log_info(f"Generated fallback {role} ID: {generated_id}")
            return generated_id
            
        except Exception as e:
            log_error(f"Error generating unique ID: {str(e)}")
            # Fallback to random ID
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    
    def auto_login_single_role(self, phone: str, auth_service) -> Tuple[bool, Optional[str], str]:
        """
        Automatically login user if they have only one role
        Returns: (success, role, message)
        """
        try:
            roles = self.get_user_roles(phone)
            
            if roles['trainer'] and not roles['client']:
                # Only trainer role
                auth_service.set_login_status(phone, 'trainer')
                message = ("✅ You are logged in as *Trainer* now.\n\n"
                          "You can ask me for any trainer related tasks to perform.\n"
                          "You can also ask to logout and then Register as Trainee.")
                return True, 'trainer', message
            
            elif roles['client'] and not roles['trainer']:
                # Only client role
                auth_service.set_login_status(phone, 'client')
                message = ("✅ You are logged in as *Client* now.\n\n"
                          "You can ask me for any client related tasks to perform.\n"
                          "You can also ask to logout and then register as trainer.")
                return True, 'client', message
            
            elif roles['trainer'] and roles['client']:
                # Both roles - need to choose
                return False, None, "multiple_roles"
            
            else:
                # No roles
                return False, None, "no_roles"
            
        except Exception as e:
            log_error(f"Error in auto login: {str(e)}")
            return False, None, str(e)