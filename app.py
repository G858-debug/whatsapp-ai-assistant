import os
import json
import traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, Response, send_file
from supabase import create_client
from dotenv import load_dotenv
import pytz
import secrets
import hashlib
from io import BytesIO

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
from services.calendar_service import CalendarService
from models.trainer import TrainerModel
from models.client import ClientModel
from models.booking import BookingModel
from utils.logger import setup_logger, log_error, log_info, log_warning
from utils.rate_limiter import RateLimiter
from utils.input_sanitizer import InputSanitizer
from config import Config
from payment_manager import PaymentManager
from payfast_webhook import PayFastWebhookHandler

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
payfast_handler = PayFastWebhookHandler()
rate_limiter = RateLimiter(Config, supabase)
input_sanitizer = InputSanitizer(Config)
calendar_service = CalendarService(supabase, Config)

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

# Schedule background tasks
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
            if Config.ENABLE_RATE_LIMITING:
                ip_address = request.remote_addr
                if not rate_limiter.check_webhook_rate(ip_address):
                    log_warning(f"Rate limit exceeded for IP: {ip_address}")
                    return jsonify({"error": "Rate limit exceeded"}), 429
            
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
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
        
        if Config.ENABLE_RATE_LIMITING:
            allowed, error_msg = rate_limiter.check_message_rate(from_number, message_type)
            if not allowed:
                if error_msg:
                    whatsapp_service.send_message(from_number, error_msg)
                return
        
        contact_name = "User"
        if contacts:
            contact = next((c for c in contacts if c['wa_id'] == from_number), None)
            if contact:
                contact_name = contact.get('profile', {}).get('name', 'User')
        
        message_data = {
            'from': from_number,
            'type': message_type,
            'contact_name': contact_name
        }
        
        if message_type == 'text':
            text_body = message.get('text', {}).get('body', '')
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
        
        response = refiloe_service.process_message(message_data)
        
        if response.get('success') and response.get('message'):
            whatsapp_service.send_message(from_number, response['message'])
            
            if response.get('media_url'):
                whatsapp_service.send_media_message(from_number, response['media_url'], 'image')
            
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
        trainer = supabase.table('trainers').select('*').eq(
            'phone_number', phone_number
        ).single().execute()
        
        if trainer.data:
            return ('trainer', trainer.data)
        
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
        data = request.form.to_dict()
        signature = request.headers.get('X-PayFast-Signature', '')
        
        if not payment_manager.verify_webhook_signature(data, signature):
            log_warning("Invalid PayFast signature")
            return 'Invalid signature', 403
        
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

# ===== NEW CLIENT CALENDAR ENDPOINTS =====

def generate_calendar_token(client_id: str) -> str:
    """Generate a secure token for calendar access"""
    token_data = f"{client_id}:{datetime.now().isoformat()}:{secrets.token_hex(16)}"
    return hashlib.sha256(token_data.encode()).hexdigest()

def verify_calendar_token(token: str, client_id: str) -> bool:
    """Verify calendar access token"""
    try:
        # Check if token exists and is valid
        result = supabase.table('calendar_access_tokens').select('*').eq(
            'token', token
        ).eq('client_id', client_id).eq('is_valid', True).execute()
        
        if result.data:
            # Check if token is not expired (24 hours)
            created_at = datetime.fromisoformat(result.data[0]['created_at'])
            if (datetime.now(pytz.UTC) - created_at).total_seconds() < 86400:
                return True
        return False
    except:
        return False

@app.route('/api/client/calendar/<client_id>')
def client_calendar_view(client_id):
    """Client calendar view endpoint"""
    try:
        # Verify access token
        token = request.args.get('token')
        if not token or not verify_calendar_token(token, client_id):
            return "Access denied. Please request a new calendar link.", 403
        
        # Get client info
        client = supabase.table('clients').select('*, trainers(*)').eq(
            'id', client_id
        ).single().execute()
        
        if not client.data:
            return "Client not found", 404
        
        # Get upcoming sessions
        today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
        end_date = today + timedelta(days=30)
        
        sessions = supabase.table('bookings').select('*').eq(
            'client_id', client_id
        ).gte('session_date', today.isoformat()).lte(
            'session_date', end_date.isoformat()
        ).order('session_date').order('session_time').execute()
        
        # Get past sessions (last 10)
        past_sessions = supabase.table('bookings').select('*').eq(
            'client_id', client_id
        ).lt('session_date', today.isoformat()).order(
            'session_date', desc=True
        ).limit(10).execute()
        
        # Find next session
        next_session = None
        for session in (sessions.data or []):
            if session['status'] in ['confirmed', 'rescheduled']:
                next_session = session
                break
        
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>My Training Calendar - {{ client_name }}</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container {
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow: hidden;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }
                .header h1 {
                    font-size: 24px;
                    margin-bottom: 10px;
                }
                .header p {
                    opacity: 0.9;
                    font-size: 14px;
                }
                .next-session {
                    background: #f0f9ff;
                    border-left: 4px solid #3b82f6;
                    margin: 20px;
                    padding: 15px;
                    border-radius: 10px;
                }
                .next-session h2 {
                    color: #1e40af;
                    font-size: 16px;
                    margin-bottom: 10px;
                }
                .session-card {
                    background: white;
                    border: 1px solid #e5e7eb;
                    margin: 10px 20px;
                    padding: 15px;
                    border-radius: 10px;
                    position: relative;
                }
                .session-card.completed {
                    opacity: 0.6;
                    background: #f9fafb;
                }
                .session-date {
                    font-weight: 600;
                    color: #374151;
                    margin-bottom: 5px;
                }
                .session-time {
                    color: #6b7280;
                    font-size: 14px;
                }
                .session-status {
                    position: absolute;
                    top: 15px;
                    right: 15px;
                    padding: 4px 8px;
                    border-radius: 5px;
                    font-size: 12px;
                    font-weight: 500;
                }
                .status-confirmed {
                    background: #d1fae5;
                    color: #065f46;
                }
                .status-completed {
                    background: #e0e7ff;
                    color: #3730a3;
                }
                .status-cancelled {
                    background: #fee2e2;
                    color: #991b1b;
                }
                .section-title {
                    font-size: 18px;
                    font-weight: 600;
                    margin: 30px 20px 15px;
                    color: #1f2937;
                }
                .action-buttons {
                    padding: 20px;
                    display: flex;
                    gap: 10px;
                }
                .btn {
                    flex: 1;
                    padding: 12px;
                    border: none;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 500;
                    text-align: center;
                    text-decoration: none;
                    cursor: pointer;
                }
                .btn-primary {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .btn-secondary {
                    background: #f3f4f6;
                    color: #374151;
                }
                .empty-state {
                    text-align: center;
                    padding: 40px 20px;
                    color: #6b7280;
                }
                .stats {
                    display: flex;
                    justify-content: space-around;
                    padding: 20px;
                    background: #f9fafb;
                }
                .stat {
                    text-align: center;
                }
                .stat-value {
                    font-size: 24px;
                    font-weight: 700;
                    color: #1f2937;
                }
                .stat-label {
                    font-size: 12px;
                    color: #6b7280;
                    margin-top: 5px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📅 My Training Calendar</h1>
                    <p>{{ client_name }} • {{ trainer_name }}</p>
                </div>
                
                {% if next_session %}
                <div class="next-session">
                    <h2>🎯 Next Session</h2>
                    <div class="session-date">{{ next_session.formatted_date }}</div>
                    <div class="session-time">{{ next_session.session_time }}</div>
                </div>
                {% endif %}
                
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">{{ upcoming_count }}</div>
                        <div class="stat-label">Upcoming</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{{ completed_count }}</div>
                        <div class="stat-label">Completed</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{{ total_count }}</div>
                        <div class="stat-label">Total</div>
                    </div>
                </div>
                
                <h2 class="section-title">📍 Upcoming Sessions</h2>
                {% if upcoming_sessions %}
                    {% for session in upcoming_sessions %}
                    <div class="session-card">
                        <div class="session-date">{{ session.formatted_date }}</div>
                        <div class="session-time">🕐 {{ session.session_time }}</div>
                        <span class="session-status status-{{ session.status }}">{{ session.status|upper }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <p>No upcoming sessions scheduled</p>
                    </div>
                {% endif %}
                
                <h2 class="section-title">✅ Recent Sessions</h2>
                {% if past_sessions %}
                    {% for session in past_sessions %}
                    <div class="session-card completed">
                        <div class="session-date">{{ session.formatted_date }}</div>
                        <div class="session-time">{{ session.session_time }}</div>
                        <span class="session-status status-{{ session.status }}">{{ session.status|upper }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <p>No past sessions</p>
                    </div>
                {% endif %}
                
                <div class="action-buttons">
                    <a href="/api/client/trainer-availability/{{ trainer_id }}?client_id={{ client_id }}&token={{ token }}" class="btn btn-primary">
                        Check Availability
                    </a>
                    <a href="/api/client/calendar/{{ client_id }}/ics?token={{ token }}" class="btn btn-secondary">
                        📥 Download Calendar
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Format dates for display
        def format_date(date_str):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%A, %d %B')
        
        # Process sessions for template
        upcoming_sessions = []
        for session in (sessions.data or []):
            session['formatted_date'] = format_date(session['session_date'])
            upcoming_sessions.append(session)
        
        past_sessions_formatted = []
        for session in (past_sessions.data or []):
            session['formatted_date'] = format_date(session['session_date'])
            past_sessions_formatted.append(session)
        
        if next_session:
            next_session['formatted_date'] = format_date(next_session['session_date'])
        
        # Count statistics
        completed_count = len([s for s in past_sessions.data if s['status'] == 'completed'])
        upcoming_count = len([s for s in sessions.data if s['status'] in ['confirmed', 'rescheduled']])
        
        from jinja2 import Template
        template = Template(html_template)
        return template.render(
            client_name=client.data['name'],
            client_id=client_id,
            trainer_name=client.data['trainers']['name'],
            trainer_id=client.data['trainer_id'],
            next_session=next_session,
            upcoming_sessions=upcoming_sessions,
            past_sessions=past_sessions_formatted,
            upcoming_count=upcoming_count,
            completed_count=completed_count,
            total_count=upcoming_count + completed_count,
            token=token
        )
        
    except Exception as e:
        log_error(f"Error in client calendar view: {str(e)}")
        return "Error loading calendar", 500

@app.route('/api/client/trainer-availability/<trainer_id>')
def trainer_availability_view(trainer_id):
    """View trainer availability for rescheduling"""
    try:
        # Verify access
        token = request.args.get('token')
        client_id = request.args.get('client_id')
        
        if not token or not client_id or not verify_calendar_token(token, client_id):
            return "Access denied. Please request a new link.", 403
        
        # Get trainer info
        trainer = supabase.table('trainers').select('*').eq(
            'id', trainer_id
        ).single().execute()
        
        if not trainer.data:
            return "Trainer not found", 404
        
        # Get next 14 days of availability
        today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
        days_data = []
        
        for i in range(14):
            date = today + timedelta(days=i)
            date_str = date.isoformat()
            day_name = date.strftime('%A')
            
            # Get available slots for this day
            available_slots = booking_model.get_available_slots(trainer_id, date_str)
            
            if available_slots:
                days_data.append({
                    'date': date_str,
                    'formatted_date': date.strftime('%a, %d %b'),
                    'day_name': day_name,
                    'slots': available_slots
                })
        
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trainer Availability - {{ trainer_name }}</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container {
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow: hidden;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }
                .header h1 {
                    font-size: 24px;
                    margin-bottom: 10px;
                }
                .day-section {
                    margin: 20px;
                    padding-bottom: 20px;
                    border-bottom: 1px solid #e5e7eb;
                }
                .day-section:last-child {
                    border-bottom: none;
                }
                .day-header {
                    font-size: 16px;
                    font-weight: 600;
                    color: #1f2937;
                    margin-bottom: 15px;
                }
                .slots-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 10px;
                }
                .slot {
                    padding: 10px;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    text-align: center;
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .slot:hover {
                    border-color: #667eea;
                    background: #f0f9ff;
                }
                .slot.available {
                    background: #d1fae5;
                    border-color: #10b981;
                    color: #065f46;
                }
                .back-btn {
                    display: block;
                    margin: 20px;
                    padding: 12px;
                    background: #f3f4f6;
                    color: #374151;
                    text-align: center;
                    text-decoration: none;
                    border-radius: 10px;
                    font-weight: 500;
                }
                .info-box {
                    margin: 20px;
                    padding: 15px;
                    background: #fef3c7;
                    border-radius: 10px;
                    font-size: 14px;
                    color: #92400e;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📅 Available Training Slots</h1>
                    <p>{{ trainer_name }}</p>
                </div>
                
                <div class="info-box">
                    💡 Click on any available time slot to request a booking via WhatsApp
                </div>
                
                {% for day in days %}
                <div class="day-section">
                    <div class="day-header">{{ day.formatted_date }}</div>
                    <div class="slots-grid">
                        {% for slot in day.slots %}
                        <div
</details>
