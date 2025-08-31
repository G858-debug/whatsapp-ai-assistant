## ANALYSIS
The error shows that `HabitTrackingService` cannot be imported from `services/habits.py`. Looking at the services/assessment.py file provided, I can see it's incomplete (truncated). The issue is that services/habits.py likely doesn't have the `HabitTrackingService` class defined. I need to create/fix the habits.py file and ensure all imports in both app.py and refiloe.py work correctly.

## FILES TO CHANGE

### FILE: services/habits.py
```python
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from utils.logger import log_error, log_info
import json

class HabitTrackingService:
    """Service for tracking client habits and daily metrics"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.habit_types = [
            'water_intake',
            'sleep_hours',
            'steps',
            'calories',
            'workout_completed',
            'meals_logged',
            'weight',
            'mood'
        ]
    
    def log_habit(self, client_id: str, habit_type: str, value: any, date: Optional[str] = None) -> Dict:
        """Log a habit entry for a client"""
        try:
            if habit_type not in self.habit_types:
                return {
                    'success': False,
                    'error': f'Invalid habit type. Valid types: {", ".join(self.habit_types)}'
                }
            
            # Use today's date if not specified
            if not date:
                date = datetime.now().date().isoformat()
            
            # Check if entry exists for today
            existing = self.db.table('habit_tracking').select('*').eq(
                'client_id', client_id
            ).eq('habit_type', habit_type).eq('date', date).execute()
            
            if existing.data:
                # Update existing entry
                result = self.db.table('habit_tracking').update({
                    'value': str(value),
                    'updated_at': datetime.now().isoformat()
                }).eq('id', existing.data[0]['id']).execute()
            else:
                # Create new entry
                result = self.db.table('habit_tracking').insert({
                    'client_id': client_id,
                    'habit_type': habit_type,
                    'value': str(value),
                    'date': date,
                    'created_at': datetime.now().isoformat()
                }).execute()
            
            if result.data:
                log_info(f"Habit logged: {habit_type} = {value} for client {client_id}")
                
                # Check for streaks
                streak = self.calculate_streak(client_id, habit_type)
                
                return {
                    'success': True,
                    'message': f'✅ {habit_type.replace("_", " ").title()} logged: {value}',
                    'streak': streak
                }
            
            return {'success': False, 'error': 'Failed to log habit'}
            
        except Exception as e:
            log_error(f"Error logging habit: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_client_habits(self, client_id: str, days: int = 7) -> Dict:
        """Get client's habit data for the specified number of days"""
        try:
            start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
            
            result = self.db.table('habit_tracking').select('*').eq(
                'client_id', client_id
            ).gte('date', start_date).order('date', desc=True).execute()
            
            # Organize by date and type
            habits_by_date = {}
            for entry in result.data:
                date = entry['date']
                if date not in habits_by_date:
                    habits_by_date[date] = {}
                habits_by_date[date][entry['habit_type']] = entry['value']
            
            return {
                'success': True,
                'data': habits_by_date,
                'days_tracked': len(habits_by_date)
            }
            
        except Exception as e:
            log_error(f"Error fetching habits: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def calculate_streak(self, client_id: str, habit_type: str) -> int:
        """Calculate current streak for a specific habit"""
        try:
            # Get all entries for this habit, ordered by date
            result = self.db.table('habit_tracking').select('date').eq(
                'client_id', client_id
            ).eq('habit_type', habit_type).order('date', desc=True).execute()
            
            if not result.data:
                return 0
            
            streak = 0
            current_date = datetime.now().date()
            
            for entry in result.data:
                entry_date = datetime.fromisoformat(entry['date']).date()
                
                # Check if dates are consecutive
                if entry_date == current_date - timedelta(days=streak):
                    streak += 1
                else:
                    break
            
            return streak
            
        except Exception as e:
            log_error(f"Error calculating streak: {str(e)}")
            return 0
    
    def get_current_streak(self, client_id: str) -> int:
        """Get the longest current streak across all habits"""
        try:
            max_streak = 0
            
            # Check workout completion streak (most important)
            workout_streak = self.calculate_streak(client_id, 'workout_completed')
            max_streak = max(max_streak, workout_streak)
            
            return max_streak
            
        except Exception as e:
            log_error(f"Error getting current streak: {str(e)}")
            return 0
    
    def get_habit_summary(self, client_id: str, days: int = 30) -> Dict:
        """Get summary statistics for client habits"""
        try:
            habits_data = self.get_client_habits(client_id, days)
            
            if not habits_data['success']:
                return habits_data
            
            summary = {
                'total_days_tracked': habits_data['days_tracked'],
                'habits': {}
            }
            
            # Calculate averages and totals for each habit type
            for habit_type in self.habit_types:
                values = []
                for date_data in habits_data['data'].values():
                    if habit_type in date_data:
                        try:
                            values.append(float(date_data[habit_type]))
                        except (ValueError, TypeError):
                            continue
                
                if values:
                    summary['habits'][habit_type] = {
                        'average': sum(values) / len(values),
                        'total': sum(values),
                        'days_logged': len(values)
                    }
            
            return {
                'success': True,
                'summary': summary
            }
            
        except Exception as e:
            log_error(f"Error getting habit summary: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def set_habit_goal(self, client_id: str, habit_type: str, goal_value: any, 
                       goal_type: str = 'daily') -> Dict:
        """Set a goal for a specific habit"""
        try:
            goal_data = {
                'client_id': client_id,
                'habit_type': habit_type,
                'goal_value': str(goal_value),
                'goal_type': goal_type,
                'is_active': True,
                'created_at': datetime.now().isoformat()
            }
            
            # Deactivate existing goals for this habit
            self.db.table('habit_goals').update({
                'is_active': False
            }).eq('client_id', client_id).eq('habit_type', habit_type).execute()
            
            # Create new goal
            result = self.db.table('habit_goals').insert(goal_data).execute()
            
            if result.data:
                return {
                    'success': True,
                    'message': f'Goal set: {goal_value} {habit_type.replace("_", " ")} {goal_type}'
                }
            
            return {'success': False, 'error': 'Failed to set goal'}
            
        except Exception as e:
            log_error(f"Error setting habit goal: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_goal_progress(self, client_id: str) -> Dict:
        """Check progress towards habit goals"""
        try:
            # Get active goals
            goals = self.db.table('habit_goals').select('*').eq(
                'client_id', client_id
            ).eq('is_active', True).execute()
            
            if not goals.data:
                return {
                    'success': True,
                    'message': 'No active goals set',
                    'goals': []
                }
            
            progress_list = []
            
            for goal in goals.data:
                # Get recent habit data
                if goal['goal_type'] == 'daily':
                    days = 1
                elif goal['goal_type'] == 'weekly':
                    days = 7
                else:
                    days = 30
                
                habits = self.get_client_habits(client_id, days)
                
                if habits['success']:
                    # Calculate progress
                    total = 0
                    count = 0
                    
                    for date_data in habits['data'].values():
                        if goal['habit_type'] in date_data:
                            try:
                                total += float(date_data[goal['habit_type']])
                                count += 1
                            except (ValueError, TypeError):
                                continue
                    
                    if count > 0:
                        average = total / count
                        goal_value = float(goal['goal_value'])
                        progress = (average / goal_value) * 100
                        
                        progress_list.append({
                            'habit': goal['habit_type'],
                            'goal': goal_value,
                            'current': average,
                            'progress_percentage': min(progress, 100),
                            'goal_type': goal['goal_type']
                        })
            
            return {
                'success': True,
                'goals': progress_list
            }
            
        except Exception as e:
            log_error(f"Error checking goal progress: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_insights(self, client_id: str) -> Dict:
        """Generate insights from habit data"""
        try:
            # Get 30-day summary
            summary = self.get_habit_summary(client_id, 30)
            
            if not summary['success']:
                return summary
            
            insights = []
            
            # Check water intake
            if 'water_intake' in summary['summary']['habits']:
                avg_water = summary['summary']['habits']['water_intake']['average']
                if avg_water < 2.0:
                    insights.append("💧 Your average water intake is below 2 liters. Try to increase it!")
                elif avg_water >= 3.0:
                    insights.append("💧 Great job on water intake! You're well hydrated.")
            
            # Check sleep
            if 'sleep_hours' in summary['summary']['habits']:
                avg_sleep = summary['summary']['habits']['sleep_hours']['average']
                if avg_sleep < 7:
                    insights.append("😴 You're averaging less than 7 hours of sleep. Aim for 7-9 hours.")
                elif avg_sleep >= 8:
                    insights.append("😴 Excellent sleep habits! Keep it up.")
            
            # Check workout consistency
            if 'workout_completed' in summary['summary']['habits']:
                workouts = summary['summary']['habits']['workout_completed']['days_logged']
                if workouts < 8:  # Less than 2 per week
                    insights.append("💪 Try to increase workout frequency to at least 3 times per week.")
                elif workouts >= 12:  # 3+ per week
                    insights.append("💪 Amazing workout consistency! You're crushing it!")
            
            # Check steps
            if 'steps' in summary['summary']['habits']:
                avg_steps = summary['summary']['habits']['steps']['average']
                if avg_steps < 5000:
                    insights.append("🚶 Your daily steps are low. Try to reach at least 8,000 steps.")
                elif avg_steps >= 10000:
                    insights.append("🚶 Fantastic step count! You're very active.")
            
            return {
                'success': True,
                'insights': insights,
                'summary': summary['summary']
            }
            
        except Exception as e:
            log_error(f"Error generating insights: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def parse_habit_from_text(self, text: str) -> Optional[Dict]:
        """Parse habit information from natural language text"""
        try:
            text_lower = text.lower()
            
            # Water intake patterns
            if any(word in text_lower for word in ['water', 'drank', 'hydration']):
                # Extract number
                import re
                numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
                if numbers:
                    value = float(numbers[0])
                    # Convert ml to liters if needed
                    if 'ml' in text_lower:
                        value = value / 1000
                    return {'type': 'water_intake', 'value': value}
            
            # Sleep patterns
            if any(word in text_lower for word in ['sleep', 'slept', 'hours sleep']):
                import re
                numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
                if numbers:
                    return {'type': 'sleep_hours', 'value': float(numbers[0])}
            
            # Steps patterns
            if any(word in text_lower for word in ['steps', 'walked', 'walking']):
                import re
                numbers = re.findall(r'(\d+)', text)
                if numbers:
                    return {'type': 'steps', 'value': int(numbers[0])}
            
            # Workout completion
            if any(word in text_lower for word in ['workout', 'completed', 'trained', 'exercise']):
                if any(word in text_lower for word in ['completed', 'done', 'finished']):
                    return {'type': 'workout_completed', 'value': 1}
            
            # Weight patterns
            if any(word in text_lower for word in ['weight', 'weigh', 'kg', 'kilograms']):
                import re
                numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
                if numbers:
                    return {'type': 'weight', 'value': float(numbers[0])}
            
            return None
            
        except Exception as e:
            log_error(f"Error parsing habit from text: {str(e)}")
            return None
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

# Initialize services with proper parameters
whatsapp_service = WhatsAppService(supabase)
refiloe_service = RefiloeService(supabase)
ai_handler = AIIntentHandler(supabase)
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
        
        # Process message with Refiloe service
        message_data = {
            'from': from_number,
            'type': message_type,
            'contact_name': contact_name
        }
        
        # Add message content based on type
        if message_type == 'text':
            message_data['text'] = {'body': message.get('text', {}).get('body', '')}
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
                whatsapp_service.send_media(from_number, response['media_url'], 'image')
            
            # Send buttons if included
            if response.get('buttons'):
                whatsapp_service.send_interactive_buttons(
                    from_number,
                    response.get('header', 'Options'),
                    response.get('body', 'Please select:'),
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

## MIGRATION: create_habit_tables.sql
```sql
-- Create habit tracking table
CREATE TABLE IF NOT EXISTS habit_tracking (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    habit_type VARCHAR(50) NOT NULL,
    value TEXT NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(client_id, habit_type, date)
);

-- Create habit goals table
CREATE TABLE IF NOT EXISTS habit_goals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    habit_type VARCHAR(50) NOT NULL,
    goal_value TEXT NOT NULL,
    goal_type VARCHAR(20) DEFAULT 'daily', -- daily, weekly, monthly
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    achieved_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better performance
CREATE INDEX idx_habit_tracking_client_date ON habit_tracking(client_id, date DESC);
CREATE INDEX idx_habit_tracking_type ON habit_tracking(habit_type);
CREATE INDEX idx_habit_goals_client_active ON habit_goals(client_id, is_active);

-- Add RLS policies
ALTER TABLE habit_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE habit_goals ENABLE ROW LEVEL SECURITY;

-- Policies for habit_tracking
CREATE POLICY "Clients can view own habits" ON habit_tracking
    FOR SELECT USING (auth.uid() IN (
        SELECT user_id FROM clients WHERE id = habit_tracking.client_id
    ));

CREATE POLICY "Trainers can view client habits" ON habit_tracking
    FOR SELECT