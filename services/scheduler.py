from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import pytz
from typing import Dict, List

from models.client import ClientModel
from models.booking import BookingModel
from services.habits import HabitService  # NEW IMPORT
from utils.logger import log_error, log_info

class SchedulerService:
    """Handle all automated scheduled tasks including habit tracking"""
    
    def __init__(self, config, supabase_client, whatsapp_service, logger):
        self.config = config
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.logger = logger
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Initialize models
        self.client_model = ClientModel(supabase_client, config)
        self.booking_model = BookingModel(supabase_client, config)
        
        # Initialize services
        self.habit_service = HabitService(config, supabase_client)  # NEW SERVICE
        
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
            
            # NEW: Habit reminders at 9 AM daily
            self.scheduler.add_job(
                func=self.send_habit_reminders,
                trigger=CronTrigger(hour=9, minute=0, timezone=self.sa_tz),
                id='morning_habit_reminders',
                name='Send morning habit check-ins',
                replace_existing=True
            )
            
            # NEW: Evening habit follow-ups at 6 PM daily
            self.scheduler.add_job(
                func=self.send_habit_followups,
                trigger=CronTrigger(hour=18, minute=0, timezone=self.sa_tz),
                id='evening_habit_followups',
                name='Send evening habit follow-ups',
                replace_existing=True
            )
            
            # NEW: Weekly habit summaries for trainers (Fridays at 3 PM)
            self.scheduler.add_job(
                func=self.send_trainer_habit_summaries,
                trigger=CronTrigger(day_of_week='fri', hour=15, minute=0, timezone=self.sa_tz),
                id='weekly_habit_summaries',
                name='Send weekly habit reports to trainers',
                replace_existing=True
            )
            
            # NEW: Monthly habit progress reports (1st of each month at 10 AM)
            self.scheduler.add_job(
                func=self.send_monthly_habit_reports,
                trigger=CronTrigger(day=1, hour=10, minute=0, timezone=self.sa_tz),
                id='monthly_habit_reports',
                name='Send monthly habit progress reports',
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
            
            log_info("Scheduled tasks configured successfully (including habit tracking)")
            
        except Exception as e:
            log_error(f"Error setting up scheduled tasks: {str(e)}")
    
    # ==================== HABIT TRACKING METHODS ====================
    
    def send_habit_reminders(self):
        """Send morning habit check-in reminders"""
        try:
            log_info("Starting morning habit reminders task")
            
            # Get all active client habits scheduled for morning reminder
            clients_with_habits = self.db.table('client_habits')\
                .select('*, clients(*), habit_templates(*)')\
                .eq('is_active', True)\
                .gte('reminder_time', '08:00:00')\
                .lte('reminder_time', '10:00:00')\
                .execute()
            
            if not clients_with_habits.data:
                log_info("No morning habit reminders to send")
                return
            
            # Group habits by client
            habits_by_client = {}
            for habit_record in clients_with_habits.data:
                client_id = habit_record['client_id']
                if client_id not in habits_by_client:
                    habits_by_client[client_id] = {
                        'client': habit_record['clients'],
                        'habits': []
                    }
                habits_by_client[client_id]['habits'].append(habit_record)
            
            sent_count = 0
            failed_count = 0
            
            for client_id, data in habits_by_client.items():
                client = data['client']
                habits = data['habits']
                
                # Check if already logged today
                today = datetime.now(self.sa_tz).date()
                already_logged = self._check_if_logged_today(client_id, today)
                
                if already_logged:
                    continue
                
                # Generate personalized reminder message
                message = self._generate_habit_reminder_message(client, habits)
                
                # Send via WhatsApp
                result = self.whatsapp.send_message(client['whatsapp'], message)
                
                if result.get('success'):
                    sent_count += 1
                    log_info(f"Sent habit reminder to {client['name']}")
                else:
                    failed_count += 1
                    log_error(f"Failed to send habit reminder to {client['name']}")
            
            log_info(f"Morning habit reminders: {sent_count} sent, {failed_count} failed")
            
        except Exception as e:
            log_error(f"Error sending habit reminders: {str(e)}", exc_info=True)
    
    def send_habit_followups(self):
        """Send evening follow-ups for incomplete habits"""
        try:
            log_info("Starting evening habit follow-ups")
            
            # Get clients who haven't logged habits today
            today = datetime.now(self.sa_tz).date()
            
            # Query for clients with active habits
            clients_with_habits = self.db.table('client_habits')\
                .select('client_id, clients(*)')\
                .eq('is_active', True)\
                .execute()
            
            if not clients_with_habits.data:
                return
            
            # Check who hasn't logged today
            sent_count = 0
            for record in clients_with_habits.data:
                client_id = record['client_id']
                client = record['clients']
                
                # Check if they've logged today
                logged_today = self.db.table('habit_tracking')\
                    .select('id')\
                    .eq('client_id', client_id)\
                    .eq('date', today.isoformat())\
                    .limit(1)\
                    .execute()
                
                if not logged_today.data:
                    # They haven't logged - send follow-up
                    message = f"""Evening check-in! 🌙

Hi {client['name']}, haven't heard from you today about your habits.

Quick check - did you:
💧 Drink your water?
🥗 Eat your veggies?
🚶 Get your steps?

Reply with your numbers or yes/no - every day counts! 💪"""
                    
                    result = self.whatsapp.send_message(client['whatsapp'], message)
                    if result.get('success'):
                        sent_count += 1
            
            log_info(f"Evening follow-ups sent to {sent_count} clients")
            
        except Exception as e:
            log_error(f"Error sending evening follow-ups: {str(e)}", exc_info=True)
    
    def send_trainer_habit_summaries(self):
        """Send weekly habit summaries to trainers"""
        try:
            log_info("Starting weekly habit summaries for trainers")
            
            # Get all active trainers
            trainers = self.db.table('trainers')\
                .select('id, name, whatsapp')\
                .eq('subscription_status', 'active')\
                .execute()
            
            if not trainers.data:
                return
            
            sent_count = 0
            for trainer in trainers.data:
                # Generate weekly report
                report = self.habit_service.generate_weekly_report(trainer['id'])
                
                if not report.get('has_data'):
                    continue
                
                # Format message
                message = f"""📊 Weekly Habit Report

Hi {trainer['name']}! Here's how your clients did this week:

**Overall Stats:**
- Active trackers: {report['active_clients']}
- Avg compliance: {report['average_compliance']}%
- Total check-ins: {report['total_checkins']}

**Top Performers:**
{report['top_performers']}

**Need Encouragement:**
{report['needs_attention']}

**Longest Streaks:**
{report['best_streaks']}

Keep up the great work motivating your clients! 💪"""
                
                result = self.whatsapp.send_message(trainer['whatsapp'], message)
                if result.get('success'):
                    sent_count += 1
            
            log_info(f"Weekly summaries sent to {sent_count} trainers")
            
        except Exception as e:
            log_error(f"Error sending trainer summaries: {str(e)}", exc_info=True)
    
    def send_monthly_habit_reports(self):
        """Send monthly progress reports to clients and trainers"""
        try:
            log_info("Starting monthly habit reports")
            
            # Get all clients with active habits
            clients = self.db.table('client_habits')\
                .select('client_id, clients(*), trainers(*)')\
                .eq('is_active', True)\
                .execute()
            
            if not clients.data:
                return
            
            # Get unique clients
            processed_clients = set()
            sent_count = 0
            
            for record in clients.data:
                client_id = record['client_id']
                
                if client_id in processed_clients:
                    continue
                
                processed_clients.add(client_id)
                client = record['clients']
                trainer = record['trainers']
                
                # Generate monthly report
                report = self.habit_service.generate_monthly_report(client_id)
                
                if not report.get('has_data'):
                    continue
                
                # Send to client
                client_message = f"""📈 Monthly Habit Progress Report

Hi {client['name']}! Here's your habit tracking summary:

**This Month:**
- Days tracked: {report['days_tracked']}/30
- Overall compliance: {report['compliance_percentage']}%
- Best streak: {report['best_streak']} days

**Habit Breakdown:**
{report['habit_details']}

**Progress:**
{report['progress_message']}

Keep going! Every day counts! 🌟"""
                
                result = self.whatsapp.send_message(client['whatsapp'], client_message)
                if result.get('success'):
                    sent_count += 1
                
                # Also notify trainer
                trainer_message = f"""📊 {client['name']}'s monthly habit report:
- Compliance: {report['compliance_percentage']}%
- Best streak: {report['best_streak']} days
- Most consistent: {report['best_habit']}
- Needs work: {report['worst_habit']}"""
                
                self.whatsapp.send_message(trainer['whatsapp'], trainer_message)
            
            log_info(f"Monthly reports sent to {sent_count} clients")
            
        except Exception as e:
            log_error(f"Error sending monthly reports: {str(e)}", exc_info=True)
    
    def _generate_habit_reminder_message(self, client: Dict, habits: List[Dict]) -> str:
        """Generate personalized habit reminder message"""
        
        # Get current streak
        streak_info = self.habit_service.get_client_streaks(client['id'])
        current_streak = streak_info.get('overall_streak', 0)
        
        # Build message
        message = f"Morning {client['name']}! ☀️\n\n"
        message += "Time to check your habits:\n\n"
        
        for habit in habits:
            template = habit.get('habit_templates', {})
            emoji = template.get('emoji', '✅')
            name = habit.get('custom_name') or template.get('name', 'Habit')
            target = habit.get('target_value') or template.get('target_value', '')
            unit = template.get('unit', '')
            
            message += f"{emoji} {name}"
            if target and unit:
                message += f" ({target} {unit})"
            message += "\n"
        
        message += "\nReply with your numbers or yes/no!"
        
        # Add streak motivation
        if current_streak > 0:
            if current_streak < 7:
                message += f"\n\n🔥 Current streak: {current_streak} days!"
            elif current_streak < 30:
                message += f"\n\n🔥 {current_streak} day streak! Keep it up!"
            else:
                message += f"\n\n👑 {current_streak} days! You're a legend!"
        else:
            message += "\n\n💪 Let's start a new streak today!"
        
        return message
    
    def _check_if_logged_today(self, client_id: str, date) -> bool:
        """Check if client has already logged habits today"""
        try:
            result = self.db.table('habit_tracking')\
                .select('id')\
                .eq('client_id', client_id)\
                .eq('date', date.isoformat())\
                .limit(1)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            log_error(f"Error checking habit log: {str(e)}")
            return False
    
    # ==================== EXISTING METHODS (UNCHANGED) ====================
    
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
- "YES" - if you're coming
- "RESCHEDULE" - to change time
- "CANCEL" - if you can't make it

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
                    # Check if they have habits to include in reminder
                    has_habits = self.db.table('client_habits')\
                        .select('id')\
                        .eq('client_id', client['id'])\
                        .eq('is_active', True)\
                        .limit(1)\
                        .execute()
                    
                    reminder_msg = f"""💪 Quick Check-in!

Hi {client['name']}! It's Refiloe here.

Your trainer wanted me to reach out and see how you're doing with your fitness goals.

Ready for your next session? I have these times available:

📅 This Week:
- Tomorrow: 10am, 2pm, 5pm
- Day after: 9am, 1pm, 4pm

Sessions remaining: {client['sessions_remaining']}"""
                    
                    # Add habit tracking reminder if applicable
                    if has_habits.data:
                        reminder_msg += "\n\n✅ Don't forget to log your daily habits too!"
                    
                    reminder_msg += "\n\nWhich time works better for you? 🏋️‍♀️"
                    
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
            # Count habit-related jobs
            habit_jobs = [j for j in jobs if 'habit' in j.id]
            return f"running ({len(jobs)} jobs, {len(habit_jobs)} habit-related)"
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
