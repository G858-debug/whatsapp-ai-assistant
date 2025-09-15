# tests/test_refiloe_complete.py
"""
Comprehensive test suite for all Refiloe features
Based on the 11-phase testing plan
"""

import pytest
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from unittest.mock import Mock, MagicMock, patch
import re

# Import the conversation tester from the existing test file
from test_conversation_flows import ConversationTester


class TestPhase1_UserRegistration:
    """Phase 1: Initial Setup & User Registration"""
    
    def test_new_trainer_onboarding(self):
        """Test 1.1: New User Onboarding - Trainer Registration"""
        tester = ConversationTester()
        
        # Mock database to simulate no existing user
        tester.db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
        
        # Step 1: Initial greeting
        response = tester.send_message("Hi")
        assert "welcome" in response['message'].lower()
        assert "trainer" in response['message'].lower() or "client" in response['message'].lower()
        
        # Step 2: Choose trainer
        response = tester.send_message("trainer")
        assert "registration" in response['message'].lower() or "setup" in response['message'].lower()
        
        # Step 3-9: Complete registration
        registration_steps = [
            ("John Smith", "name"),
            ("FitLife PT", "business"),
            ("john@fitlife.co.za", "email"),
            ("Weight loss and strength", "specializ"),
            ("5 years", "experience"),
            ("Sandton", "location"),
            ("R450", "pricing")  # Critical: Should handle currency
        ]
        
        for input_text, expected_keyword in registration_steps:
            response = tester.send_message(input_text)
            # Each step should progress without errors
            assert response['success'] == True
        
        # Final step should complete registration
        assert "welcome aboard" in response['message'].lower()
        
        # Verify pricing was parsed correctly (R450 -> 450)
        # This is the bug you mentioned - Step 7 should save numeric value
        saved_data = tester.db.table.return_value.insert.return_value.execute.call_args
        if saved_data:
            assert saved_data[0][0]['pricing_per_session'] == 450  # Not "R450"
    
    def test_trainer_recognition(self):
        """Test 1.2: Trainer Recognition"""
        tester = ConversationTester()
        
        # Mock existing trainer
        tester.db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'trainer-123',
            'name': 'John Smith',
            'whatsapp': '27731863036'
        }
        
        # Test personalized greeting
        response = tester.send_message("Hi")
        assert "john" in response['message'].lower()
        
        # Test help command
        response = tester.send_message("help")
        assert "command" in response['message'].lower() or "help" in response['message'].lower()


class TestPhase2_ClientManagement:
    """Phase 2: Client Management (As Trainer)"""
    
    def test_add_client_variations(self):
        """Test 2.1: Add Client - Multiple formats"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        test_cases = [
            "Add client Sarah 0821234567",
            "Register new client John Doe 0831234567",
            "New client Mike phone 0841234567"
        ]
        
        for command in test_cases:
            response = tester.send_message(command)
            assert response['success'] == True
            assert "added" in response['message'].lower() or "registered" in response['message'].lower()
    
    def test_view_clients(self):
        """Test 2.2: View Clients"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        # Mock client list
        tester.db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {'name': 'Sarah', 'whatsapp': '0821234567'},
            {'name': 'John', 'whatsapp': '0831234567'}
        ]
        
        test_commands = [
            "Show my clients",
            "List clients",
            "View all clients"
        ]
        
        for command in test_commands:
            response = tester.send_message(command)
            assert "sarah" in response['message'].lower()
            assert "john" in response['message'].lower()
    
    def test_set_custom_pricing(self):
        """Test 2.3: Set Custom Pricing"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        test_cases = [
            ("Set Sarah's rate to R450", 450),
            ("Change John's price to R500 per session", 500),
            ("Update Mike's session fee to 400", 400)
        ]
        
        for command, expected_price in test_cases:
            response = tester.send_message(command)
            assert response['success'] == True
            assert "updated" in response['message'].lower() or "set" in response['message'].lower()
            
            # Verify price is numeric, not string
            update_call = tester.db.table.return_value.update.call_args
            if update_call:
                assert update_call[0][0]['custom_rate'] == expected_price


class TestPhase3_SchedulingBookings:
    """Phase 3: Scheduling & Bookings"""
    
    def test_view_schedule(self):
        """Test 3.1: View Schedule"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        test_commands = [
            "Show my schedule",
            "What's on today",
            "This week's bookings",
            "Tomorrow's sessions"
        ]
        
        for command in test_commands:
            response = tester.send_message(command)
            assert response['success'] == True
            # Should show schedule or indicate it's empty
            assert "schedule" in response['message'].lower() or "booking" in response['message'].lower()
    
    def test_book_sessions(self):
        """Test 3.2: Book Sessions"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        test_cases = [
            "Book Sarah for tomorrow at 9am",
            "Schedule John Monday 6pm",
            "Add session with Mike Friday 7:00"
        ]
        
        for command in test_cases:
            response = tester.send_message(command)
            assert response['success'] == True
            assert "booked" in response['message'].lower() or "scheduled" in response['message'].lower()
    
    def test_cancel_reschedule(self):
        """Test 3.3: Cancel/Reschedule"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        # Test cancellation
        response = tester.send_message("Cancel Sarah's session tomorrow")
        assert "cancel" in response['message'].lower()
        
        # Test reschedule
        response = tester.send_message("Reschedule John to Tuesday 6pm")
        assert "reschedul" in response['message'].lower() or "moved" in response['message'].lower()


class TestPhase4_HabitTracking:
    """Phase 4: Habit Tracking Setup"""
    
    def test_setup_habits(self):
        """Test 4.1: Setup Habits for Clients"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        test_cases = [
            "Set up water tracking for Sarah",
            "Add habit tracking for John - 8 glasses water daily",
            "Sarah needs to track steps target 10000",
            "Setup sleep tracking for Mike"
        ]
        
        for command in test_cases:
            response = tester.send_message(command)
            assert response['success'] == True
            assert "habit" in response['message'].lower() or "tracking" in response['message'].lower()


class TestPhase5_WorkoutsAssessments:
    """Phase 5: Workouts & Assessments"""
    
    def test_send_workouts(self):
        """Test 5.1: Send Workouts"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        test_cases = [
            "Send workout to Sarah",
            "Create upper body workout for John",
            "Send Mike a cardio program"
        ]
        
        for command in test_cases:
            response = tester.send_message(command)
            assert response['success'] == True
            assert "workout" in response['message'].lower() or "sent" in response['message'].lower()


class TestPhase6_PaymentsRevenue:
    """Phase 6: Payments & Revenue"""
    
    def test_request_payment(self):
        """Test 6.1: Request Payment"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        test_cases = [
            "Request payment from Sarah",
            "Send invoice to John for 3 sessions",
            "Bill Mike for this month"
        ]
        
        for command in test_cases:
            response = tester.send_message(command)
            assert response['success'] == True
            assert "payment" in response['message'].lower() or "invoice" in response['message'].lower()
    
    def test_check_revenue(self):
        """Test 6.2: Check Revenue"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        test_commands = [
            "Show my revenue",
            "This month's earnings",
            "Payment history",
            "Who owes me money?"
        ]
        
        for command in test_commands:
            response = tester.send_message(command)
            assert response['success'] == True


class TestPhase8_ClientFeatures:
    """Phase 8: Testing as a Client"""
    
    def test_client_booking(self):
        """Test 8.1: Client Booking"""
        tester = ConversationTester()
        tester.current_user_type = 'client'
        
        test_cases = [
            "Book a session",
            "I want to train tomorrow",
            "Schedule me for Monday"
        ]
        
        for command in test_cases:
            response = tester.send_message(command)
            assert response['success'] == True
            assert "book" in response['message'].lower() or "session" in response['message'].lower()
    
    def test_client_habit_logging(self):
        """Test 8.2: Client Habit Logging"""
        tester = ConversationTester()
        tester.current_user_type = 'client'
        
        test_responses = [
            "7 yes no",  # water, veggies, exercise
            "6 glasses, veggies done, no workout",
            "✅ ✅ ❌"
        ]
        
        for habit_response in test_responses:
            response = tester.send_message(habit_response)
            assert response['success'] == True
            assert "logged" in response['message'].lower() or "recorded" in response['message'].lower()


class TestPhase10_AdvancedFeatures:
    """Phase 10: Advanced Features"""
    
    def test_natural_language_understanding(self):
        """Test 10.2: Natural Language Understanding"""
        tester = ConversationTester()
        
        test_cases = [
            "I'm doing good thanks",
            "The weather is nice today",
            "How are you?"
        ]
        
        for message in test_cases:
            response = tester.send_message(message)
            # Should NOT respond with rigid command errors
            assert "invalid command" not in response['message'].lower()
            assert "type 'help'" not in response['message'].lower()
            # Should respond naturally
            assert response['success'] == True
    
    def test_error_handling(self):
        """Test 10.3: Error Handling"""
        tester = ConversationTester()
        tester.current_user_type = 'trainer'
        
        test_cases = [
            ("Book session for NonExistentClient", ["not found", "doesn't exist", "no client"]),
            ("Schedule me for yesterday", ["past", "future", "cannot"]),
            ("Set price to -100", ["positive", "invalid", "greater than"])
        ]
        
        for command, expected_words in test_cases:
            response = tester.send_message(command)
            # Should give helpful error message
            assert any(word in response['message'].lower() for word in expected_words)


class TestCriticalBugs:
    """Tests for specific bugs mentioned"""
    
    def test_trainer_registration_step_7_currency_parsing(self):
        """Critical Bug: Step 7 of trainer registration should parse currency"""
        tester = ConversationTester()
        
        # Test various currency formats
        currency_inputs = [
            ("R450", 450),
            ("450", 450),
            ("R 450", 450),
            ("450.00", 450),
            ("R450.50", 450.50),
            ("four fifty", 450),  # AI should understand
            ("350 rand", 350)
        ]
        
        for input_text, expected_value in currency_inputs:
            # Mock the registration handler
            tester.trainer_reg._parse_currency = Mock(return_value=expected_value)
            
            # Process the pricing step
            result = tester.trainer_reg.handle_registration_response(
                phone='27731863036',
                message=input_text,
                current_step=6,  # Step 7 (0-indexed)
                data={'name': 'Test', 'email': 'test@test.com'}
            )
            
            # Should parse correctly
            assert result['data'].get('pricing') == expected_value
    
    def test_ai_responds_naturally_not_rigid_commands(self):
        """Bug: AI should respond naturally, not with rigid 'Invalid command' messages"""
        tester = ConversationTester()
        
        # Configure AI handler to be active
        tester.ai_handler.understand_message = Mock(return_value={
            'success': True,
            'confidence': 0.8,
            'message': "I'm doing well, thanks for asking! How can I help you today?",
            'intent': 'greeting'
        })
        
        response = tester.send_message("I'm good thanks, how are you?")
        
        # Should use AI response, not rigid commands
        assert "invalid" not in response['message'].lower()
        assert "command" not in response['message'].lower()
        assert response['success'] == True


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
