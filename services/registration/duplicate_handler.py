"""Handle duplicate registration scenarios"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class DuplicateRegistrationHandler:
    """Handles scenarios where users attempt to register multiple times"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def handle_duplicate_attempt(self, phone: str, existing_user: Dict, 
                                user_type: str) -> str:
        """
        Handle when a user tries to register but already exists
        
        Args:
            phone: User's phone number
            existing_user: Existing user record
            user_type: 'trainer' or 'client'
            
        Returns:
            Appropriate response message
        """
        try:
            # Log the duplicate attempt
            self.db.table('registration_attempts').insert({
                'phone': phone,
                'user_type': user_type,
                'existing_user_id': existing_user.get('id'),
                'attempt_type': 'duplicate',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            # Check when they last logged in
            last_login = self._get_last_login(existing_user['id'], user_type)
            
            if last_login and self._is_recently_active(last_login):
                # Recently active user
                return self._handle_active_user(existing_user, user_type)
            else:
                # Inactive user - might have forgotten they registered
                return self._handle_inactive_user(existing_user, user_type)
                
        except Exception as e:
            log_error(f"Error handling duplicate attempt: {str(e)}")
            return self._get_generic_duplicate_message(existing_user, user_type)
    
    def _get_last_login(self, user_id: str, user_type: str) -> Optional[datetime]:
        """Get user's last login time"""
        try:
            result = self.db.table('activity_logs').select('created_at').eq(
                'user_id', user_id
            ).eq('user_type', user_type).eq(
                'activity_type', 'login'
            ).order('created_at', desc=True).limit(1).execute()
            
            if result.data:
                return datetime.fromisoformat(result.data[0]['created_at'])
            return None
            
        except Exception as e:
            log_error(f"Error getting last login: {str(e)}")
            return None
    
    def _is_recently_active(self, last_login: datetime) -> bool:
        """Check if user has been active in the last 30 days"""
        if not last_login:
            return False
        
        days_inactive = (datetime.now(self.sa_tz) - last_login).days
        return days_inactive < 30
    
    def _handle_active_user(self, existing_user: Dict, user_type: str) -> str:
        """Handle duplicate attempt for active user"""
        name = existing_user.get('name', 'there')
        
        return (
            f"Welcome back, {name}! 👋\n\n"
            f"You're already registered as a {user_type}.\n\n"
            f"Here's what you can do:\n"
            f"• Type 'menu' to see available options\n"
            f"• Type 'bookings' to manage sessions\n"
            f"• Type 'profile' to view your details\n"
            f"• Type 'help' if you need assistance"
        )
    
    def _handle_inactive_user(self, existing_user: Dict, user_type: str) -> str:
        """Handle duplicate attempt for inactive user"""
        name = existing_user.get('name', 'there')
        
        return (
            f"Welcome back, {name}! 🎉\n\n"
            f"Great to see you again! You're already registered.\n\n"
            f"It's been a while since your last visit. Would you like to:\n"
            f"• Type 'refresh' to update your information\n"
            f"• Type 'continue' to use your existing profile\n"
            f"• Type 'reset password' if you've forgotten your details\n"
            f"• Type 'help' for assistance"
        )
    
    def _get_generic_duplicate_message(self, existing_user: Dict, user_type: str) -> str:
        """Get generic duplicate message"""
        return (
            f"This phone number is already registered. 📱\n\n"
            f"Options:\n"
            f"• Type 'login' to access your account\n"
            f"• Type 'forgot' if you've forgotten your details\n"
            f"• Type 'support' to contact support\n"
            f"• Type 'new account' to register with a different number"
        )
    
    def merge_duplicate_accounts(self, primary_id: str, duplicate_id: str, 
                                user_type: str) -> Dict:
        """
        Merge duplicate accounts (admin function)
        
        Args:
            primary_id: ID of account to keep
            duplicate_id: ID of account to merge and delete
            user_type: 'trainer' or 'client'
            
        Returns:
            Result of merge operation
        """
        try:
            table = 'trainers' if user_type == 'trainer' else 'clients'
            
            # Get both records
            primary = self.db.table(table).select('*').eq('id', primary_id).single().execute()
            duplicate = self.db.table(table).select('*').eq('id', duplicate_id).single().execute()
            
            if not primary.data or not duplicate.data:
                return {
                    'success': False,
                    'error': 'One or both accounts not found'
                }
            
            # Merge data (keeping primary, adding missing from duplicate)
            merged_data = primary.data.copy()
            
            for key, value in duplicate.data.items():
                if key not in ['id', 'created_at'] and not merged_data.get(key):
                    merged_data[key] = value
            
            # Update primary with merged data
            self.db.table(table).update(merged_data).eq('id', primary_id).execute()
            
            # Update all references
            if user_type == 'trainer':
                # Update bookings
                self.db.table('bookings').update({
                    'trainer_id': primary_id
                }).eq('trainer_id', duplicate_id).execute()
                
                # Update clients
                self.db.table('clients').update({
                    'trainer_id': primary_id
                }).eq('trainer_id', duplicate_id).execute()
                
            else:  # client
                # Update bookings
                self.db.table('bookings').update({
                    'client_id': primary_id
                }).eq('client_id', duplicate_id).execute()
                
                # Update habit tracking
                self.db.table('habit_tracking').update({
                    'client_id': primary_id
                }).eq('client_id', duplicate_id).execute()
            
            # Archive duplicate account
            self.db.table(f'{table}_archive').insert({
                **duplicate.data,
                'archived_at': datetime.now(self.sa_tz).isoformat(),
                'merge_target_id': primary_id,
                'archive_reason': 'duplicate_merge'
            }).execute()
            
            # Delete duplicate
            self.db.table(table).delete().eq('id', duplicate_id).execute()
            
            log_info(f"Merged duplicate {user_type} accounts: {duplicate_id} -> {primary_id}")
            
            return {
                'success': True,
                'message': f'Successfully merged accounts',
                'primary_id': primary_id
            }
            
        except Exception as e:
            log_error(f"Error merging accounts: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_similar_accounts(self, name: str, user_type: str) -> List[Dict]:
        """
        Check for similar accounts that might be duplicates
        
        Args:
            name: Name to search for
            user_type: 'trainer' or 'client'
            
        Returns:
            List of potentially duplicate accounts
        """
        try:
            table = 'trainers' if user_type == 'trainer' else 'clients'
            
            # Search for similar names
            results = self.db.table(table).select('id, name, whatsapp, email').ilike(
                'name', f'%{name}%'
            ).execute()
            
            similar_accounts = []
            
            if results.data:
                for account in results.data:
                    # Calculate similarity score
                    similarity = self._calculate_name_similarity(name, account['name'])
                    
                    if similarity > 0.7:  # 70% similarity threshold
                        similar_accounts.append({
                            'id': account['id'],
                            'name': account['name'],
                            'phone': account.get('whatsapp', 'N/A'),
                            'email': account.get('email', 'N/A'),
                            'similarity_score': similarity
                        })
            
            # Sort by similarity score
            similar_accounts.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return similar_accounts
            
        except Exception as e:
            log_error(f"Error checking similar accounts: {str(e)}")
            return []
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names
        
        Returns:
            Similarity score between 0 and 1
        """
        try:
            from difflib import SequenceMatcher
            
            # Normalize names
            n1 = name1.lower().strip()
            n2 = name2.lower().strip()
            
            # Use sequence matcher for similarity
            return SequenceMatcher(None, n1, n2).ratio()
            
        except Exception as e:
            log_error(f"Error calculating similarity: {str(e)}")
            return 0.0