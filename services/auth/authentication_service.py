"""
Authentication Service - Phase 1
Handles user authentication, login status, and role management
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
import pytz
import random
import string
from utils.logger import log_info, log_error


class AuthenticationService:
    """Manages user authentication and login status"""
    
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
    
    def get_user_roles(self, phone: str) -> Dict[str, bool]:
        """
        Check which roles user has (trainer, client, or both)
        Returns: {'trainer': bool, 'client': bool}
        """
        try:
            user = self.check_user_exists(phone)
            if not user:
                return {'trainer': False, 'client': False}
            
            return {
                'trainer': user.get('trainer_id') is not None,
                'client': user.get('client_id') is not None
            }
            
        except Exception as e:
            log_error(f"Error getting user roles: {str(e)}")
            return {'trainer': False, 'client': False}
    
    def get_login_status(self, phone: str) -> Optional[str]:
        """
        Get current login status for user
        Returns: 'trainer', 'client', or None
        """
        try:
            user = self.check_user_exists(phone)
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
    
    def auto_login_single_role(self, phone: str) -> Tuple[bool, Optional[str], str]:
        """
        Automatically login user if they have only one role
        Returns: (success, role, message)
        """
        try:
            roles = self.get_user_roles(phone)
            
            if roles['trainer'] and not roles['client']:
                # Only trainer role
                self.set_login_status(phone, 'trainer')
                message = ("✅ You are logged in as *Trainer* now.\n\n"
                          "You can ask me for any trainer related tasks to perform.\n"
                          "You can also ask to logout and then register as client.")
                return True, 'trainer', message
            
            elif roles['client'] and not roles['trainer']:
                # Only client role
                self.set_login_status(phone, 'client')
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
    
    def verify_role_exists(self, phone: str, role: str) -> bool:
        """
        Verify that user has the specified role in the respective table
        """
        try:
            user = self.check_user_exists(phone)
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
