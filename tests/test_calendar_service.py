"""
Comprehensive tests for calendar service functionality
Tests CRUD operations, sync, conflict resolution, timezone handling, and exports
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
import json
from io import BytesIO

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.calendar_service import CalendarService
from services.calendar_export_service import CalendarExportService
from config import Config


class TestCalendarService(unittest.TestCase):
    """Test suite for CalendarService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.mock_config = Mock(spec=Config)
        self.mock_config.TIMEZONE = 'Africa/Johannesburg'
        self.mock_config.get_booking_slots.return_value = {
            'monday': ['09:00', '10:00', '11:00'],
            'tuesday': ['09:00', '10:00', '11:00'],
        }
        
        self.calendar_service = CalendarService(self.mock_db, self.mock_config)
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def test_get_trainer_calendar_success(self):
        """Test successful calendar retrieval"""
        # Mock database responses
        self.mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.neq.return_value.execute.return_value.data = [
            {
                'id': 'booking1',
                'session_date': '2024-01-15',
                'session_time': '10:00',
                'status': 'confirmed',
                'session_type': 'one_on_one',
                'clients': {'id': 'client1', 'name': 'John Doe', 'whatsapp': '+27821234567'}
            }
        ]
        
        # Mock preferences
        self.mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        result = self.calendar_service.get_trainer_calendar(
            'trainer1', '2024-01-15', '2024-01-20', 'week'
        )
        
        self.assertIn('events', result)
        self.assertIn('metadata', result)
        self.assertEqual(result['metadata']['trainer_id'], 'trainer1')
        self.assertEqual(len(result['events']), 1)
    
    def test_get_trainer_calendar_with_error(self):
        """Test calendar retrieval with database error"""
        self.mock_db.table.side_effect = Exception("Database connection error")
        
        result = self.calendar_service.get_trainer_calendar(
            'trainer1', '2024-01-15', '2024-01-20', 'week'
        )
        
        self.assertIn('error', result)
        self.assertEqual(result['events'], [])
    
    def test_timezone_handling(self):
        """Test proper timezone conversion"""
        # Test date/time combination
        test_date = '2024-01-15'
        test_time = '14:30'
        
        combined = self.calendar_service._combine_date_time(test_date, test_time)
        
        self.assertEqual(combined.tzinfo.zone, 'Africa/Johannesburg')
        self.assertEqual(combined.hour, 14)
        self.assertEqual(combined.minute, 30)
    
    def test_timezone_handling_various_formats(self):
        """Test timezone handling with various time formats"""
        test_cases = [
            ('2024-01-15', '14:30', 14, 30),
            ('2024-01-15', '14', 14, 0),
            ('2024-01-15', '9:15', 9, 15),
        ]
        
        for date, time, expected_hour, expected_minute in test_cases:
            with self.subTest(time=time):
                result = self.calendar_service._combine_date_time(date, time)
                self.assertEqual(result.hour, expected_hour)
                self.assertEqual(result.minute, expected_minute)
    
    def test_get_calendar_conflicts(self):
        """Test conflict detection"""
        # Mock existing bookings
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute.return_value.data = [
            {
                'id': 'booking1',
                'session_date': '2024-01-15',
                'session_time': '10:00',
                'session_type': 'one_on_one'
            }
        ]
        
        conflicts = self.calendar_service.get_calendar_conflicts(
            'trainer1', '2024-01-15', '10:00', 60
        )
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['id'], 'booking1')
    
    def test_conflict_detection_no_conflicts(self):
        """Test conflict detection when no conflicts exist"""
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute.return_value.data = []
        
        conflicts = self.calendar_service.get_calendar_conflicts(
            'trainer1', '2024-01-15', '14:00', 60
        )
        
        self.assertEqual(len(conflicts), 0)
    
    def test_create_calendar_event_success(self):
        """Test successful calendar event creation"""
        self.mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {'id': 'event1', 'session_date': '2024-01-15'}
        ]
        
        result = self.calendar_service.create_calendar_event('trainer1', {
            'date': '2024-01-15',
            'time': '10:00',
            'duration': 60,
            'type': 'personal_time',
            'notes': 'Lunch break'
        })
        
        self.assertTrue(result['success'])
        self.assertEqual(result['event_id'], 'event1')
    
    def test_create_calendar_event_missing_fields(self):
        """Test calendar event creation with missing required fields"""
        result = self.calendar_service.create_calendar_event('trainer1', {
            'date': '2024-01-15',
            'time': '10:00'
            # Missing 'duration' and 'type'
        })
        
        self.assertFalse(result['success'])
        self.assertIn('Missing required field', result['error'])
    
    def test_update_calendar_preferences(self):
        """Test updating calendar preferences"""
        # Mock existing preferences
        self.mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {'trainer_id': 'trainer1'}
        ]
        
        self.mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()
        
        result = self.calendar_service.update_calendar_preferences('trainer1', {
            'default_view': 'month',
            'show_client_names': False,
            'start_hour': 7,
            'end_hour': 20
        })
        
        self.assertTrue(result['success'])
        self.assertEqual(result['preferences']['default_view'], 'month')
    
    def test_preferences_validation(self):
        """Test preference validation"""
        preferences = self.calendar_service._validate_preferences({
            'default_view': 'invalid_view',
            'start_hour': 25,  # Invalid hour
            'end_hour': -1,     # Invalid hour
            'session_colors': {'one_on_one': '#123456'},  # Valid color
        })
        
        self.assertEqual(preferences['default_view'], 'week')  # Should default
        self.assertEqual(preferences['start_hour'], 6)  # Should default
        self.assertEqual(preferences['end_hour'], 21)  # Should default
        self.assertEqual(preferences['session_colors']['one_on_one'], '#123456')
    
    def test_hex_color_validation(self):
        """Test hex color validation"""
        valid_colors = ['#123456', '#abc', '#FFFFFF', '#000000']
        invalid_colors = ['123456', '#12345', '#GGGGGG', 'red']
        
        for color in valid_colors:
            with self.subTest(color=color):
                self.assertTrue(self.calendar_service._is_valid_hex_color(color))
        
        for color in invalid_colors:
            with self.subTest(color=color):
                self.assertFalse(self.calendar_service._is_valid_hex_color(color))
    
    def test_format_calendar_data_day_view(self):
        """Test formatting calendar data for day view"""
        bookings = [
            {
                'id': '1',
                'session_date': '2024-01-15',
                'session_time': '09:00',
                'status': 'confirmed',
                'session_type': 'one_on_one',
                'clients': {'name': 'John Doe'}
            },
            {
                'id': '2',
                'session_date': '2024-01-15',
                'session_time': '14:00',
                'status': 'confirmed',
                'session_type': 'group_class',
                'clients': {'name': 'Jane Smith'}
            }
        ]
        
        result = self.calendar_service.format_calendar_data_for_display(
            bookings, 'day', {'start_hour': 6, 'end_hour': 18, 'show_client_names': True}
        )
        
        self.assertIn('time_slots', result)
        self.assertTrue(len(result['time_slots']) > 0)
    
    def test_format_calendar_data_week_view(self):
        """Test formatting calendar data for week view"""
        bookings = [
            {
                'id': '1',
                'session_date': '2024-01-15',
                'session_time': '09:00',
                'status': 'confirmed',
                'session_type': 'one_on_one',
                'clients': {'name': 'John Doe'}
            }
        ]
        
        result = self.calendar_service.format_calendar_data_for_display(
            bookings, 'week', {}
        )
        
        self.assertIn('days', result)
        self.assertTrue(len(result['days']) > 0)
    
    def test_format_calendar_data_month_view(self):
        """Test formatting calendar data for month view"""
        bookings = [
            {
                'id': '1',
                'session_date': '2024-01-15',
                'session_time': '09:00',
                'status': 'confirmed',
                'session_type': 'one_on_one',
                'clients': {'name': 'John Doe'}
            }
        ]
        
        result = self.calendar_service.format_calendar_data_for_display(
            bookings, 'month', {}
        )
        
        self.assertIn('calendar_grid', result)
        self.assertIn('month', result)
    
    def test_client_name_abbreviation(self):
        """Test client name abbreviation for privacy"""
        test_cases = [
            ('John Doe', 'John D.'),
            ('Jane', 'Jane'),
            ('Mary Jane Smith', 'Mary S.'),
            ('', 'Client'),
        ]
        
        for full_name, expected in test_cases:
            with self.subTest(name=full_name):
                result = self.calendar_service._abbreviate_name(full_name)
                self.assertEqual(result, expected)


class TestCalendarExportService(unittest.TestCase):
    """Test suite for CalendarExportService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.mock_config = Mock(spec=Config)
        self.mock_config.TIMEZONE = 'Africa/Johannesburg'
        self.mock_config.SMTP_SERVER = 'smtp.gmail.com'
        self.mock_config.SMTP_PORT = 587
        self.mock_config.SMTP_USERNAME = 'test@example.com'
        self.mock_config.SMTP_PASSWORD = 'password'
        self.mock_config.SENDER_EMAIL = 'noreply@refiloe.ai'
        
        self.export_service = CalendarExportService(self.mock_db, self.mock_config)
    
    def test_generate_ics_file(self):
        """Test ICS file generation"""
        booking_data = {
            'id': 'booking1',
            'session_date': '2024-01-15',
            'session_time': '10:00',
            'session_type': 'one_on_one',
            'status': 'confirmed',
            'trainer': {
                'name': 'John Trainer',
                'email': 'trainer@example.com',
                'gym_location': 'Main Gym'
            },
            'client': {
                'name': 'Jane Client',
                'email': 'client@example.com'
            }
        }
        
        ics_content = self.export_service.generate_ics_file(booking_data)
        
        self.assertIn('BEGIN:VCALENDAR', ics_content)
        self.assertIn('END:VCALENDAR', ics_content)
        self.assertIn('BEGIN:VEVENT', ics_content)
        self.assertIn('Training Session - Jane Client', ics_content)
        self.assertIn('LOCATION:Main Gym', ics_content)
    
    def test_generate_ics_file_multiple_sessions(self):
        """Test ICS file generation with multiple sessions"""
        booking_data = {
            'sessions': [
                {
                    'id': 'booking1',
                    'session_date': '2024-01-15',
                    'session_time': '10:00',
                    'session_type': 'one_on_one',
                    'status': 'confirmed'
                },
                {
                    'id': 'booking2',
                    'session_date': '2024-01-16',
                    'session_time': '14:00',
                    'session_type': 'group_class',
                    'status': 'confirmed'
                }
            ],
            'trainer': {'name': 'John Trainer'},
            'client': {'name': 'Jane Client'}
        }
        
        ics_content = self.export_service.generate_ics_file(booking_data)
        
        # Count VEVENT occurrences
        vevent_count = ics_content.count('BEGIN:VEVENT')
        self.assertEqual(vevent_count, 2)
    
    def test_export_to_csv(self):
        """Test CSV export"""
        bookings = [
            {
                'session_date': '2024-01-15',
                'session_time': '10:00',
                'session_type': 'one_on_one',
                'status': 'confirmed',
                'notes': 'Test note',
                'clients': {
                    'name': 'John Doe',
                    'whatsapp': '+27821234567',
                    'email': 'john@example.com'
                }
            }
        ]
        
        csv_bytes = self.export_service.export_to_csv(bookings)
        csv_content = csv_bytes.decode('utf-8')
        
        self.assertIn('Date,Time,Client,Phone,Email,Type,Status,Notes', csv_content)
        self.assertIn('2024-01-15', csv_content)
        self.assertIn('John Doe', csv_content)
    
    def test_bulk_export_month(self):
        """Test bulk export for a month"""
        self.mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.order.return_value.execute.return_value.data = [
            {
                'id': 'booking1',
                'session_date': '2024-01-15',
                'session_time': '10:00',
                'clients': {'name': 'John Doe'}
            }
        ]
        
        self.mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'trainer1',
            'name': 'Trainer Name'
        }
        
        result = self.export_service.bulk_export_month('trainer1', 1, 2024)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['month'], 1)
        self.assertEqual(result['year'], 2024)
        self.assertEqual(result['count'], 1)
    
    def test_email_preferences_defaults(self):
        """Test getting default email preferences"""
        self.mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
        
        prefs = self.export_service.get_email_preferences('trainer1')
        
        self.assertTrue(prefs['send_on_booking'])
        self.assertTrue(prefs['send_to_client'])
        self.assertEqual(prefs['reminder_hours'], 24)
    
    @patch('smtplib.SMTP')
    def test_send_calendar_email_success(self, mock_smtp):
        """Test successful email sending"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        result = self.export_service.send_calendar_email(
            ['test@example.com'],
            'ICS_CONTENT_HERE',
            {
                'session_date': '2024-01-15',
                'session_time': '10:00',
                'trainers': {'name': 'John Trainer', 'gym_location': 'Main Gym'},
                'clients': {'name': 'Jane Client'}
            }
        )
        
        self.assertTrue(result['success'])
        mock_server.send_message.assert_called_once()
    
    def test_send_calendar_email_no_config(self):
        """Test email sending without configuration"""
        self.export_service.smtp_server = None
        
        result = self.export_service.send_calendar_email(
            ['test@example.com'],
            'ICS_CONTENT',
            {}
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Email not configured')


class TestCalendarErrorHandling(unittest.TestCase):
    """Test error handling and recovery"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.mock_config = Mock(spec=Config)
        self.mock_config.TIMEZONE = 'Africa/Johannesburg'
        self.calendar_service = CalendarService(self.mock_db, self.mock_config)
    
    def test_invalid_date_format_handling(self):
        """Test handling of invalid date formats"""
        # Should handle gracefully and return default
        result = self.calendar_service._combine_date_time('invalid-date', '10:00')
        self.assertIsNotNone(result)
    
    def test_database_connection_error_recovery(self):
        """Test recovery from database connection errors"""
        # First call fails
        self.mock_db.table.side_effect = [Exception("Connection lost"), Mock()]
        
        # Should handle error gracefully
        result = self.calendar_service.get_trainer_calendar(
            'trainer1', '2024-01-15', '2024-01-20', 'week'
        )
        
        self.assertIn('error', result)
        self.assertEqual(result['events'], [])
    
    def test_sync_conflict_resolution(self):
        """Test calendar sync conflict resolution"""
        # Create mock sync manager
        from services.scheduler import CalendarSyncManager
        sync_manager = CalendarSyncManager(self.mock_db, Mock())
        
        local_booking = {
            'id': 'booking1',
            'status': 'confirmed',
            'updated_at': '2024-01-15T10:00:00'
        }
        
        external_event = {
            'id': 'external1',
            'updated': '2024-01-15T09:00:00'
        }
        
        result = sync_manager.handle_sync_conflicts(local_booking, external_event)
        
        self.assertEqual(result['action'], 'update_external')
    
    def test_rollback_on_failed_sync(self):
        """Test rollback functionality for failed syncs"""
        # This would test the rollback mechanism
        # In a real implementation, this would track changes and revert them
        pass


class TestCalendarIntegration(unittest.TestCase):
    """Integration tests for calendar system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.mock_config = Mock(spec=Config)
        self.mock_config.TIMEZONE = 'Africa/Johannesburg'
        self.mock_config.get_booking_slots.return_value = {
            'monday': ['09:00', '10:00', '11:00'],
        }
        
        self.calendar_service = CalendarService(self.mock_db, self.mock_config)
        self.export_service = CalendarExportService(self.mock_db, self.mock_config)
    
    def test_end_to_end_booking_to_export(self):
        """Test complete flow from booking creation to export"""
        # Create booking
        self.mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {'id': 'booking1', 'session_date': '2024-01-15'}
        ]
        
        booking_result = self.calendar_service.create_calendar_event('trainer1', {
            'date': '2024-01-15',
            'time': '10:00',
            'duration': 60,
            'type': 'one_on_one',
            'notes': 'Test session'
        })
        
        self.assertTrue(booking_result['success'])
        
        # Export to ICS
        booking_data = {
            'id': booking_result['event_id'],
            'session_date': '2024-01-15',
            'session_time': '10:00',
            'trainer': {'name': 'Trainer'},
            'client': {'name': 'Client'}
        }
        
        ics_content = self.export_service.generate_ics_file(booking_data)
        
        self.assertIn('BEGIN:VCALENDAR', ics_content)
        self.assertIn('Training Session', ics_content)


if __name__ == '__main__':
    unittest.main()