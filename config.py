import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'

    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

    # WhatsApp Configuration - Handle both Railway and standard naming
    WHATSAPP_API_TOKEN = os.environ.get('ACCESS_TOKEN')
    WHATSAPP_PHONE_ID = os.environ.get('PHONE_NUMBER_ID') or os.environ.get('WHATSAPP_PHONE_ID')
    VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe') 
    WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', 'https://graph.facebook.com/v17.0/671257819413918/messages')

    # Aliases for backward compatibility
    ACCESS_TOKEN = WHATSAPP_TOKEN
    PHONE_NUMBER_ID = WHATSAPP_PHONE_ID

    # PayFast config
    PAYFAST_MERCHANT_ID = os.environ.get('PAYFAST_MERCHANT_ID')
    PAYFAST_MERCHANT_KEY = os.environ.get('PAYFAST_MERCHANT_KEY')
    PAYFAST_RETURN_URL = os.environ.get('PAYFAST_RETURN_URL')
    PAYFAST_CANCEL_URL = os.environ.get('PAYFAST_CANCEL_URL')

    # OpenAI config
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

    # AI Configuration
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    AI_MODEL = os.environ.get('AI_MODEL', 'claude-3-5-sonnet-20241022')

     # Admin settings
    ADMIN_EMAIL = 'refiloe@refiloeradebe.co.za'
    
    # Other settings
    TIMEZONE = 'Africa/Johannesburg'
    BASE_URL = os.environ.get('BASE_URL', 'https://web-production-26de5.up.railway.app')
    DASHBOARD_URL = os.environ.get('DASHBOARD_URL', 'https://web-production-26de5.up.railway.app/dashboard')
    ENABLE_RATE_LIMITING = os.environ.get('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    ENABLE_WEB_DASHBOARD = os.environ.get('ENABLE_WEB_DASHBOARD', 'true').lower() == 'true'

    # Google Calendar config
    GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
    GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

    # Email Configuration (for calendar invites)
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@refiloe.ai')
