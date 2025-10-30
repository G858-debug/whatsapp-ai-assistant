"""
Dashboard Token Manager
Handles secure token generation and validation for dashboard access
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from utils.logger import log_info, log_error


class DashboardTokenManager:
    """Manages secure tokens for dashboard access"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
    
    def generate_token(self, user_id: str, role: str, purpose: str = 'dashboard') -> Optional[str]:
        """Generate a secure token for dashboard access"""
        try:
            # Generate secure token
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Set expiration (1 hour from now)
            expires_at = datetime.now() + timedelta(hours=1)
            
            # Store token in database - compatible with existing schema
            token_data = {
                'user_id': user_id,  # New field for both trainers and clients
                'role': role,        # New field to distinguish trainer/client
                'purpose': purpose,  # New field for token purpose
                'token_hash': token_hash,  # New secure hash field
                'token': token[:255],      # Keep original token field for compatibility
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.now().isoformat(),
                'used': False
            }
            
            # For trainers, also set trainer_id for backward compatibility
            if role == 'trainer':
                try:
                    # Try to get trainer UUID from trainers table
                    trainer_result = self.db.table('trainers').select('id').eq('trainer_id', user_id).execute()
                    if trainer_result.data:
                        token_data['trainer_id'] = trainer_result.data[0]['id']
                except:
                    # If we can't get UUID, skip trainer_id (new schema doesn't need it)
                    pass
            
            result = self.db.table('dashboard_tokens').insert(token_data).execute()
            
            if result.data:
                log_info(f"Generated dashboard token for {role} {user_id}")
                return token
            
            return None
            
        except Exception as e:
            log_error(f"Error generating dashboard token: {str(e)}")
            return None
    
    def validate_token(self, token: str, user_id: str) -> Optional[Dict]:
        """Validate token and return user info if valid"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Try new token_hash field first, fallback to old token field
            result = None
            
            # Method 1: Try with token_hash (new secure method)
            try:
                result = self.db.table('dashboard_tokens').select('*').eq(
                    'token_hash', token_hash
                ).eq('user_id', user_id).eq('used', False).gt(
                    'expires_at', datetime.now().isoformat()
                ).execute()
            except:
                pass
            
            # Method 2: Fallback to old token field if token_hash doesn't exist
            if not result or not result.data:
                try:
                    result = self.db.table('dashboard_tokens').select('*').eq(
                        'token', token
                    ).eq('user_id', user_id).gt(
                        'expires_at', datetime.now().isoformat()
                    ).execute()
                except:
                    pass
            
            # Method 3: For old records without user_id, try trainer_id
            if not result or not result.data:
                try:
                    result = self.db.table('dashboard_tokens').select('*').eq(
                        'token', token
                    ).eq('trainer_id', user_id).gt(
                        'expires_at', datetime.now().isoformat()
                    ).execute()
                except:
                    pass
            
            if not result or not result.data:
                return None
            
            token_data = result.data[0]
            
            # Mark token as used (one-time use for security)
            update_data = {'used_at': datetime.now().isoformat()}
            if 'used' in token_data:  # Only set used if column exists
                update_data['used'] = True
                
            self.db.table('dashboard_tokens').update(update_data).eq('id', token_data['id']).execute()
            
            # Extract role and user_id with fallbacks for old records
            role = token_data.get('role', 'trainer')  # Default to trainer for old records
            actual_user_id = token_data.get('user_id', user_id)
            purpose = token_data.get('purpose', 'dashboard')
            
            log_info(f"Validated dashboard token for {role} {actual_user_id}")
            
            return {
                'user_id': actual_user_id,
                'role': role,
                'purpose': purpose
            }
            
        except Exception as e:
            log_error(f"Error validating dashboard token: {str(e)}")
            return None
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        try:
            result = self.db.table('dashboard_tokens').delete().lt(
                'expires_at', datetime.now().isoformat()
            ).execute()
            
            if result.data:
                log_info(f"Cleaned up {len(result.data)} expired dashboard tokens")
                
        except Exception as e:
            log_error(f"Error cleaning up expired tokens: {str(e)}")
    
    def migrate_old_tokens(self):
        """Migrate old tokens to new format (run once after schema update)"""
        try:
            # Find tokens without user_id or role
            result = self.db.table('dashboard_tokens').select('*').is_('user_id', 'null').execute()
            
            for token_record in result.data:
                if token_record.get('trainer_id'):
                    # Update old token with new fields
                    self.db.table('dashboard_tokens').update({
                        'user_id': str(token_record['trainer_id']),
                        'role': 'trainer',
                        'purpose': 'dashboard',
                        'used': False
                    }).eq('id', token_record['id']).execute()
            
            log_info("Migrated old dashboard tokens to new format")
            
        except Exception as e:
            log_error(f"Error migrating old tokens: {str(e)}")