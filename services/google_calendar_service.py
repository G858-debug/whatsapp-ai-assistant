from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pytz
import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from utils.logger import log_error, log_info, log_warning
from services.calendar_service import CalendarService

class GoogleCalendarService(CalendarService):
    """Service for Google Calendar integration and synchronization"""
    
    # Google Calendar color IDs mapping
    GOOGLE_COLOR_IDS = {
        'one_on_one': '2',      # Green
        'online': '7',          # Blue
        'group_class': '6',     # Orange
        'personal_time': '8',   # Grey
        'cancelled': '11',      # Red
        'assessment': '3',      # Purple
        'consultation': '9',    # Cyan
    }
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, supabase_client, config):
        """Initialize Google Calendar service"""
        super().__init__(supabase_client, config)
        self.credentials_cache = {}
        self.service_cache = {}
        
        log_info("GoogleCalendarService initialized")
    
    def authenticate_google_calendar(self, trainer_id: str) -> Optional[Any]:
        """
        Authenticate with Google Calendar using trainer's service account
        
        Args:
            trainer_id: Trainer's ID
            
        Returns:
            Google Calendar service object or None if failed
        """
        try:
            # Check cache first
            if trainer_id in self.service_cache:
                return self.service_cache[trainer_id]
            
            # Get trainer's Google credentials from database
            trainer_result = self.db.table('trainers').select(
                'google_service_account_json, google_calendar_id'
            ).eq('id', trainer_id).single().execute()
            
            if not trainer_result.data:
                log_warning(f"No trainer found with ID: {trainer_id}")
                return None
            
            trainer_data = trainer_result.data
            
            if not trainer_data.get('google_service_account_json'):
                log_warning(f"No Google credentials for trainer: {trainer_id}")
                return None
            
            # Parse credentials JSON
            try:
                creds_json = json.loads(trainer_data['google_service_account_json'])
            except json.JSONDecodeError as e:
                log_error(f"Invalid Google credentials JSON for trainer {trainer_id}: {str(e)}")
                return None
            
            # Create credentials object
            credentials = service_account.Credentials.from_service_account_info(
                creds_json,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            # Build service
            service = build('calendar', 'v3', credentials=credentials)
            
            # Cache the service
            self.service_cache[trainer_id] = service
            self.credentials_cache[trainer_id] = {
                'calendar_id': trainer_data.get('google_calendar_id', 'primary'),
                'credentials': credentials
            }
            
            log_info(f"Google Calendar authenticated for trainer {trainer_id}")
            return service
            
        except Exception as e:
            log_error(f"Error authenticating Google Calendar for trainer {trainer_id}: {str(e)}")
            return None
    
    def sync_booking_to_google(self, booking_id: str, action: str = 'create') -> Dict:
        """
        Sync a booking to Google Calendar
        
        Args:
            booking_id: Booking ID
            action: 'create', 'update', or 'delete'
            
        Returns:
            Result dictionary with success status
        """
        try:
            # Get booking details
            booking_result = self.db.table('bookings').select(
                '*, clients(name, whatsapp, email), trainers(id, name)'
            ).eq('id', booking_id).single().execute()
            
            if not booking_result.data:
                return {
                    'success': False,
                    'error': 'Booking not found'
                }
            
            booking = booking_result.data
            trainer_id = booking['trainer_id']
            
            # Authenticate
            service = self.authenticate_google_calendar(trainer_id)
            if not service:
                return {
                    'success': False,
                    'error': 'Failed to authenticate with Google Calendar'
                }
            
            calendar_id = self.credentials_cache[trainer_id]['calendar_id']
            
            # Perform action
            if action == 'create':
                result = self._create_google_event_internal(service, calendar_id, booking)
            elif action == 'update':
                result = self._update_google_event_internal(service, calendar_id, booking)
            elif action == 'delete':
                result = self._delete_google_event_internal(service, calendar_id, booking)
            else:
                return {
                    'success': False,
                    'error': f'Invalid action: {action}'
                }
            
            return result
            
        except Exception as e:
            log_error(f"Error syncing booking {booking_id} to Google: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_google_to_bookings(self, trainer_id: str) -> Dict:
        """
        Sync Google Calendar events to bookings database
        
        Args:
            trainer_id: Trainer's ID
            
        Returns:
            Sync results
        """
        try:
            # Authenticate
            service = self.authenticate_google_calendar(trainer_id)
            if not service:
                return {
                    'success': False,
                    'error': 'Failed to authenticate with Google Calendar'
                }
            
            calendar_id = self.credentials_cache[trainer_id]['calendar_id']
            
            # Get events from Google Calendar (next 30 days)
            now = datetime.now(self.sa_tz)
            time_min = now.isoformat()
            time_max = (now + timedelta(days=30)).isoformat()
            
            events_result = self._execute_with_retry(
                service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy='startTime'
                )
            )
            
            if not events_result:
                return {
                    'success': False,
                    'error': 'Failed to fetch Google Calendar events'
                }
            
            events = events_result.get('items', [])
            
            # Get existing bookings with Google event IDs
            existing_bookings = self.db.table('bookings').select('*').eq(
                'trainer_id', trainer_id
            ).not_.is_('google_event_id', 'null').execute()
            
            existing_google_ids = {
                booking['google_event_id']: booking 
                for booking in (existing_bookings.data or [])
            }
            
            sync_stats = {
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': 0
            }
            
            for event in events:
                google_event_id = event['id']
                
                # Check if event already exists in bookings
                if google_event_id in existing_google_ids:
                    # Update existing booking if changed
                    booking = existing_google_ids[google_event_id]
                    if self._has_event_changed(event, booking):
                        update_result = self._update_booking_from_google(booking['id'], event)
                        if update_result['success']:
                            sync_stats['updated'] += 1
                        else:
                            sync_stats['errors'] += 1
                    else:
                        sync_stats['skipped'] += 1
                else:
                    # Create new booking from Google event
                    create_result = self._create_booking_from_google(trainer_id, event)
                    if create_result['success']:
                        sync_stats['created'] += 1
                    else:
                        sync_stats['errors'] += 1
            
            log_info(f"Google sync completed for trainer {trainer_id}: {sync_stats}")
            
            return {
                'success': True,
                'stats': sync_stats,
                'total_events': len(events)
            }
            
        except Exception as e:
            log_error(f"Error syncing Google Calendar for trainer {trainer_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_google_event(self, booking_data: Dict) -> Dict:
        """
        Create a Google Calendar event from booking data
        
        Args:
            booking_data: Booking information
            
        Returns:
            Created event details
        """
        try:
            trainer_id = booking_data.get('trainer_id')
            if not trainer_id:
                return {
                    'success': False,
                    'error': 'trainer_id is required'
                }
            
            # Authenticate
            service = self.authenticate_google_calendar(trainer_id)
            if not service:
                return {
                    'success': False,
                    'error': 'Failed to authenticate with Google Calendar'
                }
            
            calendar_id = self.credentials_cache[trainer_id]['calendar_id']
            
            # Format event
            event = self._format_google_event(booking_data)
            
            # Create event with retry
            result = self._execute_with_retry(
                service.events().insert(calendarId=calendar_id, body=event)
            )
            
            if result:
                log_info(f"Created Google event: {result.get('id')}")
                return {
                    'success': True,
                    'event_id': result.get('id'),
                    'event': result
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create Google event'
                }
                
        except Exception as e:
            log_error(f"Error creating Google event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_google_event(self, event_id: str, booking_data: Dict) -> Dict:
        """
        Update a Google Calendar event
        
        Args:
            event_id: Google event ID
            booking_data: Updated booking information
            
        Returns:
            Update result
        """
        try:
            trainer_id = booking_data.get('trainer_id')
            if not trainer_id:
                return {
                    'success': False,
                    'error': 'trainer_id is required'
                }
            
            # Authenticate
            service = self.authenticate_google_calendar(trainer_id)
            if not service:
                return {
                    'success': False,
                    'error': 'Failed to authenticate with Google Calendar'
                }
            
            calendar_id = self.credentials_cache[trainer_id]['calendar_id']
            
            # Format event
            event = self._format_google_event(booking_data)
            
            # Update event with retry
            result = self._execute_with_retry(
                service.events().update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=event
                )
            )
            
            if result:
                log_info(f"Updated Google event: {event_id}")
                return {
                    'success': True,
                    'event': result
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update Google event'
                }
                
        except Exception as e:
            log_error(f"Error updating Google event {event_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_google_event(self, event_id: str) -> Dict:
        """
        Delete a Google Calendar event
        
        Args:
            event_id: Google event ID
            
        Returns:
            Deletion result
        """
        try:
            # Get booking to find trainer
            booking_result = self.db.table('bookings').select(
                'trainer_id'
            ).eq('google_event_id', event_id).single().execute()
            
            if not booking_result.data:
                return {
                    'success': False,
                    'error': 'Booking not found for event'
                }
            
            trainer_id = booking_result.data['trainer_id']
            
            # Authenticate
            service = self.authenticate_google_calendar(trainer_id)
            if not service:
                return {
                    'success': False,
                    'error': 'Failed to authenticate with Google Calendar'
                }
            
            calendar_id = self.credentials_cache[trainer_id]['calendar_id']
            
            # Delete event with retry
            self._execute_with_retry(
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=event_id
                )
            )
            
            log_info(f"Deleted Google event: {event_id}")
            
            # Clear google_event_id from booking
            self.db.table('bookings').update({
                'google_event_id': None,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('google_event_id', event_id).execute()
            
            return {'success': True}
            
        except Exception as e:
            log_error(f"Error deleting Google event {event_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_google_events(self, trainer_id: str, start_date: str, end_date: str) -> List[Dict]:
        """
        Get Google Calendar events for a date range
        
        Args:
            trainer_id: Trainer's ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of events
        """
        try:
            # Authenticate
            service = self.authenticate_google_calendar(trainer_id)
            if not service:
                return []
            
            calendar_id = self.credentials_cache[trainer_id]['calendar_id']
            
            # Parse dates
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            
            # Localize to timezone
            start_dt = self.sa_tz.localize(start_dt)
            end_dt = self.sa_tz.localize(end_dt)
            
            # Get events
            events_result = self._execute_with_retry(
                service.events().list(
                    calendarId=calendar_id,
                    timeMin=start_dt.isoformat(),
                    timeMax=end_dt.isoformat(),
                    singleEvents=True,
                    orderBy='startTime'
                )
            )
            
            if events_result:
                return events_result.get('items', [])
            
            return []
            
        except Exception as e:
            log_error(f"Error getting Google events: {str(e)}")
            return []
    
    def setup_google_calendar_webhook(self, trainer_id: str, webhook_url: str) -> Dict:
        """
        Set up push notifications for Google Calendar changes
        
        Args:
            trainer_id: Trainer's ID
            webhook_url: URL to receive notifications
            
        Returns:
            Setup result
        """
        try:
            # Authenticate
            service = self.authenticate_google_calendar(trainer_id)
            if not service:
                return {
                    'success': False,
                    'error': 'Failed to authenticate with Google Calendar'
                }
            
            calendar_id = self.credentials_cache[trainer_id]['calendar_id']
            
            # Create watch request
            import uuid
            channel_id = str(uuid.uuid4())
            
            body = {
                'id': channel_id,
                'type': 'web_hook',
                'address': webhook_url,
                'params': {
                    'ttl': '604800'  # 7 days in seconds
                }
            }
            
            # Set up watch
            watch_result = self._execute_with_retry(
                service.events().watch(
                    calendarId=calendar_id,
                    body=body
                )
            )
            
            if watch_result:
                # Store webhook info
                self.db.table('calendar_sync_log').insert({
                    'trainer_id': trainer_id,
                    'sync_type': 'webhook_setup',
                    'sync_status': 'success',
                    'details': json.dumps({
                        'channel_id': channel_id,
                        'resource_id': watch_result.get('resourceId'),
                        'expiration': watch_result.get('expiration')
                    }),
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
                log_info(f"Google Calendar webhook set up for trainer {trainer_id}")
                
                return {
                    'success': True,
                    'channel_id': channel_id,
                    'resource_id': watch_result.get('resourceId'),
                    'expiration': watch_result.get('expiration')
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to set up webhook'
                }
                
        except Exception as e:
            log_error(f"Error setting up Google Calendar webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Private helper methods
    
    def _format_google_event(self, booking_data: Dict) -> Dict:
        """Format booking data as Google Calendar event"""
        try:
            # Get client name
            client_name = 'Client'
            if booking_data.get('client_name'):
                client_name = booking_data['client_name']
            elif booking_data.get('clients'):
                client_name = booking_data['clients'].get('name', 'Client')
            
            # Get session type
            session_type = booking_data.get('session_type', 'one_on_one')
            
            # Create title
            title = f"{client_name} - {session_type.replace('_', ' ').title()}"
            
            # Parse date and time
            session_date = booking_data.get('session_date')
            session_time = booking_data.get('session_time')
            
            start_dt = self._combine_date_time(session_date, session_time)
            end_dt = start_dt + timedelta(hours=1)  # Default 1 hour duration
            
            # Create description
            description_parts = [
                f"Session Type: {session_type.replace('_', ' ').title()}",
                f"Client: {client_name}"
            ]
            
            if booking_data.get('clients'):
                client = booking_data['clients']
                if client.get('whatsapp'):
                    description_parts.append(f"WhatsApp: {client['whatsapp']}")
                if client.get('email'):
                    description_parts.append(f"Email: {client['email']}")
            
            if booking_data.get('notes'):
                description_parts.append(f"\nNotes: {booking_data['notes']}")
            
            description = '\n'.join(description_parts)
            
            # Get color ID
            color_id = self.GOOGLE_COLOR_IDS.get(session_type, '1')
            
            # Build event
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Africa/Johannesburg',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Africa/Johannesburg',
                },
                'colorId': color_id,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 24 * 60},  # 24 hours
                        {'method': 'popup', 'minutes': 60},       # 1 hour
                    ],
                },
            }
            
            # Add location if available
            if booking_data.get('location'):
                event['location'] = booking_data['location']
            
            return event
            
        except Exception as e:
            log_error(f"Error formatting Google event: {str(e)}")
            raise
    
    def _create_google_event_internal(self, service: Any, calendar_id: str, 
                                     booking: Dict) -> Dict:
        """Internal method to create Google event"""
        try:
            # Format event
            event = self._format_google_event(booking)
            
            # Create event
            result = self._execute_with_retry(
                service.events().insert(calendarId=calendar_id, body=event)
            )
            
            if result:
                # Update booking with Google event ID
                self.db.table('bookings').update({
                    'google_event_id': result['id'],
                    'google_sync_status': 'synced',
                    'google_sync_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('id', booking['id']).execute()
                
                log_info(f"Created Google event for booking {booking['id']}")
                
                return {
                    'success': True,
                    'google_event_id': result['id']
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create Google event'
                }
                
        except Exception as e:
            log_error(f"Error creating Google event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _update_google_event_internal(self, service: Any, calendar_id: str, 
                                     booking: Dict) -> Dict:
        """Internal method to update Google event"""
        try:
            google_event_id = booking.get('google_event_id')
            if not google_event_id:
                # Create new event if no Google ID exists
                return self._create_google_event_internal(service, calendar_id, booking)
            
            # Format event
            event = self._format_google_event(booking)
            
            # Update event
            result = self._execute_with_retry(
                service.events().update(
                    calendarId=calendar_id,
                    eventId=google_event_id,
                    body=event
                )
            )
            
            if result:
                # Update sync status
                self.db.table('bookings').update({
                    'google_sync_status': 'synced',
                    'google_sync_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('id', booking['id']).execute()
                
                log_info(f"Updated Google event for booking {booking['id']}")
                
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': 'Failed to update Google event'
                }
                
        except Exception as e:
            log_error(f"Error updating Google event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _delete_google_event_internal(self, service: Any, calendar_id: str, 
                                     booking: Dict) -> Dict:
        """Internal method to delete Google event"""
        try:
            google_event_id = booking.get('google_event_id')
            if not google_event_id:
                return {
                    'success': True,
                    'message': 'No Google event to delete'
                }
            
            # Delete event
            self._execute_with_retry(
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=google_event_id
                )
            )
            
            # Clear Google event ID from booking
            self.db.table('bookings').update({
                'google_event_id': None,
                'google_sync_status': 'deleted',
                'google_sync_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', booking['id']).execute()
            
            log_info(f"Deleted Google event for booking {booking['id']}")
            
            return {'success': True}
            
        except Exception as e:
            log_error(f"Error deleting Google event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _has_event_changed(self, google_event: Dict, booking: Dict) -> bool:
        """Check if Google event differs from booking"""
        try:
            # Parse Google event time
            google_start = google_event['start'].get('dateTime', google_event['start'].get('date'))
            google_dt = datetime.fromisoformat(google_start.replace('Z', '+00:00'))
            
            # Parse booking time
            booking_dt = self._combine_date_time(
                booking['session_date'],
                booking['session_time']
            )
            
            # Check if times differ by more than 1 minute
            time_diff = abs((google_dt - booking_dt).total_seconds())
            if time_diff > 60:
                return True
            
            # Check if status changed (cancelled events)
            if google_event.get('status') == 'cancelled' and booking['status'] != 'cancelled':
                return True
            
            return False
            
        except Exception as e:
            log_error(f"Error comparing event changes: {str(e)}")
            return False
    
    def _update_booking_from_google(self, booking_id: str, google_event: Dict) -> Dict:
        """Update booking from Google event data"""
        try:
            # Parse Google event time
            google_start = google_event['start'].get('dateTime', google_event['start'].get('date'))
            google_dt = datetime.fromisoformat(google_start.replace('Z', '+00:00'))
            
            # Convert to local timezone
            local_dt = google_dt.astimezone(self.sa_tz)
            
            # Update booking
            update_data = {
                'session_date': local_dt.date().isoformat(),
                'session_time': local_dt.strftime('%H:%M'),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Check if cancelled
            if google_event.get('status') == 'cancelled':
                update_data['status'] = 'cancelled'
            
            result = self.db.table('bookings').update(
                update_data
            ).eq('id', booking_id).execute()
            
            if result.data:
                log_info(f"Updated booking {booking_id} from Google event")
                return {'success': True}
            else:
                return {'success': False}
                
        except Exception as e:
            log_error(f"Error updating booking from Google: {str(e)}")
            return {'success': False}
    
    def _create_booking_from_google(self, trainer_id: str, google_event: Dict) -> Dict:
        """Create booking from Google event"""
        try:
            # Parse Google event time
            google_start = google_event['start'].get('dateTime', google_event['start'].get('date'))
            google_dt = datetime.fromisoformat(google_start.replace('Z', '+00:00'))
            
            # Convert to local timezone
            local_dt = google_dt.astimezone(self.sa_tz)
            
            # Try to match client by name in summary
            summary = google_event.get('summary', '')
            client_id = None
            
            if ' - ' in summary:
                client_name = summary.split(' - ')[0].strip()
                
                # Try to find client
                client_result = self.db.table('clients').select('id').eq(
                    'trainer_id', trainer_id
                ).ilike('name', f'%{client_name}%').limit(1).execute()
                
                if client_result.data:
                    client_id = client_result.data[0]['id']
            
            # Determine session type from color or summary
            session_type = 'one_on_one'  # default
            color_id = google_event.get('colorId')
            if color_id:
                # Reverse lookup color to session type
                for s_type, g_color in self.GOOGLE_COLOR_IDS.items():
                    if g_color == color_id:
                        session_type = s_type
                        break
            
            # Create booking
            booking_data = {
                'trainer_id': trainer_id,
                'client_id': client_id,
                'session_date': local_dt.date().isoformat(),
                'session_time': local_dt.strftime('%H:%M'),
                'session_type': session_type,
                'status': 'confirmed' if google_event.get('status') != 'cancelled' else 'cancelled',
                'google_event_id': google_event['id'],
                'google_sync_status': 'synced',
                'google_sync_at': datetime.now(self.sa_tz).isoformat(),
                'notes': google_event.get('description', ''),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('bookings').insert(booking_data).execute()
            
            if result.data:
                log_info(f"Created booking from Google event {google_event['id']}")
                return {'success': True, 'booking_id': result.data[0]['id']}
            else:
                return {'success': False}
                
        except Exception as e:
            log_error(f
</details>
