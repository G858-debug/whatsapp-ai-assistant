from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
import pytz
from utils.logger import log_error, log_info, log_warning
from collections import defaultdict
import json
from icalendar import Calendar, Event, vText

class CalendarService:
    """Service for managing calendar operations and views"""
    
    def __init__(self, supabase_client, config):
        """Initialize calendar service"""
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)

    def generate_ics_file(self, data: Dict) -> str:
        """
        Generate ICS calendar file content
        
        Args:
            data: Dictionary containing:
                - client: Client info
                - sessions: List of sessions
                - trainer: Trainer info
        
        Returns:
            String containing ICS file content
        """
        try:
            # Create calendar
            cal = Calendar()
            
            # Set properties
            cal.add('prodid', '-//Refiloe AI Assistant//EN')
            cal.add('version', '2.0')
            cal.add('calscale', 'GREGORIAN')
            cal.add('method', 'PUBLISH')
            
            # Add events for each session
            for session in data['sessions']:
                event = Event()
                
                # Combine date and time
                session_dt = self._combine_date_time(
                    session['session_date'],
                    session['session_time']
                )
                
                # Add an hour for end time
                end_dt = session_dt + timedelta(hours=1)
                
                # Set event properties
                event.add('summary', f"Training with {data['trainer']['name']}")
                event.add('dtstart', session_dt)
                event.add('dtend', end_dt)
                
                # Set location if available
                if session.get('location'):
                    event.add('location', vText(session['location']))
                
                # Add description
                desc = f"Training session with {data['trainer']['name']}"
                if session.get('notes'):
                    desc += f"\n\nNotes: {session['notes']}"
                event.add('description', desc)
                
                # Add organizer
                event.add('organizer', f"mailto:{data['trainer'].get('email', 'trainer@refiloe.ai')}")
                
                # Add status
                status_map = {
                    'confirmed': 'CONFIRMED',
                    'cancelled': 'CANCELLED',
                    'rescheduled': 'CONFIRMED'
                }
                event.add('status', status_map.get(session['status'], 'TENTATIVE'))
                
                # Add reminder
                event.add('valarm', {
                    'trigger': timedelta(minutes=-30),  # 30 min before
                    'action': 'DISPLAY',
                    'description': f"Upcoming training session with {data['trainer']['name']}"
                })
                
                cal.add_component(event)
            
            return cal.to_ical().decode('utf-8')
            
        except Exception as e:
            log_error(f"Error generating ICS file: {str(e)}")
            # Return minimal valid ICS
            return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Refiloe AI Assistant//EN
END:VCALENDAR"""

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
            # Return current time as fallback
            return self.sa_tz.localize(datetime.now())

    def get_trainer_availability(self, trainer_id: str, date: str) -> List[str]:
        """
        Get available time slots for a trainer on a specific date
        
        Args:
            trainer_id: Trainer's ID
            date: Date to check (YYYY-MM-DD)
            
        Returns:
            List of available time slots
        """
        try:
            # Get trainer's working hours for this day
            day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%A').lower()
            working_hours = self.config.get_booking_slots().get(day_name, [])
            
            if not working_hours:
                return []  # Not working this day
            
            # Get booked slots
            booked_result = self.db.table('bookings').select('session_time').eq(
                'trainer_id', trainer_id
            ).eq('session_date', date).in_(
                'status', ['confirmed', 'rescheduled']
            ).execute()
            
            booked_times = set()
            if booked_result.data:
                booked_times = {b['session_time'] for b in booked_result.data}
            
            # Return available slots
            return [slot for slot in working_hours if slot not in booked_times]
            
        except Exception as e:
            log_error(f"Error getting trainer availability: {str(e)}")
            return []

    def check_slot_availability(self, trainer_id: str, date: str, time: str) -> bool:
        """
        Check if a specific time slot is available
        
        Args:
            trainer_id: Trainer's ID
            date: Date to check (YYYY-MM-DD)
            time: Time to check (HH:MM)
            
        Returns:
            Boolean indicating if slot is available
        """
        try:
            # Check working hours
            day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%A').lower()
            working_hours = self.config.get_booking_slots().get(day_name, [])
            
            if time not in working_hours:
                return False  # Not a valid working hour
            
            # Check existing bookings
            result = self.db.table('bookings').select('id').eq(
                'trainer_id', trainer_id
            ).eq('session_date', date).eq(
                'session_time', time
            ).in_('status', ['confirmed', 'rescheduled']).execute()
            
            return not bool(result.data)  # Available if no booking exists
            
        except Exception as e:
            log_error(f"Error checking slot availability: {str(e)}")
            return False