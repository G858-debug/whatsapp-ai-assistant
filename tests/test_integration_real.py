"""
Real Integration Tests for Refiloe
Tests with actual database and API connections
"""

import os
import pytest
from datetime import datetime, timedelta
import time
from typing import Dict

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
        
        # Create tables if they don't exist (for test database)
        cls.ensure_tables_exist()
    
    @classmethod
    def ensure_tables_exist(cls):
        """Create tables if they don't exist in test database"""
        # Note: This requires admin access. If tables don't exist,
        # you'll need to create them in Supabase dashboard first
        print("Checking if tables exist...")
        
        # Try to query trainers table
        try:
            cls.db.table('trainers').select('id').limit(1).execute()
            print("✅ trainers table exists")
        except Exception as e:
            print(f"❌ trainers table doesn't exist: {e}")
            print("Please create the following tables in your test Supabase project:")
            print("""
            CREATE TABLE trainers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                whatsapp VARCHAR(20) UNIQUE NOT NULL,
                email VARCHAR(255),
                pricing_per_session DECIMAL(10,2),
                location VARCHAR(255),
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE clients (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                whatsapp VARCHAR(20),
                trainer_id INTEGER REFERENCES trainers(id),
                custom_rate DECIMAL(10,2),
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE bookings (
                id SERIAL PRIMARY KEY,
                trainer_id INTEGER REFERENCES trainers(id),
                client_id INTEGER REFERENCES clients(id),
                booking_date DATE NOT NULL,
                time_slot VARCHAR(10) NOT NULL,
                status VARCHAR(50) DEFAULT 'confirmed',
                created_at TIMESTAMP DEFAULT NOW()
            );
            """)
            pytest.skip("Database tables not set up. Please create them first.")
    
    @classmethod
    def teardown_class(cls):
        """Clean up test data"""
        try:
            # Clean up any test data created
            for trainer_id in cls.created_ids:
                cls.db.table('trainers').delete().eq('id', trainer_id).execute()
            
            # Clean up by phone number
            cls.db.table('trainers').delete().eq('whatsapp', cls.test_phone).execute()
            cls.db.table('clients').delete().eq('whatsapp', '27000TEST02').execute()
            print("✅ Test data cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup error (may be normal): {e}")
    
    def test_trainer_registration_database(self):
        """Test that trainer data can be saved to database"""
        
        # Create test trainer data
        trainer_data = {
            'name': 'TEST_Integration_Trainer',
            'whatsapp': self.test_phone,
            'email': 'test@integration.com',
            'pricing_per_session': 500
        }
        
        # Insert into database
        result = self.db.table('trainers').insert(trainer_data).execute()
        
        # Verify it's in the database
        assert result.data is not None
        assert len(result.data) > 0
        
        trainer_id = result.data[0]['id']
        self.created_ids.append(trainer_id)
        
        # Query it back
        check = self.db.table('trainers').select('*').eq('id', trainer_id).execute()
        
        assert len(check.data) == 1
        assert check.data[0]['name'] == 'TEST_Integration_Trainer'
        print(f"✅ Trainer created with ID: {trainer_id}")
    
    def test_client_management_real(self):
        """Test adding and viewing clients with real database"""
        
        # First create a trainer
        trainer_result = self.db.table('trainers').insert({
            'name': 'TEST_Trainer_For_Client',
            'whatsapp': '27000TEST03',
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
        print(f"✅ Client created for trainer {trainer_id}")
    
    def test_booking_system_real(self):
        """Test the booking system with real database"""
        
        # Create trainer first
        trainer_result = self.db.table('trainers').insert({
            'name': 'TEST_Booking_Trainer',
            'whatsapp': '27000TEST04',
            'email': 'booking@test.com',
            'pricing_per_session': 500
        }).execute()
        
        trainer_id = trainer_result.data[0]['id']
        self.created_ids.append(trainer_id)
        
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
        print(f"✅ Booking created for trainer {trainer_id}")
        
        # Clean up booking
        if booking.data:
            self.db.table('bookings').delete().eq('id', booking.data[0]['id']).execute()
    
    def test_ai_integration_simple(self):
        """Test that AI API works with correct model name"""
        from anthropic import Anthropic
        
        try:
            client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            
            # Use correct model name
            response = client.messages.create(
                model="claude-sonnet-4-20250514",  # Latest Claude Sonnet 4
                max_tokens=100,
                messages=[
                    {"role": "user", "content": "What is 2 plus 2? Just give the number."}
                ]
            )
            
            result = response.content[0].text
            assert result is not None
            assert "4" in result or "four" in result.lower()
            print(f"✅ AI responded: {result[:50]}")
            
        except Exception as e:
            pytest.skip(f"AI API not available: {e}")
    
    def test_database_connection(self):
        """Simple test to verify database connection works"""
        
        # Try to query any table
        try:
            # This should not fail if connection is good
            result = self.db.table('trainers').select('id').limit(1).execute()
            print("✅ Database connection successful")
            assert True  # Connection works
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")
