"""
Reminder Scheduler Service
Handles cron job scheduling for habit reminders
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from datetime import datetime, time
from utils.logger import log_info, log_error
import atexit
import os


class ReminderScheduler:
    """Scheduler for habit reminders"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.scheduler = None
        self._initialize_scheduler()
    
    def _initialize_scheduler(self):
        """Initialize the APScheduler"""
        try:
            # Configure scheduler with thread pool
            executors = {
                'default': ThreadPoolExecutor(max_workers=3)
            }
            
            job_defaults = {
                'coalesce': True,  # Combine multiple pending executions
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 300  # 5 minutes grace time for missed jobs
            }
            
            self.scheduler = BackgroundScheduler(
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )
            
            # Register shutdown handler
            atexit.register(self.shutdown)
            
            log_info("Reminder scheduler initialized")
            
        except Exception as e:
            log_error(f"Error initializing reminder scheduler: {str(e)}")
    
    def start(self):
        """Start the scheduler"""
        try:
            if self.scheduler and not self.scheduler.running:
                self.scheduler.start()
                log_info("Reminder scheduler started")
                
                # Schedule daily reminders
                self._schedule_daily_reminders()
                
        except Exception as e:
            log_error(f"Error starting reminder scheduler: {str(e)}")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                log_info("Reminder scheduler shutdown")
        except Exception as e:
            log_error(f"Error shutting down reminder scheduler: {str(e)}")
    
    def _schedule_daily_reminders(self):
        """Schedule daily habit reminders"""
        try:
            # Get reminder time from environment or use default (9:00 AM)
            reminder_hour = int(os.getenv('REMINDER_HOUR', '9'))
            reminder_minute = int(os.getenv('REMINDER_MINUTE', '0'))
            
            # Schedule daily reminders
            self.scheduler.add_job(
                func=self._send_daily_reminders_job,
                trigger=CronTrigger(
                    hour=reminder_hour,
                    minute=reminder_minute,
                    timezone='UTC'
                ),
                id='daily_habit_reminders',
                name='Daily Habit Reminders',
                replace_existing=True
            )
            
            log_info(f"Daily habit reminders scheduled for {reminder_hour:02d}:{reminder_minute:02d} UTC")
            
            # Also schedule a cleanup job for old reminder records
            self.scheduler.add_job(
                func=self._cleanup_old_reminders_job,
                trigger=CronTrigger(
                    hour=2,  # 2:00 AM UTC
                    minute=0,
                    timezone='UTC'
                ),
                id='cleanup_old_reminders',
                name='Cleanup Old Reminders',
                replace_existing=True
            )
            
            log_info("Old reminders cleanup job scheduled for 02:00 UTC")
            
        except Exception as e:
            log_error(f"Error scheduling daily reminders: {str(e)}")
    
    def _send_daily_reminders_job(self):
        """Job function to send daily reminders"""
        try:
            log_info("Starting daily habit reminders job")
            
            from services.habits.reminder_service import HabitReminderService
            reminder_service = HabitReminderService(self.db, self.whatsapp)
            
            # Send reminders
            result = reminder_service.send_daily_reminders()
            
            if result['success']:
                log_info(f"Daily reminders completed: {result['reminders_sent']} sent, {result['reminders_skipped']} skipped, {result['errors']} errors")
            else:
                log_error(f"Daily reminders failed: {result.get('error', 'Unknown error')}")
            
            # Log summary to database
            self._log_reminder_job_summary(result)
            
        except Exception as e:
            log_error(f"Error in daily reminders job: {str(e)}")
    
    def _cleanup_old_reminders_job(self):
        """Job function to cleanup old reminder records"""
        try:
            log_info("Starting old reminders cleanup job")
            
            # Keep reminders for last 30 days only
            from datetime import date, timedelta
            cutoff_date = date.today() - timedelta(days=30)
            
            # Delete old reminder records
            result = self.db.table('habit_reminders').delete().lt(
                'reminder_date', cutoff_date.isoformat()
            ).execute()
            
            deleted_count = len(result.data) if result.data else 0
            log_info(f"Cleaned up {deleted_count} old reminder records before {cutoff_date}")
            
        except Exception as e:
            log_error(f"Error in cleanup old reminders job: {str(e)}")
    
    def _log_reminder_job_summary(self, result: dict):
        """Log reminder job summary to database"""
        try:
            summary_record = {
                'job_date': datetime.now().date().isoformat(),
                'job_time': datetime.now().time().isoformat(),
                'total_clients': result.get('total_clients', 0),
                'reminders_sent': result.get('reminders_sent', 0),
                'reminders_skipped': result.get('reminders_skipped', 0),
                'errors': result.get('errors', 0),
                'success': result.get('success', False),
                'details': result.get('details', []),
                'created_at': datetime.now().isoformat()
            }
            
            # Create job summary table if it doesn't exist (optional)
            # For now, just log to application logs
            log_info(f"Reminder job summary: {summary_record}")
            
        except Exception as e:
            log_error(f"Error logging reminder job summary: {str(e)}")
    
    def add_custom_reminder(self, client_id: str, reminder_time: time, days_of_week: list = None):
        """Add custom reminder schedule for specific client"""
        try:
            if days_of_week is None:
                days_of_week = [0, 1, 2, 3, 4, 5, 6]  # All days (Monday=0, Sunday=6)
            
            job_id = f"custom_reminder_{client_id}"
            
            self.scheduler.add_job(
                func=self._send_custom_reminder_job,
                args=[client_id],
                trigger=CronTrigger(
                    hour=reminder_time.hour,
                    minute=reminder_time.minute,
                    day_of_week=','.join(map(str, days_of_week)),
                    timezone='UTC'
                ),
                id=job_id,
                name=f'Custom Reminder for {client_id}',
                replace_existing=True
            )
            
            log_info(f"Custom reminder scheduled for client {client_id} at {reminder_time}")
            return True
            
        except Exception as e:
            log_error(f"Error adding custom reminder: {str(e)}")
            return False
    
    def remove_custom_reminder(self, client_id: str):
        """Remove custom reminder for specific client"""
        try:
            job_id = f"custom_reminder_{client_id}"
            self.scheduler.remove_job(job_id)
            log_info(f"Custom reminder removed for client {client_id}")
            return True
            
        except Exception as e:
            log_error(f"Error removing custom reminder: {str(e)}")
            return False
    
    def _send_custom_reminder_job(self, client_id: str):
        """Job function to send custom reminder to specific client"""
        try:
            log_info(f"Sending custom reminder to client {client_id}")
            
            from services.habits.reminder_service import HabitReminderService
            reminder_service = HabitReminderService(self.db, self.whatsapp)
            
            # Get client info
            client_result = self.db.table('clients').select('name, phone').eq('client_id', client_id).execute()
            
            if not client_result.data:
                log_error(f"Client {client_id} not found for custom reminder")
                return
            
            client = {
                'client_id': client_id,
                'name': client_result.data[0]['name'],
                'phone': client_result.data[0]['phone']
            }
            
            # Get preferences
            preferences = reminder_service._get_reminder_preferences(client_id)
            
            # Send reminder
            today = datetime.now().date()
            result = reminder_service._send_habit_reminder(client, preferences, today)
            
            if result['success']:
                log_info(f"Custom reminder sent to client {client_id}")
            else:
                log_error(f"Failed to send custom reminder to client {client_id}: {result.get('error')}")
            
        except Exception as e:
            log_error(f"Error in custom reminder job for client {client_id}: {str(e)}")
    
    def get_scheduled_jobs(self):
        """Get list of scheduled jobs"""
        try:
            if not self.scheduler:
                return []
            
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            
            return jobs
            
        except Exception as e:
            log_error(f"Error getting scheduled jobs: {str(e)}")
            return []
    
    def is_running(self):
        """Check if scheduler is running"""
        return self.scheduler and self.scheduler.running