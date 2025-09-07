"""Rate limiting utilities for Refiloe"""
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import time

class RateLimiter:
    """Handle rate limiting for messages and API calls"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        
        # In-memory cache for rate limiting (could use Redis in production)
        self.request_counts = defaultdict(list)
        self.message_counts = defaultdict(list)
        
        # Limits from config
        self.message_limit = config.MESSAGE_RATE_LIMIT
        self.voice_limit = config.VOICE_MESSAGE_RATE_LIMIT
        self.webhook_limit = 100  # Per minute
        
    def check_message_rate(self, phone_number: str, message_type: str = 'text') -> Tuple[bool, Optional[str]]:
        """
        Check if user has exceeded message rate limit
        
        Returns:
            Tuple of (allowed, error_message)
        """
        now = time.time()
        window = 60  # 1 minute window
        
        # Get appropriate limit
        if message_type == 'audio':
            limit = self.voice_limit
        else:
            limit = self.message_limit
        
        # Clean old entries
        self.message_counts[phone_number] = [
            timestamp for timestamp in self.message_counts[phone_number]
            if now - timestamp < window
        ]
        
        # Check limit
        if len(self.message_counts[phone_number]) >= limit:
            wait_time = window - (now - self.message_counts[phone_number][0])
            return False, f"Rate limit exceeded. Please wait {int(wait_time)} seconds."
        
        # Add current request
        self.message_counts[phone_number].append(now)
        return True, None
    
    def check_webhook_rate(self, ip_address: str) -> bool:
        """
        Check if IP has exceeded webhook rate limit
        
        Returns:
            Boolean indicating if request is allowed
        """
        now = time.time()
        window = 60  # 1 minute window
        
        # Clean old entries
        self.request_counts[ip_address] = [
            timestamp for timestamp in self.request_counts[ip_address]
            if now - timestamp < window
        ]
        
        # Check limit
        if len(self.request_counts[ip_address]) >= self.webhook_limit:
            return False
        
        # Add current request
        self.request_counts[ip_address].append(now)
        return True
    
    def check_daily_limit(self, phone_number: str) -> Tuple[bool, int]:
        """
        Check daily message limit (database backed)
        
        Returns:
            Tuple of (within_limit, messages_remaining)
        """
        try:
            today = datetime.now().date().isoformat()
            
            # Get today's message count
            result = self.db.table('daily_usage').select('message_count').eq(
                'phone_number', phone_number
            ).eq('date', today).single().execute()
            
            daily_limit = 500  # Daily limit per user
            
            if result.data:
                count = result.data.get('message_count', 0)
                remaining = daily_limit - count
                
                if count >= daily_limit:
                    return False, 0
                
                # Increment count
                self.db.table('daily_usage').update({
                    'message_count': count + 1,
                    'last_message_at': datetime.now().isoformat()
                }).eq('phone_number', phone_number).eq('date', today).execute()
                
                return True, remaining - 1
            else:
                # Create new daily record
                self.db.table('daily_usage').insert({
                    'phone_number': phone_number,
                    'date': today,
                    'message_count': 1,
                    'last_message_at': datetime.now().isoformat()
                }).execute()
                
                return True, daily_limit - 1
                
        except Exception:
            # On error, allow the request
            return True, -1
    
    def reset_user_limits(self, phone_number: str):
        """Reset rate limits for a user (admin function)"""
        if phone_number in self.message_counts:
            del self.message_counts[phone_number]
    
    def get_user_usage(self, phone_number: str) -> Dict:
        """Get usage statistics for a user"""
        try:
            # Get last 7 days of usage
            week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
            
            result = self.db.table('daily_usage').select('*').eq(
                'phone_number', phone_number
            ).gte('date', week_ago).execute()
            
            if result.data:
                total_messages = sum(r.get('message_count', 0) for r in result.data)
                days_active = len(result.data)
                
                return {
                    'total_messages_week': total_messages,
                    'days_active': days_active,
                    'average_daily': total_messages / 7 if total_messages > 0 else 0,
                    'current_minute_count': len(self.message_counts.get(phone_number, []))
                }
            
            return {
                'total_messages_week': 0,
                'days_active': 0,
                'average_daily': 0,
                'current_minute_count': 0
            }
            
        except Exception:
            return {}