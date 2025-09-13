import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL')
    WHATSAPP_API_TOKEN = os.environ.get('WHATSAPP_API_TOKEN')
    PAYFAST_MERCHANT_ID = os.environ.get('PAYFAST_MERCHANT_ID')
    PAYFAST_MERCHANT_KEY = os.environ.get('PAYFAST_MERCHANT_KEY')
    PAYFAST_RETURN_URL = os.environ.get('PAYFAST_RETURN_URL')
    PAYFAST_CANCEL_URL = os.environ.get('PAYFAST_CANCEL_URL')

    # OpenAI config
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

     # Admin settings
    ADMIN_EMAIL = 'refiloe@refiloeradebe.co.za'
