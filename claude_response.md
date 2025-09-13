<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5469 -->
<!-- Max Tokens: 32000 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS

Looking at the comment "CONTINUE_NEEDED", I need to continue with the registration system implementation. The previous step created the comprehensive database migration. Now I need to create the missing utility files and registration handlers that are referenced but don't exist yet.

## CHANGES NEEDED

### NEW FILE: utils/logger.py
```python
"""Logging utilities for the application"""
import logging
import sys
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger
logger = logging.getLogger('refiloe')

def log_info(message: str, **kwargs):
    """Log info message"""
    logger.info(message, extra=kwargs)

def log_error(message: str, exc_info=False, **kwargs):
    """Log error message"""
    logger.error(message, exc_info=exc_info, extra=kwargs)

def log_warning(message: str, **kwargs):
    """Log warning message"""
    logger.warning(message, extra=kwargs)

def log_debug(message: str, **kwargs):
    """Log debug message"""
    logger.debug(message, extra=kwargs)

def setup_logger(name: str = 'refiloe', level: int = logging.INFO):
    """Setup and return a logger instance"""
    log = logging.getLogger(name)
    log.setLevel(level)
    return log
```

### NEW FILE: utils/rate_limiter.py
```python
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
```

### NEW FILE: utils/input_sanitizer.py
```python
"""Input sanitization utilities"""
import re
from typing import Optional, Any
from utils.logger import log_warning

class InputSanitizer:
    """Sanitize user inputs for security"""
    
    def __init__(self, config):
        self.config = config
        self.max_length = 1000
        
        # Patterns to remove
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                 # JavaScript protocol
            r'on\w+\s*=',                  # Event handlers
            r'<iframe[^>]*>.*?</iframe>',  # Iframes
            r'DROP\s+TABLE',               # SQL injection
            r'DELETE\s+FROM',              # SQL injection
            r'INSERT\s+INTO',              # SQL injection
            r'UPDATE\s+SET',               # SQL injection
        ]
    
    def sanitize(self, text: Any) -> str:
        """
        Sanitize input text
        
        Args:
            text: Input text to sanitize
            
        Returns:
            Sanitized text string
        """
        if text is None:
            return ""
        
        # Convert to string
        text = str(text)
        
        # Truncate if too long
        if len(text) > self.max_length:
            text = text[:self.max_length]
            log_warning(f"Input truncated to {self.max_length} characters")
        
        # Remove dangerous patterns
        for pattern in self.dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove control characters except newlines
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def sanitize_phone(self, phone: str) -> Optional[str]:
        """
        Sanitize and validate phone number
        
        Args:
            phone: Phone number to sanitize
            
        Returns:
            Sanitized phone number or None if invalid
        """
        # Remove all non-digits
        phone = re.sub(r'\D', '', str(phone))
        
        # South African phone number validation
        if len(phone) == 10 and phone.startswith('0'):
            # Local format: 0821234567 -> 27821234567
            return '27' + phone[1:]
        elif len(phone) == 11 and phone.startswith('27'):
            # International format: 27821234567
            return phone
        elif len(phone) == 9:
            # Missing leading 0: 821234567 -> 27821234567
            return '27' + phone
        
        log_warning(f"Invalid phone number format: {phone}")
        return None
    
    def sanitize_email(self, email: str) -> Optional[str]:
        """
        Sanitize and validate email
        
        Args:
            email: Email to sanitize
            
        Returns:
            Sanitized email or None if invalid
        """
        email = str(email).strip().lower()
        
        # Basic email pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(pattern, email):
            return email
        
        log_warning(f"Invalid email format: {email}")
        return None
    
    def sanitize_name(self, name: str) -> str:
        """
        Sanitize name input
        
        Args:
            name: Name to sanitize
            
        Returns:
            Sanitized name
        """
        name = self.sanitize(name)
        
        # Remove numbers and special characters except spaces, hyphens, apostrophes
        name = re.sub(r'[^a-zA-Z\s\-\']', '', name)
        
        # Normalize multiple spaces
        name = re.sub(r'\s+', ' ', name)
        
        # Title case
        name = name.title()
        
        return name.strip()
    
    def sanitize_amount(self, amount: Any) -> Optional[float]:
        """
        Sanitize and validate currency amount
        
        Args:
            amount: Amount to sanitize
            
        Returns:
            Sanitized amount or None if invalid
        """
        try:
            # Remove currency symbols and spaces
            amount_str = re.sub(r'[Rr$,\s]', '', str(amount))
            
            # Convert to float
            amount_float = float(amount_str)
            
            # Validate reasonable range
            if 0 < amount_float < 100000:
                return round(amount_float, 2)
            
            log_warning(f"Amount outside valid range: {amount_float}")
            return None
            
        except (ValueError, TypeError):
            log_warning(f"Invalid amount format: {amount}")
            return None
```

### NEW FILE: services/whatsapp.py
```python
"""WhatsApp messaging service"""
import requests
from typing import Dict, List, Optional
from utils.logger import log_info, log_error
import json

class WhatsAppService:
    """Service for sending WhatsApp messages"""
    
    def __init__(self, config, supabase_client, logger):
        self.config = config
        self.db = supabase_client
        self.logger = logger
        self.api_url = config.WHATSAPP_API_URL
        self.api_token = config.WHATSAPP_API_TOKEN
        
    def send_message(self, phone: str, message: str, buttons: List[Dict] = None) -> bool:
        """
        Send WhatsApp message
        
        Args:
            phone: Recipient phone number
            message: Message text
            buttons: Optional button list
            
        Returns:
            True if sent successfully
        """
        try:
            # Format phone number
            phone = self._format_phone(phone)
            
            # Build payload
            payload = {
                'to': phone,
                'type': 'text',
                'text': {
                    'body': message
                }
            }
            
            # Add buttons if provided
            if buttons:
                payload['type'] = 'interactive'
                payload['interactive'] = {
                    'type': 'button',
                    'body': {'text': message},
                    'action': {'buttons': buttons}
                }
            
            # Send request
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Message sent to {phone}")
                return True
            else:
                log_error(f"Failed to send message: {response.status_code}")
                return False
                
        except Exception as e:
            log_error(f"Error sending WhatsApp message: {str(e)}")
            return False
    
    def send_template(self, phone: str, template_name: str, 
                     parameters: List[str] = None) -> bool:
        """Send WhatsApp template message"""
        try:
            phone = self._format_phone(phone)
            
            payload = {
                'to': phone,
                'type': 'template',
                'template': {
                    'name': template_name,
                    'language': {'code': 'en'}
                }
            }
            
            if parameters:
                payload['template']['components'] = [{
                    'type': 'body',
                    'parameters': [
                        {'type': 'text', 'text': param}
                        for param in parameters
                    ]
                }]
            
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            log_error(f"Error sending template: {str(e)}")
            return False
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number for WhatsApp"""
        # Remove all non-digits
        phone = ''.join(filter(str.isdigit, phone))
        
        # Add country code if missing
        if not phone.startswith('27'):
            if phone.startswith('0'):
                phone = '27' + phone[1:]
            else:
                phone = '27' + phone
        
        return phone
```

### NEW FILE: services/scheduler.py
```python
"""Scheduling service for reminders and automated tasks"""
from datetime import datetime, timedelta
from typing import Dict, List
import pytz
from utils.logger import log_info, log_error

class SchedulerService:
    """Service for managing scheduled tasks"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def check_and_send_reminders(self) -> Dict:
        """Check and send due reminders"""
        try:
            now = datetime.now(self.sa_tz)
            
            # Get due reminders
            reminders = self.db.table('reminders').select('*').eq(
                'status', 'pending'
            ).lte('scheduled_time', now.isoformat()).execute()
            
            sent_count = 0
            failed_count = 0
            
            for reminder in (reminders.data or []):
                success = self._send_reminder(reminder)
                if success:
                    sent_count += 1
                    # Mark as sent
                    self.db.table('reminders').update({
                        'status': 'sent',
                        'sent_at': now.isoformat()
                    }).eq('id', reminder['id']).execute()
                else:
                    failed_count += 1
            
            log_info(f"Reminders: {sent_count} sent, {failed_count} failed")
            
            return {
                'sent': sent_count,
                'failed': failed_count
            }
            
        except Exception as e:
            log_error(f"Error checking reminders: {str(e)}")
            return {'sent': 0, 'failed': 0}
    
    def _send_reminder(self, reminder: Dict) -> bool:
        """Send individual reminder"""
        try:
            return self.whatsapp.send_message(
                reminder['phone'],
                reminder['message']
            )
        except Exception as e:
            log_error(f"Error sending reminder: {str(e)}")
            return False
    
    def schedule_reminder(self, phone: str, message: str, 
                         scheduled_time: datetime) -> bool:
        """Schedule a reminder"""
        try:
            result = self.db.table('reminders').insert({
                'phone': phone,
                'message': message,
                'scheduled_time': scheduled_time.isoformat(),
                'status': 'pending',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error scheduling reminder: {str(e)}")
            return False
```

### NEW FILE: services/workout.py
```python
"""Workout service for managing training programs"""
from typing import Dict, List, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class WorkoutService:
    """Service for managing workouts and training programs"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def create_workout(self, trainer_id: str, client_id: str, 
                      workout_data: Dict) -> Dict:
        """Create a new workout"""
        try:
            workout = {
                'trainer_id': trainer_id,
                'client_id': client_id,
                'name': workout_data.get('name', 'Custom Workout'),
                'description': workout_data.get('description', ''),
                'exercises': workout_data.get('exercises', []),
                'duration_minutes': workout_data.get('duration', 60),
                'difficulty': workout_data.get('difficulty', 'intermediate'),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('workouts').insert(workout).execute()
            
            if result.data:
                log_info(f"Workout created for client {client_id}")
                return {
                    'success': True,
                    'workout_id': result.data[0]['id']
                }
            
            return {'success': False, 'error': 'Failed to create workout'}
            
        except Exception as e:
            log_error(f"Error creating workout: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_client_workouts(self, client_id: str) -> List[Dict]:
        """Get all workouts for a client"""
        try:
            result = self.db.table('workouts').select('*').eq(
                'client_id', client_id
            ).order('created_at', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting workouts: {str(e)}")
            return []
```

### NEW FILE: services/subscription_manager.py
```python
"""Subscription management service"""
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
from utils.logger import log_info, log_error

class SubscriptionManager:
    """Manages trainer subscriptions"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Subscription plans
        self.plans = {
            'free': {
                'name': 'Free',
                'price': 0,
                'client_limit': 3,
                'features': ['Basic features']
            },
            'professional': {
                'name': 'Professional',
                'price': 49,
                'client_limit': None,
                'features': ['Unlimited clients', 'All features']
            }
        }
    
    def check_subscription(self, trainer_id: str) -> Dict:
        """Check trainer's subscription status"""
        try:
            result = self.db.table('trainers').select(
                'subscription_status, subscription_expires_at'
            ).eq('id', trainer_id).single().execute()
            
            if not result.data:
                return {'status': 'free', 'valid': True}
            
            status = result.data.get('subscription_status', 'free')
            expires_at = result.data.get('subscription_expires_at')
            
            if status == 'professional' and expires_at:
                expires = datetime.fromisoformat(expires_at)
                if expires < datetime.now(self.sa_tz):
                    # Expired
                    self.db.table('trainers').update({
                        'subscription_status': 'free'
                    }).eq('id', trainer_id).execute()
                    
                    return {'status': 'free', 'valid': True, 'expired': True}
            
            return {'status': status, 'valid': True}
            
        except Exception as e:
            log_error(f"Error checking subscription: {str(e)}")
            return {'status': 'free', 'valid': False}
    
    def can_add_client(self, trainer_id: str) -> bool:
        """Check if trainer can add more clients"""
        try:
            sub = self.check_subscription(trainer_id)
            
            if sub['status'] == 'professional':
                return True
            
            # Check client count for free plan
            count = self.db.table('clients').select(
                'id', count='exact'
            ).eq('trainer_id', trainer_id).eq(
                'status', 'active'
            ).execute()
            
            return (count.count or 0) < self.plans['free']['client_limit']
            
        except Exception as e:
            log_error(f"Error checking client limit: {str(e)}")
            return False
```

## SUMMARY

Created essential utility and service files that were missing from the project:

1. **Logger utilities** - Centralized logging functionality
2. **Rate limiter** - Prevent abuse and manage API limits
3. **Input sanitizer** - Security layer for user inputs
4. **WhatsApp service** - Core messaging functionality
5. **Scheduler service** - Handle reminders and automated tasks
6. **Workout service** - Manage training programs
7. **Subscription manager** - Handle trainer subscription tiers

All files are under 600 lines and follow the existing project patterns. The registration system can now function with these supporting services in place.