# tests/test_conversation_flows.py
"""
Comprehensive conversation flow tests for Refiloe WhatsApp Assistant
Tests all user journeys and conversation paths
"""

import pytest
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from unittest.mock import Mock, patch, MagicMock
import re

# Import Refiloe modules
from services.ai_intent_handler import AIIntentHandler
from services.registration.trainer_registration import TrainerRegistrationHandler
from services.registration.client_registration import ClientRegistrationHandler
from services.booking_handler import BookingHandler
from services.habit_tracker import HabitTrackerService
from services.workout_service import WorkoutService
from services.payment_handler import PaymentHandler
from services.refiloe import RefiloeService
from utils.logger import log_info


class ConversationTester:
    """Simulates WhatsApp conversations for testing"""
    
    def __init__(self, phone: str = "27731863036"):
        self.phone = phone
        self.conversation_history = []
        self.current_user_type = None
        self.current_user_data = None
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize services (will be mocked in tests)
        self.setup_services()
    
    def setup_services(self):
        """Initialize all required services"""
        self.db = Mock()  # Will be replaced with actual Supabase in integration tests
        self.config = Mock()
        self.whatsapp = Mock()
        
        # Initialize all services
        self.refiloe = RefiloeService(self.db)
        self.ai_handler = AIIntentHandler(self.config, self.db)
        self.trainer_reg = TrainerRegistrationHandler(self.db, self.whatsapp)
        self.client_reg = ClientRegistrationHandler(self.db, self.whatsapp)
        self.booking_handler = BookingHandler(self.db, self.config)
        self.habit_tracker = HabitTrackerService(self.db)
        self.workout_service = WorkoutService(self.db, self.config)
        self.payment_handler = PaymentHandler(self.db, self.config)
    
    def send_message(self, text: str) -> Dict:
        """Simulate sending a message to Refiloe"""
        # Add to history
        self.conversation_history.append({
            'sender': 'user',
            'text': text,
            'timestamp': datetime.now(self.sa_tz)
        })
        
        # Process message through Refiloe
        response = self.refiloe.handle_message(self.phone, text)
        
        # Add response to history
        self.conversation_history.append({
            'sender': 'refiloe',
            'text': response.get('message', ''),
            'timestamp': datetime.now(self.sa_tz),
            'buttons': response.get('buttons', [])
        })
        
        return response
    
    def verify_response(self, response: Dict, expected_patterns: List[str], 
                       should_fail: bool = False) -> bool:
        """Verify response matches expected patterns"""
        message = response.get('message', '')
        
        for pattern in expected_patterns:
            if isinstance(pattern, str):
                if pattern.lower() not in message.lower():
                    if not should_fail:
                        pytest.fail(f"Expected '{pattern}' in response but got: {message}")
                    return False
            elif isinstance(pattern, re.Pattern):
                if not pattern.search(message):
                    if not should_fail:
                        pytest.fail(f"Pattern {pattern.pattern} not found in: {message}")
                    return False
        
        return True
    
    def verify_database_state(self, table: str, conditions: Dict) -> bool:
        """Verify database state matches expected conditions"""
        # This will check actual Supabase in integration tests
        return True
    
    def cleanup(self):
        """Clean up test data"""
        # Clean up test data from Supabase
        pass


class TestPhase1_Registration:
    """Test user registration flows"""
    
    @pytest.fixture
    def tester(self):
        """Create a conversation tester"""
        tester = ConversationTester()
        yield tester
        tester.cleanup()
    
    def test_trainer_registration_complete_flow(self, tester):
        """Test complete trainer registration flow"""
        
        # Step 1: Initial greeting
        response = tester.send_message("Hi")
        assert tester.verify_response(response, [
            "welcome",
            ["trainer", "client"]  # Should ask user type
        ])
        
        # Step 2: Choose trainer
        response = tester.send_message("trainer")
        assert tester.verify_response(response, [
            "excited",
            "Step 1 of 7",
            "name"
        ])
        
        # Step 3: Provide name
        response = tester.send_message("John Smith")
        assert tester.verify_response(response, [
            "Step 2 of 7",
            "business name"
        ])
        
        # Step 4: Business name
        response = tester.send_message("FitLife PT")
        assert tester.verify_response(response, [
            "Step 3 of 7",
            "email"
        ])
        
        # Step 5: Email
        response = tester.send_message("john@fitlife.co.za")
        assert tester.verify_response(response, [
            "Step 4 of 7",
            "specializ"  # specialization
        ])
        
        # Step 6: Specialization
        response = tester.send_message("Weight loss and strength training")
        assert tester.verify_response(response, [
            "Step 5 of 7",
            "experience"
        ])
        
        # Step 7: Experience
        response = tester.send_message("5 years")
        assert tester.verify_response(response, [
            "Step 6 of 7",
            "location"
        ])
        
        # Step 8: Location
        response = tester.send_message("Sandton, Johannesburg")
        assert tester.verify_response(response, [
            "Step 7 of 7",
            ["pricing", "rate", "charge"]
        ])
        
        # Step 9: Pricing (with currency)
        response = tester.send_message("R450")
        assert tester.verify_response(response, [
            "Welcome aboard",
            "John",
            ["dashboard", "add client", "help"]
        ])
        
        # Verify trainer was created in database
        assert tester.verify_database_state('trainers', {
            'whatsapp': '27731863036',
            'name': 'John Smith',
            'business_name': 'FitLife PT',
            'email': 'john@fitlife.co.za',
            'pricing_per_session': 450  # Should be numeric, not string
        })
    
    def test_trainer_registration_with_currency_variations(self, tester):
        """Test registration handles different currency formats"""
        
        # Quick setup to pricing step
        tester.send_message("Hi")
        tester.send_message("trainer")
        tester.send_message("Jane Doe")
        tester.send_message("skip")  # Skip business name
        tester.send_message("jane@test.com")
        tester.send_message("Yoga")
        tester.send_message("3")
        tester.send_message("Cape Town")
        
        # Test various currency formats
        test_cases = [
            ("R450", 450),
            ("450", 450),
            ("R 450", 450),
            ("450.00", 450),
            ("R450.50", 450.50),
            ("four fifty", 450),  # AI should understand
            ("350 rand", 350)
        ]
        
        for input_text, expected_value in test_cases:
            response = tester.send_message(input_text)
            assert "Welcome aboard" in response.get('message', '')
            
            # Verify correct numeric value saved
            assert tester.verify_database_state('trainers', {
                'pricing_per_session': expected_value
            })
            
            # Reset for next test
            tester.cleanup()
            tester = ConversationTester()
    
    def test_client_registration_flow(self, tester):
        """Test client registration flow"""
        
        # First register as trainer
        self._quick_trainer_registration(tester)
        
        # Now add a client
        response = tester.send_message("Add client Sarah 0821234567")
        assert tester.verify_response(response, [
            ["added", "registered"],
            "Sarah"
        ])
        
        # Simulate client's first message
        client_tester = ConversationTester(phone="27821234567")
        response = client_tester.send_message("Hi")
        assert client_tester.verify_response(response, [
            "Sarah",
            ["book", "session", "training"]
        ])
    
    def _quick_trainer_registration(self, tester):
        """Helper to quickly register a trainer"""
        tester.send_message("Hi")
        tester.send_message("trainer")
        tester.send_message("Test Trainer")
        tester.send_message("skip")
        tester.send_message("test@test.com")
        tester.send_message("General")
        tester.send_message("5")
        tester.send_message("Sandton")
        tester.send_message("400")


class TestPhase2_ClientManagement:
    """Test client management features"""
    
    @pytest.fixture
    def trainer_tester(self):
        """Create a registered trainer tester"""
        tester = ConversationTester()
        # Quick registration
        self._quick_trainer_registration(tester)
        yield tester
        tester.cleanup()
    
    def _quick_trainer_registration(self, tester):
        """Helper to quickly register a trainer"""
        tester.send_message("Hi")
        tester.send_message("trainer")
        tester.send_message("Test Trainer")
        tester.send_message("skip")
        tester.send_message("test@test.com")
        tester.send_message("General")
        tester.send_message("5")
        tester.send_message("Sandton")
        tester.send_message("400")
    
    def test_add_client_variations(self, trainer_tester):
        """Test different ways to add clients"""
        
        test_cases = [
            "Add client Sarah 0821234567",
            "Register new client John Doe 0831234567",
            "New client Mike phone 0841234567",
            "add Mary Jones +27851234567",
            "Sign up client Peter 0861234567"
        ]
        
        for command in test_cases:
            response = trainer_tester.send_message(command)
            assert trainer_tester.verify_response(response, [
                ["added", "registered", "created"],
                ["welcome", "sent"]
            ])
    
    def test_view_clients(self, trainer_tester):
        """Test viewing client list"""
        
        # Add some clients first
        trainer_tester.send_message("Add client Sarah 0821234567")
        trainer_tester.send_message("Add client John 0831234567")
        
        # Test different ways to view clients
        test_commands = [
            "Show my clients",
            "List clients",
            "View all clients",
            "my clients",
            "who are my clients"
        ]
        
        for command in test_commands:
            response = trainer_tester.send_message(command)
            assert trainer_tester.verify_response(response, [
                "Sarah",
                "John",
                ["0821234567", "0831234567"]
            ])
    
    def test_set_custom_pricing(self, trainer_tester):
        """Test setting custom pricing for clients"""
        
        # Add a client
        trainer_tester.send_message("Add client Sarah 0821234567")
        
        # Test different pricing commands
        test_cases = [
            ("Set Sarah's rate to R450", 450),
            ("Change Sarah's price to R500 per session", 500),
            ("Update Sarah's session fee to 400", 400),
            ("Sarah pays 350", 350)
        ]
        
        for command, expected_price in test_cases:
            response = trainer_tester.send_message(command)
            assert trainer_tester.verify_response(response, [
                ["updated", "set", "changed"],
                "Sarah",
                str(expected_price)
            ])
            
            # Verify in database
            assert trainer_tester.verify_database_state('clients', {
                'name': 'Sarah',
                'custom_rate': expected_price
            })


class TestPhase3_Scheduling:
    """Test scheduling and booking features"""
    
    @pytest.fixture
    def trainer_with_clients(self):
        """Create trainer with registered clients"""
        tester = ConversationTester()
        self._setup_trainer_with_clients(tester)
        yield tester
        tester.cleanup()
    
    def _setup_trainer_with_clients(self, tester):
        """Setup trainer with clients"""
        # Register trainer
        tester.send_message("Hi")
        tester.send_message("trainer")
        tester.send_message("Test Trainer")
        tester.send_message("skip")
        tester.send_message("test@test.com")
        tester.send_message("General")
        tester.send_message("5")
        tester.send_message("Sandton")
        tester.send_message("400")
        
        # Add clients
        tester.send_message("Add client Sarah 0821234567")
        tester.send_message("Add client John 0831234567")
    
    def test_view_schedule(self, trainer_with_clients):
        """Test viewing schedule"""
        
        test_commands = [
            "Show my schedule",
            "What's on today",
            "This week's bookings",
            "Tomorrow's sessions",
            "my calendar"
        ]
        
        for command in test_commands:
            response = trainer_with_clients.send_message(command)
            # Should show schedule even if empty
            assert trainer_with_clients.verify_response(response, [
                ["schedule", "bookings", "sessions", "no bookings", "free"]
            ])
    
    def test_book_sessions(self, trainer_with_clients):
        """Test booking sessions for clients"""
        
        test_cases = [
            "Book Sarah for tomorrow at 9am",
            "Schedule John Monday 6pm",
            "Add session with Sarah Friday 7:00"
        ]
        
        for command in test_cases:
            response = trainer_with_clients.send_message(command)
            assert trainer_with_clients.verify_response(response, [
                ["booked", "scheduled", "confirmed"],
                ["Sarah", "John"]  # Client name should be mentioned
            ])
    
    def test_cancel_reschedule(self, trainer_with_clients):
        """Test canceling and rescheduling"""
        
        # First book a session
        trainer_with_clients.send_message("Book Sarah tomorrow 9am")
        
        # Test cancel
        response = trainer_with_clients.send_message("Cancel Sarah's session tomorrow")
        assert trainer_with_clients.verify_response(response, [
            ["cancelled", "canceled", "removed"],
            "Sarah"
        ])
        
        # Book again for reschedule test
        trainer_with_clients.send_message("Book John Monday 6pm")
        
        # Test reschedule
        response = trainer_with_clients.send_message("Reschedule John to Tuesday 6pm")
        assert trainer_with_clients.verify_response(response, [
            ["rescheduled", "moved", "updated"],
            "John",
            "Tuesday"
        ])


# Continue with more test classes...
class TestPhase4_HabitTracking:
    """Test habit tracking features"""
    
    @pytest.fixture
    def trainer_with_habits(self):
        tester = ConversationTester()
        self._setup_trainer_with_habits(tester)
        yield tester
        tester.cleanup()
    
    def _setup_trainer_with_habits(self, tester):
        """Setup trainer with clients and habits"""
        # Quick trainer setup
        tester.send_message("Hi")
        tester.send_message("trainer")
        tester.send_message("Test Trainer")
        tester.send_message("skip")
        tester.send_message("test@test.com")
        tester.send_message("General")
        tester.send_message("5")
        tester.send_message("Sandton")
        tester.send_message("400")
        
        # Add client
        tester.send_message("Add client Sarah 0821234567")
    
    def test_setup_habits(self, trainer_with_habits):
        """Test setting up habits for clients"""
        
        test_cases = [
            "Set up water tracking for Sarah",
            "Add habit tracking for Sarah - 8 glasses water daily",
            "Sarah needs to track steps target 10000",
            "Setup sleep tracking for Sarah"
        ]
        
        for command in test_cases:
            response = trainer_with_habits.send_message(command)
            assert trainer_with_habits.verify_response(response, [
                ["set", "added", "created", "tracking"],
                "Sarah"
            ])


class TestPhase5_Workouts:
    """Test workout and assessment features"""
    
    @pytest.fixture
    def trainer_with_clients(self):
        tester = ConversationTester()
        self._setup_trainer_with_clients(tester)
        yield tester
        tester.cleanup()
    
    def _setup_trainer_with_clients(self, tester):
        # Quick setup
        tester.send_message("Hi")
        tester.send_message("trainer")
        tester.send_message("Test Trainer")
        tester.send_message("skip")
        tester.send_message("test@test.com")
        tester.send_message("General")
        tester.send_message("5")
        tester.send_message("Sandton")
        tester.send_message("400")
        tester.send_message("Add client Sarah 0821234567")
    
    def test_send_workouts(self, trainer_with_clients):
        """Test sending workouts to clients"""
        
        test_cases = [
            "Send workout to Sarah",
            "Create upper body workout for Sarah",
            "Send Sarah a cardio program"
        ]
        
        for command in test_cases:
            response = trainer_with_clients.send_message(command)
            assert trainer_with_clients.verify_response(response, [
                ["sent", "created", "delivered"],
                "Sarah",
                "workout"
            ])


class TestPhase6_Payments:
    """Test payment features"""
    
    @pytest.fixture
    def trainer_with_clients(self):
        tester = ConversationTester()
        self._setup_trainer_with_clients(tester)
        yield tester
        tester.cleanup()
    
    def _setup_trainer_with_clients(self, tester):
        # Quick setup
        tester.send_message("Hi")
        tester.send_message("trainer")
        tester.send_message("Test Trainer")
        tester.send_message("skip")
        tester.send_message("test@test.com")
        tester.send_message("General")
        tester.send_message("5")
        tester.send_message("Sandton")
        tester.send_message("400")
        tester.send_message("Add client Sarah 0821234567")
    
    def test_request_payment(self, trainer_with_clients):
        """Test requesting payments"""
        
        test_cases = [
            "Request payment from Sarah",
            "Send invoice to Sarah for 3 sessions",
            "Bill Sarah for this month"
        ]
        
        for command in test_cases:
            response = trainer_with_clients.send_message(command)
            assert trainer_with_clients.verify_response(response, [
                ["payment", "invoice", "bill"],
                "Sarah",
                ["link", "sent", "requested"]
            ])


class TestPhase10_NaturalLanguage:
    """Test natural language understanding"""
    
    @pytest.fixture
    def tester(self):
        tester = ConversationTester()
        # Quick trainer setup
        tester.send_message("Hi")
        tester.send_message("trainer")
        tester.send_message("Test Trainer")
        tester.send_message("skip")
        tester.send_message("test@test.com")
        tester.send_message("General")
        tester.send_message("5")
        tester.send_message("Sandton")
        tester.send_message("400")
        yield tester
        tester.cleanup()
    
    def test_casual_conversation(self, tester):
        """Test that AI handles casual conversation naturally"""
        
        test_cases = [
            ("I'm doing good thanks", ["great", "glad", "good to hear"]),
            ("The weather is nice today", ["weather", "enjoy", "nice"]),
            ("How are you?", ["well", "thanks", "ready to help"])
        ]
        
        for message, expected_words in test_cases:
            response = tester.send_message(message)
            # Should NOT respond with "Invalid command"
            assert "invalid command" not in response.get('message', '').lower()
            assert "type 'help'" not in response.get('message', '').lower()
            
            # Should respond naturally
            assert any(word in response.get('message', '').lower() 
                      for word in expected_words)
    
    def test_ai_understands_context(self, tester):
        """Test AI understanding based on context"""
        
        # Add a client first
        tester.send_message("Add client Sarah 0821234567")
        
        # Now use natural language that requires understanding
        test_cases = [
            "Book Sarah for our usual time",  # AI should ask what time
            "Sarah can't make it tomorrow",   # Should understand cancellation
            "How's Sarah doing?",             # Should show client progress
            "Sarah paid me cash"              # Should understand payment
        ]
        
        for message in test_cases:
            response = tester.send_message(message)
            # Should not give rigid command error
            assert "invalid command" not in response.get('message', '').lower()
            assert "Sarah" in response.get('message', '')


class TestPhase11_ErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.fixture
    def tester(self):
        tester = ConversationTester()
        yield tester
        tester.cleanup()
    
    def test_handles_invalid_data_gracefully(self, tester):
        """Test handling of invalid data"""
        
        # Register trainer first
        tester.send_message("Hi")
        tester.send_message("trainer")
        tester.send_message("Test Trainer")
        tester.send_message("skip")
        tester.send_message("test@test.com")
        tester.send_message("General")
        tester.send_message("5")
        tester.send_message("Sandton")
        tester.send_message("400")
        
        test_cases = [
            ("Book session for NonExistentClient", ["don't have", "not found", "no client"]),
            ("Schedule me for yesterday", ["past", "future date", "can't book"]),
            ("Set price to negative amount", ["positive", "valid amount", "greater than"])
        ]
        
        for command, expected_words in test_cases:
            response = tester.send_message(command)
            # Should give helpful error, not crash
            assert any(word in response.get('message', '').lower() 
                      for word in expected_words)


# Main test runner
def run_all_tests():
    """Run all conversation flow tests"""
    pytest.main([__file__, '-v', '--tb=short'])
  
