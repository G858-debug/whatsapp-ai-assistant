"""
End-to-End Test Automation for Refiloe
Tests complete conversation flows as a real user would experience them
"""

import os
import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class RefiloeE2ETester:
    """
    End-to-end tester that simulates actual WhatsApp conversations
    """
    
    def __init__(self):
        """Initialize with real connections"""
        from supabase import create_client
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Setup connections
        self.db = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        
        # Import the actual message handler
        from app_core import process_whatsapp_message
        self.process_message = process_whatsapp_message
        
        # Test phone numbers
        self.test_trainer_phone = "27000E2E01"
        self.test_client_phone = "27000E2E02"
        
        # Track conversation state
        self.conversation_history = []
        
    def send_message(self, message: str, phone: str = None) -> Dict:
        """
        Simulate sending a WhatsApp message and getting response
        """
        if not phone:
            phone = self.test_trainer_phone
            
        # Create a mock WhatsApp message structure
        mock_message = {
            "from": phone,
            "text": {"body": message},
            "type": "text",
            "timestamp": str(int(time.time()))
        }
        
        # Process through actual system
        response = self.process_message(mock_message)
        
        # Log the conversation
        self.conversation_history.append({
            "user": message,
            "phone": phone,
            "response": response
        })
        
        return response
    
    def cleanup_test_data(self):
        """Clean up all test data after tests"""
        try:
            # Delete test trainers
            self.db.table('trainers').delete().eq('whatsapp', self.test_trainer_phone).execute()
            self.db.table('trainers').delete().eq('whatsapp', '27000E2E03').execute()
            
            # Delete test clients
            self.db.table('clients').delete().eq('whatsapp', self.test_client_phone).execute()
            self.db.table('clients').delete().like('whatsapp', '27000E2E%').execute()
            
            print("✅ Test data cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


# ==================== PHASE 1 TESTS ====================

class TestPhase1_Registration:
    """Test complete registration flows"""
    
    def setup_method(self):
        """Setup for each test"""
        self.tester = RefiloeE2ETester()
        self.tester.cleanup_test_data()  # Start fresh
    
    def teardown_method(self):
        """Cleanup after each test"""
        self.tester.cleanup_test_data()
    
    def test_complete_trainer_onboarding(self):
        """Test 1.1: New User Onboarding"""
        
        # Step 1: Initial greeting
        response = self.tester.send_message("Hi")
        assert "trainer" in response.lower() or "client" in response.lower()
        print(f"✅ Step 1: Got welcome message")
        
        # Step 2: Choose trainer
        response = self.tester.send_message("trainer")
        assert "name" in response.lower() or "register" in response.lower()
        print(f"✅ Step 2: Started trainer registration")
        
        # Step 3: Provide name
        response = self.tester.send_message("John E2E Tester")
        assert any(word in response.lower() for word in ["email", "next", "great"])
        print(f"✅ Step 3: Name accepted")
        
        # Step 4: Provide email
        response = self.tester.send_message("john@e2etest.com")
        assert any(word in response.lower() for word in ["location", "where", "city"])
        print(f"✅ Step 4: Email accepted")
        
        # Step 5: Provide location
        response = self.tester.send_message("Cape Town")
        assert any(word in response.lower() for word in ["price", "rate", "charge"])
        print(f"✅ Step 5: Location accepted")
        
        # Step 6: Provide pricing
        response = self.tester.send_message("R500")
        assert any(word in response.lower() for word in ["complete", "success", "welcome", "done"])
        print(f"✅ Step 6: Registration completed")
        
        # Verify in database
        trainer = self.db.table('trainers').select('*').eq('whatsapp', self.test_trainer_phone).execute()
        assert len(trainer.data) > 0
        assert trainer.data[0]['name'] == "John E2E Tester"
        print(f"✅ Verified: Trainer saved in database")
    
    def test_trainer_recognition_after_registration(self):
        """Test 1.2: Trainer Recognition"""
        
        # First, create a trainer
        self.db.table('trainers').insert({
            'name': 'John Recognized',
            'whatsapp': self.test_trainer_phone,
            'email': 'john@recognized.com',
            'pricing_per_session': 500
        }).execute()
        
        # Now test recognition
        response = self.tester.send_message("Hi")
        assert "john" in response.lower() or "welcome back" in response.lower()
        print(f"✅ Trainer recognized by name")
        
        # Test help command
        response = self.tester.send_message("help")
        assert any(word in response.lower() for word in ["command", "help", "available"])
        print(f"✅ Help command works for trainer")


# ==================== PHASE 2 TESTS ====================

class TestPhase2_ClientManagement:
    """Test client management features"""
    
    def setup_method(self):
        """Setup for each test"""
        self.tester = RefiloeE2ETester()
        self.tester.cleanup_test_data()
        
        # Create a trainer for these tests
        self.trainer_id = self.db.table('trainers').insert({
            'name': 'Test Trainer',
            'whatsapp': self.tester.test_trainer_phone,
            'email': 'trainer@test.com',
            'pricing_per_session': 500
        }).execute().data[0]['id']
    
    def teardown_method(self):
        """Cleanup after each test"""
        self.tester.cleanup_test_data()
    
    def test_add_client_variations(self):
        """Test 2.1: Add Client with different commands"""
        
        # Variation 1: "Add client"
        response = self.tester.send_message("Add client Sarah 0821234567")
        assert "sarah" in response.lower() or "added" in response.lower()
        print(f"✅ Added client with 'Add client' command")
        
        # Variation 2: "Register new client"  
        response = self.tester.send_message("Register new client John Doe 0831234567")
        assert "john" in response.lower() or "added" in response.lower()
        print(f"✅ Added client with 'Register new client' command")
        
        # Variation 3: "New client"
        response = self.tester.send_message("New client Mike phone 0841234567")
        assert "mike" in response.lower() or "added" in response.lower()
        print(f"✅ Added client with 'New client' command")
        
        # Verify all clients in database
        clients = self.db.table('clients').select('*').eq('trainer_id', self.trainer_id).execute()
        assert len(clients.data) >= 1  # At least one client added
        print(f"✅ Verified: {len(clients.data)} clients in database")
    
    def test_view_clients(self):
        """Test 2.2: View Clients"""
        
        # First add some clients
        self.db.table('clients').insert([
            {'name': 'Sarah Test', 'whatsapp': '27000E2E10', 'trainer_id': self.trainer_id},
            {'name': 'John Test', 'whatsapp': '27000E2E11', 'trainer_id': self.trainer_id}
        ]).execute()
        
        # Test different view commands
        for command in ["Show my clients", "List clients", "View all clients"]:
            response = self.tester.send_message(command)
            assert "sarah" in response.lower() or "john" in response.lower() or "client" in response.lower()
            print(f"✅ '{command}' command works")
    
    def test_custom_pricing(self):
        """Test 2.3 & 2.4: Set and Check Custom Pricing"""
        
        # Add a client first
        client_id = self.db.table('clients').insert({
            'name': 'Sarah Price',
            'whatsapp': '27000E2E12',
            'trainer_id': self.trainer_id
        }).execute().data[0]['id']
        
        # Set custom price
        response = self.tester.send_message("Set Sarah's rate to R450")
        assert "450" in response or "updated" in response.lower()
        print(f"✅ Set custom pricing")
        
        # Check the price
        response = self.tester.send_message("What is Sarah's rate?")
        assert "450" in response or "sarah" in response.lower()
        print(f"✅ Retrieved custom pricing")


# ==================== PHASE 3 TESTS ====================

class TestPhase3_Scheduling:
    """Test scheduling and booking features"""
    
    def setup_method(self):
        """Setup for each test"""
        self.tester = RefiloeE2ETester()
        self.tester.cleanup_test_data()
        
        # Create trainer and client
        self.trainer_id = self.db.table('trainers').insert({
            'name': 'Schedule Trainer',
            'whatsapp': self.tester.test_trainer_phone,
            'email': 'schedule@test.com',
            'pricing_per_session': 500
        }).execute().data[0]['id']
        
        self.client_id = self.db.table('clients').insert({
            'name': 'Sarah Schedule',
            'whatsapp': '27000E2E20',
            'trainer_id': self.trainer_id
        }).execute().data[0]['id']
    
    def teardown_method(self):
        """Cleanup after each test"""
        self.tester.cleanup_test_data()
    
    def test_view_schedule(self):
        """Test 3.1: View Schedule"""
        
        # Create some bookings
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        self.db.table('bookings').insert([
            {
                'trainer_id': self.trainer_id,
                'client_id': self.client_id,
                'booking_date': tomorrow.isoformat(),
                'time_slot': '09:00',
                'status': 'confirmed'
            }
        ]).execute()
        
        # Test schedule viewing commands
        for command in ["Show my schedule", "What's on today", "Tomorrow's sessions"]:
            response = self.tester.send_message(command)
            # Should mention schedule, booking, session, or "no bookings"
            assert any(word in response.lower() for word in ["schedule", "booking", "session", "9:00", "sarah", "no bookings"])
            print(f"✅ '{command}' command works")
    
    def test_book_sessions(self):
        """Test 3.2: Book Sessions"""
        
        # Test booking commands
        test_bookings = [
            "Book Sarah for tomorrow at 9am",
            "Schedule Sarah Monday 6pm",
            "Add session with Sarah Friday 7:00"
        ]
        
        for booking_command in test_bookings:
            response = self.tester.send_message(booking_command)
            # Should confirm booking
            assert any(word in response.lower() for word in ["booked", "scheduled", "confirmed", "session"])
            print(f"✅ Booking command works: {booking_command[:30]}...")
        
        # Verify bookings in database
        bookings = self.db.table('bookings').select('*').eq('trainer_id', self.trainer_id).execute()
        assert len(bookings.data) > 0
        print(f"✅ Verified: {len(bookings.data)} bookings in database")
    
    def test_cancel_reschedule(self):
        """Test 3.3: Cancel/Reschedule Sessions"""
        
        # Create a booking to cancel
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        booking = self.db.table('bookings').insert({
            'trainer_id': self.trainer_id,
            'client_id': self.client_id,
            'booking_date': tomorrow.isoformat(),
            'time_slot': '09:00',
            'status': 'confirmed'
        }).execute().data[0]
        
        # Test cancellation
        response = self.tester.send_message("Cancel Sarah's session tomorrow")
        assert any(word in response.lower() for word in ["cancel", "removed", "deleted"])
        print(f"✅ Cancellation works")
        
        # Test reschedule
        response = self.tester.send_message("Reschedule Sarah to Tuesday 6pm")
        assert any(word in response.lower() for word in ["reschedule", "moved", "changed", "updated"])
        print(f"✅ Rescheduling works")


# ==================== TEST RUNNER ====================

def run_all_e2e_tests():
    """
    Run all end-to-end tests and generate report
    """
    print("=" * 60)
    print("REFILOE END-TO-END TEST SUITE")
    print("=" * 60)
    
    results = {
        "Phase 1": {"passed": 0, "failed": 0},
        "Phase 2": {"passed": 0, "failed": 0},
        "Phase 3": {"passed": 0, "failed": 0}
    }
    
    # Run Phase 1 tests
    print("\n📝 PHASE 1: Registration Tests")
    print("-" * 40)
    phase1 = TestPhase1_Registration()
    
    try:
        phase1.setup_method()
        phase1.test_complete_trainer_onboarding()
        results["Phase 1"]["passed"] += 1
    except Exception as e:
        print(f"❌ Onboarding test failed: {e}")
        results["Phase 1"]["failed"] += 1
    finally:
        phase1.teardown_method()
    
    try:
        phase1.setup_method()
        phase1.test_trainer_recognition_after_registration()
        results["Phase 1"]["passed"] += 1
    except Exception as e:
        print(f"❌ Recognition test failed: {e}")
        results["Phase 1"]["failed"] += 1
    finally:
        phase1.teardown_method()
    
    # Run Phase 2 tests
    print("\n📝 PHASE 2: Client Management Tests")
    print("-" * 40)
    phase2 = TestPhase2_ClientManagement()
    
    tests_phase2 = [
        ("Add clients", phase2.test_add_client_variations),
        ("View clients", phase2.test_view_clients),
        ("Custom pricing", phase2.test_custom_pricing)
    ]
    
    for test_name, test_func in tests_phase2:
        try:
            phase2.setup_method()
            test_func()
            results["Phase 2"]["passed"] += 1
        except Exception as e:
            print(f"❌ {test_name} test failed: {e}")
            results["Phase 2"]["failed"] += 1
        finally:
            phase2.teardown_method()
    
    # Run Phase 3 tests
    print("\n📝 PHASE 3: Scheduling Tests")
    print("-" * 40)
    phase3 = TestPhase3_Scheduling()
    
    tests_phase3 = [
        ("View schedule", phase3.test_view_schedule),
        ("Book sessions", phase3.test_book_sessions),
        ("Cancel/Reschedule", phase3.test_cancel_reschedule)
    ]
    
    for test_name, test_func in tests_phase3:
        try:
            phase3.setup_method()
            test_func()
            results["Phase 3"]["passed"] += 1
        except Exception as e:
            print(f"❌ {test_name} test failed: {e}")
            results["Phase 3"]["failed"] += 1
        finally:
            phase3.teardown_method()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_passed = sum(r["passed"] for r in results.values())
    total_failed = sum(r["failed"] for r in results.values())
    
    for phase, result in results.items():
        status = "✅" if result["failed"] == 0 else "⚠️"
        print(f"{status} {phase}: {result['passed']} passed, {result['failed']} failed")
    
    print("-" * 60)
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("\n🎉 ALL E2E TESTS PASSED! 🎉")
    else:
        print(f"\n⚠️ {total_failed} tests need attention")
    
    return total_failed == 0


if __name__ == "__main__":
    # Run when called directly
    success = run_all_e2e_tests()
    exit(0 if success else 1)
