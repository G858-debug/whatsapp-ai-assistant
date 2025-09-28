import os

class Config:
    # Basic Flask config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    
    # Supabase config
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    # Railway API config
    RAILWAY_API_TOKEN = os.environ.get('RAILWAY_API_TOKEN')
    
    # WhatsApp API config
    WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', 'https://graph.facebook.com/v17.0/671257819413918/messages')
    WHATSAPP_API_TOKEN = os.environ.get('ACCESS_TOKEN')  # Gets from Railway's ACCESS_TOKEN
    WHATSAPP_WEBHOOK_VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe')
    PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID', '671257819413918')
    
    # AI config
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    AI_MODEL = os.environ.get('AI_MODEL', 'claude-sonnet-4-20250514')
    
    # PayFast config
    PAYFAST_MERCHANT_ID = os.environ.get('PAYFAST_MERCHANT_ID')
    PAYFAST_MERCHANT_KEY = os.environ.get('PAYFAST_MERCHANT_KEY')
    PAYFAST_RETURN_URL = os.environ.get('PAYFAST_RETURN_URL')
    PAYFAST_CANCEL_URL = os.environ.get('PAYFAST_CANCEL_URL')
    PAYFAST_TEST_MODE = os.environ.get('PAYFAST_TEST_MODE', 'true')
    PAYFAST_PASSPHRASE = os.environ.get('PAYFAST_PASSPHRASE', '')
    
    # Google Calendar config
    GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
    GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    # Other settings
    TIMEZONE = 'Africa/Johannesburg'
    BASE_URL = os.environ.get('BASE_URL', 'https://your-app.railway.app')
    DASHBOARD_URL = os.environ.get('DASHBOARD_URL', 'https://your-app.railway.app/dashboard')
    
    # Admin settings
    ADMIN_EMAIL = 'refiloe@refiloeradebe.co.za'
    ADMIN_PHONE = '+27730564882'
    
    # Additional settings
    ENABLE_RATE_LIMITING = os.environ.get('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    ENABLE_WEB_DASHBOARD = os.environ.get('ENABLE_WEB_DASHBOARD', 'true').lower() == 'true'
    
    # Email settings
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@refiloe.ai')
