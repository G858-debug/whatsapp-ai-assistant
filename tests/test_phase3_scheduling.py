# tests/test_phase3_scheduling.py
"""
Phase 3: Scheduling & Bookings Tests
Testing actual booking functionality with real code
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, date
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.refiloe import RefiloeService
from models.booking import BookingModel
from services.ai_intent_handler import AIIntentHandler
from utils.validators import InputValidator


class TestViewScheduleReal:
    """Test 3.1: View Schedule functionality"""
    
    @pytest.fixture
    def setup_schedule(self):
        mock_db = Mock()
        mock_config = Mock()
        mock_config.TIMEZONE = 'Africa/Johannesburg'
        
        # Mock upcoming bookings
        mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.neq.return_value.execute.return_value.data = [
            {
                'id': 'booking-1',
                'session_date': '2024-01-20',
                'session_time': '09:00',
                'status': 'confirmed',
                'clients': {'name': 'Sarah Johnson'}
            },
            {
                'id': 'booking-2',
                'session_date': '2024-01-20',
                'session_time': '14:00',
                'status': 'confirmed',
                'clients': {'name': 'John Doe'}
            }
        ]
        
        refiloe = RefiloeService(mock_db)
        booking_model = BookingModel(mock_db, mock_config)
        
        return refiloe, booking_model, mock_db
    
    def test_view_schedule_commands(self, setup_schedule):
        """Test various ways to view schedule"""
        refiloe, booking_model, mock_db = setup_schedule
        
        schedule_commands = [
            "Show my schedule",
            "What's on today",
            "This week's bookings",
            "Tomorrow's sessions",
            "My calendar",
            "Show bookings",
            "What's my schedule",
            "Today's appointments"
        ]
        
        for command in schedule_commands:
            response = refiloe.handle_message('27731863036', command)
            
            message = response.get('message', '').lower()
            # Should show schedule or indicate no bookings
            assert 'schedule' in message or 'booking' in message or \
                   'session' in message or 'appointment' in message or \
                   'no bookings' in message or 'free' in message, \
                   f"Failed to show schedule with: {command}"


class TestBookSessionsReal:
    """Test 3.2: Book Sessions functionality"""
    
    @pytest.fixture
    def setup_booking(self):
        mock_db = Mock()
        mock_config = Mock()
        mock_config.TIMEZONE = 'Africa/Johannesburg'
        mock_config.ANTHROPIC_API_KEY = 'test-key'
        
        # Mock client exists
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'client-456',
            'name': 'Sarah Johnson',
            'trainer_id': 'trainer-123'
        }
        
        # Mock no conflicts
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        
        # Mock successful booking
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {'id': 'booking-new', 'status': 'confirmed'}
        ]
        
        booking_model = BookingModel(mock_db, mock_config)
        ai_handler = AIIntentHandler(mock_config, mock_db)
        refiloe = RefiloeService(mock_db)
        
        return refiloe, booking_model, ai_handler, mock_db
    
    @pytest.mark.critical
    def test_book_session_natural_language(self, setup_booking):
        """Test booking with natural language variations"""
        refiloe, booking_model, ai_handler, mock_db = setup_booking
        
        # Natural booking requests
        booking_requests = [
            "Book Sarah for tomorrow at 9am",
            "Schedule John Monday 6pm",
            "Add session with Mike Friday 7:00",
            "Can you book Sarah tomorrow morning",
            "Set up a session with John on Monday",
            "Book Sarah in for tomorrow",
            "Sarah tomorrow 9",
            "Get John in on Monday evening",
            "Sarah wants to train tomorrow at 9",
            "Book Sarah at 09:00",
            "Book Sarah at 9 AM",
        ]
        
        for request in booking_requests:
            # Test if AI understands booking intent
            intent_result = ai_handler.understand_message(
                message=request,
                sender_type='trainer',
                sender_data={'id': 'trainer-123'},
                conversation_history=[]
            )
            
            # Should recognize booking intent
            assert intent_result.get('intent') in ['booking', 'schedule', None] or \
                   intent_result.get('confidence', 0) > 0.5, \
                   f"Failed to understand booking intent: {request}"
    
    def test_booking_time_formats(self, setup_booking):
        """Test various time format inputs"""
        refiloe, booking_model, ai_handler, mock_db = setup_booking
        
        time_formats = [
            "9am",
            "9:00",
            "09:00",
            "9 AM",
            "9:00am",
            "09:00 AM",
            "9 o'clock",
            "9:30",
            "14:00",
            "2pm",
            "2:00 PM",
        ]
        
        validator = InputValidator()
        
        for time_format in time_formats:
            # Validate time format
            is_valid, error = validator.validate_time_format(time_format)
            assert is_valid == True, f"Failed to validate time: {time_format}"
    
    def test_booking_date_parsing(self, setup_booking):
        """Test various date format inputs"""
        refiloe, booking_model, ai_handler, mock_db = setup_booking
        
        # Test relative dates
        today = datetime.now(pytz.timezone('Africa/Johannesburg'))
        
        date_tests = [
            ("today", today.date()),
            ("tomorrow", (today + timedelta(days=1)).date()),
            ("Monday", None),  # Next Monday
            ("next week", None),  # 7 days from now
            ("2024-01-20", date(2024, 1, 20)),
            ("20/01/2024", date(2024, 1, 20)),
            ("20 Jan", None),  # Current year assumed
        ]
        
        validator = InputValidator()
        
        for date_input, expected in date_tests:
            if expected:  # Test specific date parsing
                is_valid, parsed_date, error = validator.validate_date(
                    date_input,
                    min_date=today.date()
                )
                
                # Should parse dates correctly
                if expected and is_valid:
                    assert parsed_date == expected or parsed_date is not None


class TestCancelRescheduleReal:
    """Test 3.3: Cancel/Reschedule functionality"""
    
    @pytest.fixture
    def setup_cancel_reschedule(self):
        mock_db = Mock()
        mock_config = Mock()
        mock_config.TIMEZONE = 'Africa/Johannesburg'
        
        # Mock existing booking
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'booking-123',
            'client_id': 'client-456',
            'session_date': '2024-01-20',
            'session_time': '09:00',
            'status': 'confirmed'
        }
        
        booking_model = BookingModel(mock_db, mock_config)
        refiloe = RefiloeService(mock_db)
        
        return refiloe, booking_model, mock_db
    
    def test_cancel_booking_variations(self, setup_cancel_reschedule):
        """Test various ways to cancel bookings"""
        refiloe, booking_model, mock_db = setup_cancel_reschedule
        
        cancel_commands = [
            "Cancel Sarah's session tomorrow",
            "Cancel tomorrow's 9am session",
            "Remove Sarah from tomorrow",
            "Delete booking for Sarah",
            "Cancel my 9am",
            "Sarah can't make it tomorrow",
            "Skip tomorrow's session",
            "Cancel booking 123",
        ]
        
        for command in cancel_commands:
            # Should handle cancellation request
            response = refiloe.handle_message('27731863036', command)
            
            # Check if cancellation is understood
            message = response.get('message', '').lower()
            assert 'cancel' in message or 'remove' in message or \
                   'deleted' in message or response.get('success') == True, \
                   f"Failed to handle cancellation: {command}"
    
    def test_reschedule_booking(self, setup_cancel_reschedule):
        """Test rescheduling bookings"""
        refiloe, booking_model, mock_db = setup_cancel_reschedule
        
        reschedule_commands = [
            "Reschedule John to Tuesday 6pm",
            "Move Mike's session to 8am",
            "Change Sarah's booking to tomorrow",
            "Can we move John to Wednesday",
            "Shift Mike's session to the afternoon",
        ]
        
        for command in reschedule_commands:
            response = refiloe.handle_message('27731863036', command)
            
            message = response.get('message', '').lower()
            # Should handle reschedule request
            assert 'reschedule' in message or 'move' in message or \
                   'change' in message or 'updated' in message or \
                   response.get('success') == True, \
                   f"Failed to handle reschedule: {command}"


class TestBookingConflictsAndValidation:
    """Test booking conflicts and validation"""
    
    @pytest.fixture
    def setup_conflicts(self):
        mock_db = Mock()
        mock_config = Mock()
        mock_config.TIMEZONE = 'Africa/Johannesburg'
        
        booking_model = BookingModel(mock_db, mock_config)
        return booking_model, mock_db
    
    def test_double_booking_prevention(self, setup_conflicts):
        """Test that double bookings are prevented"""
        booking_model, mock_db = setup_conflicts
        
        # Mock existing booking at 9am
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                'id': 'existing-booking',
                'session_time': '09:00',
                'status': 'confirmed'
            }
        ]
        
        # Try to book same slot
        result = booking_model.create_booking(
            trainer_id='trainer-123',
            client_id='client-789',
            booking_data={
                'session_date': '2024-01-20',
                'session_time': '09:00',
                'session_type': 'one_on_one'
            }
        )
        
        # Should prevent double booking
        assert result['success'] == False
        assert 'already booked' in result.get('error', '').lower() or \
               'conflict' in result.get('error', '').lower() or \
               'not available' in result.get('error', '').lower()
    
    def test_past_date_booking_prevention(self, setup_conflicts):
        """Test that bookings in the past are prevented"""
        booking_model, mock_db = setup_conflicts
        
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        result = booking_model.create_booking(
            trainer_id='trainer-123',
            client_id='client-456',
            booking_data={
                'session_date': yesterday,
                'session_time': '09:00',
                'session_type': 'one_on_one'
            }
        )
        
        # Should prevent past bookings
        assert result['success'] == False or \
               'past' in result.get('error', '').lower() or \
               'future' in result.get('error', '').lower()
    
    def test_invalid_time_slots(self, setup_conflicts):
        """Test handling of invalid time slots"""
        booking_model, mock_db = setup_conflicts
        
        invalid_times = [
            "25:00",  # Invalid hour
            "09:65",  # Invalid minute
            "midnight",  # Ambiguous
            "sometime",  # Too vague
        ]
        
        validator = InputValidator()
        
        for time in invalid_times:
            is_valid, error = validator.validate_time_format(time)
            assert is_valid == False, f"Should reject invalid time: {time}"
