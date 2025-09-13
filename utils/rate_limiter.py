"""Rate limiting utilities"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from utils.logger import log_warning, log_info

class RateLimiter:
    """Rate limiter for API calls and user actions"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        
        # Default limits
        self.limits = {
            'message': {'count': 60, 'window': 60},  # 60 messages per minute
            'api': {'count': 100, 'window': 60},     # 100 API calls per minute
            'registration': {'count': 3, 'window': 3600}  # 3 registration attempts per hour
        }
        
        # In-memory cache for performance
        self.cache: Dict[str, Dict] = {}
    
    def check_limit(self, identifier: str, action_type: str = 'message') -> bool:
        """
        Check if action is within rate limit
        
        Args:
            identifier: User identifier (phone number or ID)
            action_type: Type of action being rate limited
            
        Returns:
            True if within limit, False if exceeded
        """
        try:
            limit_config = self.limits.get(action_type, self.limits['message'])
            cache_key = f"{identifier}:{action_type}"
            
            # Check cache first
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                if (datetime.now() - cached['timestamp']).seconds < limit_config['window']:
                    if cached['count'] >= limit_config['count']:
                        log_warning(f"Rate limit exceeded for {identifier} - {action_type}")
                        return False
                    cached['count'] += 1
                    return True
                else:
                    # Window expired, reset
                    self.cache[cache_key] = {
                        'count': 1,
                        'timestamp': datetime.now()
                    }
                    return True
            
            # Initialize cache entry
            self.cache[cache_key] = {
                'count': 1,
                'timestamp': datetime.now()
            }
            return True
            
        except Exception as e:
            log_warning(f"Rate limiter error: {str(e)}")
            return True  # Allow on error to avoid blocking users
    
    def reset_limit(self, identifier: str, action_type: str = None):
        """Reset rate limit for identifier"""
        if action_type:
            cache_key = f"{identifier}:{action_type}"
            if cache_key in self.cache:
                del self.cache[cache_key]
        else:
            # Reset all limits for identifier
            keys_to_delete = [k for k in self.cache.keys() if k.startswith(f"{identifier}:")]
            for key in keys_to_delete:
                del self.cache[key]
    
    def cleanup_cache(self):
        """Remove expired entries from cache"""
        current_time = datetime.now()
        keys_to_delete = []
        
        for key, value in self.cache.items():
            action_type = key.split(':')[1] if ':' in key else 'message'
            limit_config = self.limits.get(action_type, self.limits['message'])
            
            if (current_time - value['timestamp']).seconds > limit_config['window']:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.cache[key]
        
        if keys_to_delete:
            log_info(f"Cleaned up {len(keys_to_delete)} expired rate limit entries")