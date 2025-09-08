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
