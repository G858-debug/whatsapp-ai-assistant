from flask import Flask
from config import Config
from app_core import setup_app_core
from app_routes import setup_routes
import os

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Setup core services and models (this already registers dashboard_bp!)
app, scheduler = setup_app_core(app)

# Setup basic routes
setup_routes(app)

# Import and register OTHER blueprints (NOT dashboard)
from routes.calendar import calendar_bp
from routes.payment import payment_bp
from routes.webhooks import webhooks_bp
from routes.flow_webhook import setup_flow_webhook
from payfast_webhook import payfast_webhook_bp

# Register blueprints (NO dashboard_bp here!)
app.register_blueprint(calendar_bp, url_prefix='/calendar')
app.register_blueprint(payment_bp, url_prefix='/payment')
app.register_blueprint(webhooks_bp)  # NO PREFIX - webhook should be at /webhook
app.register_blueprint(payfast_webhook_bp)  # PayFast at /webhooks/payfast

# Setup flow webhook (requires supabase and whatsapp_service)
try:
    from supabase import create_client
    from services.whatsapp import WhatsAppService
    from config import Config
    
    # Only setup flow webhook if we have the required environment variables
    if Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY:
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
        from utils.logger import log_info
        whatsapp_service = WhatsAppService(Config, supabase, log_info)
        setup_flow_webhook(app, supabase, whatsapp_service)
    else:
        print("Warning: Supabase credentials not found. Flow webhook setup skipped.")
except Exception as e:
    print(f"Warning: Failed to setup flow webhook: {str(e)}")

if __name__ == '__main__':
    # Use Railway's PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
