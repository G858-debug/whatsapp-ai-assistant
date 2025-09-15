# tests/test_phase1_registration.py
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

# Import actual Refiloe services
from services.registration.trainer_registration import TrainerRegistrationHandler
from services.refiloe import RefiloeService
from services.ai_intent_handler import AIIntentHandler


class TestTrainerRegistrationReal:
    """Test trainer registration with actual Refiloe code"""
    
    @pytest.fixture
    def setup_services(self):
        """Setup real services with mocked database"""
        # Mock database
        mock_db = Mock()
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [{'id': 'trainer-123'}]
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        # Mock WhatsApp
        mock_whatsapp = Mock()
        mock_whatsapp.send_message.return_value = {'success': True}
        
        # Create real handler
        handler = TrainerRegistrationHandler(mock_db, mock_whatsapp)
        
        # Create real Refiloe service
        refiloe = RefiloeService(mock_db)
        
        return handler, refiloe, mock_db, mock_whatsapp
    
    @pytest.mark.critical
    def test_complete_trainer_registration_flow(self, setup_services):
        """Test 1.1: Complete trainer onboarding flow"""
        handler, refiloe, mock_db, _ = setup_services
        
        phone = "27731863036"
        
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
        assert "step 2" in result['message'].lower()
        
        # Step 3: Business name
        result = handler.handle_registration_response(
            phone=phone,
            message="FitLife PT",
            current_step=1,
            data=result['data']
        )
        assert result['success'] == True
        assert result['data']['business_name'] == "FitLife PT"
        
        # Step 4: Email
        result = handler.handle_registration_response(
            phone=phone,
            message="john@fitlife.co.za",
            current_step=2,
            data=result['data']
        )
        assert result['success'] == True
        assert result['data']['email'] == "john@fitlife.co.za"
        
        # Step 5: Specialization
        result = handler.handle_registration_response(
            phone=phone,
            message="Weight loss and strength training",
            current_step=3,
            data=result['data']
        )
        assert result['success'] == True
        assert result['data']['specialization'] == "Weight loss and strength training"
        
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
        assert result['data']['location'] == "Sandton, Johannesburg"
        
        # Step 8: Pricing - CRITICAL TEST
        result = handler.handle_registration_response(
            phone=phone,
            message="R450",
            current_step=6,
            data=result['data']
        )
        
        # This should complete registration
        assert result['success'] == True
        assert "welcome" in result['message'].lower()
        
        # Verify database insert was called with correct data
        insert_calls = mock_db.table.return_value.insert.call_args_list
        if insert_calls:
            saved_data = insert_calls[-1][0][0]
            # CRITICAL: Pricing should be numeric, not string
            assert isinstance(saved_data.get('pricing_per_session'), (int, float)), \
                f"Pricing saved as {type(saved_data.get('pricing_per_session'))} instead of numeric"
            assert saved_data.get('pricing_per_session') == 450, \
                f"Pricing saved as {saved_data.get('pricing_per_session')} instead of 450"
    
    @pytest.mark.critical
    def test_currency_parsing_variations(self, setup_services):
        """Test currency parsing with all real-world variations"""
        handler, _, mock_db, _ = setup_services
        
        test_cases = [
            # Standard formats
            ("R450", 450),
            ("r450", 450),
            ("R 450", 450),
            ("450", 450),
            ("450.00", 450),
            ("R450.50", 450.50),
            
            # Natural language
            ("four fifty", 450),
            ("450 rand", 450),
            ("R450 per session", 450),
            ("I charge R450", 450),
            
            # With spaces and special characters
            ("R 450.00", 450),
            ("R450,-", 450),
            ("R450/session", 450),
            
            # Thousand separators
            ("R1,000", 1000),
            ("R1 000", 1000),
            ("R2000", 2000),
            
            # Edge cases
            ("450r", 450),
            ("ZAR 450", 450),
            ("450 bucks", 450),
        ]
        
        for input_text, expected_value in test_cases:
            # Reset mock
            mock_db.reset_mock()
            
            result = handler.handle_registration_response(
                phone="27731863036",
                message=input_text,
                current_step=6,  # Pricing step
                data={
                    'name': 'Test',
                    'email': 'test@test.com',
                    'specialization': 'Fitness',
                    'experience': '5',
                    'location': 'Sandton'
                }
            )
            
            # Should parse correctly
            if 'data' in result and 'pricing' in result['data']:
                actual_value = result['data']['pricing']
                assert actual_value == expected_value, \
                    f"Failed to parse '{input_text}': got {actual_value}, expected {expected_value}"
    
    def test_registration_with_missing_fields(self, setup_services):
        """Test registration handles missing optional fields"""
        handler, _, mock_db, _ = setup_services
        
        # Skip business name (should be optional)
        result = handler.handle_registration_response(
            phone="27731863036",
            message="skip",
            current_step=1,  # Business name step
            data={'name': 'Jane Doe'}
        )
        
        assert result['success'] == True
        assert result['continue'] == True
        
    def test_trainer_recognition_after_registration(self, setup_services):
        """Test 1.2: Trainer recognition after registration"""
        _, refiloe, mock_db, _ = setup_services
        
        # Mock existing trainer
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'trainer-123',
            'name': 'John Smith',
            'first_name': 'John',
            'whatsapp': '27731863036'
        }
        
        # Send greeting
        response = refiloe.handle_message('27731863036', 'Hi')
        
        # Should recognize trainer and greet by name
        assert 'john' in response.get('message', '').lower() or \
               'welcome back' in response.get('message', '').lower(), \
               "Should recognize and greet trainer by name"
    
    def test_registration_saves_all_fields_correctly(self, setup_services):
        """Test that all registration fields are saved correctly to database"""
        handler, _, mock_db, _ = setup_services
        
        registration_data = {
            'name': 'John Smith',
            'business_name': 'FitLife PT',
            'email': 'john@fitlife.co.za',
            'specialization': 'Weight loss',
            'experience': '5',
            'location': 'Sandton',
            'pricing': 'R450'
        }
        
        # Complete registration
        result = handler._complete_registration('27731863036', registration_data)
        
        # Get what was saved
        insert_calls = mock_db.table.return_value.insert.call_args_list
        assert len(insert_calls) > 0, "Should have called insert"
        
        saved_data = insert_calls[-1][0][0]
        
        # Verify all fields
        assert saved_data.get('name') == 'John Smith'
        assert saved_data.get('business_name') == 'FitLife PT'
        assert saved_data.get('email') == 'john@fitlife.co.za'
        assert saved_data.get('whatsapp') == '27731863036'
        assert saved_data.get('specialization') == 'Weight loss'
        assert saved_data.get('years_experience') in [5, '5']  # Could be string or int
        assert saved_data.get('location') == 'Sandton'
        assert saved_data.get('pricing_per_session') == 450  # Must be numeric!
        assert saved_data.get('status') == 'active'


class TestClientRegistrationReal:
    """Test client registration with actual code"""
    
    @pytest.fixture
    def setup_client_services(self):
        """Setup services for client testing"""
        mock_db = Mock()
        mock_whatsapp = Mock()
        
        # Mock trainer exists
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'trainer-123',
            'name': 'John Smith'
        }
        
        refiloe = RefiloeService(mock_db)
        
        return refiloe, mock_db, mock_whatsapp
    
    def test_client_receives_welcome_after_registration(self, setup_client_services):
        """Test client receives proper welcome after being added"""
        refiloe, mock_db, mock_whatsapp = setup_client_services
        
        # Trainer adds client
        response = refiloe.handle_message('27731863036', 'Add client Sarah 0821234567')
        
        # Should confirm client added
        assert 'added' in response.get('message', '').lower() or \
               'registered' in response.get('message', '').lower()
        
        # Mock client's first message
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'client-456',
            'name': 'Sarah',
            'trainer_id': 'trainer-123'
        }
        
        # Client sends first message
        response = refiloe.handle_message('27821234567', 'Hi')
        
        # Should receive personalized welcome
        assert 'sarah' in response.get('message', '').lower() or \
               'welcome' in response.get('message', '').lower()


class TestRegistrationEdgeCases:
    """Test edge cases and error handling in registration"""
    
    @pytest.fixture
    def setup_services(self):
        mock_db = Mock()
        mock_whatsapp = Mock()
        handler = TrainerRegistrationHandler(mock_db, mock_whatsapp)
        return handler, mock_db
    
    def test_duplicate_registration_attempt(self, setup_services):
        """Test handling of duplicate registration attempts"""
        handler, mock_db = setup_services
        
        # Mock existing trainer
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'trainer-123',
            'name': 'John Smith'
        }
        
        # Try to register again
        response = handler.start_registration('27731863036')
        
        # Should recognize existing trainer
        assert 'already' in response.lower() or \
               'welcome back' in response.lower()
    
    def test_invalid_email_format(self, setup_services):
        """Test email validation during registration"""
        handler, mock_db = setup_services
        
        invalid_emails = [
            "notanemail",
            "missing@",
            "@nodomain.com",
            "spaces in@email.com",
            "double@@domain.com"
        ]
        
        for email in invalid_emails:
            result = handler.handle_registration_response(
                phone="27731863036",
                message=email,
                current_step=2,  # Email step
                data={'name': 'Test', 'business_name': 'Test Business'}
            )
            
            # Should reject invalid email
            assert result['success'] == False or \
                   'invalid' in result.get('message', '').lower() or \
                   'valid email' in result.get('message', '').lower()
    
    def test_extremely_long_input(self, setup_services):
        """Test handling of extremely long input"""
        handler, mock_db = setup_services
        
        very_long_name = "A" * 500  # 500 character name
        
        result = handler.handle_registration_response(
            phone="27731863036",
            message=very_long_name,
            current_step=0,  # Name step
            data={}
        )
        
        # Should either truncate or reject
        if result['success']:
            assert len(result['data']['name']) <= 255  # Reasonable limit
        else:
            assert 'too long' in result.get('message', '').lower()
    
    def test_special_characters_in_name(self, setup_services):
        """Test handling of special characters in names"""
        handler, mock_db = setup_services
        
        special_names = [
            "Jean-Pierre",
            "O'Brien",
            "José García",
            "Mary-Jane",
            "Dr. Smith",
            "van der Merwe"
        ]
        
        for name in special_names:
            result = handler.handle_registration_response(
                phone="27731863036",
                message=name,
                current_step=0,  # Name step
                data={}
            )
            
            # Should accept these valid name formats
            assert result['success'] == True
            assert result['data']['name'] == name
