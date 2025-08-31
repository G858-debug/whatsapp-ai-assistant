## ANALYSIS

Looking at the error `ImportError: cannot import name 'process_voice_note' from 'voice_helpers'`, I can see that:

1. In `app.py` line 33, it's trying to import `process_voice_note` from `voice_helpers`
2. Looking at `voice_helpers.py`, there is NO function called `process_voice_note` - instead there's a `VoiceProcessor` class with methods like `handle_voice_note_with_fallback`
3. The import is incorrect and needs to be fixed

The `voice_helpers.py` file contains a `VoiceProcessor` class but no standalone `process_voice_note` function. We need to either:
- Remove the unused import from `app.py` (since it's not used anywhere in the file)
- Or import the correct class/function

Looking through `app.py`, I don't see `process_voice_note` being used anywhere, so we can simply remove this import.

## FILES TO CHANGE

### FILE: app.py
```python
import os
import json
import traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from supabase import create_client
from dotenv import load_dotenv
import pytz

# Import APScheduler for background tasks
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Import services and utilities
from services.whatsapp import WhatsAppService
from services.refiloe import RefiloeService
from services.ai_intent_handler import AIIntentHandler
from services.scheduler import SchedulerService
from services.assessment import EnhancedAssessmentService
from services.habits import HabitTrackingService
from services.workout import WorkoutService
from services.subscription_manager import SubscriptionManager
from services.analytics import AnalyticsService
from models.trainer import TrainerModel
from models.client import ClientModel
from models.booking import BookingModel
from utils.logger import setup_logger, log_error, log_info, log_warning
from utils.rate_limiter import RateLimiter
from utils.input_sanitizer import InputSanitizer
from config import Config
from payment_manager import PaymentManager
from payfast_webhook import PayFastWebhookHandler
# Removed the problematic import: from voice_helpers import process_voice_note

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

# Initialize Supabase client
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

# Initialize services with proper parameters
whatsapp_service = WhatsAppService(Config, supabase, logger)
ai_handler = AIIntentHandler(Config, supabase)
scheduler_service = SchedulerService(supabase, whatsapp_service)
assessment_service = EnhancedAssessmentService(supabase)
habit_service = HabitTrackingService(supabase)
workout_service = WorkoutService(Config, supabase)
subscription_manager = SubscriptionManager(supabase)
analytics_service = AnalyticsService(supabase)
payment_manager = PaymentManager(supabase)
payfast_handler = PayFastWebhookHandler()  # Already has its own init
rate_limiter = RateLimiter(Config, supabase)
input_sanitizer = InputSanitizer(Config)

# Initialize Refiloe service after other services
refiloe_service = RefiloeService(supabase)

# Initialize models with proper parameters
trainer_model = TrainerModel(supabase, Config)
client_model = ClientModel(supabase, Config)
booking_model = BookingModel(supabase, Config)

# Initialize background scheduler
scheduler = BackgroundScheduler(timezone=pytz.timezone(Config.TIMEZONE))

def send_daily_reminders():
    """Send daily workout and payment reminders"""
    try:
        log_info("Running daily reminders task")
        
        # Use scheduler_service for reminders
        results = scheduler_service.check_and_send_reminders()
        
        log_info(f"Daily reminders completed: {results}")
        
    except Exception as e:
        log_error(f"Error in daily reminders task: {str(e)}")

def check_subscription_status():
    """Check and update subscription statuses"""
    try:
        log_info("Checking subscription statuses")
        
        # Get all active subscriptions
        active_subs = supabase.table('trainer_subscriptions').select('*').eq(
            'status', 'active'
        ).execute()
        
        expired_count = 0
        for sub in (active_subs.data or []):
            # Check if expired
            if sub.get('end_date'):
                end_date = datetime.fromisoformat(sub['end_date'])
                if end_date < datetime.now(pytz.timezone(Config.TIMEZONE)):
                    # Mark as expired
                    supabase.table('trainer_subscriptions').update({
                        'status': 'expired'
                    }).eq('id', sub['id']).execute()
                    expired_count += 1
        
        log_info(f"Processed {expired_count} expired subscriptions")
        
    except Exception as e:
        log_error(f"Error checking subscriptions: {str(e)}")

# Schedule background tasks
scheduler.add_job(
    send_daily_reminders,
    CronTrigger(hour=8, minute=0),  # Run at 8 AM daily
    id='daily_reminders',
    replace_existing=True
)

scheduler.add_job(
    check_subscription_status,
    CronTrigger(hour=0, minute=0),  # Run at midnight daily
    id='check_subscriptions',
    replace_existing=True
)

# Start the scheduler
scheduler.start()
log_info("Background scheduler started")

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
        # Check Supabase connection
        supabase.table('trainers').select('id').limit(1).execute()
        db_status = "connected"
    except:
        db_status = "error"
    
    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Main WhatsApp webhook endpoint"""
    
    if request.method == 'GET':
        # Webhook verification
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if verify_token == Config.VERIFY_TOKEN:
            log_info("Webhook verified successfully")
            return challenge
        else:
            log_warning("Invalid verification token")
            return 'Invalid verification token', 403
    
    elif request.method == 'POST':
        try:
            # Check rate limits
            if Config.ENABLE_RATE_LIMITING:
                ip_address = request.remote_addr
                if not rate_limiter.check_webhook_rate(ip_address):
                    log_warning(f"Rate limit exceeded for IP: {ip_address}")
                    return jsonify({"error": "Rate limit exceeded"}), 429
            
            # Process webhook data
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            # Extract message details
            if 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message in change['value']['messages']:
                                    process_message(message, change['value'].get('contacts', []))
            
            return jsonify({"status": "success"}), 200
            
        except Exception as e:
            log_error(f"Webhook processing error: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"error": "Internal server error"}), 500

def process_message(message: dict, contacts: list):
    """Process incoming WhatsApp message"""
    try:
        from_number = message['from']
        message_type = message.get('type', 'text')
        
        # Check user rate limits
        if Config.ENABLE_RATE_LIMITING:
            allowed, error_msg = rate_limiter.check_message_rate(from_number, message_type)
            if not allowed:
                if error_msg:
                    whatsapp_service.send_message(from_number, error_msg)
                return
        
        # Get contact name
        contact_name = "User"
        if contacts:
            contact = next((c for c in contacts if c['wa_id'] == from_number), None)
            if contact:
                contact_name = contact.get('profile', {}).get('name', 'User')
        
        # Process message with Refiloe service
        message_data = {
            'from': from_number,
            'type': message_type,
            'contact_name': contact_name
        }
        
        # Add message content based on type
        if message_type == 'text':
            text_body = message.get('text', {}).get('body', '')
            # Sanitize input
            sanitized, is_safe, warnings = input_sanitizer.sanitize_message(text_body, from_number)
            if not is_safe:
                whatsapp_service.send_message(from_number, "Sorry, your message contained invalid content.")
                return
            message_data['text'] = {'body': sanitized}
        elif message_type == 'audio':
            message_data['audio'] = message.get('audio', {})
        elif message_type == 'image':
            message_data['image'] = message.get('image', {})
        elif message_type == 'interactive':
            message_data['interactive'] = message.get('interactive', {})
        elif message_type == 'button':
            message_data['button'] = message.get('button', {})
        
        # Process with Refiloe service
        response = refiloe_service.process_message(message_data)
        
        # Send response if successful
        if response.get('success') and response.get('message'):
            whatsapp_service.send_message(from_number, response['message'])
            
            # Send media if included
            if response.get('media_url'):
                whatsapp_service.send_media_message(from_number, response['media_url'], 'image')
            
            # Send buttons if included
            if response.get('buttons'):
                whatsapp_service.send_message_with_buttons(
                    from_number,
                    response.get('header', 'Options'),
                    response['buttons']
                )
            
    except Exception as e:
        log_error(f"Message processing error: {str(e)}")
        try:
            whatsapp_service.send_message(
                from_number,
                "Sorry, I encountered an error processing your message. Please try again."
            )
        except:
            pass

def identify_user(phone_number: str) -> tuple:
    """Identify if user is trainer or client"""
    try:
        # Check trainers table
        trainer = supabase.table('trainers').select('*').eq(
            'phone_number', phone_number
        ).single().execute()
        
        if trainer.data:
            return ('trainer', trainer.data)
        
        # Check clients table
        client = supabase.table('clients').select('*').eq(
            'phone_number', phone_number
        ).single().execute()
        
        if client.data:
            return ('client', client.data)
        
        return (None, None)
        
    except Exception as e:
        log_error(f"User identification error: {str(e)}")
        return (None, None)

@app.route('/webhook/payfast', methods=['POST'])
def payfast_webhook():
    """Handle PayFast payment webhooks"""
    try:
        # Get webhook data
        data = request.form.to_dict()
        signature = request.headers.get('X-PayFast-Signature', '')
        
        # Verify signature
        if not payment_manager.verify_webhook_signature(data, signature):
            log_warning("Invalid PayFast signature")
            return 'Invalid signature', 403
        
        # Process webhook
        result = payfast_handler.process_payment_notification(data)
        
        if result['success']:
            return 'OK', 200
        else:
            return 'Processing failed', 500
            
    except Exception as e:
        log_error(f"PayFast webhook error: {str(e)}")
        return 'Internal error', 500

@app.route('/dashboard')
def dashboard():
    """Simple web dashboard for trainers"""
    if not Config.ENABLE_WEB_DASHBOARD:
        return "Dashboard is disabled", 404
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Refiloe Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            .status { padding: 10px; background: #e8f5e9; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Refiloe AI Assistant Dashboard</h1>
        <div class="status">
            <p>✅ System is running</p>
            <p>📊 View your analytics and manage clients</p>
        </div>
    </body>
    </html>
    """)

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    log_error(f"Server error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

# Cleanup scheduler on shutdown
import atexit
atexit.register(lambda: scheduler.shutdown(wait=False))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    log_info(f"Starting Refiloe AI Assistant on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
```

## SUMMARY

Fixed the import error by removing the unused `from voice_helpers import process_voice_note` import from `app.py`. The `voice_helpers.py` file contains a `VoiceProcessor` class but no `process_voice_note` function. Since this function is not used anywhere in `app.py`, the simplest fix is to remove the import statement entirely. The application should now start without the ImportError.