from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import pytz
from typing import Dict, List

from models.client import ClientModel
from models.booking import BookingModel
from utils.logger import log_error, log_info

class SchedulerService:
    """Handle all automated scheduled tasks"""
    
    def __init__(self, config, supabase_client, whatsapp_service, logger):
        self.config = config
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.logger = logger
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Initialize models
        self.client_model = ClientModel(supabase_client, config)
        self.booking_model = BookingModel(supabase_client, config)
        
        # Initialize scheduler
        self.scheduler = BackgroundScheduler(timezone=self.sa_tz)
        self.setup_scheduled_tasks()
        self.scheduler.start()
    
    def setup_scheduled_tasks(self):
        """Configure all scheduled tasks"""
        try:
            # Daily reminders at 9 AM
            self.scheduler.add_job(
                func=self.send_daily_reminders,
                trigger=CronTrigger(hour=9, minute=0, timezone=self.sa_tz),
                id='daily_reminders',
                name='Send daily session reminders',
                replace_existing=True
            )
            
            # Session confirmations at 6 PM (day before)
            self.scheduler.add_job(
                func=self.send_session_confirmations,
                trigger=CronTrigger(hour=18, minute=0, timezone=self.sa_tz),
                id='session_confirmations',
                name='Send 24h session confirmations',
                replace_existing=True
            )
            
            # Payment reminders at 10 AM on weekdays
            if self.config.ENABLE_PAYMENT_TRACKING:
                self.scheduler.add_job(
                    func=self.send_payment_reminders,
                    trigger=CronTrigger(hour=10, minute=0, day_of_week='0-4', timezone=self.sa_tz),
                    id='payment_reminders',
                    name='Send payment reminders',
                    replace_existing=True
                )
            
            # Log cleanup at 2 AM daily
            self.scheduler.add_job(
                func=self.cleanup_old_logs,
                trigger=CronTrigger(hour=2, minute=0, timezone=self.sa_tz),
                id='log_cleanup',
                name='Clean up old logs',
                replace_existing=True
            )
            
            log_info("Scheduled tasks configured successfully")
            
        except Exception as e:
            log_error(f"Error setting up scheduled tasks: {str(e)}")
    
    def send_daily_reminders(self):
        """Send daily reminders to inactive clients"""
        try:
            log_info("Starting daily reminders task")
            
            # Get clients who need reminders
            clients = self.client_model.get_clients_needing_reminders(
                self.config.REMINDER_DAYS_THRESHOLD
            )
            
            sent_count = 0
            for client in clients:
                if client.get('sessions_remaining', 0) > 0:
                    trainer = client['trainers']
                    
                    reminder_msg = f"""💪 Stay Strong, {client['name']}!

It's Refiloe here! It's been a week since your last session with {trainer['name']}. 

Ready to get back on track? I have these times available:

📅 Today: 2pm, 5pm
📅 Tomorrow: 9am, 10am, 2pm

Sessions remaining: {client['sessions_remaining']}

Which time works for you? 🏋️‍♀️"""
                    
                    result = self.whatsapp.send_message(client['whatsapp'], reminder_msg)
                    if result['success']:
                        sent_count += 1
            
            log_info(f"Daily reminders sent to {sent_count} clients")
            
        except Exception as e:
            log_error(f"Error in daily reminders: {str(e)}", exc_info=True)
    
    def send_session_confirmations(self):
        """Send 24-hour session confirmations"""
        try:
            log_info("Starting session confirmations task")
            
            # Get tomorrow's sessions
            tomorrow = (datetime.now(self.sa_tz) + timedelta(days=1)).date()
            tomorrow_start = self.sa_tz.localize(datetime.combine(tomorrow, datetime.min.time()))
            tomorrow_end = tomorrow_start + timedelta(days=1)
            
            # Get all trainers
            trainers = self.db.table('trainers').select('id').eq('status', 'active').execute()
            
            sent_count = 0
            for trainer in trainers.data:
                bookings = self.booking_model.get_trainer_schedule(
                    trainer['id'], tomorrow_start, tomorrow_end
                )
                
                for booking in bookings:
                    if booking['status'] == 'scheduled':
                        client = booking['clients']
                        session_time = datetime.fromisoformat(booking['session_datetime'])
                        
                        confirmation_msg = f"""⏰ Session Reminder

Hi {client['name']}! It's Refiloe here.

Just confirming your training session tomorrow:

📅 {session_time.strftime('%A, %d %B')}
🕐 Time: {session_time.strftime('%I:%M %p')}
💰 Price: R{booking['price']:.0f}

Reply:
• "YES" - if you're coming
• "RESCHEDULE" - to change time
• "CANCEL" - if you can't make it

See you tomorrow! 💪"""
                        
                        result = self.whatsapp.send_message(client['whatsapp'], confirmation_msg)
                        if result['success']:
                            sent_count += 1
            
            log_info(f"Session confirmations sent for {sent_count} bookings")
            
        except Exception as e:
            log_error(f"Error in session confirmations: {str(e)}", exc_info=True)
    
    def send_payment_reminders(self):
        """Send payment reminders for overdue payments"""
        try:
            log_info("Starting payment reminders task")
            
            # This is a placeholder for when payment tracking is fully implemented
            # For now, we'll skip this functionality
            log_info("Payment reminders not yet implemented")
            
        except Exception as e:
            log_error(f"Error in payment reminders: {str(e)}", exc_info=True)
    
    def send_trainer_reminders(self, trainer_id: str) -> Dict:
        """Manually trigger reminders for a specific trainer's clients"""
        try:
            # Get trainer's clients
            clients = self.client_model.get_trainer_clients(trainer_id)
            
            sent_count = 0
            failed_count = 0
            
            for client in clients:
                if client['sessions_remaining'] > 0:
                    reminder_msg = f"""💪 Quick Check-in!

Hi {client['name']}! It's Refiloe here.

Your trainer wanted me to reach out and see how you're doing with your fitness goals.

Ready for your next session? I have these times available:

📅 This Week:
• Tomorrow: 10am, 2pm, 5pm
• Day after: 9am, 1pm, 4pm

Sessions remaining: {client['sessions_remaining']}

Which works better for you? 🏋️‍♀️"""
                    
                    result = self.whatsapp.send_message(client['whatsapp'], reminder_msg)
                    if result['success']:
                        sent_count += 1
                    else:
                        failed_count += 1
            
            log_info(f"Manual reminders: {sent_count} sent, {failed_count} failed")
            
            return {
                'success': True,
                'sent': sent_count,
                'failed': failed_count,
                'message': f'Sent reminders to {sent_count} clients'
            }
            
        except Exception as e:
            log_error(f"Error sending trainer reminders: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to send reminders'
            }
    
    def cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            log_info("Starting log cleanup task")
            self.logger.cleanup_old_logs(self.config.LOG_RETENTION_DAYS)
            
        except Exception as e:
            log_error(f"Error in log cleanup: {str(e)}")
    
    def check_health(self) -> str:
        """Check scheduler health"""
        if self.scheduler.running:
            jobs = self.scheduler.get_jobs()
            return f"running ({len(jobs)} jobs)"
        else:
            return "stopped"
    
    def shutdown(self):
        """Shutdown scheduler gracefully"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                log_info("Scheduler shut down successfully")
        except Exception as e:
            log_error(f"Error shutting down scheduler: {str(e)}")
