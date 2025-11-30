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
        
        Fallback strategy:
        1. Check users table
        2. If not found, check trainers table by whatsapp
        3. If not found, check clients table by whatsapp
        4. If found in trainer/client, create users entry and return it
        
        Returns user data if found, None otherwise
        """
        try:
            # Clean phone number (remove + and other formatting)
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            
            # Step 1: Check users table
            result = self.db.table('users').select('*').eq(
                'phone_number', clean_phone
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Step 2: Fallback - Check trainers table
            # trainers.whatsapp stores phone WITH + (e.g., +27123456789)
            log_info(f"User not found in users table, checking trainers table for {phone}")
            trainer_result = self.db.table('trainers').select('*').eq(
                'whatsapp', phone  # Use original phone format (with +)
            ).execute()
            
            if trainer_result.data and len(trainer_result.data) > 0:
                trainer = trainer_result.data[0]
                trainer_id = trainer.get('trainer_id')
                log_info(f"Found trainer {trainer_id} in trainers table, creating users entry")
                
                # Create users entry with cleaned phone number
                user_data = {
                    'phone_number': clean_phone,  # users table uses cleaned format
                    'trainer_id': trainer_id,
                    'login_status': None,  # Will be set on login
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }
                
                user_result = self.db.table('users').insert(user_data).execute()
                if user_result.data:
                    log_info(f"Created users entry for trainer {trainer_id}")
                    return user_result.data[0]
            
            # Step 3: Fallback - Check clients table
            # clients.whatsapp stores phone WITH + (e.g., +27123456789)
            log_info(f"User not found in trainers table, checking clients table for {phone}")
            client_result = self.db.table('clients').select('*').eq(
                'whatsapp', phone  # Use original phone format (with +)
            ).execute()
            
            if client_result.data and len(client_result.data) > 0:
                client = client_result.data[0]
                client_id = client.get('client_id')
                log_info(f"Found client {client_id} in clients table, creating users entry")
                
                # Create users entry with cleaned phone number
                user_data = {
                    'phone_number': clean_phone,  # users table uses cleaned format
                    'client_id': client_id,
                    'login_status': None,  # Will be set on login
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }
                
                user_result = self.db.table('users').insert(user_data).execute()
                if user_result.data:
                    log_info(f"Created users entry for client {client_id}")
                    return user_result.data[0]
            
            # Not found anywhere
            return None
            
        except Exception as e:
            log_error(f"Error checking user existence: {str(e)}")
            return None
    
    def create_user_entry(self, phone: str, role: str, role_id: str) -> bool:
        """
        Create or update user entry in users table
        """
        try:
            # Clean phone number (remove + and other formatting)
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            
            existing_user = self.check_user_exists(clean_phone)
            
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
                    'phone_number', clean_phone
                ).execute()
                
                log_info(f"Updated user entry for {clean_phone} with {role} role")
            else:
                # Create new user
                user_data = {
                    'phone_number': clean_phone,
                    'login_status': None,
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }
                
                if role == 'trainer':
                    user_data['trainer_id'] = role_id
                else:
                    user_data['client_id'] = role_id
                
                result = self.db.table('users').insert(user_data).execute()
                
                log_info(f"Created new user entry for {clean_phone} as {role}")
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error creating user entry: {str(e)}")
            return False
    
    def get_user_id_by_role(self, phone: str, role: str) -> Optional[str]:
        """
        Get trainer_id or client_id for user based on role
        """
        try:
            # Clean phone number (remove + and other formatting)
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            user = self.check_user_exists(clean_phone)
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
            # Clean phone number (remove + and other formatting)
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            user = self.check_user_exists(clean_phone)
            if not user:
                return False
            
            role_id = user.get(f'{role}_id')
            if not role_id:
                return False
            
            # Delete all related data first
            self._delete_role_related_data(role_id, role, clean_phone)
            
            # Delete from role table
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            self.db.table(table).delete().eq(id_column, role_id).execute()
            log_info(f"Deleted {role} record for {role_id}")
            
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
                self.db.table('users').delete().eq('phone_number', clean_phone).execute()
                log_info(f"Deleted user entry for {clean_phone}")
            else:
                # Just remove this role
                self.db.table('users').update(update_data).eq(
                    'phone_number', clean_phone
                ).execute()
                log_info(f"Removed {role} role for {clean_phone}")
            
            return True
            
        except Exception as e:
            log_error(f"Error deleting user role: {str(e)}")
            return False
    
    def _delete_role_related_data(self, role_id: str, role: str, phone: str):
        """Delete all data related to a user role"""
        try:
            if role == 'client':
                # Delete client-related data
                log_info(f"Deleting client-related data for {role_id}")
                
                # Delete from relationship tables
                self.db.table('client_trainer_list').delete().eq('client_id', role_id).execute()
                self.db.table('trainer_client_list').delete().eq('client_id', role_id).execute()
                
                # Delete client tasks
                self.db.table('client_tasks').delete().eq('client_id', role_id).execute()
                
                # Delete client invitations (both sent and received)
                self.db.table('client_invitations').delete().eq('client_phone', phone).execute()
                
                # Delete habit-related data if exists
                try:
                    self.db.table('client_habits').delete().eq('client_id', role_id).execute()
                    self.db.table('habit_logs').delete().eq('client_id', role_id).execute()
                except:
                    pass  # Tables might not exist
                
                log_info(f"Deleted all client-related data for {role_id}")
                
            elif role == 'trainer':
                # Delete trainer-related data
                log_info(f"Deleting trainer-related data for {role_id}")
                
                # Delete from relationship tables
                self.db.table('trainer_client_list').delete().eq('trainer_id', role_id).execute()
                self.db.table('client_trainer_list').delete().eq('trainer_id', role_id).execute()
                
                # Delete trainer tasks
                self.db.table('trainer_tasks').delete().eq('trainer_id', role_id).execute()
                
                # Delete trainer invitations
                self.db.table('client_invitations').delete().eq('trainer_id', role_id).execute()
                
                # Delete habit-related data if exists
                try:
                    self.db.table('trainer_habits').delete().eq('trainer_id', role_id).execute()
                    # Note: Don't delete habit_logs as they belong to clients
                except:
                    pass  # Tables might not exist
                
                log_info(f"Deleted all trainer-related data for {role_id}")
                
        except Exception as e:
            log_error(f"Error deleting related data for {role} {role_id}: {str(e)}")
            # Continue with deletion even if some related data fails