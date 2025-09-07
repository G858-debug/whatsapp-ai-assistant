<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0370 -->
<!-- Max Tokens: 8000 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS
The app.py file exceeds the 600-line limit (1125 lines). It needs to be split into smaller, logically grouped modules to improve maintainability.

## CHANGES NEEDED

### SPLIT FILE: app.py
Split into 3 new files:

### NEW FILE: app.py
```python
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

# Cleanup on shutdown
def cleanup():
    """Cleanup resources on shutdown"""
    try:
        scheduler.shutdown()
        log_info("Scheduler shut down successfully")
    except Exception as e:
        log_error(f"Error during cleanup: {str(e)}")

import atexit
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
```

### NEW FILE: app_core.py
```python
from supabase import create_client
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime

from config import Config
from services.whatsapp import WhatsAppService
from services.refiloe import RefiloeService
from services.ai_intent_handler import AIIntentHandler
from services.scheduler import SchedulerService
from services.assessment import EnhancedAssessmentService
from services.habits import HabitTrackingService
from services.workout import WorkoutService
from services.subscription_manager import SubscriptionManager
from services.analytics import AnalyticsService
from services.calendar_service import CalendarService
from models.trainer import TrainerModel
from models.client import ClientModel
from models.booking import BookingModel
from utils.logger import log_info, log_error
from utils.rate_limiter import RateLimiter
from utils.input_sanitizer import InputSanitizer
from payment_manager import PaymentManager
from payfast_webhook import PayFastWebhookHandler
from routes.dashboard import dashboard_bp

def setup_app_core(app):
    """Initialize core services and models"""
    
    # Initialize Supabase client
    supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
    
    # Initialize services
    whatsapp_service = WhatsAppService(Config, supabase)
    ai_handler = AIIntentHandler(Config, supabase)
    scheduler_service = SchedulerService(supabase, whatsapp_service)
    assessment_service = EnhancedAssessmentService(supabase)
    habit_service = HabitTrackingService(supabase)
    workout_service = WorkoutService(Config, supabase)
    subscription_manager = SubscriptionManager(supabase)
    analytics_service = AnalyticsService(supabase)
    payment_manager = PaymentManager(supabase)
    payfast_handler = PayFastWebhookHandler()
    rate_limiter = RateLimiter(Config, supabase)
    input_sanitizer = InputSanitizer(Config)
    calendar_service = CalendarService(supabase, Config)
    refiloe_service = RefiloeService(supabase)
    
    # Initialize models
    trainer_model = TrainerModel(supabase, Config)
    client_model = ClientModel(supabase, Config)
    booking_model = BookingModel(supabase, Config)
    
    # Initialize scheduler
    scheduler = BackgroundScheduler(timezone=pytz.timezone(Config.TIMEZONE))
    
    # Setup scheduled tasks
    setup_scheduled_tasks(scheduler, scheduler_service, supabase)
    
    # Start scheduler
    scheduler.start()
    log_info("Background scheduler started")
    
    # Register blueprints
    app.register_blueprint(dashboard_bp)
    
    # Store services in app context
    app.config['services'] = {
        'whatsapp': whatsapp_service,
        'ai_handler': ai_handler,
        'scheduler': scheduler_service,
        'assessment': assessment_service,
        'habit': habit_service,
        'workout': workout_service,
        'subscription': subscription_manager,
        'analytics': analytics_service,
        'payment': payment_manager,
        'payfast': payfast_handler,
        'rate_limiter': rate_limiter,
        'input_sanitizer': input_sanitizer,
        'calendar': calendar_service,
        'refiloe': refiloe_service
    }
    
    app.config['models'] = {
        'trainer': trainer_model,
        'client': client_model,
        'booking': booking_model
    }
    
    app.config['supabase'] = supabase
    
    return app, scheduler

def setup_scheduled_tasks(scheduler, scheduler_service, supabase):
    """Setup scheduled background tasks"""
    
    def send_daily_reminders():
        """Send daily workout and payment reminders"""
        try:
            log_info("Running daily reminders task")
            results = scheduler_service.check_and_send_reminders()
            log_info(f"Daily reminders completed: {results}")
        except Exception as e:
            log_error(f"Error in daily reminders task: {str(e)}")

    def check_subscription_status():
        """Check and update subscription statuses"""
        try:
            log_info("Checking subscription statuses")
            active_subs = supabase.table('trainer_subscriptions').select('*').eq(
                'status', 'active'
            ).execute()
            
            expired_count = 0
            for sub in (active_subs.data or []):
                if sub.get('end_date'):
                    end_date = datetime.fromisoformat(sub['end_date'])
                    if end_date < datetime.now(pytz.timezone(Config.TIMEZONE)):
                        supabase.table('trainer_subscriptions').update({
                            'status': 'expired'
                        }).eq('id', sub['id']).execute()
                        expired_count += 1
            
            log_info(f"Processed {expired_count} expired subscriptions")
        except Exception as e:
            log_error(f"Error checking subscriptions: {str(e)}")

    scheduler.add_job(
        send_daily_reminders,
        CronTrigger(hour=8, minute=0),
        id='daily_reminders',
        replace_existing=True
    )

    scheduler.add_job(
        check_subscription_status,
        CronTrigger(hour=0, minute=0),
        id='check_subscriptions',
        replace_existing=True
    )
```

### NEW FILE: app_routes.py
```python
from flask import request, jsonify, render_template_string, Response, send_file
from datetime import datetime, timedelta
import pytz
from io import BytesIO
from utils.logger import log_error, log_info, log_warning
from config import Config

def setup_routes(app):
    """Setup application routes"""
    
    @app.route('/')
    def home():
        """Home page"""
        return jsonify({
            "status": "active", 
            "service": "Refiloe AI Assistant",
            "version": "2.0",
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            app.config['supabase'].table('trainers').select('id').limit(1).execute()
            db_status = "connected"
        except:
            db_status = "error"
        
        return jsonify({
            "status": "healthy" if db_status == "connected" else "degraded",
            "database": db_status,
            "timestamp": datetime.now().isoformat()
        })

    # Import route modules
    from routes import (
        webhook_routes,
        calendar_routes,
        assessment_routes,
        analytics_routes,
        admin_routes
    )
    
    # Register route modules
    webhook_routes.register_routes(app)
    calendar_routes.register_routes(app)
    assessment_routes.register_routes(app)
    analytics_routes.register_routes(app)
    admin_routes.register_routes(app)
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors"""
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500) 
    def server_error(e):
        """Handle 500 errors"""
        log_error(f"Server error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
```

## SUMMARY
Split the large app.py file (1125 lines) into 3 smaller, more manageable files:
1. app.py - Main application setup and entry point
2. app_core.py - Core service initialization and configuration
3. app_routes.py - Route definitions and handlers

The code has been reorganized to improve maintainability while preserving all functionality. Additional route modules should be created in the routes/ directory to further split the route handlers.

CONTINUE_NEEDED: Yes - Need to create the individual route modules referenced in app_routes.py