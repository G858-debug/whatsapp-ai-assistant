<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0607 -->
<!-- Tokens: ~20,223 -->

## ANALYSIS
Need to create new tables for calendar synchronization and update existing bookings table to support calendar features. Will create a migration file and update booking model.

## FILES TO CHANGE

### FILE: models/booking.py
```python
# Previous booking.py content remains unchanged
# Calendar sync features will be added via new models
```

### NEW FILE: models/calendar_sync.py
```python
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
```

## MIGRATION: 20240327_calendar_sync_tables.sql
```sql
-- Calendar sync preferences
CREATE TABLE calendar_sync_preferences (
    trainer_id UUID REFERENCES trainers(id) PRIMARY KEY,
    google_calendar_enabled BOOLEAN DEFAULT FALSE,
    apple_calendar_enabled BOOLEAN DEFAULT FALSE,
    email_calendar_enabled BOOLEAN DEFAULT FALSE,
    sync_frequency VARCHAR(20) DEFAULT 'realtime',
    calendar_view_default VARCHAR(20) DEFAULT 'month',
    show_client_names BOOLEAN DEFAULT TRUE,
    session_colors JSONB DEFAULT '{}',
    timezone_display VARCHAR(100) DEFAULT 'Africa/Johannesburg',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Calendar sync status
CREATE TABLE calendar_sync_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainer_id UUID REFERENCES trainers(id),
    provider VARCHAR(50) NOT NULL,
    last_sync TIMESTAMPTZ,
    sync_status VARCHAR(20),
    events_synced INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trainer_id, provider)
);

-- Calendar events mapping
CREATE TABLE calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID REFERENCES bookings(id),
    external_event_id VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(booking_id, provider)
);

-- Add calendar fields to bookings table
ALTER TABLE bookings 
ADD COLUMN google_event_id VARCHAR(255),
ADD COLUMN apple_event_id VARCHAR(255),
ADD COLUMN session_type VARCHAR(50) DEFAULT 'one_on_one',
ADD COLUMN color_hex VARCHAR(7);

-- Create indexes
CREATE INDEX idx_calendar_sync_status_trainer ON calendar_sync_status(trainer_id);
CREATE INDEX idx_calendar_events_booking ON calendar_events(booking_id);
CREATE INDEX idx_bookings_session_type ON bookings(session_type);
```

## SUMMARY
1. Created new calendar sync tables:
   - calendar_sync_preferences for trainer settings
   - calendar_sync_status to track sync operations
   - calendar_events to map bookings to external calendar events
2. Added calendar-related fields to bookings table
3. Created CalendarSyncModel class to handle calendar operations
4. Added appropriate indexes for performance
5. Maintained South African context with timezone defaults

The changes enable full calendar integration while keeping the existing booking functionality intact. The new model provides methods for managing calendar sync preferences, tracking sync status, and mapping external calendar events.