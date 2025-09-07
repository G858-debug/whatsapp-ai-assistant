"""Rate limiting utility"""
from datetime import datetime, timedelta
from typing import Tuple

class RateLimiter:
    """Handle rate limiting for API calls"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.cache = {}
    
    def check_webhook_rate(self, ip_address: str) -> bool:
        """Check if IP has exceeded webhook rate limit"""
        # Simple in-memory rate limiting
        now = datetime.now()
        
        if ip_address not in self.cache:
            self.cache[ip_address] = []
        
        # Clean old entries
        self.cache[ip_address] = [
            t for t in self.cache[ip_address] 
            if now - t < timedelta(minutes=1)
        ]
        
        # Check limit
        if len(self.cache[ip_address]) >= 100:  # 100 requests per minute
            return False
        
        self.cache[ip_address].append(now)
        return True
    
    def check_message_rate(self, phone_number: str, message_type: str) -> Tuple[bool, str]:
        """Check if user has exceeded message rate limit"""
        limit = self.config.MESSAGE_RATE_LIMIT
        
        if message_type == 'audio':
            limit = self.config.VOICE_MESSAGE_RATE_LIMIT
        
        # Check in cache first
        cache_key = f"{phone_number}:{message_type}"
        now = datetime.now()
        
        if cache_key not in self.cache:
            self.cache[cache_key] = []
        
        # Clean old entries
        self.cache[cache_key] = [
            t for t in self.cache[cache_key] 
            if now - t < timedelta(minutes=1)
        ]
        
        # Check limit
        if len(self.cache[cache_key]) >= limit:
            return False, f"Rate limit exceeded. Please wait before sending more {message_type} messages."
        
        self.cache[cache_key].append(now)
        return True, None