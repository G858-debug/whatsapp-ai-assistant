"""
Real Integration Tests for Refiloe
Tests with actual database and API connections
"""

import os
import pytest
from datetime import datetime, timedelta
import time

# Only run if properly configured
SKIP_INTEGRATION = not all([
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY'),
    os.getenv('ANTHROPIC_API_KEY')
])

@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration test environment not configured")
class TestRealIntegration:
    """Test with real connections"""
    
    @classmethod
    def setup_class(cls):
        """Setup real connections"""
        from supabase import create_client
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Use TEST_ prefixed vars if available, otherwise use regular ones
        url = os.getenv('TEST_SUPABASE_URL') or os.getenv('SUPABASE_URL')
        key = os.getenv('TEST_SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')
        
        cls.db = create_client(url, key)
        cls.test_phone = "27000TEST01"  # Phone that won't receive real messages
        cls.created_ids = []
    
    @classmethod
    def teardown_class(cls):
        """Clean up test data"""
        # Clean up any test data created
        for trainer_id in cls.created_ids:
            cls.db.table('trainers').delete().eq('id', trainer_id).execute()
        
        # Clean up by phone number
        cls.db.table('trainers').delete().eq('whatsapp', cls.test_phone).execute()
        cls.db.table('clients').delete().eq('whatsapp', '27000TEST02').execute()
    
    def test_trainer_registration_database(self):
        """Test that trainer registration actually saves to database"""
        from services.registration.trainer_registration import TrainerRegistrationHandler
        
        handler = TrainerRegistrationHandler()
        
        # Register a test trainer
        trainer_data = {
            'name': 'TEST_Integration_Trainer',
            'whatsapp': self.test_phone,
            'email': 'test@integration.com',
            'pricing': 'R500'
        }
        
        # Call the actual registration method
        result = handler.complete_registration(trainer_data, self.test_phone)
        
        # Verify it's in the database
        check = self.db.table('trainers').select('*').eq('whatsapp', self.test_phone).execute()
        
        assert len(check.data) > 0
        assert check.data[0]['name'] == 'TEST_Integration_Trainer'
        
        # Track for cleanup
        if check.data:
            self.created_ids.append(check.data[0]['id'])
    
    def test_client_management_real(self):
        """Test adding and viewing clients with real database"""
        
        # First create a trainer
        trainer_result = self.db.table('trainers').insert({
            'name': 'TEST_Trainer',
            'whatsapp': self.test_phone,
            'email': 'trainer@test.com',
            'pricing_per_session': 500
        }).execute()
        
        trainer_id = trainer_result.data[0]['id']
        self.created_ids.append(trainer_id)
        
        # Add a client
        client_result = self.db.table('clients').insert({
            'name': 'TEST_Client',
            'whatsapp': '27000TEST02',
            'trainer_id': trainer_id
        }).execute()
        
        # Verify relationship
        clients = self.db.table('clients').select('*').eq('trainer_id', trainer_id).execute()
        
        assert len(clients.data) == 1
        assert clients.data[0]['name'] == 'TEST_Client'
    
    def test_booking_system_real(self):
        """Test the booking system with real database"""
        
        # Setup trainer and client (reuse from previous test or create new)
        trainer = self.db.table('trainers').select('*').eq('whatsapp', self.test_phone).execute()
        
        if not trainer.data:
            # Create if doesn't exist
            trainer_result = self.db.table('trainers').insert({
                'name': 'TEST_Booking_Trainer',
                'whatsapp': self.test_phone,
                'email': 'booking@test.com',
                'pricing_per_session': 500
            }).execute()
            trainer_id = trainer_result.data[0]['id']
            self.created_ids.append(trainer_id)
        else:
            trainer_id = trainer.data[0]['id']
        
        # Create a booking
        tomorrow = datetime.now() + timedelta(days=1)
        booking = self.db.table('bookings').insert({
            'trainer_id': trainer_id,
            'client_id': None,  # Can be None for test
            'booking_date': tomorrow.date().isoformat(),
            'time_slot': '09:00',
            'status': 'confirmed'
        }).execute()
        
        # Verify booking exists
        assert booking.data is not None
        assert len(booking.data) > 0
        
        # Clean up booking
        if booking.data:
            self.db.table('bookings').delete().eq('id', booking.data[0]['id']).execute()
    
    def test_ai_integration(self):
        """Test that AI handler works with real Claude API"""
        from services.ai_intent_handler import AIIntentHandler
        
        handler = AIIntentHandler()
        
        # Test a simple query (this will use real API tokens!)
        response = handler.generate_smart_response(
            "What is 2 plus 2?",
            self.test_phone
        )
        
        # Should get some response
        assert response is not None
        
        # Note: Be careful with this test as it uses real API credits!
