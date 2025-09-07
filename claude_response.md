<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5271 -->
<!-- Max Tokens: 16000 -->
<!-- Step 1 of 5 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS

Step 1 focuses on analyzing the current code structure and identifying critical issues. The codebase has several problems:

1. **app.py is 1125 lines** - Far exceeds the 600-line limit and contains mixed responsibilities (routes, initialization, business logic)
2. **services/refiloe.py already split** - Good news: it's been refactored into refiloe_handlers.py and refiloe_helpers.py
3. **routes/dashboard.py is 817 lines** - Needs splitting
4. **services/ai_intent_handler.py is 649 lines** - Needs splitting
5. **services/dashboard_sync.py is 640 lines** - Needs splitting
6. **payment_integration.py is 746 lines** - Needs splitting and should be moved to services/
7. **payment_manager.py** - Already in root, should be moved to services/
8. **payfast_webhook.py** - In root, should be moved to services/ or routes/
9. **Missing utils files** - logger.py, rate_limiter.py, input_sanitizer.py, validators.py are imported but don't exist
10. **Empty __init__.py files** - Need proper exports for clean imports

## CHANGES NEEDED

### EDIT: app.py

**Change 1:** Extract imports and configuration to identify what needs to be moved
Location: Analysis only - no changes yet, just documenting issues

Issues identified in app.py:
- Lines 1-50: Heavy imports section
- Lines 51-125: Service initialization (should be in a factory)
- Lines 126-185: Background scheduler setup (should be separate)
- Lines 186-1125: Mixed routes and business logic (should be split into routes/)

### NEW FILE: STRUCTURE_ANALYSIS.md
```markdown
# Codebase Structure Analysis

## Critical Issues Found

### 1. Files Exceeding 600 Lines
- **app.py**: 1125 lines (CRITICAL)
  - Mixed responsibilities: routes, initialization, business logic
  - Contains calendar routes, assessment routes, webhook handlers
  - Should be split into: app.py (lean), routes/*, services/initialization.py

- **routes/dashboard.py**: 817 lines
  - Contains both gamification and calendar routes
  - Should split into: routes/gamification.py, routes/calendar.py

- **services/dashboard_sync.py**: 640 lines
  - Mixed dashboard sync and notification logic
  - Should split into: services/dashboard_sync.py, services/notification_manager.py

- **services/ai_intent_handler.py**: 649 lines
  - Contains intent handling and response generation
  - Should split into: services/ai_intent.py, services/ai_responses.py

- **payment_integration.py**: 746 lines (also in wrong location)
  - Should move to services/ and split into smaller modules

### 2. Misplaced Files
- **payment_manager.py** → services/payment_manager.py
- **payment_integration.py** → services/payment_integration.py (then split)
- **payfast_webhook.py** → routes/webhooks.py

### 3. Missing Required Files
These are imported but don't exist:
- utils/logger.py
- utils/rate_limiter.py
- utils/input_sanitizer.py
- utils/validators.py

### 4. Successfully Refactored
✅ services/refiloe.py has been split into:
- services/refiloe.py (core)
- services/refiloe_handlers.py
- services/refiloe_helpers.py

### 5. Circular Import Risks
- app.py imports from services which may import Config
- routes/dashboard.py imports from app (supabase client)

## Recommended Refactoring Order

### Phase 1: Create Missing Utils (Step 2)
1. Create utils/logger.py
2. Create utils/rate_limiter.py
3. Create utils/input_sanitizer.py
4. Create utils/validators.py

### Phase 2: Move Misplaced Files (Step 3)
1. Move payment_manager.py → services/
2. Move payment_integration.py → services/ (then split)
3. Move payfast_webhook.py → routes/webhooks.py

### Phase 3: Split Large Files (Step 4)
1. Split app.py into:
   - app.py (Flask app, <200 lines)
   - routes/webhook.py (WhatsApp webhooks)
   - routes/calendar.py (calendar routes)
   - routes/assessment.py (assessment routes)
   - routes/api.py (general API routes)
   - services/app_factory.py (service initialization)

2. Split routes/dashboard.py into:
   - routes/dashboard_calendar.py
   - routes/dashboard_gamification.py
   - routes/dashboard_core.py

3. Split services/dashboard_sync.py into:
   - services/dashboard_sync.py (<400 lines)
   - services/notification_batch.py

4. Split services/ai_intent_handler.py into:
   - services/ai_intent.py
   - services/ai_response_generator.py

5. Split payment_integration.py into:
   - services/payment_commands.py
   - services/payment_processor.py

### Phase 4: Fix Imports (Step 5)
1. Update all imports after file moves
2. Add proper __init__.py exports
3. Fix circular dependencies

## File Size Summary
| File | Current Lines | Target Lines | Action |
|------|--------------|--------------|--------|
| app.py | 1125 | <200 | Split into 6+ files |
| routes/dashboard.py | 817 | <400 each | Split into 3 files |
| services/dashboard_sync.py | 640 | <400 | Split into 2 files |
| services/ai_intent_handler.py | 649 | <400 each | Split into 2 files |
| payment_integration.py | 746 | <400 each | Move & split into 2 files |
```

### NEW FILE: utils/logger.py
```python
"""Logging utilities for Refiloe"""
import logging
import sys
from datetime import datetime
from typing import Any, Optional
import traceback

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(name: str = "refiloe", level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with console and optional file output
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger

# Create default logger instance
default_logger = setup_logger()

def log_info(message: str, extra: Optional[dict] = None):
    """Log info message"""
    if extra:
        message = f"{message} | {extra}"
    default_logger.info(message)

def log_warning(message: str, extra: Optional[dict] = None):
    """Log warning message"""
    if extra:
        message = f"{message} | {extra}"
    default_logger.warning(message)

def log_error(message: str, extra: Optional[dict] = None, exc_info: bool = False):
    """Log error message with optional exception info"""
    if extra:
        message = f"{message} | {extra}"
    
    if exc_info:
        message = f"{message}\n{traceback.format_exc()}"
    
    default_logger.error(message)

def log_debug(message: str, extra: Optional[dict] = None):
    """Log debug message"""
    if extra:
        message = f"{message} | {extra}"
    default_logger.debug(message)

def log_critical(message: str, extra: Optional[dict] = None):
    """Log critical message"""
    if extra:
        message = f"{message} | {extra}"
    default_logger.critical(message)

# Convenience function for structured logging
def log_event(event_type: str, user_id: Optional[str] = None, 
              data: Optional[dict] = None, level: str = "info"):
    """
    Log a structured event
    
    Args:
        event_type: Type of event
        user_id: User ID if applicable
        data: Additional event data
        level: Log level
    """
    log_data = {
        "event": event_type,
        "timestamp": datetime.now().isoformat()
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    if data:
        log_data.update(data)
    
    message = f"Event: {event_type}"
    
    if level == "error":
        log_error(message, log_data)
    elif level == "warning":
        log_warning(message, log_data)
    elif level == "debug":
        log_debug(message, log_data)
    else:
        log_info(message, log_data)
```

### NEW FILE: utils/rate_limiter.py
```python
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
```

## SUMMARY

Completed Step 1 analysis:
- Identified 5 files exceeding 600 lines that need splitting
- Found 2 misplaced payment files that need moving to services/
- Created STRUCTURE_ANALYSIS.md documenting all issues
- Created 2 missing utils files (logger.py and rate_limiter.py) that are critical dependencies
- Documented the recommended refactoring order for subsequent steps

The analysis reveals app.py as the most critical issue (1125 lines with mixed responsibilities), followed by several service files that need splitting. The good news is services/refiloe.py has already been successfully refactored.

## CONTINUE_NEEDED
Next step: Step 2: Create remaining missing utils files (input_sanitizer.py, validators.py)
Run @claude @continue to proceed with next step