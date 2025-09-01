import os
from typing import Dict, List

class Config:
    """Application configuration"""
    
    # WhatsApp Configuration
    WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN')
    WHATSAPP_PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID')
    VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'refiloe_verify_token')
    
    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    # AI Configuration
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    
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
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
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