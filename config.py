import os
from datetime import datetime

class Config:
    """Centralized configuration management"""
    
    # WhatsApp Configuration
    VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe')
    ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
    PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
    WEBHOOK_VERIFY_TOKEN = os.environ.get('WEBHOOK_VERIFY_TOKEN')  # For signature verification
    
    # Anthropic Configuration
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    AI_MODEL = "claude-3-5-sonnet-20241022"  # Updated to Sonnet 4
    
    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    # Application Settings
    TIMEZONE = 'Africa/Johannesburg'
    DEFAULT_CURRENCY = 'R'
    DEFAULT_SESSION_PRICE = 300.00
    
    # Business Rules
    MAX_CONCURRENT_BOOKINGS = 1  # Prevent double bookings
    BOOKING_WINDOW_HOURS = 168  # How far ahead clients can book (7 days)
    REMINDER_DAYS_THRESHOLD = 7  # Send reminder after X days of inactivity
    PAYMENT_OVERDUE_DAYS = 3  # Mark payment overdue after X days
    
    # Session Packages
    PACKAGE_SESSIONS = {
        'single': 1,
        '4-pack': 4,
        '8-pack': 8,
        '12-pack': 12,
        'monthly': 8
    }
    
    # Error Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    MAX_LOG_SIZE_MB = 10
    LOG_RETENTION_DAYS = 30
    
    # ===================================
    # ENHANCED RATE LIMITING CONFIGURATION
    # ===================================
    
    # Message Rate Limiting
    MESSAGE_RATE_LIMIT = 60  # Max messages per minute per user
    MESSAGE_BURST_LIMIT = 10  # Max messages in a 10-second burst
    MESSAGE_DAILY_LIMIT = 500  # Max messages per day per user
    
    # API Rate Limiting
    API_RATE_LIMIT = 100  # Max API calls per minute
    API_BURST_LIMIT = 20  # Max API calls in a 10-second burst
    
    # Webhook Rate Limiting
    WEBHOOK_RATE_LIMIT = 200  # Max webhook calls per minute (total)
    WEBHOOK_PER_IP_LIMIT = 50  # Max webhook calls per IP per minute
    
    # Voice Note Rate Limiting
    VOICE_NOTE_RATE_LIMIT = 10  # Max voice notes per minute per user
    VOICE_NOTE_DAILY_LIMIT = 50  # Max voice notes per day per user
    
    # Payment Request Rate Limiting
    PAYMENT_REQUEST_RATE_LIMIT = 5  # Max payment requests per hour per user
    PAYMENT_REQUEST_DAILY_LIMIT = 10  # Max payment requests per day per user
    
    # Blocking Configuration
    RATE_LIMIT_BLOCK_DURATION_MINUTES = 15  # How long to block after exceeding limits
    RATE_LIMIT_WARNING_THRESHOLD = 0.8  # Warn at 80% of limit
    
    # Whitelist (never rate limited)
    RATE_LIMIT_WHITELIST = os.environ.get('RATE_LIMIT_WHITELIST', '').split(',')
    
    # Enable/Disable Rate Limiting (for testing)
    ENABLE_RATE_LIMITING = os.environ.get('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    
    # Rate Limit Messages
    RATE_LIMIT_MESSAGE = (
        "🚦 Whoa there! You're sending messages too quickly. "
        "Please wait a moment before trying again. "
        "This helps me provide better service to everyone! 😊"
    )
    
    RATE_LIMIT_WARNING_MESSAGE = (
        "⚠️ Heads up! You're approaching the message limit. "
        "Please slow down a bit to avoid being temporarily blocked."
    )
    
    RATE_LIMIT_DAILY_MESSAGE = (
        "📅 You've reached your daily message limit. "
        "Please try again tomorrow! "
        "If this is urgent, please contact your trainer directly."
    )
    
    # ===================================
    # END OF RATE LIMITING CONFIGURATION
    # ===================================
    
    # Feature Flags
    ENABLE_PAYMENT_TRACKING = True
    ENABLE_WORKOUT_PROGRAMS = True  
    ENABLE_WEB_DASHBOARD = True  # Changed to True since we're adding it now!
    ENABLE_MULTI_LANGUAGE = False  # Coming soon
    
    # Dashboard Settings
    DASHBOARD_BASE_URL = 'https://web-production-26de5.up.railway.app'
    DASHBOARD_TOKEN_EXPIRY_HOURS = 24  # How long dashboard links remain valid
    
    # Workout Settings
    GIPHY_API_KEY = os.environ.get('GIPHY_API_KEY')
    
    # Exercise categories
    MUSCLE_GROUPS = ['chest', 'back', 'legs', 'shoulders', 'arms', 'core', 'full body']
    
    # Default workout settings
    DEFAULT_REST_SECONDS = 90
    DEFAULT_WORKOUT_DURATION = 60  # minutes
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = [
            'ACCESS_TOKEN',
            'PHONE_NUMBER_ID',
            'ANTHROPIC_API_KEY',
            'SUPABASE_URL',
            'SUPABASE_SERVICE_KEY'
        ]
        
        missing = [field for field in required if not getattr(cls, field)]
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_booking_slots(cls):
        """Get available booking slots"""
        # This can be customized per trainer later
        return {
            'monday': ['09:00', '10:00', '11:00', '14:00', '15:00', '17:00', '18:00'],
            'tuesday': ['09:00', '10:00', '11:00', '14:00', '15:00', '17:00', '18:00'],
            'wednesday': ['09:00', '10:00', '11:00', '14:00', '15:00', '17:00', '18:00'],
            'thursday': ['09:00', '10:00', '11:00', '14:00', '15:00', '17:00', '18:00'],
            'friday': ['09:00', '10:00', '11:00', '14:00', '15:00', '17:00', '18:00'],
            'saturday': ['08:00', '09:00', '10:00', '11:00'],
            'sunday': []  # Closed on Sundays
        }
