<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5473 -->
<!-- Max Tokens: 32000 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS

Looking at the registration system, I need to add duplicate prevention and database error handling to Step 3. The current registration system needs to:
1. Prevent duplicate registrations when someone is already registered
2. Handle database errors gracefully with retry logic
3. Provide clear error messages and recovery options
4. Ensure data integrity during registration

## CHANGES NEEDED

### EDIT: services/registration/registration_state.py

**Change 1:** Add duplicate checking and error handling methods
Location: After the `_get_step_value` method (around line 470)

```python
# ADD after _get_step_value method:

    def check_duplicate_registration(self, phone: str, email: str, 
                                    registration_type: str) -> Dict:
        """
        Check if user is already registered
        
        Returns:
            Dict with duplicate status and existing user info
        """
        try:
            # Check by phone number
            if registration_type == 'trainer':
                existing_phone = self.db.table('trainers').select(
                    'id, name, email, created_at'
                ).eq('whatsapp', phone).execute()
                
                if existing_phone.data:
                    return {
                        'is_duplicate': True,
                        'duplicate_field': 'phone',
                        'existing_user': existing_phone.data[0],
                        'message': f"This phone number is already registered to {existing_phone.data[0].get('name', 'a trainer')}."
                    }
                
                # Check by email if provided
                if email:
                    existing_email = self.db.table('trainers').select(
                        'id, name, whatsapp, created_at'
                    ).eq('email', email.lower()).execute()
                    
                    if existing_email.data:
                        return {
                            'is_duplicate': True,
                            'duplicate_field': 'email',
                            'existing_user': existing_email.data[0],
                            'message': f"This email is already registered to {existing_email.data[0].get('name', 'another trainer')}."
                        }
            
            else:  # client
                existing_phone = self.db.table('clients').select(
                    'id, name, email, trainer_id, created_at'
                ).eq('whatsapp', phone).execute()
                
                if existing_phone.data:
                    return {
                        'is_duplicate': True,
                        'duplicate_field': 'phone',
                        'existing_user': existing_phone.data[0],
                        'message': f"This phone number is already registered to {existing_phone.data[0].get('name', 'a client')}."
                    }
                
                if email:
                    existing_email = self.db.table('clients').select(
                        'id, name, whatsapp, trainer_id, created_at'
                    ).eq('email', email.lower()).execute()
                    
                    if existing_email.data:
                        return {
                            'is_duplicate': True,
                            'duplicate_field': 'email',
                            'existing_user': existing_email.data[0],
                            'message': f"This email is already registered to {existing_email.data[0].get('name', 'another client')}."
                        }
            
            return {
                'is_duplicate': False,
                'message': 'No duplicate found'
            }
            
        except Exception as e:
            log_error(f"Error checking duplicate registration: {str(e)}")
            return {
                'is_duplicate': False,
                'error': str(e),
                'message': 'Could not verify duplicate status'
            }
    
    def handle_database_error(self, error: Exception, session_id: str, 
                            operation: str) -> Dict:
        """
        Handle database errors with retry logic and recovery options
        
        Args:
            error: The exception that occurred
            session_id: Current session ID
            operation: What operation failed
            
        Returns:
            Dict with error handling response
        """
        error_str = str(error).lower()
        
        # Categorize error types
        if 'duplicate' in error_str or 'unique' in error_str:
            return {
                'error_type': 'duplicate',
                'message': (
                    "It looks like you're already registered! 🤔\n\n"
                    "• To update your info, type: 'update profile'\n"
                    "• To login instead, type: 'login'\n"
                    "• To start fresh, type: 'reset registration'"
                ),
                'recoverable': True
            }
        
        elif 'connection' in error_str or 'timeout' in error_str:
            # Mark for retry
            self._mark_session_for_retry(session_id)
            
            return {
                'error_type': 'connection',
                'message': (
                    "Connection issue detected. Don't worry! 📶\n\n"
                    "I'll retry automatically in a moment.\n"
                    "Your progress has been saved.\n\n"
                    "Type 'retry' to try again now, or wait a moment."
                ),
                'recoverable': True,
                'retry_available': True
            }
        
        elif 'constraint' in error_str or 'foreign key' in error_str:
            return {
                'error_type': 'data_integrity',
                'message': (
                    "There's an issue with the data provided. 🔍\n\n"
                    "Please check your information and try again.\n"
                    "Type 'back' to go to the previous step."
                ),
                'recoverable': True
            }
        
        elif 'permission' in error_str or 'denied' in error_str:
            return {
                'error_type': 'permission',
                'message': (
                    "Permission issue encountered. 🔒\n\n"
                    "This might be a temporary issue.\n"
                    "Please try again in a few minutes.\n\n"
                    "If this persists, contact support."
                ),
                'recoverable': False
            }
        
        else:
            # Generic error
            log_error(f"Unhandled database error in {operation}: {error}")
            
            return {
                'error_type': 'unknown',
                'message': (
                    "Something went wrong, but don't worry! 🛠️\n\n"
                    "Your information is safe. You can:\n"
                    "• Type 'retry' to try again\n"
                    "• Type 'back' to go back\n"
                    "• Type 'help' for assistance"
                ),
                'recoverable': True
            }
    
    def _mark_session_for_retry(self, session_id: str):
        """Mark a session for automatic retry"""
        try:
            self.db.table('registration_sessions').update({
                'needs_retry': True,
                'retry_count': self.db.rpc('increment', {
                    'x': 1,
                    'row_id': session_id,
                    'column': 'retry_count'
                }),
                'last_error_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
        except Exception as e:
            log_error(f"Error marking session for retry: {str(e)}")
    
    def retry_failed_operation(self, session_id: str) -> Dict:
        """
        Retry a previously failed operation
        
        Returns:
            Dict with retry result
        """
        try:
            # Get session with retry info
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': 'Session not found. Please start again.'
                }
            
            # Check retry count
            retry_count = session.data.get('retry_count', 0)
            if retry_count >= 3:
                return {
                    'success': False,
                    'message': (
                        "Maximum retries reached. 😔\n\n"
                        "Please start a new registration by typing 'hi'.\n"
                        "Your previous answers can be reused."
                    )
                }
            
            # Get the operation to retry
            step = session.data.get('step')
            data = session.data.get('data', {})
            
            # Attempt to complete registration if at confirmation step
            if step == 'confirmation':
                return self._retry_complete_registration(session.data)
            
            # Otherwise, just mark as ready to continue
            self.db.table('registration_sessions').update({
                'needs_retry': False,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            return {
                'success': True,
                'message': 'Ready to continue! Please answer the current question.',
                'current_step': step
            }
            
        except Exception as e:
            log_error(f"Error retrying operation: {str(e)}")
            return {
                'success': False,
                'message': 'Retry failed. Please type "help" for assistance.'
            }
    
    def _retry_complete_registration(self, session_data: Dict) -> Dict:
        """Retry completing a registration that previously failed"""
        try:
            registration_type = session_data.get('registration_type')
            data = session_data.get('data', {})
            
            if registration_type == 'trainer':
                # Retry trainer registration
                result = self.db.table('trainers').insert({
                    'name': data.get('name'),
                    'email': data.get('email'),
                    'whatsapp': session_data.get('phone'),
                    'business_name': data.get('business_name'),
                    'location': data.get('location'),
                    'specialization': data.get('specialization'),
                    'pricing_per_session': data.get('pricing_per_session'),
                    'status': 'active',
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
            else:  # client
                # Retry client registration
                trainer_id = data.get('trainer_id')
                if not trainer_id and data.get('preferred_trainer'):
                    # Try to find trainer
                    trainer = self.db.table('trainers').select('id').ilike(
                        'name', f"%{data['preferred_trainer']}%"
                    ).limit(1).execute()
                    
                    if trainer.data:
                        trainer_id = trainer.data[0]['id']
                
                result = self.db.table('clients').insert({
                    'name': data.get('name'),
                    'email': data.get('email'),
                    'whatsapp': session_data.get('phone'),
                    'trainer_id': trainer_id,
                    'fitness_goals': data.get('fitness_goals'),
                    'availability': data.get('availability'),
                    'status': 'active',
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
            
            if result.data:
                # Mark session as completed
                self.db.table('registration_sessions').update({
                    'status': 'completed',
                    'completed_at': datetime.now(self.sa_tz).isoformat(),
                    'needs_retry': False
                }).eq('id', session_data['id']).execute()
                
                return {
                    'success': True,
                    'message': (
                        "✅ Registration completed successfully!\n\n"
                        "Welcome to Refiloe! You can now use all features.\n"
                        "Type 'help' to see what I can do for you."
                    )
                }
            
            return {
                'success': False,
                'message': 'Registration still failing. Please contact support.'
            }
            
        except Exception as e:
            # Handle the error
            error_response = self.handle_database_error(
                e, session_data['id'], 'registration_completion'
            )
            
            return {
                'success': False,
                'message': error_response['message']
            }
```

### EDIT: services/registration/registration_handlers.py

**Change 1:** Add duplicate check before processing registration
Location: In the handle_registration method (around line 50, after getting session)

```python
# ADD after session retrieval (around line 50):

            # Check for duplicates before proceeding
            if step == 'email' and message:
                # User just provided email, check for duplicates
                duplicate_check = self.state_manager.check_duplicate_registration(
                    phone=phone,
                    email=message,
                    registration_type=session.get('registration_type', 'trainer')
                )
                
                if duplicate_check.get('is_duplicate'):
                    # Handle duplicate
                    existing_user = duplicate_check.get('existing_user', {})
                    
                    return (
                        f"⚠️ {duplicate_check.get('message')}\n\n"
                        f"Options:\n"
                        f"• Type 'login' to access your account\n"
                        f"• Type 'update' to update your information\n"
                        f"• Type 'new' to register with different details\n"
                        f"• Type 'help' if you need assistance"
                    )
```

**Change 2:** Add error handling with retry mechanism
Location: In the _complete_registration method (around line 180)

```python
# REMOVE (existing try-except block):
        try:
            # Create trainer/client record
            # ... existing code ...
        except Exception as e:
            log_error(f"Registration completion error: {str(e)}")
            return "Sorry, there was an error completing your registration. Please try again."

# ADD:
        try:
            # Create trainer/client record
            # ... existing code ...
        except Exception as e:
            # Use comprehensive error handling
            error_response = self.state_manager.handle_database_error(
                e, session_id, 'registration_completion'
            )
            
            if error_response.get('retry_available'):
                # Schedule automatic retry
                from threading import Timer
                Timer(5.0, lambda: self.state_manager.retry_failed_operation(session_id)).start()
            
            return error_response.get('message')
```

### NEW FILE: services/registration/duplicate_handler.py

```python
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
```

## SUMMARY

In Step 3, I've implemented comprehensive duplicate prevention and database error handling:

1. **Duplicate Prevention** in `registration_state.py`:
   - Added `check_duplicate_registration` method to check for existing users by phone and email
   - Checks both trainers and clients tables
   - Provides clear messages about who owns the existing account

2. **Database Error Handling** in `registration_state.py`:
   - Added `handle_database_error` method that categorizes errors (duplicate, connection, data integrity, permission)
   - Implements retry logic with automatic retry for connection issues
   - Tracks retry attempts and limits them to 3
   - Provides user-friendly error messages with recovery options

3. **New Duplicate Handler Module** (`duplicate_handler.py`):
   - Sophisticated duplicate account detection and handling
   - Different responses for active vs inactive users
   - Account merging functionality for admins
   - Similar account detection using name similarity scoring
   - Comprehensive logging of duplicate attempts

4. **Enhanced Registration Flow**:
   - Duplicate check integrated into registration process
   - Automatic retry mechanism for failed operations
   - Better error recovery with clear user options
   - Session marked for retry on connection failures

The system now gracefully handles all database errors, prevents duplicate registrations, and provides clear recovery paths for users.

## CONTINUE_NEEDED
Next step: Step 4: Create comprehensive migration for registration tables