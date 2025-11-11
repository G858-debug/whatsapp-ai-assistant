"""Scheduling service for reminders and automated tasks"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_info, log_error

class SchedulerService:
    """Handle scheduling of reminders and automated messages"""

    def __init__(self, supabase_client, whatsapp_service, analytics_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.analytics = analytics_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')

        # Initialize timeout service for task monitoring
        self.timeout_service = None
        try:
            from services.task_timeout_service import TaskTimeoutService
            self.timeout_service = TaskTimeoutService(
                supabase_client,
                whatsapp_service,
                analytics_service
            )
        except Exception as e:
            log_error(f"Failed to initialize timeout service: {str(e)}")
    
    def check_and_send_reminders(self) -> Dict:
        """Check and send due reminders"""
        try:
            results = {
                'workout_reminders': self._send_workout_reminders(),
                'payment_reminders': self._send_payment_reminders(),
                'assessment_reminders': self._send_assessment_reminders(),
                'habit_reminders': self._send_habit_reminders(),
                'task_timeouts': self._check_task_timeouts()
            }

            return results

        except Exception as e:
            log_error(f"Error checking reminders: {str(e)}")
            return {'error': str(e)}
    
    def _send_workout_reminders(self) -> Dict:
        """Send workout reminders"""
        try:
            tomorrow = (datetime.now(self.sa_tz) + timedelta(days=1)).date()
            
            # Get tomorrow's bookings
            bookings = self.db.table('bookings').select(
                '*, clients(name, whatsapp), trainers(name, business_name)'
            ).eq('session_date', tomorrow.isoformat()).eq(
                'status', 'confirmed'
            ).execute()
            
            sent_count = 0
            
            for booking in (bookings.data or []):
                client = booking.get('clients', {})
                trainer = booking.get('trainers', {})
                
                if client.get('whatsapp'):
                    message = (
                        f"🏋️ *Workout Reminder*\n\n"
                        f"Hi {client.get('name', 'there')}! Just a reminder about "
                        f"your training session tomorrow:\n\n"
                        f"📅 Date: {booking['session_date']}\n"
                        f"⏰ Time: {booking['session_time']}\n"
                        f"👤 Trainer: {trainer.get('name', 'Your trainer')}\n\n"
                        f"See you there! 💪"
                    )
                    
                    result = self.whatsapp.send_message(
                        client['whatsapp'], 
                        message
                    )
                    
                    if result['success']:
                        sent_count += 1
                        
                        # Log reminder
                        self.db.table('reminder_logs').insert({
                            'booking_id': booking['id'],
                            'reminder_type': 'workout',
                            'sent_to': client['whatsapp'],
                            'sent_at': datetime.now(self.sa_tz).isoformat()
                        }).execute()
            
            return {'sent': sent_count, 'total': len(bookings.data or [])}
            
        except Exception as e:
            log_error(f"Error sending workout reminders: {str(e)}")
            return {'error': str(e)}
    
    def _send_payment_reminders(self) -> Dict:
        """Send payment reminders"""
        try:
            # Get overdue payments
            cutoff_date = (datetime.now(self.sa_tz) - timedelta(days=7)).date()
            
            payments = self.db.table('payment_requests').select(
                '*, clients(name, whatsapp), trainers(name, business_name)'
            ).eq('status', 'pending').lte(
                'created_at', cutoff_date.isoformat()
            ).execute()
            
            sent_count = 0
            
            for payment in (payments.data or []):
                client = payment.get('clients', {})
                
                if client.get('whatsapp'):
                    message = (
                        f"💳 *Payment Reminder*\n\n"
                        f"Hi {client.get('name', 'there')}! You have a pending "
                        f"payment request:\n\n"
                        f"Amount: R{payment['amount']}\n"
                        f"Description: {payment.get('description', 'Training sessions')}\n\n"
                        f"Please complete the payment at your earliest convenience."
                    )
                    
                    result = self.whatsapp.send_message(
                        client['whatsapp'],
                        message
                    )
                    
                    if result['success']:
                        sent_count += 1
            
            return {'sent': sent_count, 'total': len(payments.data or [])}
            
        except Exception as e:
            log_error(f"Error sending payment reminders: {str(e)}")
            return {'error': str(e)}
    
    def _send_assessment_reminders(self) -> Dict:
        """Send assessment reminders"""
        try:
            # Get due assessments
            result = self.db.table('fitness_assessments').select(
                '*, clients(name, whatsapp)'
            ).eq('status', 'pending').lte(
                'due_date', datetime.now(self.sa_tz).isoformat()
            ).execute()
            
            sent_count = 0
            
            for assessment in (result.data or []):
                client = assessment.get('clients', {})
                
                if client.get('whatsapp'):
                    message = (
                        f"📋 *Assessment Reminder*\n\n"
                        f"Hi {client.get('name', 'there')}! Your fitness assessment "
                        f"is due. Please complete it to track your progress.\n\n"
                        f"Reply 'start assessment' to begin."
                    )
                    
                    result = self.whatsapp.send_message(
                        client['whatsapp'],
                        message
                    )
                    
                    if result['success']:
                        sent_count += 1
            
            return {'sent': sent_count}
            
        except Exception as e:
            log_error(f"Error sending assessment reminders: {str(e)}")
            return {'error': str(e)}
    
    def _send_habit_reminders(self) -> Dict:
        """Send daily habit tracking reminders"""
        try:
            # Get clients with habit tracking enabled
            clients = self.db.table('clients').select(
                'id, name, whatsapp'
            ).eq('habit_tracking_enabled', True).execute()
            
            sent_count = 0
            current_hour = datetime.now(self.sa_tz).hour
            
            # Only send between 7am and 8pm
            if 7 <= current_hour <= 20:
                for client in (clients.data or []):
                    # Check if already logged today
                    today = datetime.now(self.sa_tz).date()
                    
                    logged = self.db.table('habit_tracking').select('id').eq(
                        'client_id', client['id']
                    ).eq('date', today.isoformat()).execute()
                    
                    if not logged.data and client.get('whatsapp'):
                        message = (
                            f"📊 *Daily Check-in*\n\n"
                            f"Hi {client.get('name', 'there')}! Time to log your "
                            f"daily habits:\n\n"
                            f"• Water intake (liters)\n"
                            f"• Sleep hours\n"
                            f"• Steps taken\n"
                            f"• Workout completed (yes/no)\n\n"
                            f"Reply with your numbers separated by commas.\n"
                            f"Example: 2.5, 7, 8000, yes"
                        )
                        
                        result = self.whatsapp.send_message(
                            client['whatsapp'],
                            message
                        )
                        
                        if result['success']:
                            sent_count += 1
            
            return {'sent': sent_count}
            
        except Exception as e:
            log_error(f"Error sending habit reminders: {str(e)}")
            return {'error': str(e)}
    
    def _check_task_timeouts(self) -> Dict:
        """Check for timed out tasks and send reminders or cleanup"""
        try:
            if not self.timeout_service:
                log_info("Timeout service not available, skipping task timeout checks")
                return {'skipped': True, 'reason': 'timeout_service_unavailable'}

            results = self.timeout_service.check_and_process_timeouts()

            log_info(f"Task timeout check: {results.get('reminders_sent', 0)} reminders, "
                    f"{results.get('tasks_cleaned', 0)} cleanups")

            return results

        except Exception as e:
            log_error(f"Error checking task timeouts: {str(e)}")
            return {'error': str(e)}

    def schedule_message(self, phone: str, message: str,
                        send_at: datetime) -> Dict:
        """Schedule a message for future sending"""
        try:
            scheduled_data = {
                'phone_number': phone,
                'message': message,
                'scheduled_for': send_at.isoformat(),
                'status': 'pending',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }

            result = self.db.table('scheduled_messages').insert(
                scheduled_data
            ).execute()

            if result.data:
                return {'success': True, 'scheduled_id': result.data[0]['id']}

            return {'success': False, 'error': 'Failed to schedule message'}

        except Exception as e:
            log_error(f"Error scheduling message: {str(e)}")
            return {'success': False, 'error': str(e)}