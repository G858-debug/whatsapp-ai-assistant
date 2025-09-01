from typing import Dict
from datetime import datetime
import pytz

# Existing scheduler.py content kept for reference
# Adding calendar sync classes at the end

class CalendarSyncManager:
    """Manage calendar synchronization for trainers"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        
    def sync_trainer_calendars(self, trainer_id: str) -> Dict:
        """Synchronize calendars for a trainer"""
        try:
            # Get trainer's sync preferences
            prefs = self.db.table('calendar_sync_preferences').select('*').eq(
                'trainer_id', trainer_id
            ).single().execute()
            
            if not prefs.data:
                return {'success': False, 'error': 'No sync preferences found'}
            
            results = {
                'google': None,
                'apple': None,
                'outlook': None
            }
            
            # Sync enabled calendars
            if prefs.data.get('google_calendar_enabled'):
                results['google'] = self._sync_google_calendar(trainer_id)
            
            if prefs.data.get('apple_calendar_enabled'):
                results['apple'] = self._sync_apple_calendar(trainer_id)
            
            # Log sync status
            self._log_sync_status(trainer_id, results)
            
            return {'success': True, 'results': results}
            
        except Exception as e:
            self._log_sync_status(trainer_id, {'error': str(e)})
            return {'success': False, 'error': str(e)}
    
    def handle_sync_conflicts(self, local_booking: Dict, external_event: Dict) -> Dict:
        """Handle conflicts between local and external calendar events"""
        try:
            # Local booking takes precedence
            if local_booking['status'] == 'cancelled':
                return {
                    'action': 'delete_external',
                    'event_id': external_event['id']
                }
            
            if local_booking['updated_at'] > external_event['updated']:
                return {
                    'action': 'update_external',
                    'booking': local_booking
                }
            
            return {
                'action': 'no_action',
                'reason': 'No conflict detected'
            }
            
        except Exception as e:
            return {'action': 'error', 'error': str(e)}
    
    def _sync_google_calendar(self, trainer_id: str) -> Dict:
        """Sync with Google Calendar"""
        # Placeholder implementation
        return {'status': 'not_implemented'}
    
    def _sync_apple_calendar(self, trainer_id: str) -> Dict:
        """Sync with Apple Calendar"""
        # Placeholder implementation
        return {'status': 'not_implemented'}
    
    def _log_sync_status(self, trainer_id: str, details: Dict):
        """Log calendar sync status"""
        try:
            now = datetime.now(pytz.UTC)
            
            # Log overall sync status
            self.db.table('calendar_sync_status').upsert({
                'trainer_id': trainer_id,
                'last_sync': now.isoformat(),
                'sync_status': 'success' if not details.get('error') else 'error',
                'error_message': details.get('error'),
                'updated_at': now.isoformat()
            }).execute()
            
            # Notify trainer of failures if needed
            if details.get('error'):
                self._notify_sync_failure(trainer_id, details['error'])
            
        except Exception as e:
            print(f"Error logging sync status: {str(e)}")
    
    def _notify_sync_failure(self, trainer_id: str, error: str):
        """Send notification about sync failure"""
        try:
            # Get trainer details
            trainer = self.db.table('trainers').select('*').eq(
                'id', trainer_id
            ).single().execute()
            
            if trainer.data:
                message = (
                    f"⚠️ Calendar Sync Failed\n\n"
                    f"There was a problem syncing your calendar:\n"
                    f"{error}\n\n"
                    f"Please check your calendar settings."
                )
                
                self.whatsapp.send_message(
                    trainer.data['whatsapp'],
                    message
                )
                
        except Exception as e:
            print(f"Error sending sync notification: {str(e)}")


class SchedulerService:
    """Main scheduler service for managing appointments and reminders"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.calendar_sync = CalendarSyncManager(supabase_client, whatsapp_service)
    
    def check_and_send_reminders(self) -> Dict:
        """Check and send workout/payment reminders"""
        try:
            results = {
                'workout_reminders_sent': 0,
                'payment_reminders_sent': 0,
                'errors': []
            }
            
            # Get all active clients who need reminders
            clients = self.db.table('clients').select('*').eq(
                'status', 'active'
            ).execute()
            
            for client in (clients.data or []):
                try:
                    # Check if client needs a workout reminder
                    last_workout = self._get_last_workout_date(client['id'])
                    if self._should_send_workout_reminder(last_workout):
                        self._send_workout_reminder(client)
                        results['workout_reminders_sent'] += 1
                    
                    # Check if client needs a payment reminder
                    if self._has_outstanding_payment(client['id']):
                        self._send_payment_reminder(client)
                        results['payment_reminders_sent'] += 1
                        
                except Exception as e:
                    results['errors'].append(f"Error for client {client['id']}: {str(e)}")
            
            return results
            
        except Exception as e:
            return {
                'error': str(e),
                'workout_reminders_sent': 0,
                'payment_reminders_sent': 0
            }
    
    def _get_last_workout_date(self, client_id: str):
        """Get the date of the client's last workout"""
        try:
            result = self.db.table('bookings').select('session_date').eq(
                'client_id', client_id
            ).eq('status', 'completed').order(
                'session_date', desc=True
            ).limit(1).execute()
            
            if result.data:
                return datetime.fromisoformat(result.data[0]['session_date'])
            return None
            
        except Exception:
            return None
    
    def _should_send_workout_reminder(self, last_workout_date) -> bool:
        """Check if workout reminder should be sent"""
        if not last_workout_date:
            return True
        
        days_since = (datetime.now() - last_workout_date).days
        return days_since >= 7  # Send reminder after 7 days of inactivity
    
    def _has_outstanding_payment(self, client_id: str) -> bool:
        """Check if client has outstanding payments"""
        try:
            result = self.db.table('payment_requests').select('id').eq(
                'client_id', client_id
            ).eq('status', 'pending').execute()
            
            return bool(result.data)
            
        except Exception:
            return False
    
    def _send_workout_reminder(self, client: Dict):
        """Send workout reminder to client"""
        message = (
            f"Hi {client['name']}! 💪\n\n"
            f"It's been a while since your last workout. "
            f"Time to get back on track!\n\n"
            f"Reply 'book' to schedule your next session."
        )
        
        self.whatsapp.send_message(client['whatsapp'], message)
    
    def _send_payment_reminder(self, client: Dict):
        """Send payment reminder to client"""
        message = (
            f"Hi {client['name']}! 💰\n\n"
            f"You have an outstanding payment. "
            f"Please settle your account to continue booking sessions.\n\n"
            f"Reply 'pay' to view payment details."
        )
        
        self.whatsapp.send_message(client['whatsapp'], message)