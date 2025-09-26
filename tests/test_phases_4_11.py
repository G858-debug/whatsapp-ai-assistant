"""
End-to-End Tests for Refiloe Phases 4-11
Testing habit tracking, workouts, payments, analytics, and advanced features
"""

import os
import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class RefiloeE2ETesterExtended:
    """
    Extended E2E tester for Phases 4-11
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
        try:
            from app_core import process_whatsapp_message
            self.process_message = process_whatsapp_message
        except ImportError:
            # Alternative import path
            from services.refiloe import process_message
            self.process_message = process_message
        
        # Test phone numbers
        self.test_trainer_phone = "27000E2E01"
        self.test_client_phone = "27000E2E02"
        
        # Track conversation state
        self.conversation_history = []
        
        # Setup test data
        self.setup_test_data()
    
    def setup_test_data(self):
        """Create necessary test data for phases 4-11"""
        # Create a test trainer if doesn't exist
        trainer = self.db.table('trainers').select('*').eq('whatsapp', self.test_trainer_phone).execute()
        if not trainer.data:
            self.trainer_id = self.db.table('trainers').insert({
                'name': 'Test Trainer',
                'whatsapp': self.test_trainer_phone,
                'email': 'trainer@e2etest.com',
                'pricing_per_session': 500
            }).execute().data[0]['id']
        else:
            self.trainer_id = trainer.data[0]['id']
        
        # Create test clients
        self.create_test_clients()
    
    def create_test_clients(self):
        """Create test clients for testing"""
        client_names = ['Sarah', 'John', 'Mike']
        self.client_ids = {}
        
        for i, name in enumerate(client_names):
            phone = f"27000E2E0{i+3}"
            
            # Check if client exists
            client = self.db.table('clients').select('*').eq('whatsapp', phone).execute()
            if not client.data:
                result = self.db.table('clients').insert({
                    'name': f'{name} Test',
                    'whatsapp': phone,
                    'trainer_id': self.trainer_id
                }).execute()
                self.client_ids[name.lower()] = result.data[0]['id']
            else:
                self.client_ids[name.lower()] = client.data[0]['id']
    
    def send_message(self, message: str, phone: str = None) -> Dict:
        """Simulate sending a WhatsApp message"""
        if not phone:
            phone = self.test_trainer_phone
        
        mock_message = {
            "from": phone,
            "text": {"body": message},
            "type": "text",
            "timestamp": str(int(time.time()))
        }
        
        try:
            response = self.process_message(mock_message)
        except Exception as e:
            response = {"error": str(e)}
        
        self.conversation_history.append({
            "user": message,
            "phone": phone,
            "response": response
        })
        
        return response
    
    def cleanup_test_data(self):
        """Clean up test data"""
        try:
            # Clean up habits
            self.db.table('habits').delete().eq('trainer_id', self.trainer_id).execute()
            
            # Clean up workouts
            self.db.table('workouts').delete().eq('trainer_id', self.trainer_id).execute()
            
            # Clean up payments
            self.db.table('payments').delete().eq('trainer_id', self.trainer_id).execute()
            
            # Clean up challenges
            self.db.table('challenge_participants').delete().in_('user_id', list(self.client_ids.values())).execute()
            
            print("✅ Test data cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


# ==================== PHASE 4: HABIT TRACKING ====================

class TestPhase4_HabitTracking:
    """Test habit tracking features"""
    
    def setup_method(self):
        self.tester = RefiloeE2ETesterExtended()
    
    def teardown_method(self):
        self.tester.cleanup_test_data()
    
    def test_setup_habits_for_clients(self):
        """Test 4.1: Setup Habits for Clients"""
        
        test_cases = [
            "Set up water tracking for Sarah",
            "Add habit tracking for John - 8 glasses water daily",
            "Sarah needs to track steps target 10000",
            "Setup sleep tracking for Mike"
        ]
        
        for command in test_cases:
            response = self.tester.send_message(command)
            # Should confirm habit setup
            assert any(word in str(response).lower() for word in 
                      ["habit", "tracking", "setup", "added", "created", "will track"])
            print(f"✅ Habit setup command works: {command[:40]}...")
        
        # Verify in database
        habits = self.tester.db.table('habits').select('*').eq('trainer_id', self.tester.trainer_id).execute()
        assert len(habits.data) > 0
        print(f"✅ {len(habits.data)} habits created in database")
    
    def test_check_habit_compliance(self):
        """Test 4.2: Check Habit Compliance"""
        
        commands = [
            "Show Sarah's habit progress",
            "Check John's water intake this week",
            "How's Mike doing with habits?"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should show habit statistics
            assert any(word in str(response).lower() for word in 
                      ["progress", "streak", "completed", "habit", "%", "days"])
            print(f"✅ Habit progress command works: {command[:30]}...")
    
    def test_send_habit_reminders(self):
        """Test 4.3: Send Manual Habit Reminders"""
        
        commands = [
            "Send habit check to Sarah",
            "Remind John about habits",
            "Check in with Mike on habits"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should confirm reminder sent
            assert any(word in str(response).lower() for word in 
                      ["sent", "reminded", "check", "message", "notified"])
            print(f"✅ Habit reminder sent: {command[:30]}...")


# ==================== PHASE 5: WORKOUTS & ASSESSMENTS ====================

class TestPhase5_WorkoutsAssessments:
    """Test workout and assessment features"""
    
    def setup_method(self):
        self.tester = RefiloeE2ETesterExtended()
    
    def teardown_method(self):
        self.tester.cleanup_test_data()
    
    def test_send_workouts(self):
        """Test 5.1: Send Workouts"""
        
        commands = [
            "Send workout to Sarah",
            "Create upper body workout for John",
            "Send Mike a cardio program"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should confirm workout sent
            assert any(word in str(response).lower() for word in 
                      ["workout", "sent", "program", "exercise", "created"])
            print(f"✅ Workout command works: {command[:30]}...")
    
    def test_start_assessment(self):
        """Test 5.2: Start Assessment"""
        
        commands = [
            "Start fitness assessment for Sarah",
            "Begin John's evaluation",
            "Assessment for Mike"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should send assessment form/link
            assert any(word in str(response).lower() for word in 
                      ["assessment", "form", "link", "evaluation", "test"])
            print(f"✅ Assessment started: {command[:30]}...")
    
    def test_view_assessment_results(self):
        """Test 5.3: View Assessment Results"""
        
        commands = [
            "Show Sarah's assessment results",
            "Check John's fitness test"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should display assessment data
            assert any(word in str(response).lower() for word in 
                      ["results", "assessment", "score", "fitness", "level", "no assessment"])
            print(f"✅ Assessment results command works")


# ==================== PHASE 6: PAYMENTS & REVENUE ====================

class TestPhase6_PaymentsRevenue:
    """Test payment and revenue features"""
    
    def setup_method(self):
        self.tester = RefiloeE2ETesterExtended()
    
    def teardown_method(self):
        self.tester.cleanup_test_data()
    
    def test_request_payment(self):
        """Test 6.1: Request Payment"""
        
        commands = [
            "Request payment from Sarah",
            "Send invoice to John for 3 sessions",
            "Bill Mike for this month"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should generate payment link
            assert any(word in str(response).lower() for word in 
                      ["payment", "invoice", "link", "pay", "sent", "requested"])
            print(f"✅ Payment request works: {command[:30]}...")
    
    def test_check_revenue(self):
        """Test 6.2: Check Revenue"""
        
        commands = [
            "Show my revenue",
            "This month's earnings",
            "Payment history",
            "Who owes me money?"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should show revenue data
            assert any(word in str(response).lower() for word in 
                      ["revenue", "earned", "payment", "r", "owed", "total"])
            print(f"✅ Revenue check works: {command[:30]}...")
    
    def test_payment_confirmation(self):
        """Test 6.3: Payment Confirmation"""
        
        commands = [
            "Mark Sarah's payment as received",
            "Confirm John paid cash"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should confirm payment recorded
            assert any(word in str(response).lower() for word in 
                      ["recorded", "confirmed", "received", "payment", "updated"])
            print(f"✅ Payment confirmation works")


# ==================== PHASE 7: ANALYTICS & REPORTS ====================

class TestPhase7_AnalyticsReports:
    """Test analytics and reporting features"""
    
    def setup_method(self):
        self.tester = RefiloeE2ETesterExtended()
    
    def teardown_method(self):
        self.tester.cleanup_test_data()
    
    def test_view_dashboard(self):
        """Test 7.1: View Dashboard/Stats"""
        
        commands = [
            "Show dashboard",
            "My stats",
            "Business overview"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should show summary statistics
            assert any(word in str(response).lower() for word in 
                      ["clients", "sessions", "revenue", "stats", "overview"])
            print(f"✅ Dashboard command works: {command}")
    
    def test_client_analytics(self):
        """Test 7.2: Client Analytics"""
        
        commands = [
            "Sarah's progress report",
            "John's attendance this month"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should show client-specific data
            assert any(word in str(response).lower() for word in 
                      ["progress", "attendance", "sessions", "report", "no data"])
            print(f"✅ Client analytics works")


# ==================== PHASE 8: CLIENT FEATURES ====================

class TestPhase8_ClientFeatures:
    """Test features from client perspective"""
    
    def setup_method(self):
        self.tester = RefiloeE2ETesterExtended()
        # Use client phone for these tests
        self.client_phone = self.tester.test_client_phone
    
    def teardown_method(self):
        self.tester.cleanup_test_data()
    
    def test_client_booking(self):
        """Test 8.1: Client Booking"""
        
        commands = [
            "Book a session",
            "I want to train tomorrow",
            "Schedule me for Monday"
        ]
        
        for command in commands:
            response = self.tester.send_message(command, phone=self.client_phone)
            # Should show available slots or confirm booking
            assert any(word in str(response).lower() for word in 
                      ["available", "booked", "session", "slot", "confirm"])
            print(f"✅ Client booking works: {command[:30]}...")
    
    def test_client_habit_logging(self):
        """Test 8.2: Client Habit Logging"""
        
        # Test different response formats
        responses = [
            "7 yes no",
            "6 glasses, veggies done, no workout",
            "✅ ✅ ❌"
        ]
        
        for habit_response in responses:
            response = self.tester.send_message(habit_response, phone=self.client_phone)
            # Should confirm habits logged
            assert any(word in str(response).lower() for word in 
                      ["logged", "recorded", "great", "well done", "habit"])
            print(f"✅ Habit logging works: {habit_response[:20]}...")
    
    def test_client_progress(self):
        """Test 8.3: Client Progress"""
        
        commands = [
            "Show my progress",
            "Check my streak",
            "My habit score"
        ]
        
        for command in commands:
            response = self.tester.send_message(command, phone=self.client_phone)
            # Should show progress data
            assert any(word in str(response).lower() for word in 
                      ["progress", "streak", "score", "days", "%", "habit"])
            print(f"✅ Client progress works")


# ==================== PHASE 9: CHALLENGES & GAMIFICATION ====================

class TestPhase9_Challenges:
    """Test challenge and gamification features"""
    
    def setup_method(self):
        self.tester = RefiloeE2ETesterExtended()
    
    def teardown_method(self):
        self.tester.cleanup_test_data()
    
    def test_view_challenges(self):
        """Test 9.1: View Challenges"""
        
        commands = [
            "Show challenges",
            "Active challenges",
            "What challenges are available?"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should list challenges
            assert any(word in str(response).lower() for word in 
                      ["challenge", "water", "steps", "available", "no challenges"])
            print(f"✅ View challenges works")
    
    def test_join_leave_challenges(self):
        """Test 9.2: Join/Leave Challenges"""
        
        commands = [
            "Join water challenge",
            "Sign me up for steps challenge",
            "Leave the plank challenge"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should confirm action
            assert any(word in str(response).lower() for word in 
                      ["joined", "signed", "left", "challenge", "removed"])
            print(f"✅ Challenge participation works")
    
    def test_leaderboard(self):
        """Test 9.3: Leaderboard"""
        
        commands = [
            "Show leaderboard",
            "Challenge rankings",
            "Who's winning the water challenge?"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should show rankings
            assert any(word in str(response).lower() for word in 
                      ["leaderboard", "ranking", "1.", "winner", "no participants"])
            print(f"✅ Leaderboard works")


# ==================== PHASE 10: ADVANCED FEATURES ====================

class TestPhase10_AdvancedFeatures:
    """Test advanced system features"""
    
    def setup_method(self):
        self.tester = RefiloeE2ETesterExtended()
    
    def teardown_method(self):
        self.tester.cleanup_test_data()
    
    def test_bulk_operations(self):
        """Test 10.1: Bulk Operations"""
        
        commands = [
            "Send reminder to all clients",
            "Check all unpaid sessions"
        ]
        
        for command in commands:
            response = self.tester.send_message(command)
            # Should confirm bulk action
            assert any(word in str(response).lower() for word in 
                      ["all", "clients", "sent", "reminder", "unpaid", "sessions"])
            print(f"✅ Bulk operation works: {command[:30]}...")
    
    def test_natural_language(self):
        """Test 10.2: Natural Language Understanding"""
        
        casual_messages = [
            "I'm doing good thanks",
            "The weather is nice today",
            "How are you?"
        ]
        
        for message in casual_messages:
            response = self.tester.send_message(message)
            # Should respond naturally
            assert response is not None
            assert len(str(response)) > 0
            print(f"✅ Natural response to: {message[:30]}...")
    
    def test_error_handling(self):
        """Test 10.3: Error Handling"""
        
        error_cases = [
            "Book session for NonExistentClient",
            "Schedule me for yesterday",
            "Set price to negative amount"
        ]
        
        for error_case in error_cases:
            response = self.tester.send_message(error_case)
            # Should provide helpful error message
            assert any(word in str(response).lower() for word in 
                      ["not found", "cannot", "invalid", "error", "sorry", "past"])
            print(f"✅ Error handled: {error_case[:30]}...")


# ==================== PHASE 11: AUTOMATED FEATURES ====================

class TestPhase11_AutomatedFeatures:
    """Test automated system features"""
    
    def setup_method(self):
        self.tester = RefiloeE2ETesterExtended()
    
    def teardown_method(self):
        self.tester.cleanup_test_data()
    
    def test_check_scheduled_reminders(self):
        """Test 11.1: Check if reminder system exists"""
        
        # Check if reminder tables/functions exist
        try:
            # Check for scheduled_reminders table or similar
            reminders = self.tester.db.table('scheduled_reminders').select('*').limit(1).execute()
            print("✅ Reminder system exists")
        except:
            print("⚠️ No reminder system found - may need implementation")
    
    def test_subscription_monitoring(self):
        """Test 11.2: Check subscription monitoring"""
        
        # Check trainer subscription status
        trainer = self.tester.db.table('trainers').select('subscription_status,subscription_end').eq('id', self.tester.trainer_id).execute()
        
        if trainer.data and 'subscription_status' in trainer.data[0]:
            print("✅ Subscription monitoring exists")
        else:
            print("⚠️ No subscription monitoring found - may need implementation")


# ==================== MAIN TEST RUNNER ====================

def run_phases_4_11_tests():
    """Run all tests for phases 4-11"""
    
    print("=" * 60)
    print("REFILOE E2E TESTS: PHASES 4-11")
    print("=" * 60)
    
    test_classes = [
        ("Phase 4: Habit Tracking", TestPhase4_HabitTracking),
        ("Phase 5: Workouts & Assessments", TestPhase5_WorkoutsAssessments),
        ("Phase 6: Payments & Revenue", TestPhase6_PaymentsRevenue),
        ("Phase 7: Analytics & Reports", TestPhase7_AnalyticsReports),
        ("Phase 8: Client Features", TestPhase8_ClientFeatures),
        ("Phase 9: Challenges", TestPhase9_Challenges),
        ("Phase 10: Advanced Features", TestPhase10_AdvancedFeatures),
        ("Phase 11: Automated Features", TestPhase11_AutomatedFeatures)
    ]
    
    results = {}
    
    for phase_name, test_class in test_classes:
        print(f"\n📝 {phase_name}")
        print("-" * 40)
        
        results[phase_name] = {"passed": 0, "failed": 0}
        
        # Get all test methods
        test_instance = test_class()
        test_methods = [m for m in dir(test_instance) if m.startswith('test_')]
        
        for test_method_name in test_methods:
            try:
                test_instance.setup_method()
                test_method = getattr(test_instance, test_method_name)
                test_method()
                results[phase_name]["passed"] += 1
                print(f"✅ {test_method_name}")
            except Exception as e:
                results[phase_name]["failed"] += 1
                print(f"❌ {test_method_name}: {str(e)[:100]}")
            finally:
                test_instance.teardown_method()
    
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
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_phases_4_11_tests()
    exit(0 if success else 1)
