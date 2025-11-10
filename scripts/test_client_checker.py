#!/usr/bin/env python3
"""
Test script for ClientChecker service
Tests all 4 scenarios for adding clients
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly from the module file to avoid dependencies
import importlib.util
spec = importlib.util.spec_from_file_location("client_checker",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'services', 'relationships', 'client_checker.py'))
client_checker_module = importlib.util.module_from_spec(spec)

# Mock dependencies before loading the module
class MockLogger:
    @staticmethod
    def log_info(msg): print(f"ℹ️  {msg}")
    @staticmethod
    def log_error(msg): print(f"❌ {msg}")

class MockPhoneUtils:
    @staticmethod
    def normalize_phone_number(phone):
        if not phone:
            return None
        digits = ''.join(filter(str.isdigit, str(phone)))
        if digits.startswith('0'):
            digits = '27' + digits[1:]
        elif not digits.startswith('27') and len(digits) == 9:
            digits = '27' + digits
        return digits

# Mock pytz
class MockPytz:
    @staticmethod
    def timezone(tz):
        return None

sys.modules['utils.logger'] = type(sys)('utils.logger')
sys.modules['utils.logger'].log_info = MockLogger.log_info
sys.modules['utils.logger'].log_error = MockLogger.log_error
sys.modules['utils.phone_utils'] = type(sys)('utils.phone_utils')
sys.modules['utils.phone_utils'].normalize_phone_number = MockPhoneUtils.normalize_phone_number
sys.modules['pytz'] = type(sys)('pytz')
sys.modules['pytz'].timezone = MockPytz.timezone

# Now load the module
spec.loader.exec_module(client_checker_module)

ClientChecker = client_checker_module.ClientChecker
SCENARIO_NEW = client_checker_module.SCENARIO_NEW
SCENARIO_AVAILABLE = client_checker_module.SCENARIO_AVAILABLE
SCENARIO_ALREADY_YOURS = client_checker_module.SCENARIO_ALREADY_YOURS
SCENARIO_HAS_OTHER_TRAINER = client_checker_module.SCENARIO_HAS_OTHER_TRAINER
check_client_status = client_checker_module.check_client_status


class MockSupabaseResult:
    """Mock Supabase result object"""
    def __init__(self, data):
        self.data = data


class MockSupabaseTable:
    """Mock Supabase table for testing"""
    def __init__(self, table_name, mock_data):
        self.table_name = table_name
        self.mock_data = mock_data
        self.filters = {}

    def select(self, columns):
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def execute(self):
        # Simulate database queries
        if self.table_name == 'clients':
            if 'whatsapp' in self.filters:
                phone = self.filters['whatsapp']
                client = self.mock_data.get('clients', {}).get(phone)
                return MockSupabaseResult([client] if client else [])

        elif self.table_name == 'client_trainer_list':
            if 'client_id' in self.filters:
                client_id = self.filters['client_id']
                relationships = self.mock_data.get('client_trainer_list', {}).get(client_id, [])
                # Filter by connection_status if present
                if 'connection_status' in self.filters:
                    status = self.filters['connection_status']
                    relationships = [r for r in relationships if r.get('connection_status') == status]
                return MockSupabaseResult(relationships)

        elif self.table_name == 'trainer_client_list':
            if 'trainer_id' in self.filters and 'client_id' in self.filters:
                trainer_id = self.filters['trainer_id']
                client_id = self.filters['client_id']
                key = f"{trainer_id}:{client_id}"
                relationship = self.mock_data.get('trainer_client_list', {}).get(key)
                return MockSupabaseResult([relationship] if relationship else [])

        elif self.table_name == 'trainers':
            if 'trainer_id' in self.filters:
                trainer_id = self.filters['trainer_id']
                trainer = self.mock_data.get('trainers', {}).get(trainer_id)
                return MockSupabaseResult([trainer] if trainer else [])

        return MockSupabaseResult([])


class MockSupabaseClient:
    """Mock Supabase client for testing"""
    def __init__(self, mock_data):
        self.mock_data = mock_data

    def table(self, table_name):
        return MockSupabaseTable(table_name, self.mock_data)


def test_scenario_new():
    """Test SCENARIO_NEW: Client doesn't exist"""
    print("\n🧪 Testing SCENARIO_NEW: Client doesn't exist")

    mock_data = {
        'clients': {},
        'client_trainer_list': {},
        'trainer_client_list': {},
        'trainers': {}
    }

    client = MockSupabaseClient(mock_data)
    checker = ClientChecker(client)

    result = checker.check_client_status('0821234567', 'TRAINER001')

    assert result['scenario'] == SCENARIO_NEW, f"Expected SCENARIO_NEW, got {result['scenario']}"
    assert result['client_data'] is None, "Client data should be None"
    assert result['normalized_phone'] == '27821234567', "Phone should be normalized"
    assert result['error'] is False, "Should not have error"

    print("✅ SCENARIO_NEW test passed")
    print(f"   Message: {result['message']}")


def test_scenario_available():
    """Test SCENARIO_AVAILABLE: Client exists but has no active trainer"""
    print("\n🧪 Testing SCENARIO_AVAILABLE: Client exists but has no trainer")

    mock_data = {
        'clients': {
            '27821234567': {
                'client_id': 'CLIENT001',
                'name': 'John Doe',
                'whatsapp': '27821234567',
                'email': 'john@example.com'
            }
        },
        'client_trainer_list': {
            'CLIENT001': []  # No active relationships
        },
        'trainer_client_list': {},
        'trainers': {}
    }

    client = MockSupabaseClient(mock_data)
    checker = ClientChecker(client)

    result = checker.check_client_status('+27821234567', 'TRAINER001')

    assert result['scenario'] == SCENARIO_AVAILABLE, f"Expected SCENARIO_AVAILABLE, got {result['scenario']}"
    assert result['client_data'] is not None, "Client data should exist"
    assert result['client_data']['client_id'] == 'CLIENT001', "Client ID should match"
    assert result['trainer_info'] is None, "Trainer info should be None"
    assert result['error'] is False, "Should not have error"

    print("✅ SCENARIO_AVAILABLE test passed")
    print(f"   Message: {result['message']}")


def test_scenario_already_yours():
    """Test SCENARIO_ALREADY_YOURS: Client is already this trainer's client"""
    print("\n🧪 Testing SCENARIO_ALREADY_YOURS: Client is already yours")

    mock_data = {
        'clients': {
            '27821234567': {
                'client_id': 'CLIENT001',
                'name': 'Jane Smith',
                'whatsapp': '27821234567',
                'email': 'jane@example.com'
            }
        },
        'client_trainer_list': {
            'CLIENT001': [{
                'client_id': 'CLIENT001',
                'trainer_id': 'TRAINER001',
                'connection_status': 'active'
            }]
        },
        'trainer_client_list': {
            'TRAINER001:CLIENT001': {
                'trainer_id': 'TRAINER001',
                'client_id': 'CLIENT001',
                'connection_status': 'active'
            }
        },
        'trainers': {
            'TRAINER001': {
                'trainer_id': 'TRAINER001',
                'name': 'Coach Mike',
                'first_name': 'Mike',
                'last_name': 'Trainer'
            }
        }
    }

    client = MockSupabaseClient(mock_data)
    checker = ClientChecker(client)

    result = checker.check_client_status('0821234567', 'TRAINER001')

    assert result['scenario'] == SCENARIO_ALREADY_YOURS, f"Expected SCENARIO_ALREADY_YOURS, got {result['scenario']}"
    assert result['client_data'] is not None, "Client data should exist"
    assert result['trainer_info'] is not None, "Trainer info should exist"
    assert result['relationship'] is not None, "Relationship should exist"
    assert result['relationship']['connection_status'] == 'active', "Relationship should be active"
    assert result['error'] is False, "Should not have error"

    print("✅ SCENARIO_ALREADY_YOURS test passed")
    print(f"   Message: {result['message']}")


def test_scenario_has_other_trainer():
    """Test SCENARIO_HAS_OTHER_TRAINER: Client has a different trainer"""
    print("\n🧪 Testing SCENARIO_HAS_OTHER_TRAINER: Client has different trainer")

    mock_data = {
        'clients': {
            '27821234567': {
                'client_id': 'CLIENT001',
                'name': 'Bob Johnson',
                'whatsapp': '27821234567',
                'email': 'bob@example.com'
            }
        },
        'client_trainer_list': {
            'CLIENT001': [{
                'client_id': 'CLIENT001',
                'trainer_id': 'TRAINER002',
                'connection_status': 'active'
            }]
        },
        'trainer_client_list': {
            'TRAINER002:CLIENT001': {
                'trainer_id': 'TRAINER002',
                'client_id': 'CLIENT001',
                'connection_status': 'active'
            }
        },
        'trainers': {
            'TRAINER002': {
                'trainer_id': 'TRAINER002',
                'name': 'Coach Sarah',
                'first_name': 'Sarah',
                'last_name': 'Johnson'
            }
        }
    }

    client = MockSupabaseClient(mock_data)
    checker = ClientChecker(client)

    # TRAINER001 tries to add CLIENT001 who already has TRAINER002
    result = checker.check_client_status('27821234567', 'TRAINER001')

    assert result['scenario'] == SCENARIO_HAS_OTHER_TRAINER, f"Expected SCENARIO_HAS_OTHER_TRAINER, got {result['scenario']}"
    assert result['client_data'] is not None, "Client data should exist"
    assert result['trainer_info'] is not None, "Trainer info should exist"
    assert result['trainer_info']['trainer_id'] == 'TRAINER002', "Should show the other trainer"
    assert result['relationship'] is not None, "Relationship should exist"
    assert result['error'] is False, "Should not have error"

    print("✅ SCENARIO_HAS_OTHER_TRAINER test passed")
    print(f"   Message: {result['message']}")


def test_phone_normalization():
    """Test phone number normalization with various formats"""
    print("\n🧪 Testing phone number normalization")

    mock_data = {
        'clients': {
            '27821234567': {
                'client_id': 'CLIENT001',
                'name': 'Test User',
                'whatsapp': '27821234567'
            }
        },
        'client_trainer_list': {'CLIENT001': []},
        'trainer_client_list': {},
        'trainers': {}
    }

    client = MockSupabaseClient(mock_data)
    checker = ClientChecker(client)

    # Test different phone formats
    formats = [
        '+27821234567',
        '27821234567',
        '0821234567',
    ]

    for phone_format in formats:
        result = checker.check_client_status(phone_format, 'TRAINER001')
        assert result['normalized_phone'] == '27821234567', f"Failed to normalize {phone_format}"
        assert result['scenario'] == SCENARIO_AVAILABLE, f"Should find client with format {phone_format}"

    print("✅ Phone normalization test passed")
    print("   All formats normalized correctly: +27, 27, 0")


def test_convenience_function():
    """Test the convenience function"""
    print("\n🧪 Testing convenience function")

    mock_data = {
        'clients': {},
        'client_trainer_list': {},
        'trainer_client_list': {},
        'trainers': {}
    }

    client = MockSupabaseClient(mock_data)
    result = check_client_status(client, '0821234567', 'TRAINER001')

    assert result['scenario'] == SCENARIO_NEW, "Convenience function should work"
    print("✅ Convenience function test passed")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Running ClientChecker Tests")
    print("=" * 60)

    try:
        test_scenario_new()
        test_scenario_available()
        test_scenario_already_yours()
        test_scenario_has_other_trainer()
        test_phone_normalization()
        test_convenience_function()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
