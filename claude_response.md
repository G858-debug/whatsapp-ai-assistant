## ANALYSIS
The deployment is failing because the `apscheduler` module is not installed. The error shows that `app.py` is trying to import `BackgroundScheduler` from `apscheduler.schedulers.background` but the module is not available. This is a missing dependency issue that needs to be fixed by adding the package to the requirements.txt file.

## FILES TO CHANGE

### FILE: requirements.txt
```python
# Core Framework
Flask==3.0.0
gunicorn==21.2.0

# WhatsApp & Communication
requests==2.31.0
twilio==8.10.0

# AI & NLP
anthropic==0.39.0

# Database
supabase==2.3.0

# Scheduling & Background Tasks
APScheduler==3.10.4

# Payment Processing
# PayFast uses built-in libraries (hashlib, urllib)

# Utilities
python-dotenv==1.0.0
pytz==2023.3

# Security & Validation
cryptography==41.0.7

# Logging & Monitoring
colorlog==6.8.0

# Data Processing
pandas==2.1.4
numpy==1.26.2

# HTTP & API
urllib3==2.1.0

# Date & Time
python-dateutil==2.8.2

# Environment & Config
python-decouple==3.8
```

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
from models.trainer import Trainer
from models.client import Client
from models.booking import Booking
from utils.logger import setup_logger, log_error, log_info, log_warning
from utils.rate_limiter import RateLimiter
from utils.input_sanitizer import InputSanitizer
from config import Config
from payment_manager import PaymentManager
from payfast_webhook import PayFastWebhookHandler
from voice_helpers import process_voice_note

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Setup logger
setup_logger()

# Validate configuration
try:
    Config.validate()
    log_info("Configuration validated successfully")
except ValueError as e:
    log_error(f"Configuration error: {str(e)}")
    raise

# Initialize Supabase client
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

# Initialize services
whatsapp_service = WhatsAppService(Config.ACCESS_TOKEN, Config.PHONE_NUMBER_ID)
refiloe_service = RefiloeService(supabase, Config.ANTHROPIC_API_KEY)
ai_handler = AIIntentHandler(supabase, Config.ANTHROPIC_API_KEY)
scheduler_service = SchedulerService(supabase)
assessment_service = EnhancedAssessmentService(supabase)
habit_service = HabitTrackingService(supabase)
workout_service = WorkoutService(supabase)
subscription_manager = SubscriptionManager(supabase)
analytics_service = AnalyticsService(supabase)
payment_manager = PaymentManager(supabase)
payfast_handler = PayFastWebhookHandler(supabase)
rate_limiter = RateLimiter(supabase)
input_sanitizer = InputSanitizer()

# Initialize background scheduler
scheduler = BackgroundScheduler(timezone=pytz.timezone(Config.TIMEZONE))

def send_daily_reminders():
    """Send daily workout and payment reminders"""
    try:
        log_info("Running daily reminders task")
        
        # Get today's bookings
        today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
        bookings = scheduler_service.get_bookings_for_date(today)
        
        for booking in bookings:
            # Send reminder 1 hour before session
            session_time = datetime.fromisoformat(booking['session_time'])
            reminder_time = session_time - timedelta(hours=1)
            
            if datetime.now(pytz.timezone(Config.TIMEZONE)) >= reminder_time:
                client_phone = booking['client']['phone_number']
                trainer_name = booking['trainer']['name']
                time_str = session_time.strftime('%I:%M %p')
                
                message = f"🏋️ Reminder: You have a training session with {trainer_name} at {time_str} today!"
                whatsapp_service.send_message(client_phone, message)
        
        # Check for overdue payments
        overdue_payments = payment_manager.get_overdue_payments()
        for payment in overdue_payments:
            client_phone = payment['client']['phone_number']
            amount = payment['amount']
            days_overdue = payment['days_overdue']
            
            message = f"💳 Payment reminder: R{amount} is {days_overdue} days overdue. Please settle your account."
            whatsapp_service.send_message(client_phone, message)
            
        log_info(f"Sent reminders for {len(bookings)} bookings and {len(overdue_payments)} overdue payments")
        
    except Exception as e:
        log_error(f"Error in daily reminders task: {str(e)}")

def check_subscription_status():
    """Check and update subscription statuses"""
    try:
        log_info("Checking subscription statuses")
        expired_count = subscription_manager.check_expired_subscriptions()
        trial_ending_count = subscription_manager.send_trial_ending_reminders()
        
        log_info(f"Processed {expired_count} expired subscriptions and {trial_ending_count} trial endings")
        
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
                if not rate_limiter.check_webhook_rate_limit(ip_address):
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
            if not rate_limiter.check_message_rate_limit(from_number):
                whatsapp_service.send_message(from_number, Config.RATE_LIMIT_MESSAGE)
                return
        
        # Get contact name
        contact_name = "User"
        if contacts:
            contact = next((c for c in contacts if c['wa_id'] == from_number), None)
            if contact:
                contact_name = contact.get('profile', {}).get('name', 'User')
        
        # Handle different message types
        if message_type == 'text':
            text = input_sanitizer.sanitize_text(message['text']['body'])
            handle_text_message(from_number, text, contact_name)
            
        elif message_type == 'audio':
            audio_id = message['audio']['id']
            handle_voice_message(from_number, audio_id, contact_name)
            
        elif message_type == 'interactive':
            handle_interactive_message(from_number, message['interactive'])
            
        elif message_type == 'button':
            handle_button_response(from_number, message['button'])
            
        else:
            whatsapp_service.send_message(
                from_number,
                "I can only process text and voice messages at the moment. Please send me a text or voice note! 😊"
            )
            
    except Exception as e:
        log_error(f"Message processing error: {str(e)}")
        whatsapp_service.send_message(
            from_number,
            "Sorry, I encountered an error processing your message. Please try again."
        )

def handle_text_message(phone_number: str, text: str, contact_name: str):
    """Handle text message"""
    try:
        # Check if user is trainer or client
        user_type, user_data = identify_user(phone_number)
        
        if not user_type:
            # New user - start onboarding
            handle_new_user(phone_number, text, contact_name)
        else:
            # Process message based on user type
            response = ai_handler.process_message(text, phone_number, user_type, user_data)
            
            # Send response
            if response.get('message'):
                whatsapp_service.send_message(phone_number, response['message'])
            
            # Send interactive elements if any
            if response.get('buttons'):
                whatsapp_service.send_interactive_buttons(
                    phone_number,
                    response.get('header', 'Options'),
                    response.get('body', 'Please select:'),
                    response['buttons']
                )
                
    except Exception as e:
        log_error(f"Text message handling error: {str(e)}")
        whatsapp_service.send_message(
            phone_number,
            "Sorry, I couldn't process your message. Please try again."
        )

def handle_voice_message(phone_number: str, audio_id: str, contact_name: str):
    """Handle voice message"""
    try:
        # Check voice note rate limits
        if Config.ENABLE_RATE_LIMITING:
            if not rate_limiter.check_voice_note_rate_limit(phone_number):
                whatsapp_service.send_message(
                    phone_number,
                    "🎤 You're sending voice notes too quickly. Please wait a moment before sending another."
                )
                return
        
        # Process voice note
        transcribed_text = process_voice_note(audio_id, Config.ACCESS_TOKEN)
        
        if transcribed_text:
            # Process as text message
            handle_text_message(phone_number, transcribed_text, contact_name)
        else:
            whatsapp_service.send_message(
                phone_number,
                "Sorry, I couldn't understand your voice message. Please try speaking clearly or send a text message instead."
            )
            
    except Exception as e:
        log_error(f"Voice message handling error: {str(e)}")
        whatsapp_service.send_message(
            phone_number,
            "Sorry, I couldn't process your voice message. Please try again or send a text message."
        )

def handle_interactive_message(phone_number: str, interactive_data: dict):
    """Handle interactive message responses"""
    try:
        response_type = interactive_data.get('type')
        
        if response_type == 'button_reply':
            button_id = interactive_data['button_reply']['id']
            handle_button_click(phone_number, button_id)
            
        elif response_type == 'list_reply':
            list_id = interactive_data['list_reply']['id']
            handle_list_selection(phone_number, list_id)
            
    except Exception as e:
        log_error(f"Interactive message handling error: {str(e)}")

def handle_button_click(phone_number: str, button_id: str):
    """Handle button click from interactive message"""
    try:
        # Process based on button ID
        response = ai_handler.handle_button_action(phone_number, button_id)
        
        if response.get('message'):
            whatsapp_service.send_message(phone_number, response['message'])
            
    except Exception as e:
        log_error(f"Button click handling error: {str(e)}")

def handle_list_selection(phone_number: str, list_id: str):
    """Handle list selection from interactive message"""
    try:
        # Process based on list ID
        response = ai_handler.handle_list_selection(phone_number, list_id)
        
        if response.get('message'):
            whatsapp_service.send_message(phone_number, response['message'])
            
    except Exception as e:
        log_error(f"List selection handling error: {str(e)}")

def handle_button_response(phone_number: str, button_data: dict):
    """Handle button response"""
    try:
        button_text = button_data.get('text', '')
        button_payload = button_data.get('payload', '')
        
        # Process button response
        response = ai_handler.process_button_response(phone_number, button_text, button_payload)
        
        if response.get('message'):
            whatsapp_service.send_message(phone_number, response['message'])
            
    except Exception as e:
        log_error(f"Button response handling error: {str(e)}")

def handle_new_user(phone_number: str, text: str, contact_name: str):
    """Handle new user onboarding"""
    try:
        # Send welcome message
        welcome_message = f"""
👋 Hi {contact_name}! Welcome to Refiloe - your AI fitness assistant!

I help personal trainers and their clients with:
• 📅 Booking sessions
• 💪 Tracking workouts
• 📊 Monitoring progress
• 💳 Managing payments
• 🎯 Setting and achieving goals

Are you a:
1️⃣ Personal Trainer
2️⃣ Client

Please reply with 1 or 2 to get started!
"""
        whatsapp_service.send_message(phone_number, welcome_message)
        
        # Store pending onboarding
        supabase.table('pending_onboarding').insert({
            'phone_number': phone_number,
            'contact_name': contact_name,
            'initial_message': text,
            'created_at': datetime.now().isoformat()
        }).execute()
        
    except Exception as e:
        log_error(f"New user handling error: {str(e)}")

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
        result = payfast_handler.process_webhook(data)
        
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
    
    # Import dashboard routes
    from routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
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
Fixed the deployment crash by adding the missing `APScheduler==3.10.4` dependency to requirements.txt. The app.py file was already correctly importing and using APScheduler for background tasks like daily reminders and subscription status checks. The issue was simply that the package wasn't listed in the requirements file, so it wasn't being installed during deployment.