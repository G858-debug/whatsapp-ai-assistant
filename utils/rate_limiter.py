# utils/rate_limiter.py
"""
Rate Limiting Implementation for Refiloe
Protects against spam and abuse
"""

import time
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Tuple, Optional
import json
import pytz

from utils.logger import log_warning, log_error, log_info

class RateLimiter:
    """
    Simple in-memory rate limiter for WhatsApp messages
    Uses token bucket algorithm for smooth rate limiting
    """
    
    def __init__(self, config, supabase_client=None):
        """Initialize rate limiter"""
        self.config = config
        self.supabase = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # In-memory storage for rate limiting
        # Format: {phone_number: {'tokens': float, 'last_update': timestamp}}
        self.message_buckets = defaultdict(lambda: {
            'tokens': float(config.MESSAGE_RATE_LIMIT),
            'last_update': time.time(),
            'daily_count': 0,
            'daily_reset': datetime.now(self.sa_tz).date()
        })
        
        # Track blocked users
        # Format: {phone_number: unblock_timestamp}
        self.blocked_users = {}
        
        # Track warnings sent
        self.warnings_sent = set()
        
        # Track IP addresses for webhook protection
        self.ip_buckets = defaultdict(lambda: {
            'tokens': float(config.WEBHOOK_PER_IP_LIMIT),
            'last_update': time.time()
        })
        
        log_info("Rate limiter initialized")
    
    def check_message_rate(self, phone_number: str, message_type: str = 'text') -> Tuple[bool, Optional[str]]:
        """
        Check if a message from this phone number should be allowed
        Returns: (allowed: bool, error_message: str or None)
        """
        try:
            # Check if rate limiting is enabled
            if not self.config.ENABLE_RATE_LIMITING:
                return True, None
            
            # Check whitelist
            if phone_number in self.config.RATE_LIMIT_WHITELIST:
                return True, None
            
            # Check if user is blocked
            if phone_number in self.blocked_users:
                unblock_time = self.blocked_users[phone_number]
                if time.time() < unblock_time:
                    remaining_minutes = int((unblock_time - time.time()) / 60)
                    return False, f"🚫 You're temporarily blocked for {remaining_minutes} more minutes due to excessive messages."
                else:
                    # Unblock the user
                    del self.blocked_users[phone_number]
                    if phone_number in self.warnings_sent:
                        self.warnings_sent.remove(phone_number)
            
            # Get or create bucket for this phone number
            bucket = self.message_buckets[phone_number]
            
            # Check daily limit
            today = datetime.now(self.sa_tz).date()
            if bucket['daily_reset'] != today:
                # Reset daily counter
                bucket['daily_count'] = 0
                bucket['daily_reset'] = today
            
            # Check daily limit based on message type
            if message_type == 'voice':
                daily_limit = self.config.VOICE_NOTE_DAILY_LIMIT
            else:
                daily_limit = self.config.MESSAGE_DAILY_LIMIT
            
            if bucket['daily_count'] >= daily_limit:
                return False, self.config.RATE_LIMIT_DAILY_MESSAGE
            
            # Calculate tokens (token bucket algorithm)
            current_time = time.time()
            time_passed = current_time - bucket['last_update']
            
            # Determine rate limit based on message type
            if message_type == 'voice':
                rate_limit = self.config.VOICE_NOTE_RATE_LIMIT
                burst_limit = min(10, rate_limit)  # Smaller burst for voice notes
            else:
                rate_limit = self.config.MESSAGE_RATE_LIMIT
                burst_limit = self.config.MESSAGE_BURST_LIMIT
            
            # Refill tokens based on time passed
            tokens_to_add = time_passed * (rate_limit / 60.0)  # tokens per second
            bucket['tokens'] = min(burst_limit, bucket['tokens'] + tokens_to_add)
            bucket['last_update'] = current_time
            
            # Check if we have enough tokens
            if bucket['tokens'] >= 1:
                # Consume a token
                bucket['tokens'] -= 1
                bucket['daily_count'] += 1
                
                # Check if we should send a warning
                if bucket['tokens'] < (burst_limit * self.config.RATE_LIMIT_WARNING_THRESHOLD):
                    if phone_number not in self.warnings_sent:
                        self.warnings_sent.add(phone_number)
                        log_warning(f"Rate limit warning for {phone_number}")
                        # Don't block the message, just log the warning
                        # The warning message will be sent after the current message is processed
                
                return True, None
            else:
                # No tokens available - block the user
                self._block_user(phone_number)
                log_warning(f"Rate limit exceeded for {phone_number} - user blocked")
                return False, self.config.RATE_LIMIT_MESSAGE
                
        except Exception as e:
            log_error(f"Error in rate limiter: {str(e)}")
            # On error, allow the message through
            return True, None
    
    def check_webhook_rate(self, ip_address: str) -> bool:
        """
        Check if a webhook request from this IP should be allowed
        """
        try:
            if not self.config.ENABLE_RATE_LIMITING:
                return True
            
            bucket = self.ip_buckets[ip_address]
            current_time = time.time()
            time_passed = current_time - bucket['last_update']
            
            # Refill tokens
            tokens_to_add = time_passed * (self.config.WEBHOOK_PER_IP_LIMIT / 60.0)
            bucket['tokens'] = min(self.config.WEBHOOK_PER_IP_LIMIT, bucket['tokens'] + tokens_to_add)
            bucket['last_update'] = current_time
            
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            else:
                log_warning(f"Webhook rate limit exceeded for IP {ip_address}")
                return False
                
        except Exception as e:
            log_error(f"Error checking webhook rate: {str(e)}")
            return True
    
    def check_payment_rate(self, phone_number: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a payment request from this user should be allowed
        """
        try:
            if not self.config.ENABLE_RATE_LIMITING:
                return True, None
            
            # Use a separate bucket for payment requests
            key = f"payment_{phone_number}"
            if key not in self.message_buckets:
                self.message_buckets[key] = {
                    'tokens': float(self.config.PAYMENT_REQUEST_RATE_LIMIT),
                    'last_update': time.time(),
                    'daily_count': 0,
                    'daily_reset': datetime.now(self.sa_tz).date()
                }
            
            bucket = self.message_buckets[key]
            
            # Check daily limit
            today = datetime.now(self.sa_tz).date()
            if bucket['daily_reset'] != today:
                bucket['daily_count'] = 0
                bucket['daily_reset'] = today
            
            if bucket['daily_count'] >= self.config.PAYMENT_REQUEST_DAILY_LIMIT:
                return False, "🏦 Daily payment request limit reached. Please try again tomorrow."
            
            # Check hourly rate
            current_time = time.time()
            time_passed = current_time - bucket['last_update']
            tokens_to_add = time_passed * (self.config.PAYMENT_REQUEST_RATE_LIMIT / 3600.0)  # tokens per second
            bucket['tokens'] = min(self.config.PAYMENT_REQUEST_RATE_LIMIT, bucket['tokens'] + tokens_to_add)
            bucket['last_update'] = current_time
            
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                bucket['daily_count'] += 1
                return True, None
            else:
                return False, "⏰ Please wait before making another payment request."
                
        except Exception as e:
            log_error(f"Error checking payment rate: {str(e)}")
            return True, None
    
    def _block_user(self, phone_number: str):
        """
        Block a user for the configured duration
        """
        block_duration = self.config.RATE_LIMIT_BLOCK_DURATION_MINUTES * 60  # Convert to seconds
        self.blocked_users[phone_number] = time.time() + block_duration
        
        # Log to database if available
        if self.supabase:
            try:
                self.supabase.table('rate_limit_blocks').insert({
                    'phone_number': phone_number,
                    'blocked_at': datetime.now(self.sa_tz).isoformat(),
                    'unblock_at': datetime.fromtimestamp(
                        self.blocked_users[phone_number], 
                        self.sa_tz
                    ).isoformat(),
                    'reason': 'rate_limit_exceeded'
                }).execute()
            except Exception as e:
                log_error(f"Error logging block to database: {str(e)}")
    
    def should_send_warning(self, phone_number: str) -> bool:
        """
        Check if we should send a warning message to this user
        """
        return phone_number in self.warnings_sent
    
    def get_rate_limit_status(self, phone_number: str) -> Dict:
        """
        Get current rate limit status for a phone number
        Useful for debugging and monitoring
        """
        if phone_number not in self.message_buckets:
            return {
                'tokens_remaining': self.config.MESSAGE_RATE_LIMIT,
                'daily_messages_sent': 0,
                'is_blocked': False,
                'warning_sent': False
            }
        
        bucket = self.message_buckets[phone_number]
        is_blocked = phone_number in self.blocked_users and time.time() < self.blocked_users[phone_number]
        
        return {
            'tokens_remaining': bucket['tokens'],
            'daily_messages_sent': bucket['daily_count'],
            'is_blocked': is_blocked,
            'warning_sent': phone_number in self.warnings_sent,
            'unblock_time': self.blocked_users.get(phone_number)
        }
    
    def reset_user_limits(self, phone_number: str):
        """
        Reset rate limits for a specific user
        Useful for admin override
        """
        if phone_number in self.message_buckets:
            del self.message_buckets[phone_number]
        if phone_number in self.blocked_users:
            del self.blocked_users[phone_number]
        if phone_number in self.warnings_sent:
            self.warnings_sent.remove(phone_number)
        
        log_info(f"Rate limits reset for {phone_number}")
    
    def cleanup_old_data(self):
        """
        Clean up old data to prevent memory leaks
        Should be called periodically
        """
        current_time = time.time()
        
        # Remove expired blocks
        expired_blocks = [
            phone for phone, unblock_time in self.blocked_users.items()
            if unblock_time < current_time
        ]
        for phone in expired_blocks:
            del self.blocked_users[phone]
        
        # Remove old buckets (not used in last 24 hours)
        cutoff_time = current_time - 86400  # 24 hours
        old_buckets = [
            phone for phone, bucket in self.message_buckets.items()
            if bucket['last_update'] < cutoff_time
        ]
        for phone in old_buckets:
            del self.message_buckets[phone]
        
        if expired_blocks or old_buckets:
            log_info(f"Cleaned up {len(expired_blocks)} expired blocks and {len(old_buckets)} old buckets")
