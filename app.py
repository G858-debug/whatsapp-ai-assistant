import os
from flask import Flask
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from config import Config
from app_core import setup_app_core
from app_routes import setup_routes
from utils.logger import setup_logger, log_info, log_error

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Setup logger
logger = setup_logger()

# Validate configuration
try:
    Config.validate()
    log_info("Configuration validated successfully")
except ValueError as e:
    log_error(f"Configuration error: {str(e)}")
    raise

# Initialize core services and models
app, scheduler = setup_app_core(app)

# Setup routes
setup_routes(app)

# Register webhook routes
from routes.webhooks import webhooks_bp
app.register_blueprint(webhooks_bp)

# Register payment routes
from routes.payment import payment_bp
app.register_blueprint(payment_bp)

@app.route('/test-buttons/<phone>', methods=['GET'])
def test_buttons(phone):
    """Test endpoint to send buttons directly"""
    try:
        # Get the WhatsApp service from the app context
        # The WhatsApp service should already be initialized in app_core
        from services.whatsapp import WhatsAppService
        from config import Config
        
        # Get the supabase client that was initialized in app_core
        from app_core import setup_app_core
        
        # Since app_core returns (app, scheduler), we need to get services differently
        # Access the refiloe_service that was set up
        whatsapp = WhatsAppService(Config, app.supabase, logger)
        
        # Log what we're about to do
        logger.info(f"TEST: Attempting to send buttons to {phone}")
        logger.info(f"TEST: ACCESS_TOKEN present: {bool(Config.ACCESS_TOKEN)}")
        logger.info(f"TEST: PHONE_NUMBER_ID: {Config.PHONE_NUMBER_ID}")
        
        # Try to send a simple button message
        result = whatsapp.send_button_message(
            phone=phone,
            body="🧪 Test Message\n\nCan you see these buttons below?",
            buttons=[
                {
                    "type": "reply", 
                    "reply": {
                        "id": "test_yes", 
                        "title": "✅ Yes, I see them!"
                    }
                },
                {
                    "type": "reply", 
                    "reply": {
                        "id": "test_no", 
                        "title": "❌ No buttons"
                    }
                },
                {
                    "type": "reply", 
                    "reply": {
                        "id": "test_help", 
                        "title": "📞 Need help"
                    }
                }
            ]
        )
        
        # Return detailed results
        return jsonify({
            'test_status': 'completed',
            'phone_number': phone,
            'whatsapp_configured': bool(Config.ACCESS_TOKEN and Config.PHONE_NUMBER_ID),
            'result': result,
            'instructions': 'Check your WhatsApp for the test message'
        })
        
    except Exception as e:
        logger.error(f"Test endpoint error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'test_status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc(),
            'whatsapp_configured': bool(Config.ACCESS_TOKEN and Config.PHONE_NUMBER_ID),
            'config_check': {
                'has_token': bool(Config.ACCESS_TOKEN),
                'has_phone_id': bool(Config.PHONE_NUMBER_ID)
            }
        }), 500

# ALSO ADD A SIMPLER CONFIG CHECK ENDPOINT:

@app.route('/test-config', methods=['GET'])
def test_config():
    """Test endpoint to check configuration"""
    from config import Config
    
    return jsonify({
        'whatsapp': {
            'ACCESS_TOKEN_configured': bool(Config.ACCESS_TOKEN),
            'PHONE_NUMBER_ID_configured': bool(Config.PHONE_NUMBER_ID),
            'PHONE_NUMBER_ID_value': Config.PHONE_NUMBER_ID if Config.PHONE_NUMBER_ID else 'NOT SET',
            'TOKEN_length': len(Config.ACCESS_TOKEN) if Config.ACCESS_TOKEN else 0
        },
        'database': {
            'SUPABASE_URL_configured': bool(Config.SUPABASE_URL),
            'SUPABASE_KEY_configured': bool(Config.SUPABASE_SERVICE_KEY)
        },
        'ai': {
            'ANTHROPIC_configured': bool(Config.ANTHROPIC_API_KEY)
        },
        'environment': {
            'DEBUG': Config.DEBUG,
            'TIMEZONE': Config.TIMEZONE
        }
    })

# Cleanup on shutdown
def cleanup():
    """Cleanup resources on shutdown"""
    try:
        scheduler.shutdown()
        log_info("Scheduler shut down successfully")
    except Exception as e:
        log_error(f"Error during cleanup: {str(e)}")

import signal
import atexit

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    log_info(f"Received signal {signum}")
    cleanup()
    exit(0)

# Register signal handlers
atexit.register(cleanup)

if __name__ == '__main__':
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    log_info(f"Starting Refiloe AI Assistant on port {port}")
    log_info(f"Debug mode: {debug_mode}")
    log_info(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
