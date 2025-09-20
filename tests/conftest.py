# tests/conftest.py
"""
Pytest configuration and shared fixtures for all tests
"""

import pytest
import os
import sys
from unittest.mock import Mock, MagicMock
from datetime import datetime
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global flag to control mock vs real testing
USE_REAL_CONNECTIONS = os.environ.get('USE_REAL_CONNECTIONS', 'true').lower() == 'true'


@pytest.fixture(scope="session")
def test_config():
    """Create a test configuration object"""
    config = Mock()
    config.TIMEZONE = 'Africa/Johannesburg'
    config.ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', 'test-key')
    config.WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN', 'test-token')
    config.WHATSAPP_PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID', 'test-phone-id')
    config.SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://test.supabase.co')
    config.SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', 'test-anon-key')
    config.SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', 'test-service-key')
    config.SENDER_EMAIL = 'test@refiloe.ai'
    config.PAYMENT_SUCCESS_URL = 'https://test.refiloe.ai/success'
    config.PAYMENT_CANCEL_URL = 'https://test.refiloe.ai/cancel'
    return config


@pytest.fixture(scope="function")
def mock_db():
    """Create either real or mock database client based on environment"""
    if USE_REAL_CONNECTIONS:
        # Try to use real database
        try:
            from supabase import create_client
            url = os.environ.get('SUPABASE_URL')
            key = os.environ.get('SUPABASE_SERVICE_KEY')
            
            if url and key:
                print("✅ Using REAL database connection for testing")
                return create_client(url, key)
        except Exception as e:
            print(f"⚠️ Could not connect to real database: {e}")
    
    # Fall back to mock
    print("📦 Using MOCK database for testing")
    db = Mock()
    
    # Setup common database responses
    db.table.return_value.select.return_value = db
    db.table.return_value.insert.return_value = db
    db.table.return_value.update.return_value = db
    db.table.return_value.delete.return_value = db
    db.eq.return_value = db
    db.single.return_value = db
    db.execute.return_value.data = []
    
    return db


@pytest.fixture(scope="function")
def real_db():
    """Force real database connection for specific tests"""
    from supabase import create_client
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    
    if url and key:
        return create_client(url, key)
    else:
        pytest.skip("Real database credentials not available")


@pytest.fixture(scope="function")
def real_validators():
    """Get real validator instance"""
    from utils.validators import Validators
    return Validators()


@pytest.fixture(scope="function")
def real_ai_handler(real_db):
    """Get real AI handler with actual database"""
    from services.ai_intent_handler import AIIntentHandler
    return AIIntentHandler(real_db)


@pytest.fixture(scope="function")
def real_trainer_handler(real_db):
    """Get real trainer registration handler"""
    from services.registration.trainer_registration import TrainerRegistrationHandler
    return TrainerRegistrationHandler(real_db)


@pytest.fixture(scope="function")
def mock_whatsapp():
    """Create a mock WhatsApp service"""
    whatsapp = Mock()
    whatsapp.send_message.return_value = {'success': True, 'message_id': 'test-123'}
    whatsapp.send_template.return_value = {'success': True, 'message_id': 'test-456'}
    return whatsapp


@pytest.fixture(scope="function")
def test_trainer_data():
    """Sample trainer data for testing"""
    return {
        'id': 'trainer-123',
        'name': 'John Smith',
        'first_name': 'John',
        'last_name': 'Smith',
        'business_name': 'FitLife PT',
        'email': 'john@fitlife.co.za',
        'whatsapp': '27731863036',
        'specialization': 'Weight loss and strength training',
        'years_experience': 5,
        'location': 'Sandton, Johannesburg',
        'pricing_per_session': 450,  # Numeric, not string
        'status': 'active',
        'created_at': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
    }


@pytest.fixture(scope="function")
def test_client_data():
    """Sample client data for testing"""
    return {
        'id': 'client-456',
        'name': 'Sarah Johnson',
        'first_name': 'Sarah',
        'last_name': 'Johnson',
        'email': 'sarah@example.com',
        'whatsapp': '27821234567',
        'trainer_id': 'trainer-123',
        'custom_rate': None,
        'sessions_remaining': 10,
        'status': 'active',
        'created_at': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
    }


@pytest.fixture(scope="function")
def test_booking_data():
    """Sample booking data for testing"""
    return {
        'id': 'booking-789',
        'trainer_id': 'trainer-123',
        'client_id': 'client-456',
        'session_date': '2024-01-20',
        'session_time': '09:00',
        'session_type': 'one_on_one',
        'status': 'confirmed',
        'notes': 'Focus on upper body',
        'created_at': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
    }


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test"""
    yield
    # Cleanup after each test if needed


@pytest.fixture(autouse=True)
def cleanup_test_data(request):
    """Clean up test data after each test if using real database"""
    yield
    
    if USE_REAL_CONNECTIONS:
        # Clean up any test data created
        try:
            from supabase import create_client
            url = os.environ.get('SUPABASE_URL')
            key = os.environ.get('SUPABASE_SERVICE_KEY')
            test_phone = os.environ.get('TEST_PHONE', '27731863036')
            
            if url and key:
                db = create_client(url, key)
                # Clean test data
                db.table('trainers').delete().eq('whatsapp', test_phone).execute()
                db.table('clients').delete().eq('whatsapp', '27821234567').execute()
                db.table('registration_states').delete().eq('phone_number', test_phone).execute()
                db.table('conversation_states').delete().eq('phone_number', test_phone).execute()
        except:
            pass  # Ignore cleanup errors


@pytest.fixture(scope="session")
def test_phone_numbers():
    """Test phone numbers for different scenarios"""
    return {
        'trainer': '27731863036',
        'client1': '27821234567',
        'client2': '27831234567',
        'client3': '27841234567',
        'invalid': '123456',
        'international': '+44 20 1234 5678'
    }


# Markers for categorizing tests
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "trainer: Tests for trainer functionality"
    )
    config.addinivalue_line(
        "markers", "client: Tests for client functionality"
    )
    config.addinivalue_line(
        "markers", "registration: Tests for registration flows"
    )
    config.addinivalue_line(
        "markers", "booking: Tests for booking system"
    )
    config.addinivalue_line(
        "markers", "payment: Tests for payment processing"
    )
    config.addinivalue_line(
        "markers", "ai: Tests for AI/natural language processing"
    )
    config.addinivalue_line(
        "markers", "critical: Critical tests that must pass"
    )
    config.addinivalue_line(
        "markers", "real_db: Tests that require real database"
    )
    config.addinivalue_line(
        "markers", "mock: Tests using mock objects"
    )
