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