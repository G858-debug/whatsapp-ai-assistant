from supabase import create_client
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime

from config import Config
from services.whatsapp import WhatsAppService
from services.refiloe import RefiloeService
from services.whatsapp_flow_handler import WhatsAppFlowHandler
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
    from utils.logger import setup_logger
    logger = setup_logger()
    whatsapp_service = WhatsAppService(Config, supabase, logger)
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
    flow_handler = WhatsAppFlowHandler(supabase, whatsapp_service)
    
    # Initialize trainer registration handler
    from services.registration.trainer_registration import TrainerRegistrationHandler
    trainer_registration_handler = TrainerRegistrationHandler(supabase, whatsapp_service)
    
    # Create services dictionary for AI intent handler
    services_dict = {
        'whatsapp': whatsapp_service,
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
        'refiloe': refiloe_service,
        'flow_handler': flow_handler,
        'trainer_registration': trainer_registration_handler
    }
    
    # Initialize AI handler with access to all services
    ai_handler = AIIntentHandler(Config, supabase, services_dict)
    
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
    
    # Initialize dashboard services
    from routes.dashboard import init_dashboard_services
    init_dashboard_services(supabase)
    
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

def process_whatsapp_message(phone, text):
    """
    Process WhatsApp messages - wrapper function for compatibility with tests
    """
    try:
        # Get the refiloe service from app config
        from app import app
        refiloe_service = app.config['services']['refiloe']
        
        # Process the message
        result = refiloe_service.handle_message({'from': phone, 'text': {'body': text}, 'type': 'text'})
        return result
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Error processing WhatsApp message: {str(e)}")
        return {'success': False, 'error': str(e)}

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
