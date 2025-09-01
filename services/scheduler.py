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