"""
Phase 1: User Registration Tests
Testing actual registration flows with real Refiloe code
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force use of mocks for these tests
os.environ['USE_REAL_CONNECTIONS'] = 'false'

# Import actual Refiloe services
from services.registration.trainer_registration import TrainerRegistrationHandler
from services.refiloe import RefiloeService
from services.ai_intent_handler import AIIntentHandler


class TestTrainerRegistrationReal:
    """Test trainer registration with actual Refiloe code"""
    
    @pytest.fixture
    def setup_services(self):
        """Setup real services with properly configured mocks"""
        # Create mock database that handles different tables
        mock_db = MagicMock()
        
        def create_table_mock(table_name):
            """Create a mock for specific table"""
            table_mock = MagicMock()
            
            if table_name == 'trainers':
                # For trainers table, always return empty (no existing trainer)
                result = MagicMock()
                result.data = []
                table_mock.select.return_value.eq.return_value.execute.return_value = result
                table_mock.insert.return_value.execute.return_value = MagicMock(
                    data=[{'id': 'trainer-123'}]
                )
            elif table_name == 'registration_states':
                # For registration states, return empty
                result = MagicMock()
                result.data = []
                table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = result
                table_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = result
                table_mock.insert.return_value.execute.return_value = MagicMock(data=[])
                table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            else:
                # Default behavior for other tables
                result = MagicMock()
                result.data = []
                table_mock.select.return_value.eq.return_value.execute.return_value = result
                table_mock.insert.return_value.execute.return_value = MagicMock(data=[])
            
            return table_mock
        
        # Set the side_effect to handle different tables
        mock_db.table.side_effect = create_table_mock
        
        # Mock WhatsApp
        mock_whatsapp = Mock()
        mock_whatsapp.send_message.return_value = {'success': True}
        
        # Create real handler with mocked dependencies
        handler = TrainerRegistrationHandler(mock_db, mock_whatsapp)
        
        # Create real Refiloe service
        refiloe = RefiloeService(mock_db)
        
        return handler, refiloe, mock_db, mock_whatsapp
    
    @pytest.mark.critical
    def test_complete_trainer_registration_flow(self, setup_services):
        """Test 1.1: Complete trainer onboarding flow"""
        handler, refiloe, mock_db, _ = setup_services
        
        phone = "27731863036"
        
        # Create a more sophisticated mock that handles different tables correctly
        def mock_table_handler(table_name):
            table_mock = MagicMock()
            
            if table_name == 'trainers':
                # For trainers table, always return empty (no existing trainer)
                empty_result = MagicMock()
                empty_result.data = []
                table_mock.select.return_value.eq.return_value.execute.return_value = empty_result
                # Allow insert to succeed
                table_mock.insert.return_value.execute.return_value = MagicMock(
                    data=[{'id': 'trainer-123', 'name': 'John Smith'}]
                )
            elif table_name == 'registration_states':
                # For registration states, return empty
                empty_result = MagicMock()
                empty_result.data = []
                table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = empty_result
                table_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = empty_result
                # Allow insert/update to succeed
                table_mock.insert.return_value.execute.return_value = MagicMock(data=[])
                table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            else:
                # Default for any other table
                empty_result = MagicMock()
                empty_result.data = []
                table_mock.select.return_value.execute.return_value = empty_result
                table_mock.insert.return_value.execute.return_value = MagicMock(data=[])
            
            return table_mock
        
        # Replace both the mock_db and handler's db to ensure it works
        mock_db.table.side_effect = mock_table_handler
        handler.db = mock_db  # Ensure handler uses our mock
        
        # Step 1: Start registration
        response = handler.start_registration(phone)
        assert "excited" in response.lower() or "welcome" in response.lower()
        assert "step 1" in response.lower()
        
        # Step 2: Name
        result = handler.handle_registration_response(
            phone=phone,
            message="John Smith",
            current_step=0,
            data={}
        )
        assert result['success'] == True
        assert result['data']['name'] == "John Smith"
        
        # Continue through all steps...
        # Step 3: Business name
        result = handler.handle_registration_response(
            phone=phone,
            message="FitLife PT",
            current_step=1,
            data=result['data']
        )
        assert result['success'] == True
        
        # Step 4: Email
        result = handler.handle_registration_response(
            phone=phone,
            message="john@fitlife.co.za",
            current_step=2,
            data=result['data']
        )
        assert result['success'] == True
        
        # Step 5: Specialization
        result = handler.handle_registration_response(
            phone=phone,
            message="Weight loss and strength training",
            current_step=3,
            data=result['data']
        )
        assert result['success'] == True
        
        # Step 6: Experience
        result = handler.handle_registration_response(
            phone=phone,
            message="5 years",
            current_step=4,
            data=result['data']
        )
        assert result['success'] == True
        
        # Step 7: Location
        result = handler.handle_registration_response(
            phone=phone,
            message="Sandton, Johannesburg",
            current_step=5,
            data=result['data']
        )
        assert result['success'] == True
        
        # Step 8: Pricing
        result = handler.handle_registration_response(
            phone=phone,
            message="R450",
            current_step=6,
            data=result['data']
        )
        
        # Should complete registration
        assert result['success'] == True
        assert "welcome" in result['message'].lower() or "congratulations" in result['message'].lower()
    
    @pytest.mark.critical
    def test_currency_parsing_variations(self, setup_services):
        """Test currency parsing with all real-world variations"""
        handler, _, mock_db, _ = setup_services
        
        test_cases = [
            ("R450", 450),
            ("r450", 450),
            ("R 450", 450),
            ("450", 450),
            ("450.00", 450),
            ("R450.50", 450.50),
        ]
        
        for input_text, expected_value in test_cases:
            result = handler._validate_field('pricing', input_text)
            assert result['valid'] == True
            assert result['value'] == expected_value
    
    def test_registration_with_missing_fields(self, setup_services):
        """Test registration handles missing optional fields"""
        handler, _, mock_db, _ = setup_services
        
        result = handler.handle_registration_response(
            phone="27731863036",
            message="skip",
            current_step=1,
            data={'name': 'Jane Doe'}
        )
        
        assert result['success'] == True
    
    def test_trainer_recognition_after_registration(self, setup_services):
        """Test 1.2: Trainer recognition after registration"""
        _, refiloe, mock_db, _ = setup_services
        
        # Configure mock to return existing trainer
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                'id': 'trainer-123',
                'name': 'John Smith',
                'first_name': 'John',
                'whatsapp': '27731863036'
            }]
        )
        
        # Configure AI response
        with patch('services.ai_intent_handler.AIIntentHandler') as mock_ai:
            mock_ai_instance = MagicMock()
            mock_ai_instance.process_message.return_value = {
                'success': True,
                'response': 'Welcome back, John! How can I help you today?',
                'message': 'Welcome back, John! How can I help you today?'
            }
            mock_ai.return_value = mock_ai_instance
            
            response = refiloe.handle_message('27731863036', 'Hi')
            
            # Should contain greeting
            assert response.get('success') == True
            assert 'john' in response.get('response', '').lower() or \
                   'welcome' in response.get('response', '').lower()


class TestClientRegistrationReal:
    """Test client registration with actual code"""
    
    @pytest.fixture
    def setup_client_services(self):
        """Setup services for client testing"""
        mock_db = MagicMock()
        mock_whatsapp = Mock()
        
        # Configure mock database
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.single.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[{
            'id': 'trainer-123',
            'name': 'John Smith'
        }])
        
        mock_db.table.return_value = mock_query
        
        refiloe = RefiloeService(mock_db)
        
        return refiloe, mock_db, mock_whatsapp
    
    def test_client_receives_welcome_after_registration(self, setup_client_services):
        """Test client receives proper welcome after being added"""
        refiloe, mock_db, mock_whatsapp = setup_client_services
        
        with patch('services.ai_intent_handler.AIIntentHandler') as mock_ai:
            mock_ai_instance = MagicMock()
            mock_ai_instance.process_message.return_value = {
                'success': True,
                'response': 'Client Sarah has been added successfully.',
                'message': 'Client Sarah has been added successfully.'
            }
            mock_ai.return_value = mock_ai_instance
            
            response = refiloe.handle_message('27731863036', 'Add client Sarah 0821234567')
            
            assert response.get('success') == True
            assert 'added' in response.get('response', '').lower() or \
                   'registered' in response.get('response', '').lower()


class TestRegistrationEdgeCases:
    """Test edge cases and error handling in registration"""
    
    @pytest.fixture
    def setup_services(self):
        mock_db = MagicMock()
        mock_whatsapp = Mock()
        handler = TrainerRegistrationHandler(mock_db, mock_whatsapp)
        return handler, mock_db
    
    def test_duplicate_registration_attempt(self, setup_services):
        """Test handling of duplicate registration attempts"""
        handler, mock_db = setup_services
        
        # Configure mock to return existing trainer
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                'id': 'trainer-123',
                'first_name': 'John'
            }]
        )
        
        response = handler.start_registration('27731863036')
        
        assert 'already' in response.lower() or 'welcome back' in response.lower()
    
    def test_invalid_email_format(self, setup_services):
        """Test email validation during registration"""
        handler, mock_db = setup_services
        
        result = handler.handle_registration_response(
            phone="27731863036",
            message="notanemail",
            current_step=2,
            data={'name': 'Test', 'business_name': 'Test Business'}
        )
        
        assert result['success'] == False
        assert 'valid email' in result.get('message', '').lower()
    
    def test_extremely_long_input(self, setup_services):
        """Test handling of extremely long input"""
        handler, mock_db = setup_services
        
        very_long_name = "A" * 500
        
        # The validator should limit the name length
        result = handler._validate_field('name', very_long_name)
        
        # Should either truncate or reject
        if result['valid']:
            # If accepted, should be truncated to reasonable length
            assert len(result['value']) <= 255
        else:
            # Or should be rejected with error message
            assert 'too long' in result.get('error', '').lower()
    
    def test_special_characters_in_name(self, setup_services):
        """Test handling of special characters in names"""
        handler, mock_db = setup_services
        
        special_names = [
            "Jean-Pierre",
            "O'Brien",
            "José García",
            "Mary-Jane"
        ]
        
        for name in special_names:
            result = handler._validate_field('name', name)
            assert result['valid'] == True
            assert result['value'] == name
