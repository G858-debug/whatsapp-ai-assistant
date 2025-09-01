from datetime import datetime
import pytz
from typing import Dict, List, Optional

class CalendarSyncModel:
    """Handle calendar synchronization operations"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)

    def get_trainer_preferences(self, trainer_id: str) -> Optional[Dict]:
        """Get trainer's calendar sync preferences"""
        try:
            result = self.db.table('calendar_sync_preferences').select('*').eq(
                'trainer_id', trainer_id
            ).single().execute()
            
            return result.data
            
        except Exception as e:
            return None

    def update_sync_status(self, trainer_id: str, provider: str, 
                          status: str, events_count: int = 0, 
                          error_message: str = None) -> bool:
        """Update sync status for a provider"""
        try:
            data = {
                'trainer_id': trainer_id,
                'provider': provider,
                'last_sync': datetime.now(self.sa_tz).isoformat(),
                'sync_status': status,
                'events_synced': events_count
            }
            if error_message:
                data['error_message'] = error_message

            self.db.table('calendar_sync_status').upsert(data).execute()
            return True
            
        except Exception:
            return False

    def create_calendar_event(self, booking_id: str, 
                            external_event_id: str,
                            provider: str) -> bool:
        """Create calendar event mapping"""
        try:
            data = {
                'booking_id': booking_id,
                'external_event_id': external_event_id,
                'provider': provider,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            self.db.table('calendar_events').insert(data).execute()
            return True
            
        except Exception:
            return False

    def update_trainer_preferences(self, trainer_id: str, preferences: Dict) -> bool:
        """Update trainer's calendar sync preferences"""
        try:
            preferences['updated_at'] = datetime.now(self.sa_tz).isoformat()
            
            self.db.table('calendar_sync_preferences').upsert({
                'trainer_id': trainer_id,
                **preferences
            }).execute()
            
            return True
            
        except Exception:
            return False