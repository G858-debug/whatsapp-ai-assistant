"""
User Manager
Handles user CRUD operations and basic user management
"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error


class UserManager:
    """Manages user data and basic operations"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def check_user_exists(self, phone: str) -> Optional[Dict]:
        """
        Check if user exists in users table
        Returns user data if found, None otherwise
        """
        try:
            result = self.db.table('users').select('*').eq(
                'phone_number', phone
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            log_error(f"Error checking user existence: {str(e)}")
            return None
    
    def create_user_entry(self, phone: str, role: str, role_id: str) -> bool:
        """
        Create or update user entry in users table
        """
        try:
            existing_user = self.check_user_exists(phone)
            
            if existing_user:
                # Update existing user with new role
                update_data = {
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }
                
                if role == 'trainer':
                    update_data['trainer_id'] = role_id
                else:
                    update_data['client_id'] = role_id
                
                result = self.db.table('users').update(update_data).eq(
                    'phone_number', phone
                ).execute()
                
                log_info(f"Updated user entry for {phone} with {role} role")
            else:
                # Create new user
                user_data = {
                    'phone_number': phone,
                    'login_status': None,
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }
                
                if role == 'trainer':
                    user_data['trainer_id'] = role_id
                else:
                    user_data['client_id'] = role_id
                
                result = self.db.table('users').insert(user_data).execute()
                
                log_info(f"Created new user entry for {phone} as {role}")
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error creating user entry: {str(e)}")
            return False
    
    def get_user_id_by_role(self, phone: str, role: str) -> Optional[str]:
        """
        Get trainer_id or client_id for user based on role
        """
        try:
            user = self.check_user_exists(phone)
            if not user:
                return None
            
            if role == 'trainer':
                return user.get('trainer_id')
            elif role == 'client':
                return user.get('client_id')
            
            return None
            
        except Exception as e:
            log_error(f"Error getting user ID by role: {str(e)}")
            return None
    
    def delete_user_role(self, phone: str, role: str) -> bool:
        """
        Delete user's role data (for account deletion)
        Returns True if successful
        """
        try:
            user = self.check_user_exists(phone)
            if not user:
                return False
            
            role_id = user.get(f'{role}_id')
            if not role_id:
                return False
            
            # Delete from role table
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            self.db.table(table).delete().eq(id_column, role_id).execute()
            
            # Update users table
            update_data = {
                f'{role}_id': None,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # If no other role exists, delete user entry
            other_role = 'client' if role == 'trainer' else 'trainer'
            other_role_id = user.get(f'{other_role}_id')
            
            if not other_role_id:
                # Delete user completely
                self.db.table('users').delete().eq('phone_number', phone).execute()
                log_info(f"Deleted user entry for {phone}")
            else:
                # Just remove this role
                self.db.table('users').update(update_data).eq(
                    'phone_number', phone
                ).execute()
                log_info(f"Removed {role} role for {phone}")
            
            return True
            
        except Exception as e:
            log_error(f"Error deleting user role: {str(e)}")
            return False