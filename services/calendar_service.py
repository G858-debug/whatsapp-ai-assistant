from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
import pytz
from utils.logger import log_error, log_info, log_warning
from collections import defaultdict
import json

class CalendarService:
    """Service for managing calendar operations and views"""
    
    # Session type color definitions
    SESSION_COLORS = {
        'one_on_one': '#4CAF50',      # Green
        'online': '#2196F3',           # Blue
        'group_class': '#FF9800',      # Orange
        'personal_time': '#9E9E9E',    # Grey
        'cancelled': '#F44336',        # Red
        'assessment': '#9C27B0',       # Purple (additional)
        'consultation': '#00BCD4',    # Cyan (additional)
    }
    
    # Default calendar preferences
    DEFAULT_PREFERENCES = {
        'default_view': 'week',
        'show_client_names': True,
        'show_session_types': True,
        'start_hour': 6,
        'end_hour': 21,
        'time_slot_duration': 60,  # minutes
        'first_day_of_week': 1,    # Monday
        'show_cancelled': False,
        'enable_notifications': True,
        'notification_minutes': 60,  # Remind 60 minutes before
    }
    
    def __init__(self, supabase_client, config):
        """Initialize calendar service"""
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        log_info("CalendarService initialized")
    
    def get_trainer_calendar(self, trainer_id: str, start_date: str, 
                            end_date: str, view_type: str = 'week') -> Dict:
        """
        Get trainer's calendar data for specified date range
        
        Args:
            trainer_id: Trainer's ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            view_type: 'day', 'week', 'month', or 'list'
        
        Returns:
            Dictionary with calendar events and metadata
        """
        try:
            # Validate dates
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Get bookings
            bookings_query = self.db.table('bookings').select(
                '*, clients(id, name, whatsapp)'
            ).eq('trainer_id', trainer_id).gte(
                'session_date', start_date
            ).lte('session_date', end_date)
            
            # Get trainer preferences
            preferences = self._get_trainer_preferences(trainer_id)
            
            # Apply preference filters
            if not preferences.get('show_cancelled', False):
                bookings_query = bookings_query.neq('status', 'cancelled')
            
            bookings_result = bookings_query.execute()
            bookings = bookings_result.data if bookings_result.data else []
            
            # Get trainer's availability/working hours
            availability = self._get_trainer_availability(trainer_id, start_date, end_date)
            
            # Format for display
            calendar_data = self.format_calendar_data_for_display(
                bookings, view_type, preferences
            )
            
            # Add metadata
            calendar_data['metadata'] = {
                'trainer_id': trainer_id,
                'start_date': start_date,
                'end_date': end_date,
                'view_type': view_type,
                'total_events': len(bookings),
                'preferences': preferences,
                'availability': availability
            }
            
            # Calculate statistics
            stats = self._calculate_calendar_stats(bookings)
            calendar_data['statistics'] = stats
            
            log_info(f"Retrieved calendar for trainer {trainer_id}: {len(bookings)} events")
            return calendar_data
            
        except Exception as e:
            log_error(f"Error getting trainer calendar: {str(e)}")
            return {
                'events': [],
                'error': str(e),
                'metadata': {
                    'trainer_id': trainer_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'view_type': view_type
                }
            }
    
    def get_client_calendar(self, client_id: str, start_date: str, 
                          end_date: str) -> Dict:
        """
        Get client's calendar data for specified date range
        
        Args:
            client_id: Client's ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Dictionary with calendar events
        """
        try:
            # Get client's bookings
            bookings_result = self.db.table('bookings').select(
                '*, trainers(id, name, business_name)'
            ).eq('client_id', client_id).gte(
                'session_date', start_date
            ).lte('session_date', end_date).in_(
                'status', ['confirmed', 'rescheduled']
            ).execute()
            
            bookings = bookings_result.data if bookings_result.data else []
            
            # Format for client view (simplified)
            events = []
            for booking in bookings:
                trainer_name = booking['trainers']['business_name'] or booking['trainers']['name']
                
                # Parse datetime
                session_datetime = self._combine_date_time(
                    booking['session_date'], 
                    booking['session_time']
                )
                
                events.append({
                    'id': booking['id'],
                    'title': f"Session with {trainer_name}",
                    'start': session_datetime.isoformat(),
                    'end': (session_datetime + timedelta(hours=1)).isoformat(),
                    'type': booking.get('session_type', 'one_on_one'),
                    'color': self.get_session_color(booking.get('session_type', 'one_on_one')),
                    'status': booking['status'],
                    'location': booking.get('location', 'TBD'),
                    'notes': booking.get('notes', '')
                })
            
            return {
                'events': events,
                'metadata': {
                    'client_id': client_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'total_events': len(events)
                }
            }
            
        except Exception as e:
            log_error(f"Error getting client calendar: {str(e)}")
            return {
                'events': [],
                'error': str(e),
                'metadata': {
                    'client_id': client_id,
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
    
    def format_calendar_data_for_display(self, bookings: List[Dict], 
                                        view_type: str,
                                        preferences: Dict = None) -> Dict:
        """
        Format calendar data based on view type
        
        Args:
            bookings: List of booking records
            view_type: 'day', 'week', 'month', or 'list'
            preferences: Display preferences
        
        Returns:
            Formatted calendar data
        """
        try:
            if not preferences:
                preferences = self.DEFAULT_PREFERENCES.copy()
            
            formatted_data = {
                'events': [],
                'view_type': view_type
            }
            
            # Process each booking
            for booking in bookings:
                event = self._booking_to_calendar_event(booking, preferences)
                if event:
                    formatted_data['events'].append(event)
            
            # Sort events by datetime
            formatted_data['events'].sort(key=lambda x: x['start'])
            
            # Apply view-specific formatting
            if view_type == 'day':
                formatted_data = self._format_day_view(formatted_data, preferences)
            elif view_type == 'week':
                formatted_data = self._format_week_view(formatted_data, preferences)
            elif view_type == 'month':
                formatted_data = self._format_month_view(formatted_data, preferences)
            elif view_type == 'list':
                formatted_data = self._format_list_view(formatted_data, preferences)
            
            return formatted_data
            
        except Exception as e:
            log_error(f"Error formatting calendar data: {str(e)}")
            return {
                'events': [],
                'view_type': view_type,
                'error': str(e)
            }
    
    def get_session_color(self, session_type: str) -> str:
        """
        Get color code for session type
        
        Args:
            session_type: Type of session
        
        Returns:
            Hex color code
        """
        return self.SESSION_COLORS.get(session_type, '#757575')  # Default grey
    
    def update_calendar_preferences(self, trainer_id: str, preferences: Dict) -> Dict:
        """
        Update trainer's calendar preferences
        
        Args:
            trainer_id: Trainer's ID
            preferences: Dictionary of preferences to update
        
        Returns:
            Updated preferences
        """
        try:
            # Get existing preferences
            existing = self._get_trainer_preferences(trainer_id)
            
            # Merge with new preferences
            updated_prefs = {**existing, **preferences}
            
            # Validate preferences
            validated_prefs = self._validate_preferences(updated_prefs)
            
            # Check if record exists
            result = self.db.table('calendar_sync_preferences').select('trainer_id').eq(
                'trainer_id', trainer_id
            ).execute()
            
            if result.data:
                # Update existing
                self.db.table('calendar_sync_preferences').update({
                    'session_colors': json.dumps(validated_prefs.get('session_colors', {})),
                    'calendar_view_default': validated_prefs.get('default_view', 'week'),
                    'show_client_names': validated_prefs.get('show_client_names', True),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('trainer_id', trainer_id).execute()
            else:
                # Create new
                self.db.table('calendar_sync_preferences').insert({
                    'trainer_id': trainer_id,
                    'session_colors': json.dumps(validated_prefs.get('session_colors', {})),
                    'calendar_view_default': validated_prefs.get('default_view', 'week'),
                    'show_client_names': validated_prefs.get('show_client_names', True),
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
            
            log_info(f"Updated calendar preferences for trainer {trainer_id}")
            
            return {
                'success': True,
                'preferences': validated_prefs
            }
            
        except Exception as e:
            log_error(f"Error updating calendar preferences: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_calendar_event(self, trainer_id: str, event_data: Dict) -> Dict:
        """
        Create a calendar event (personal time, etc.)
        
        Args:
            trainer_id: Trainer's ID
            event_data: Event details
        
        Returns:
            Created event
        """
        try:
            # Validate required fields
            required = ['date', 'time', 'duration', 'type']
            for field in required:
                if field not in event_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Create booking record for personal time
            booking_data = {
                'trainer_id': trainer_id,
                'client_id': None,  # No client for personal time
                'session_date': event_data['date'],
                'session_time': event_data['time'],
                'session_type': event_data['type'],
                'status': 'confirmed',
                'notes': event_data.get('notes', ''),
                'color_hex': self.get_session_color(event_data['type']),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('bookings').insert(booking_data).execute()
            
            if result.data:
                log_info(f"Created calendar event for trainer {trainer_id}")
                return {
                    'success': True,
                    'event_id': result.data[0]['id'],
                    'event': result.data[0]
                }
            
            return {
                'success': False,
                'error': 'Failed to create event'
            }
            
        except Exception as e:
            log_error(f"Error creating calendar event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_calendar_conflicts(self, trainer_id: str, date: str, 
                             time: str, duration: int = 60) -> List[Dict]:
        """
        Check for scheduling conflicts
        
        Args:
            trainer_id: Trainer's ID
            date: Date to check (YYYY-MM-DD)
            time: Time to check (HH:MM)
            duration: Session duration in minutes
        
        Returns:
            List of conflicting events
        """
        try:
            # Parse start and end times
            start_dt = self._combine_date_time(date, time)
            end_dt = start_dt + timedelta(minutes=duration)
            
            # Get all bookings for that day
            bookings = self.db.table('bookings').select('*').eq(
                'trainer_id', trainer_id
            ).eq('session_date', date).in_(
                'status', ['confirmed', 'rescheduled']
            ).execute()
            
            conflicts = []
            
            for booking in (bookings.data or []):
                booking_start = self._combine_date_time(
                    booking['session_date'], 
                    booking['session_time']
                )
                booking_end = booking_start + timedelta(minutes=60)  # Assume 1 hour sessions
                
                # Check for overlap
                if (start_dt < booking_end and end_dt > booking_start):
                    conflicts.append({
                        'id': booking['id'],
                        'start': booking_start.isoformat(),
                        'end': booking_end.isoformat(),
                        'type': booking.get('session_type', 'one_on_one')
                    })
            
            return conflicts
            
        except Exception as e:
            log_error(f"Error checking calendar conflicts: {str(e)}")
            return []
    
    # Private helper methods
    
    def _get_trainer_preferences(self, trainer_id: str) -> Dict:
        """Get trainer's calendar preferences"""
        try:
            result = self.db.table('calendar_sync_preferences').select('*').eq(
                'trainer_id', trainer_id
            ).execute()
            
            if result.data:
                prefs = result.data[0]
                # Parse JSON fields
                if prefs.get('session_colors'):
                    prefs['session_colors'] = json.loads(prefs['session_colors'])
                
                # Map database fields to preference keys
                return {
                    'default_view': prefs.get('calendar_view_default', 'week'),
                    'show_client_names': prefs.get('show_client_names', True),
                    'session_colors': prefs.get('session_colors', {}),
                    'show_cancelled': False,
                    'timezone': prefs.get('timezone_display', 'Africa/Johannesburg')
                }
            
            return self.DEFAULT_PREFERENCES.copy()
            
        except Exception as e:
            log_error(f"Error getting trainer preferences: {str(e)}")
            return self.DEFAULT_PREFERENCES.copy()
    
    def _get_trainer_availability(self, trainer_id: str, start_date: str, 
                                 end_date: str) -> Dict:
        """Get trainer's availability/working hours"""
        try:
            # This could be expanded to pull from a trainer_availability table
            # For now, use config defaults
            return self.config.get_booking_slots()
            
        except Exception as e:
            log_error(f"Error getting trainer availability: {str(e)}")
            return {}
    
    def _combine_date_time(self, date_str: str, time_str: str) -> datetime:
        """Combine date and time strings into datetime object"""
        try:
            # Handle various time formats
            if ':' in time_str:
                dt_str = f"{date_str} {time_str}"
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
            else:
                # Assume it's just an hour
                dt_str = f"{date_str} {time_str}:00"
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
            
            # Localize to SA timezone
            return self.sa_tz.localize(dt)
            
        except Exception as e:
            log_error(f"Error combining date/time: {str(e)}")
            # Return a default datetime
            return self.sa_tz.localize(datetime.strptime(date_str, '%Y-%m-%d'))
    
    def _booking_to_calendar_event(self, booking: Dict, preferences: Dict) -> Optional[Dict]:
        """Convert booking record to calendar event format"""
        try:
            # Get client name
            client_name = 'Personal Time'
            if booking.get('clients'):
                if preferences.get('show_client_names', True):
                    client_name = booking['clients']['name']
                else:
                    # Abbreviate name (e.g., "John D.")
                    client_name = self._abbreviate_name(booking['clients']['name'])
            
            # Combine date and time
            start_dt = self._combine_date_time(
                booking['session_date'], 
                booking['session_time']
            )
            
            # Assume 1 hour duration (could be made configurable)
            end_dt = start_dt + timedelta(hours=1)
            
            # Get color
            session_type = booking.get('session_type', 'one_on_one')
            color = preferences.get('session_colors', {}).get(
                session_type, 
                self.get_session_color(session_type)
            )
            
            return {
                'id': booking['id'],
                'title': client_name,
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat(),
                'type': session_type,
                'color': color,
                'status': booking['status'],
                'client_id': booking.get('client_id'),
                'notes': booking.get('notes', ''),
                'editable': booking['status'] not in ['completed', 'cancelled']
            }
            
        except Exception as e:
            log_error(f"Error converting booking to event: {str(e)}")
            return None
    
    def _abbreviate_name(self, full_name: str) -> str:
        """Abbreviate client name for privacy"""
        try:
            parts = full_name.split()
            if len(parts) > 1:
                return f"{parts[0]} {parts[-1][0]}."
            return parts[0]
        except:
            return "Client"
    
    def _calculate_calendar_stats(self, bookings: List[Dict]) -> Dict:
        """Calculate statistics from bookings"""
        try:
            stats = {
                'total': len(bookings),
                'by_status': defaultdict(int),
                'by_type': defaultdict(int),
                'by_day': defaultdict(int)
            }
            
            for booking in bookings:
                stats['by_status'][booking['status']] += 1
                stats['by_type'][booking.get('session_type', 'one_on_one')] += 1
                
                # Get day of week
                date_obj = datetime.strptime(booking['session_date'], '%Y-%m-%d')
                day_name = date_obj.strftime('%A')
                stats['by_day'][day_name] += 1
            
            # Convert defaultdicts to regular dicts
            stats['by_status'] = dict(stats['by_status'])
            stats['by_type'] = dict(stats['by_type'])
            stats['by_day'] = dict(stats['by_day'])
            
            return stats
            
        except Exception as e:
            log_error(f"Error calculating stats: {str(e)}")
            return {}
    
    def _format_day_view(self, data: Dict, preferences: Dict) -> Dict:
        """Format calendar data for day view"""
        try:
            # Group events by hour
            hourly_events = defaultdict(list)
            
            for event in data['events']:
                start_dt = datetime.fromisoformat(event['start'])
                hour = start_dt.hour
                hourly_events[hour].append(event)
            
            # Create time slots
            start_hour = preferences.get('start_hour', 6)
            end_hour = preferences.get('end_hour', 21)
            
            time_slots = []
            for hour in range(start_hour, end_hour + 1):
                time_slots.append({
                    'hour': hour,
                    'time': f"{hour:02d}:00",
                    'events': hourly_events.get(hour, [])
                })
            
            data['time_slots'] = time_slots
            return data
            
        except Exception as e:
            log_error(f"Error formatting day view: {str(e)}")
            return data
    
    def _format_week_view(self, data: Dict, preferences: Dict) -> Dict:
        """Format calendar data for week view"""
        try:
            # Group events by day
            daily_events = defaultdict(list)
            
            for event in data['events']:
                start_dt = datetime.fromisoformat(event['start'])
                day_key = start_dt.date().isoformat()
                daily_events[day_key].append(event)
            
            # Create week structure
            week_data = []
            
            # Get all unique dates
            dates = set()
            for event in data['events']:
                start_dt = datetime.fromisoformat(event['start'])
                dates.add(start_dt.date())
            
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                
                current_date = min_date
                while current_date <= max_date:
                    week_data.append({
                        'date': current_date.isoformat(),
                        'day_name': current_date.strftime('%A'),
                        'day_number': current_date.day,
                        'events': daily_events.get(current_date.isoformat(), [])
                    })
                    current_date += timedelta(days=1)
            
            data['days'] = week_data
            return data
            
        except Exception as e:
            log_error(f"Error formatting week view: {str(e)}")
            return data
    
    def _format_month_view(self, data: Dict, preferences: Dict) -> Dict:
        """Format calendar data for month view"""
        try:
            # Group events by date
            daily_events = defaultdict(list)
            
            for event in data['events']:
                start_dt = datetime.fromisoformat(event['start'])
                day_key = start_dt.date().isoformat()
                daily_events[day_key].append(event)
            
            # Create month grid
            if data['events']:
                first_event_date = datetime.fromisoformat(data['events'][0]['start']).date()
                
                # Get first day of month
                first_day = first_event_date.replace(day=1)
                
                # Get last day of month
                if first_day.month == 12:
                    last_day = first_day.replace(year=first_day.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    last_day = first_day.replace(month=first_day.month + 1, day=1) - timedelta(days=1)
                
                # Create calendar grid
                calendar_grid = []
                current_date = first_day
                
                while current_date <= last_day:
                    calendar_grid.append({
                        'date': current_date.isoformat(),
                        'day': current_date.day,
                        'weekday': current_date.weekday(),
                        'events': daily_events.get(current_date.isoformat(), []),
                        'event_count': len(daily_events.get(current_date.isoformat(), []))
                    })
                    current_date += timedelta(days=1)
                
                data['calendar_grid'] = calendar_grid
                data['month'] = first_day.strftime('%B %Y')
            
            return data
            
        except Exception as e:
            log_error(f"Error formatting month view: {str(e)}")
            return data
    
    def _format_list_view(self, data: Dict, preferences: Dict) -> Dict:
        """Format calendar data for list view"""
        try:
            # Group events by date
            grouped_events = defaultdict(list)
            
            for event in data['events']:
                start_dt = datetime.fromisoformat(event['start'])
                date_key = start_dt.date().isoformat()
                grouped_events[date_key].append(event)
            
            # Create sorted list
            list_data = []
            for date_key in sorted(grouped_events.keys()):
                date_obj = datetime.strptime(date_key, '%Y-%m-%d').date()
                list_data.append({
                    'date': date_key,
                    'date_display': date_obj.strftime('%A, %d %B %Y'),
                    'events': sorted(grouped_events[date_key], 
                                   key=lambda x: x['start'])
                })
            
            data['grouped_events'] = list_data
            return data
            
        except Exception as e:
            log_error(f"Error formatting list view: {str(e)}")
            return data
    
    def _validate_preferences(self, preferences: Dict) -> Dict:
        """Validate and sanitize preferences"""
        validated = {}
        
        # Validate view type
        valid_views = ['day', 'week', 'month', 'list']
        if preferences.get('default_view') in valid_views:
            validated['default_view'] = preferences['default_view']
        else:
            validated['default_view'] = 'week'
        
        # Validate boolean preferences
        validated['show_client_names'] = bool(preferences.get('show_client_names', True))
        validated['show_cancelled'] = bool(preferences.get('show_cancelled', False))
        
        # Validate hour ranges
        start_hour = preferences.get('start_hour', 6)
        if 0 <= start_hour <= 23:
            validated['start_hour'] = start_hour
        else:
            validated['start_hour'] = 6
        
        end_hour = preferences.get('end_hour', 21)
        if 0 <= end_hour <= 23 and end_hour > validated['start_hour']:
            validated['end_hour'] = end_hour
        else:
            validated['end_hour'] = 21
        
        # Validate custom colors
        if preferences.get('session_colors'):
            validated['session_colors'] = {}
            for session_type, color in preferences['session_colors'].items():
                if self._is_valid_hex_color(color):
                    validated['session_colors'][session_type] = color
        
        return validated
    
    def _is_valid_hex_color(self, color: str) -> bool:
        """Check if string is valid hex color"""
        import re
        return bool(re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color))