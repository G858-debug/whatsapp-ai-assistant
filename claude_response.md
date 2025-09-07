<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5315 -->
<!-- Max Tokens: 16000 -->
<!-- Step 2 of 0 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS

Step 2 focuses on integrating the dashboard_sync service with existing services. The dashboard_sync.py file was created in Step 1, but it needs to be integrated with the main app.py and other services like refiloe.py and whatsapp.py. We also need to update config.py with the missing dashboard URL configuration and ensure the service is properly initialized and used throughout the system.

## CHANGES NEEDED

### EDIT: config.py

**Change 1:** Add dashboard configuration
Location: After line 32 (SENDER_EMAIL)
```python
# REMOVE (none - just adding):

# ADD:
    # Dashboard Configuration
    DASHBOARD_URL = os.environ.get('DASHBOARD_URL', 'https://refiloe.ai/dashboard')
    ADMIN_KEY = os.environ.get('ADMIN_KEY', 'default_admin_key_change_in_production')
```

### EDIT: app.py

**Change 1:** Import dashboard sync service
Location: After line 34 (from routes.dashboard import dashboard_bp)
```python
# REMOVE (none - just adding):

# ADD:
from services.dashboard_sync import DashboardSyncService
```

**Change 2:** Initialize dashboard sync service
Location: After line 63 (calendar_service initialization)
```python
# REMOVE (none - just adding):

# ADD:
# Initialize dashboard sync service
dashboard_sync = DashboardSyncService(supabase, Config, whatsapp_service)
```

**Change 3:** Pass dashboard_sync to refiloe_service
Location: Line 66 (refiloe_service initialization)
```python
# REMOVE (line 66):
refiloe_service = RefiloeService(supabase)

# ADD:
refiloe_service = RefiloeService(supabase, dashboard_sync_service=dashboard_sync)
```

### EDIT: services/refiloe.py

**Change 1:** Update __init__ to accept dashboard_sync_service
Location: Lines 20-42 (__init__ method)
```python
# REMOVE (line 20):
    def __init__(self, supabase_client):

# ADD:
    def __init__(self, supabase_client, dashboard_sync_service=None):
```

**Change 2:** Add dashboard_sync to service initialization
Location: After line 37 (self.ai_handler initialization)
```python
# REMOVE (none - just adding):

# ADD:
        self.dashboard_sync = dashboard_sync_service
```

**Change 3:** Integrate dashboard sync in process_message
Location: After line 99 (before AI intent understanding)
```python
# REMOVE (none - just adding):

# ADD:
        # Check for dashboard quick commands first
        if self.dashboard_sync:
            quick_command = self.dashboard_sync.handle_quick_command(
                text, user_context.get('client_id') or user_context.get('trainer_id'),
                'trainer' if user_context.get('is_trainer') else 'client',
                from_number
            )
            if quick_command:
                return quick_command
```

**Change 4:** Add dashboard action handling for web-originated actions
Location: After line 136 (in handle intent section)
```python
# REMOVE (none - just adding):

# ADD:
            # Sync to dashboard if relevant
            if self.dashboard_sync and primary_intent in ['log_habits', 'join_challenge']:
                self.dashboard_sync.sync_whatsapp_to_dashboard(
                    user_context.get('client_id') or user_context.get('trainer_id'),
                    'trainer' if user_context.get('is_trainer') else 'client',
                    primary_intent,
                    intent_result.get('extracted_data', {})
                )
```

### EDIT: routes/dashboard.py

**Change 1:** Import dashboard sync service
Location: After line 6 (import secrets)
```python
# REMOVE (none - just adding):

# ADD:
from services.dashboard_sync import DashboardSyncService
```

**Change 2:** Initialize dashboard sync in routes that need it
Location: After line 295 (in pre_book_challenge function)
```python
# REMOVE (none - just adding):

# ADD:
        # Import and use dashboard sync
        from app import dashboard_sync
        
        # Handle dashboard action
        sync_result = dashboard_sync.handle_dashboard_action(
            request.user['id'],
            request.user_type,
            'pre_book_challenge',
            {'challenge_name': challenge.data['name']}
        )
```

**Change 3:** Add similar integration to update_preferences
Location: After line 192 (in update_preferences function, after successful update)
```python
# REMOVE (none - just adding):

# ADD:
        # Sync preference change
        from app import dashboard_sync
        dashboard_sync.handle_dashboard_action(
            request.user['id'],
            request.user_type,
            'change_preferences',
            updates
        )
```

### NEW FILE: utils/logger.py
```python
"""Logging utilities for Refiloe"""
import logging
import sys
from datetime import datetime
import pytz

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def setup_logger(name='refiloe'):
    """Setup and return a logger instance"""
    return logging.getLogger(name)

def log_info(message, **kwargs):
    """Log info message"""
    logger = logging.getLogger('refiloe')
    logger.info(message, **kwargs)

def log_error(message, exc_info=False, **kwargs):
    """Log error message"""
    logger = logging.getLogger('refiloe')
    logger.error(message, exc_info=exc_info, **kwargs)

def log_warning(message, **kwargs):
    """Log warning message"""
    logger = logging.getLogger('refiloe')
    logger.warning(message, **kwargs)

def log_debug(message, **kwargs):
    """Log debug message"""
    logger = logging.getLogger('refiloe')
    logger.debug(message, **kwargs)
```

### NEW FILE: utils/rate_limiter.py
```python
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
```

### NEW FILE: utils/input_sanitizer.py
```python
"""Input sanitization utilities"""
import re
from typing import Tuple

class InputSanitizer:
    """Sanitize user input for security"""
    
    def __init__(self, config):
        self.config = config
        # Patterns to block
        self.sql_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)',
            r'(--|#|\/\*|\*\/)',
        ]
        self.script_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
    
    def sanitize_message(self, message: str, sender: str) -> Tuple[str, bool, list]:
        """
        Sanitize message text
        Returns: (sanitized_text, is_safe, warnings)
        """
        warnings = []
        is_safe = True
        sanitized = message
        
        # Check for SQL injection attempts
        for pattern in self.sql_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                warnings.append("Potential SQL injection detected")
                is_safe = False
        
        # Check for script injection
        for pattern in self.script_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                warnings.append("Script injection detected")
                is_safe = False
        
        # Remove potentially harmful characters
        if not is_safe:
            # Remove special characters that could be harmful
            sanitized = re.sub(r'[<>\"\'`;]', '', message)
        
        # Limit message length
        max_length = 4096
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            warnings.append("Message truncated due to length")
        
        return sanitized, is_safe, warnings
    
    def sanitize_phone(self, phone: str) -> str:
        """Sanitize phone number"""
        # Remove all non-numeric characters
        cleaned = re.sub(r'\D', '', phone)
        
        # Handle South African format
        if cleaned.startswith('27'):
            return f"+{cleaned}"
        elif cleaned.startswith('0'):
            return f"+27{cleaned[1:]}"
        else:
            return f"+27{cleaned}"
```

## MIGRATION: 20250103_dashboard_sync_tables.sql
```sql
-- Create notification queue table for digest management
CREATE TABLE IF NOT EXISTS notification_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    notification_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create dashboard updates table for real-time sync
CREATE TABLE IF NOT EXISTS dashboard_updates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    action VARCHAR(100) NOT NULL,
    data JSONB,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add dashboard URL preferences to gamification_profiles
ALTER TABLE gamification_profiles 
ADD COLUMN IF NOT EXISTS dashboard_access_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_dashboard_access TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS prefer_dashboard_for_complex BOOLEAN DEFAULT TRUE;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_notification_queue_user ON notification_queue(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_notification_queue_scheduled ON notification_queue(scheduled_for, sent);
CREATE INDEX IF NOT EXISTS idx_notification_queue_created ON notification_queue(created_at);
CREATE INDEX IF NOT EXISTS idx_dashboard_updates_user ON dashboard_updates(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_dashboard_updates_created ON dashboard_updates(created_at);
CREATE INDEX IF NOT EXISTS idx_dashboard_updates_processed ON dashboard_updates(processed);

-- Comment for rollback:
-- DROP TABLE IF EXISTS notification_queue;
-- DROP TABLE IF EXISTS dashboard_updates;
-- ALTER TABLE gamification_profiles 
-- DROP COLUMN IF EXISTS dashboard_access_count,
-- DROP COLUMN IF EXISTS last_dashboard_access,
-- DROP COLUMN IF EXISTS prefer_dashboard_for_complex;
```

## SUMMARY

**Step 2 Complete:** Core dashboard sync functionality integrated with existing services. Added proper initialization in app.py, integrated with RefiloeService for WhatsApp command routing, connected dashboard routes for action handling, and created missing utility modules (logger, rate_limiter, input_sanitizer). The system now properly routes dashboard quick commands from WhatsApp and syncs actions between dashboard and WhatsApp.

## CONTINUE_NEEDED