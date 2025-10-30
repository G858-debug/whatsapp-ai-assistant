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
            
            # Use your current schema format
            token_data = {
                'user_id': user_id,
                'role': role,
                'purpose': purpose,
                'token_hash': token_hash,
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.now().isoformat(),
                'used': False
            }
            
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
            
            # Find valid token using your current schema
            result = self.db.table('dashboard_tokens').select('*').eq(
                'token_hash', token_hash
            ).eq('user_id', user_id).eq('used', False).gt(
                'expires_at', datetime.now().isoformat()
            ).execute()
            
            if not result.data:
                return None
            
            token_data = result.data[0]
            
            # Mark token as used (one-time use for security)
            self.db.table('dashboard_tokens').update({
                'used': True,
                'used_at': datetime.now().isoformat()
            }).eq('id', token_data['id']).execute()
            
            log_info(f"Validated dashboard token for {token_data['role']} {user_id}")
            
            return {
                'user_id': token_data['user_id'],
                'role': token_data['role'],
                'purpose': token_data['purpose']
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
    
