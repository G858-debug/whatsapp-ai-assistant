"""Scheduling service for reminders and automated tasks"""
from datetime import datetime, timedelta
from typing import Dict, List
import pytz
from utils.logger import log_info, log_error

class SchedulerService:
    """Service for managing scheduled tasks"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def check_and_send_reminders(self) -> Dict:
        """Check and send due reminders"""
        try:
            now = datetime.now(self.sa_tz)
            
            # Get due reminders
            reminders = self.db.table('reminders').select('*').eq(
                'status', 'pending'
            ).lte('scheduled_time', now.isoformat()).execute()
            
            sent_count = 0
            failed_count = 0
            
            for reminder in (reminders.data or []):
                success = self._send_reminder(reminder)
                if success:
                    sent_count += 1
                    # Mark as sent
                    self.db.table('reminders').update({
                        'status': 'sent',
                        'sent_at': now.isoformat()
                    }).eq('id', reminder['id']).execute()
                else:
                    failed_count += 1
            
            log_info(f"Reminders: {sent_count} sent, {failed_count} failed")
            
            return {
                'sent': sent_count,
                'failed': failed_count
            }
            
        except Exception as e:
            log_error(f"Error checking reminders: {str(e)}")
            return {'sent': 0, 'failed': 0}
    
    def _send_reminder(self, reminder: Dict) -> bool:
        """Send individual reminder"""
        try:
            return self.whatsapp.send_message(
                reminder['phone'],
                reminder['message']
            )
        except Exception as e:
            log_error(f"Error sending reminder: {str(e)}")
            return False
    
    def schedule_reminder(self, phone: str, message: str, 
                         scheduled_time: datetime) -> bool:
        """Schedule a reminder"""
        try:
            result = self.db.table('reminders').insert({
                'phone': phone,
                'message': message,
                'scheduled_time': scheduled_time.isoformat(),
                'status': 'pending',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error scheduling reminder: {str(e)}")
            return False