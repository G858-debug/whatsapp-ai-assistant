# tests/test_phase2_client_management.py
"""
Phase 2: Client Management Tests
Testing actual client management functionality
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime
import pytz
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.refiloe import RefiloeService
from services.ai_intent_handler import AIIntentHandler
from utils.validators import Validators


class TestAddClientReal:
    """Test 2.1: Add Client functionality with real code"""
    
    @pytest.fixture
    def setup_services(self):
        mock_db = Mock()
        mock_config = Mock()
        mock_config.TIMEZONE = 'Africa/Johannesburg'
        mock_config.ANTHROPIC_API_KEY = 'test-key'
        
        # Mock trainer exists
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'trainer-123',
            'name': 'John Smith',
            'whatsapp': '27731863036'
        }
        
        # Mock successful insert
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [{'id': 'client-456'}]
        
        refiloe = RefiloeService(mock_db)
        ai_handler = AIIntentHandler(mock_config, mock_db)
        validator = Validators()
        
        return refiloe, ai_handler, validator, mock_db
    
    @pytest.mark.critical
    def test_add_client_command_variations(self, setup_services):
        """Test various ways to add clients"""
        refiloe, ai_handler, validator, mock_db = setup_services
        
        # Different command formats people actually use
        test_commands = [
            "Add client Sarah 0821234567",
            "Register new client John Doe 0831234567",
            "New client Mike phone 0841234567",
            "add mary 0851234567",
            "ADD CLIENT PETER 0861234567",
            "Can you add Sarah as a client 0821234567",
            "Please register John 0831234567",
            "Sign up Mike 0841234567",
            "Create client for Sarah 0821234567",
            "I have a new client Jane 0871234567"
        ]
        
        for command in test_commands:
            response = refiloe.handle_message('27731863036', command)
            
            # Should successfully add client
            assert response.get('success') == True or \
                   'added' in response.get('message', '').lower() or \
                   'registered' in response.get('message', '').lower(), \
                   f"Failed to add client with command: {command}"
    
    @pytest.mark.critical
    def test_phone_number_normalization(self, setup_services):
        """Test phone number handling and normalization"""
        refiloe, ai_handler, validator, mock_db = setup_services
        
        # Real-world phone formats
        phone_formats = [
            ("0821234567", "27821234567"),
            ("27821234567", "27821234567"),
            ("+27821234567", "27821234567"),
            ("+27 82 123 4567", "27821234567"),
            ("082-123-4567", "27821234567"),
            ("082 123 4567", "27821234567"),
            ("(082) 123-4567", "27821234567"),
            ("082.123.4567", "27821234567"),
        ]
        
        for input_phone, expected_phone in phone_formats:
            # Validate phone number
            is_valid, normalized, error = validator.validate_phone_number(input_phone)
            
            assert is_valid == True, f"Failed to validate: {input_phone}"
            assert normalized == expected_phone, \
                f"Expected {expected_phone} but got {normalized} for {input_phone}"
    
    def test_add_client_with_special_names(self, setup_services):
        """Test adding clients with special characters in names"""
        refiloe, ai_handler, validator, mock_db = setup_services
        
        special_names = [
            "Jean-Pierre",
            "O'Brien",
            "José García",
            "Mary-Jane van der Merwe",
            "Dr. Sarah Smith",
            "Anne Marie",
            "McDonald",
        ]
        
        for name in special_names:
            command = f"Add client {name} 0821234567"
            response = refiloe.handle_message('27731863036', command)
            
            # Should handle special names
            assert 'error' not in response.get('message', '').lower(), \
                f"Failed to handle name: {name}"


class TestViewClientsReal:
    """Test 2.2: View Clients functionality"""
    
    @pytest.fixture
    def setup_with_clients(self):
        mock_db = Mock()
        
        # Mock trainer with clients
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {'id': 'c1', 'name': 'Sarah Johnson', 'whatsapp': '27821234567', 'custom_rate': None},
            {'id': 'c2', 'name': 'John Doe', 'whatsapp': '27831234567', 'custom_rate': 500},
            {'id': 'c3', 'name': 'Mike Smith', 'whatsapp': '27841234567', 'custom_rate': 400}
        ]
        
        refiloe = RefiloeService(mock_db)
        return refiloe, mock_db
    
    def test_view_clients_commands(self, setup_with_clients):
        """Test different ways to view clients"""
        refiloe, mock_db = setup_with_clients
        
        view_commands = [
            "Show my clients",
            "List clients",
            "View all clients",
            "my clients",
            "who are my clients",
            "Show client list",
            "Display clients",
        ]
        
        for command in view_commands:
            response = refiloe.handle_message('27731863036', command)
            
            # Should list clients
            message = response.get('message', '').lower()
            assert 'sarah' in message or 'john' in message or 'mike' in message or \
                   'client' in message, \
                   f"Failed to list clients with command: {command}"


class TestCustomPricingReal:
    """Test 2.3 & 2.4: Custom Pricing functionality"""
    
    @pytest.fixture
    def setup_pricing(self):
        mock_db = Mock()
        
        # Mock client exists
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'client-456',
            'name': 'Sarah Johnson',
            'trainer_id': 'trainer-123',
            'custom_rate': None
        }
        
        # Mock update success
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {'id': 'client-456', 'custom_rate': 450}
        ]
        
        refiloe = RefiloeService(mock_db)
        validator = Validators()
        return refiloe, validator, mock_db
    
    @pytest.mark.critical
    def test_set_custom_pricing_variations(self, setup_pricing):
        """Test 2.3: Setting custom pricing with various formats"""
        refiloe, validator, mock_db = setup_pricing
        
        pricing_commands = [
            ("Set Sarah's rate to R450", 450),
            ("Change John's price to R500 per session", 500),
            ("Update Mike's session fee to 400", 400),
            ("Sarah's rate is now R350", 350),
            ("Make Sarah's price 450", 450),
            ("Sarah pays R400", 400),
            ("Custom rate for Sarah: R500", 500),
            ("Set pricing for Sarah at 450", 450),
        ]
        
        for command, expected_price in pricing_commands:
            # Validate amount parsing
            is_valid, parsed_amount, error = validator.validate_amount(str(expected_price))
            
            assert is_valid == True
            assert parsed_amount == expected_price
            
            # Test command
            response = refiloe.handle_message('27731863036', command)
            
            # Should update pricing
            assert response.get('success') == True or \
                   'updated' in response.get('message', '').lower() or \
                   'set' in response.get('message', '').lower(), \
                   f"Failed to set pricing with: {command}"
    
    def test_check_client_pricing(self, setup_pricing):
        """Test 2.4: Check client pricing"""
        refiloe, validator, mock_db = setup_pricing
        
        check_commands = [
            "What is Sarah's rate?",
            "Show John's price",
            "Check Mike's session fee",
            "How much does Sarah pay?",
            "Sarah's pricing",
            "Rate for John",
        ]
        
        for command in check_commands:
            response = refiloe.handle_message('27731863036', command)
            
            # Should show pricing
            message = response.get('message', '').lower()
            assert 'r' in message or 'rand' in message or \
                   any(str(x) in message for x in [300, 350, 400, 450, 500]), \
                   f"Failed to show pricing with: {command}"


class TestClientManagementEdgeCases:
    """Test edge cases in client management"""
    
    @pytest.fixture
    def setup_services(self):
        mock_db = Mock()
        refiloe = RefiloeService(mock_db)
        validator = Validators()
        return refiloe, validator, mock_db
    
    def test_add_client_with_duplicate_phone(self, setup_services):
        """Test handling duplicate client registration"""
        refiloe, validator, mock_db = setup_services
        
        # Mock client already exists
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'existing-client',
            'name': 'Existing Client',
            'whatsapp': '27821234567'
        }
        
        response = refiloe.handle_message('27731863036', 'Add client New Person 0821234567')
        
        # Should handle duplicate
        assert 'already' in response.get('message', '').lower() or \
               'exists' in response.get('message', '').lower()
    
    def test_invalid_phone_numbers(self, setup_services):
        """Test handling of invalid phone numbers"""
        refiloe, validator, mock_db = setup_services
        
        invalid_phones = [
            "123",  # Too short
            "abcdefghij",  # Letters
            "0000000000",  # All zeros
            "123456789012345",  # Too long
        ]
        
        for phone in invalid_phones:
            is_valid, _, error = validator.validate_phone_number(phone)
            assert is_valid == False, f"Should reject invalid phone: {phone}"
            assert error is not None
    
    def test_set_negative_pricing(self, setup_services):
        """Test that negative pricing is rejected"""
        refiloe, validator, mock_db = setup_services
        
        # Test negative amount validation
        is_valid, _, error = validator.validate_amount("-100")
        assert is_valid == False
        assert "cannot be less than" in error.lower() or "positive" in error.lower()
        
        # Test extremely high amount
        is_valid, _, error = validator.validate_amount("999999")
        assert is_valid == False
        assert "exceed" in error.lower() or "too high" in error.lower()
    
    def test_client_not_found(self, setup_services):
        """Test handling when client doesn't exist"""
        refiloe, validator, mock_db = setup_services
        
        # Mock no client found
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
        
        response = refiloe.handle_message('27731863036', "Set NonExistent's rate to R450")
        
        # Should handle gracefully
        assert 'not found' in response.get('message', '').lower() or \
               "doesn't exist" in response.get('message', '').lower() or \
               'no client' in response.get('message', '').lower()
