"""Rate limiting utilities"""
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Tuple

class RateLimiter:
    """Handle rate limiting for messages and webhooks"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        # In-memory tracking for quick checks
        self.message_counts = defaultdict(list)
        self.webhook_counts = defaultdict(list)
    
    def check_message_rate(self, phone_number: str, message_type: str) -> Tuple[bool, str]:
        """Check if message rate is within limits"""
        now = datetime.now()
        window = timedelta(minutes=1)
        
        # Clean old entries
        self.message_counts[phone_number] = [
            t for t in self.message_counts[phone_number]
            if now - t < window
        ]
        
        # Check limits based on type
        if message_type == 'voice':
            limit = self.config.VOICE_MESSAGE_RATE_LIMIT
        else:
            limit = self.config.MESSAGE_RATE_LIMIT
        
        if len(self.message_counts[phone_number]) >= limit:
            return False, f"Rate limit exceeded. Please wait a moment before sending more messages."
        
        # Add current request
        self.message_counts[phone_number].append(now)
        return True, ""
    
    def check_webhook_rate(self, ip_address: str) -> bool:
        """Check if webhook rate is within limits"""
        now = datetime.now()
        window = timedelta(seconds=10)
        
        # Clean old entries
        self.webhook_counts[ip_address] = [
            t for t in self.webhook_counts[ip_address]
            if now - t < window
        ]
        
        # Allow 10 webhooks per 10 seconds
        if len(self.webhook_counts[ip_address]) >= 10:
            return False
        
        self.webhook_counts[ip_address].append(now)
        return True