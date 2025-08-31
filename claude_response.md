## ANALYSIS

After reviewing the entire codebase, I've identified several critical issues that could cause errors:

1. **Circular Import Issues**: 
   - `services/scheduler.py` imports `HabitTrackingService` inside `__init__` but doesn't pass proper parameters
   - `services/refiloe.py` creates services without proper parameter passing
   - `services/whatsapp.py` expects 3 parameters but gets only 1 in many places

2. **Missing Import**: 
   - `services/scheduler.py` uses `log_warning` but doesn't import it

3. **Parameter Mismatches**:
   - `AIIntentHandler` expects `(config, supabase_client)` but gets only `(supabase_client)` in multiple places
   - `WhatsAppService` expects `(config, supabase_client, logger)` but gets only `(supabase_client)`
   - `SchedulerService` expects `(supabase_client, whatsapp_service)` but gets only `(supabase_client)`

4. **Missing datetime import in payfast_webhook.py**:
   - Uses `timedelta` but doesn't import it

5. **Incorrect method calls**:
   - `app.py` calls non-existent `ai_handler.process_message()` 
   - Should use `ai_handler.understand_message()` instead

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
from voice_helpers import process_voice_note

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

### FILE: services/scheduler.py
```python
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info, log_warning
from config import Config

class SchedulerService:
    """Service for handling scheduled tasks and reminders"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.timezone = pytz.timezone(Config.TIMEZONE)
        self.habits = None  # Will be initialized when needed
    
    def _get_habits_service(self):
        """Lazy load habits service to avoid circular import"""
        if self.habits is None:
            from services.habits import HabitTrackingService
            self.habits = HabitTrackingService(self.db)
        return self.habits
    
    def check_and_send_reminders(self) -> Dict:
        """Check for and send any pending reminders"""
        try:
            now = datetime.now(self.timezone)
            results = {
                'session_reminders': 0,
                'payment_reminders': 0,
                'assessment_reminders': 0,
                'habit_reminders': 0,
                'errors': []
            }
            
            # Session reminders (24 hours before)
            session_count = self._send_session_reminders(now)
            results['session_reminders'] = session_count
            
            # Payment reminders (overdue payments)
            payment_count = self._send_payment_reminders(now)
            results['payment_reminders'] = payment_count
            
            # Assessment reminders
            assessment_count = self._send_assessment_reminders(now)
            results['assessment_reminders'] = assessment_count
            
            # Habit tracking reminders
            habit_count = self._send_habit_reminders(now)
            results['habit_reminders'] = habit_count
            
            log_info(f"Reminders sent: {results}")
            return results
            
        except Exception as e:
            log_error(f"Error in check_and_send_reminders: {str(e)}")
            return {'error': str(e)}
    
    def _send_session_reminders(self, now: datetime) -> int:
        """Send reminders for upcoming sessions"""
        try:
            # Find sessions happening in the next 24 hours
            tomorrow = now + timedelta(days=1)
            
            sessions = self.db.table('bookings').select(
                '*, client:clients(name, phone_number)'
            ).eq('status', 'confirmed').gte(
                'session_date', now.date().isoformat()
            ).lte(
                'session_date', tomorrow.date().isoformat()
            ).execute()
            
            count = 0
            for session in (sessions.data or []):
                # Check if reminder already sent
                if session.get('reminder_sent'):
                    continue
                
                # Parse session time
                session_datetime = datetime.fromisoformat(
                    f"{session['session_date']}T{session['session_time']}"
                ).replace(tzinfo=self.timezone)
                
                # Check if within 24-hour window
                hours_until = (session_datetime - now).total_seconds() / 3600
                
                if 20 <= hours_until <= 24:
                    # Send reminder
                    client = session['client']
                    message = (
                        f"🏋️ Reminder: You have a training session tomorrow!\n\n"
                        f"📅 Date: {session['session_date']}\n"
                        f"⏰ Time: {session['session_time']}\n\n"
                        f"Reply CANCEL if you need to reschedule.\n"
                        f"Looking forward to seeing you! 💪"
                    )
                    
                    result = self.whatsapp.send_message(
                        client['phone_number'],
                        message
                    )
                    
                    if result['success']:
                        # Mark reminder as sent
                        self.db.table('bookings').update({
                            'reminder_sent': True,
                            'reminder_sent_at': now.isoformat()
                        }).eq('id', session['id']).execute()
                        count += 1
            
            return count
            
        except Exception as e:
            log_error(f"Error sending session reminders: {str(e)}")
            return 0
    
    def _send_payment_reminders(self, now: datetime) -> int:
        """Send reminders for overdue payments"""
        try:
            # Find overdue payments
            overdue_date = (now - timedelta(days=Config.PAYMENT_OVERDUE_DAYS)).date()
            
            payments = self.db.table('payments').select(
                '*, client:clients(name, phone_number)'
            ).eq('status', 'pending').lte(
                'due_date', overdue_date.isoformat()
            ).execute()
            
            count = 0
            for payment in (payments.data or []):
                # Check if reminder was sent recently (within 3 days)
                if payment.get('last_reminder_sent'):
                    last_reminder = datetime.fromisoformat(payment['last_reminder_sent'])
                    if (now - last_reminder).days < 3:
                        continue
                
                client = payment['client']
                message = (
                    f"💳 Payment Reminder\n\n"
                    f"Hi {client['name']}, you have an outstanding payment:\n\n"
                    f"Amount: R{payment['amount']:.2f}\n"
                    f"Due Date: {payment['due_date']}\n\n"
                    f"Please make payment at your earliest convenience.\n"
                    f"Reply PAID once payment is complete."
                )
                
                result = self.whatsapp.send_message(
                    client['phone_number'],
                    message
                )
                
                if result['success']:
                    # Update last reminder sent
                    self.db.table('payments').update({
                        'last_reminder_sent': now.isoformat()
                    }).eq('id', payment['id']).execute()
                    count += 1
            
            return count
            
        except Exception as e:
            log_error(f"Error sending payment reminders: {str(e)}")
            return 0
    
    def _send_assessment_reminders(self, now: datetime) -> int:
        """Send reminders for pending assessments"""
        try:
            # Find assessments due soon
            assessments = self.db.table('fitness_assessments').select(
                '*, client:clients(name, phone_number)'
            ).eq('status', 'pending').lte(
                'due_date', (now + timedelta(days=2)).date().isoformat()
            ).execute()
            
            count = 0
            for assessment in (assessments.data or []):
                # Check if reminder sent
                if assessment.get('reminder_sent'):
                    continue
                
                client = assessment['client']
                message = (
                    f"📋 Assessment Reminder\n\n"
                    f"Hi {client['name']}, please complete your fitness assessment.\n\n"
                    f"Due: {assessment['due_date']}\n\n"
                    f"Reply ASSESSMENT to start or visit your dashboard."
                )
                
                result = self.whatsapp.send_message(
                    client['phone_number'],
                    message
                )
                
                if result['success']:
                    self.db.table('fitness_assessments').update({
                        'reminder_sent': True
                    }).eq('id', assessment['id']).execute()
                    count += 1
            
            return count
            
        except Exception as e:
            log_error(f"Error sending assessment reminders: {str(e)}")
            return 0
    
    def _send_habit_reminders(self, now: datetime) -> int:
        """Send daily habit tracking reminders"""
        try:
            # Only send at specific times (e.g., 8 AM and 8 PM)
            current_hour = now.hour
            if current_hour not in [8, 20]:
                return 0
            
            # Get habits service
            habits_service = self._get_habits_service()
            
            # Get all active clients
            today = now.date().isoformat()
            clients = self.db.table('clients').select('*').eq(
                'status', 'active'
            ).execute()
            
            count = 0
            for client in (clients.data or []):
                # Check if they've logged any habits today
                habits_today = self.db.table('habit_tracking').select('id').eq(
                    'client_id', client['id']
                ).eq('date', today).execute()
                
                if not habits_today.data:
                    # Check their current streak
                    streak = habits_service.get_current_streak(client['id'])
                    
                    if current_hour == 8:
                        message = (
                            f"🌅 Good morning {client['name']}!\n\n"
                            f"Start your day strong! Remember to:\n"
                            f"💧 Stay hydrated\n"
                            f"🏃 Get your steps in\n"
                            f"💪 Complete your workout\n\n"
                        )
                    else:  # 8 PM
                        message = (
                            f"🌙 Evening check-in!\n\n"
                            f"Don't forget to log your habits for today:\n"
                            f"💧 Water intake\n"
                            f"😴 Sleep hours\n"
                            f"🏃 Steps\n"
                            f"💪 Workout status\n\n"
                            f"Reply with your updates!\n"
                        )
                    
                    if streak > 0:
                        message += f"\n🔥 Current streak: {streak} days! Keep it up!"
                    
                    result = self.whatsapp.send_message(
                        client['phone_number'],
                        message
                    )
                    
                    if result['success']:
                        count += 1
                        
                        # Log that reminder was sent
                        self.db.table('reminder_log').insert({
                            'client_id': client['id'],
                            'reminder_type': 'habit_tracking',
                            'sent_at': now.isoformat()
                        }).execute()
            
            return count
            
        except Exception as e:
            log_error(f"Error sending habit reminders: {str(e)}")
            return 0
    
    def schedule_message(self, recipient: str, message: str, send_at: datetime) -> Dict:
        """Schedule a message to be sent at a specific time"""
        try:
            scheduled_data = {
                'recipient': recipient,
                'message': message,
                'scheduled_for': send_at.isoformat(),
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            result = self.db.table('scheduled_messages').insert(scheduled_data).execute()
            
            if result.data:
                return {
                    'success': True,
                    'scheduled_id': result.data[0]['id'],
                    'send_at': send_at.isoformat()
                }
            
            return {'success': False, 'error': 'Failed to schedule message'}
            
        except Exception as e:
            log_error(f"Error scheduling message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_scheduled_messages(self) -> Dict:
        """Process and send any scheduled messages that are due"""
        try:
            now = datetime.now(self.timezone)
            
            # Get pending messages scheduled for now or earlier
            messages = self.db.table('scheduled_messages').select('*').eq(
                'status', 'pending'
            ).lte('scheduled_for', now.isoformat()).execute()
            
            sent_count = 0
            failed_count = 0
            
            for msg in (messages.data or []):
                result = self.whatsapp.send_message(
                    msg['recipient'],
                    msg['message']
                )
                
                if result['success']:
                    # Mark as sent
                    self.db.table('scheduled_messages').update({
                        'status': 'sent',
                        'sent_at': now.isoformat()
                    }).eq('id', msg['id']).execute()
                    sent_count += 1
                else:
                    # Mark as failed
                    self.db.table('scheduled_messages').update({
                        'status': 'failed',
                        'error': result.get('error', 'Unknown error')
                    }).eq('id', msg['id']).execute()
                    failed_count += 1
            
            return {
                'success': True,
                'sent': sent_count,
                'failed': failed_count
            }
            
        except Exception as e:
            log_error(f"Error processing scheduled messages: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_upcoming_sessions(self, trainer_id: str, days: int = 7) -> List[Dict]:
        """Get upcoming sessions for a trainer"""
        try:
            start_date = datetime.now(self.timezone).date()
            end_date = start_date + timedelta(days=days)
            
            sessions = self.db.table('bookings').select(
                '*, client:clients(name, phone_number)'
            ).eq('trainer_id', trainer_id).eq(
                'status', 'confirmed'
            ).gte('session_date', start_date.isoformat()).lte(
                'session_date', end_date.isoformat()
            ).order('session_date', desc=False).order(
                'session_time', desc=False
            ).execute()
            
            return sessions.data if sessions.data else []
            
        except Exception as e:
            log_error(f"Error getting upcoming sessions: {str(e)}")
            return []
    
    def send_bulk_message(self, trainer_id: str, message: str, client_filter: Optional[Dict] = None) -> Dict:
        """Send a bulk message to multiple clients"""
        try:
            # Get clients based on filter
            query = self.db.table('clients').select('*').eq('trainer_id', trainer_id)
            
            if client_filter:
                if 'status' in client_filter:
                    query = query.eq('status', client_filter['status'])
                if 'package_type' in client_filter:
                    query = query.eq('package_type', client_filter['package_type'])
            
            clients = query.execute()
            
            sent_count = 0
            failed_count = 0
            
            for client in (clients.data or []):
                result = self.whatsapp.send_message(
                    client['phone_number'],
                    message
                )
                
                if result['success']:
                    sent_count += 1
                else:
                    failed_count += 1
            
            return {
                'success': True,
                'sent': sent_count,
                'failed': failed_count,
                'total': len(clients.data) if clients.data else 0
            }
            
        except Exception as e:
            log_error(f"Error sending bulk message: {str(e)}")
            return {'success': False, 'error': str(e)}
```

### FILE: payfast_webhook.py
```python
# payfast_webhook.py
"""
PayFast Webhook Handler for Refiloe
Processes PayFast notifications for payments and subscriptions
"""

import os
import hashlib
import urllib.parse
import json
from datetime import datetime, timedelta
from