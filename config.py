import os
from typing import Dict, List

class Config:
    """Application configuration"""
    
    # WhatsApp Configuration - Handle both Railway and standard naming
    WHATSAPP_TOKEN = os.environ.get('ACCESS_TOKEN') or os.environ.get('WHATSAPP_TOKEN')
    WHATSAPP_PHONE_ID = os.environ.get('PHONE_NUMBER_ID') or os.environ.get('WHATSAPP_PHONE_ID')
    VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe')  # Use your actual verify token
    
    # Aliases for backward compatibility
    ACCESS_TOKEN = WHATSAPP_TOKEN
    PHONE_NUMBER_ID = WHATSAPP_PHONE_ID
    
    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    # AI Configuration
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    AI_MODEL = os.environ.get('AI_MODEL', 'claude-3-5-sonnet-20241022')
    
    # Google Calendar Configuration
    GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
    GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    # Payment Configuration
    PAYFAST_MERCHANT_ID = os.environ.get('PAYFAST_MERCHANT_ID')
    PAYFAST_MERCHANT_KEY = os.environ.get('PAYFAST_MERCHANT_KEY')
    PAYFAST_PASSPHRASE = os.environ.get('PAYFAST_PASSPHRASE', '')
    PAYFAST_SANDBOX = os.environ.get('PAYFAST_SANDBOX', 'true').lower() == 'true'
    
    # Email Configuration (for calendar invites)
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@refiloe.ai')
    
    # Application Settings
    TIMEZONE = 'Africa/Johannesburg'
    DEFAULT_SESSION_PRICE = 350.00
    ENABLE_RATE_LIMITING = os.environ.get('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    ENABLE_WEB_DASHBOARD = os.environ.get('ENABLE_WEB_DASHBOARD', 'true').lower() == 'true'
    
    # Rate Limiting
    MESSAGE_RATE_LIMIT = 30  # messages per minute
    VOICE_MESSAGE_RATE_LIMIT = 5  # voice messages per minute
    
    # Packages
    PACKAGE_SESSIONS = {
        'single': 1,
        'weekly_4': 4,
        'weekly_8': 8,
        'monthly_12': 12,
        'monthly_16': 16
    }
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = [
            'WHATSAPP_TOKEN',
            'WHATSAPP_PHONE_ID',
            'SUPABASE_URL',
            'SUPABASE_SERVICE_KEY',
            'ANTHROPIC_API_KEY'
        ]
        
        missing = []
        for key in required:
            if not getattr(cls, key):
                missing.append(key)
        
        if missing:
            # Log what we actually have for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Environment variables present: {list(os.environ.keys())}")
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_booking_slots(cls) -> Dict[str, List[str]]:
        """Get available booking time slots per day"""
        return {
            'monday': ['06:00', '07:00', '08:00', '09:00', '16:00', '17:00', '18:00', '19:00'],
            'tuesday': ['06:00', '07:00', '08:00', '09:00', '16:00', '17:00', '18:00', '19:00'],
            'wednesday': ['06:00', '07:00', '08:00', '09:00', '16:00', '17:00', '18:00', '19:00'],
            'thursday': ['06:00', '07:00', '08:00', '09:00', '16:00', '17:00', '18:00', '19:00'],
            'friday': ['06:00', '07:00', '08:00', '09:00', '16:00', '17:00', '18:00'],
            'saturday': ['08:00', '09:00', '10:00', '11:00'],
            'sunday': []  # Closed on Sundays
        }
