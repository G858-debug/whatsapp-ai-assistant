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
    
    # Rate Limiting
    MESSAGE_RATE_LIMIT = 60  # Max messages per minute per user
    API_RATE_LIMIT = 100  # Max API calls per minute
    
    # Feature Flags
    ENABLE_PAYMENT_TRACKING = True
    ENABLE_WORKOUT_PROGRAMS = False  # Coming soon
    ENABLE_WEB_DASHBOARD = False  # Coming soon
    ENABLE_MULTI_LANGUAGE = False  # Coming soon
    
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
