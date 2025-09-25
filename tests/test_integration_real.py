#!/usr/bin/env python3
"""
Integration Test Setup for Refiloe
Tests against real test database and API
"""

import os
import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestConfig:
    """Configuration for integration tests"""
    
    # Test environment variables (set these in GitHub Secrets with TEST_ prefix)
    TEST_SUPABASE_URL = os.getenv('TEST_SUPABASE_URL') or os.getenv('SUPABASE_URL')
    TEST_SUPABASE_KEY = os.getenv('TEST_SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')
    TEST_ANTHROPIC_KEY = os.getenv('TEST_ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    
    # Test phone numbers (use numbers that won't receive real messages)
    TEST_TRAINER_PHONE = "27000000001"  # Test trainer
    TEST_CLIENT_PHONE = "27000000002"   # Test client
    
    # Test data prefix to identify test records
    TEST_PREFIX = "TEST_"
    
    # Cleanup settings
    CLEANUP_AFTER_TESTS = True
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if test environment is properly configured"""
        return all([
            cls.TEST_SUPABASE_URL,
            cls.TEST_SUPABASE_KEY,
            cls.TEST_ANTHROPIC_KEY
        ])


class IntegrationTestBase:
    """Base class for integration tests"""
    
    @classmethod
    def setup_class(cls):
        """Set up test class - run once before all tests"""
        if not TestConfig.is_configured():
            pytest.skip("Test environment not configured. Set TEST_SUPABASE_URL, TEST_SUPABASE_KEY, and TEST_ANTHROPIC_API_KEY")
        
        # Import here to avoid import errors if not configured
        from supabase import create_client
        from anthropic import Anthropic
        
        # Create real clients
        cls.supabase = create_client(
            TestConfig.TEST_SUPABASE_URL,
            TestConfig.TEST_SUPABASE_KEY
        )
        cls.anthropic = Anthropic(api_key=TestConfig.TEST_ANTHROPIC_KEY)
        
        # Track created test data for cleanup
        cls.test_trainers = []
        cls.test_clients = []
        cls.test_bookings = []
        
        logger.info("Integration test setup complete")
    
    @classmethod
    def teardown_class(cls):
        """Clean up after all tests"""
        if TestConfig.CLEANUP_AFTER_TESTS:
            cls.cleanup_test_data()
    
    @classmethod
    def cleanup_test_data(cls):
        """Remove all test data from database"""
        logger.info("Cleaning up test data...")
        
        try:
            # Clean up bookings
            for booking_id in cls.test_bookings:
                cls.supabase.table('bookings').delete().eq('id', booking_id).execute()
            
            # Clean up clients
            for client_id in cls.test_clients:
                cls.supabase.table('clients').delete().eq('id', client_id).execute()
            
            # Clean up trainers
            for trainer_id in cls.test_trainers:
                cls.supabase.table('trainers').delete().eq('id', trainer_id).execute()
            
            # Also clean up by test prefix
            cls.supabase.table('trainers').delete().like('name', f'{TestConfig.TEST_PREFIX}%').execute()
            cls.supabase.table('clients').delete().like('name', f'{TestConfig.TEST_PREFIX}%').execute()
            
            # Clean up test phone numbers
            cls.supabase.table('trainers').delete().in_('whatsapp', [
                TestConfig.TEST_TRAINER_PHONE,
                TestConfig.TEST_CLIENT_PHONE
            ]).execute()
            
            logger.info("Test data cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error cleaning up test data: {e}")
    
    def create_test_trainer(self, name: str = None) -> Dict:
        """Create a test trainer in the real database"""
        trainer_name = name or f"{TestConfig.TEST_PREFIX}Trainer_{datetime.now().timestamp()}"
        
        trainer_data = {
            "name": trainer_name,
            "whatsapp": TestConfig.TEST_TRAINER_PHONE,
            "email": f"test_{datetime.now().timestamp()}@test.com",
            "pricing_per_session": 500,
            "location": "Test Location",
            "status": "active"
        }
        
        result = self.supabase.table('trainers').insert(trainer_data).execute()
        
        if result.data:
            trainer = result.data[0]
            self.test_trainers.append(trainer['id'])
            logger.info(f"Created test trainer: {trainer['id']}")
            return trainer
        
        raise Exception("Failed to create test trainer")
    
    def create_test_client(self, trainer_id: int, name: str = None) -> Dict:
        """Create a test client in the real database"""
        client_name = name or f"{TestConfig.TEST_PREFIX}Client_{datetime.now().timestamp()}"
        
        client_data = {
            "name": client_name,
            "whatsapp": TestConfig.TEST_CLIENT_PHONE,
            "trainer_id": trainer_id,
            "custom_rate": 450,
            "status": "active"
        }
        
        result = self.supabase.table('clients').insert(client_data).execute()
        
        if result.data:
            client = result.data[0]
            self.test_clients.append(client['id'])
            logger.info(f"Created test client: {client['id']}")
            return client
        
        raise Exception("Failed to create test client")
    
    def call_refiloe_api(self, message: str, phone: str) -> Dict:
        """Make a real API call to Refiloe"""
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from services.ai_intent_handler import AIIntentHandler
        
        # Create real handler with real connections
        handler = AIIntentHandler()
        
        # Process the message
        response = handler.generate_smart_response(message, phone)
        
        return response
    
    def test_real_ai_response(self, prompt: str) -> str:
        """Test getting a real response from Claude"""
        try:
            response = self.anthropic.messages.create(
                model="claude-3-sonnet-20241022",
                max_tokens=100,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            return None


# ========== ACTUAL INTEGRATION TESTS ==========

class TestRealTrainerRegistration(IntegrationTestBase):
    """Test real trainer registration flow"""
    
    def test_complete_registration_flow(self):
        """Test the complete trainer registration process with real API"""
        
        # Start registration
        response = self.call_refiloe_api(
            "Hi, I want to register as a trainer",
            TestConfig.TEST_TRAINER_PHONE
        )
        
        assert response.get('success') == True
        assert 'register' in response.get('message', '').lower()
        
        # Provide name
        response = self.call_refiloe_api(
            f"{TestConfig.TEST_PREFIX}John Doe",
            TestConfig.TEST_TRAINER_PHONE
        )
        
        assert response.get('success') == True
        
        # Continue through registration steps...
        # (Add more steps as needed)
    
    def test_trainer_exists_in_database(self):
        """Verify trainer is actually saved in database"""
        
        # Create a trainer
        trainer = self.create_test_trainer("TEST_Integration_Trainer")
        
        # Query the database directly
        result = self.supabase.table('trainers').select('*').eq('id', trainer['id']).execute()
        
        assert len(result.data) == 1
        assert result.data[0]['name'] == "TEST_Integration_Trainer"
        assert result.data[0]['whatsapp'] == TestConfig.TEST_TRAINER_PHONE


class TestRealClientManagement(IntegrationTestBase):
    """Test real client management features"""
    
    def test_add_and_retrieve_client(self):
        """Test adding a client and retrieving client list"""
        
        # First create a trainer
        trainer = self.create_test_trainer()
        
        # Add a client
        client = self.create_test_client(trainer['id'], "TEST_Sarah Johnson")
        
        # Verify client exists in database
        result = self.supabase.table('clients').select('*').eq('id', client['id']).execute()
        
        assert len(result.data) == 1
        assert result.data[0]['name'] == "TEST_Sarah Johnson"
        
        # Test retrieving through API
        response = self.call_refiloe_api(
            "Show my clients",
            TestConfig.TEST_TRAINER_PHONE
        )
        
        # Check if response mentions clients (may need adjustment based on actual response)
        assert response.get('success') == True


class TestRealScheduling(IntegrationTestBase):
    """Test real scheduling functionality"""
    
    def test_create_and_view_booking(self):
        """Test creating and viewing bookings"""
        
        # Setup trainer and client
        trainer = self.create_test_trainer()
        client = self.create_test_client(trainer['id'])
        
        # Create a booking directly in database
        booking_data = {
            "trainer_id": trainer['id'],
            "client_id": client['id'],
            "booking_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "time_slot": "09:00",
            "status": "confirmed"
        }
        
        result = self.supabase.table('bookings').insert(booking_data).execute()
        
        if result.data:
            booking = result.data[0]
            self.test_bookings.append(booking['id'])
            
            # Verify booking exists
            check = self.supabase.table('bookings').select('*').eq('id', booking['id']).execute()
            assert len(check.data) == 1


class TestRealAIResponses(IntegrationTestBase):
    """Test real AI responses"""
    
    def test_ai_understands_context(self):
        """Test that AI provides contextual responses"""
        
        # Test a simple query
        response = self.test_real_ai_response(
            "If I'm a personal trainer with 3 clients, how many sessions would I have in a week if each client trains twice?"
        )
        
        assert response is not None
        assert '6' in response or 'six' in response.lower()
    
    def test_ai_handles_south_african_context(self):
        """Test AI understanding of South African context"""
        
        response = self.test_real_ai_response(
            "Convert R500 per session to approximate USD (use rough estimate)"
        )
        
        assert response is not None
        # Should mention dollars or USD in response


# ========== GITHUB ACTIONS WORKFLOW UPDATE ==========

def create_integration_test_workflow():
    """Create a GitHub Actions workflow for integration tests"""
    
    workflow = """# .github/workflows/integration_tests.yml
name: Integration Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    env:
      # Use separate test database/API keys
      TEST_SUPABASE_URL: ${{ secrets.TEST_SUPABASE_URL }}
      TEST_SUPABASE_SERVICE_KEY: ${{ secrets.TEST_SUPABASE_SERVICE_KEY }}
      TEST_ANTHROPIC_API_KEY: ${{ secrets.TEST_ANTHROPIC_API_KEY }}
      
      # Fallback to production (be careful!)
      SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
      SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run integration tests
      run: |
        echo "Running integration tests against real test database..."
        python -m pytest tests/test_integration.py -v --tb=short
    
    - name: Cleanup test data
      if: always()
      run: |
        python -c "
from tests.test_integration import IntegrationTestBase
base = IntegrationTestBase()
base.setup_class()
base.cleanup_test_data()
        " || echo "Cleanup completed"
"""
    
    return workflow


if __name__ == "__main__":
    print("Integration Test Setup")
    print("=" * 50)
    print("\nThis script sets up real integration tests for Refiloe")
    print("\n1. Save this as: tests/test_integration.py")
    print("2. Set up test environment variables:")
    print("   - TEST_SUPABASE_URL")
    print("   - TEST_SUPABASE_SERVICE_KEY") 
    print("   - TEST_ANTHROPIC_API_KEY")
    print("\n3. Run: python -m pytest tests/test_integration.py -v")
    print("\nNote: Tests will use REAL API calls and database operations!")
    print("Consider using a separate test database to avoid affecting production data.")
