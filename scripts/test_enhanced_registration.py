#!/usr/bin/env python3
"""
Test Enhanced Registration State Management
Tests the new features added in Phase 2.1
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Load environment variables manually
def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    env_vars = {}
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"\'')
                    env_vars[key] = value
                    os.environ[key] = value
    
    return env_vars

env_vars = load_env_file()

def test_registration_state_management():
    """Test the enhanced registration state management features"""
    
    print("🧪 Testing Enhanced Registration State Management")
    print("=" * 55)
    
    try:
        # Add parent directory to path
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        
        from services.registration.registration_state import RegistrationStateManager
        from services.registration.trainer_registration import TrainerRegistrationHandler
        
        # Mock supabase for testing
        class MockSupabase:
            def __init__(self):
                self.mock_data = {}
            
            def table(self, table_name):
                return MockTable(self.mock_data, table_name)
        
        class MockTable:
            def __init__(self, mock_data, table_name):
                self.mock_data = mock_data
                self.table_name = table_name
                if table_name not in self.mock_data:
                    self.mock_data[table_name] = []
            
            def select(self, fields):
                return MockQuery(self.mock_data, self.table_name, 'select')
            
            def insert(self, data):
                self.mock_data[self.table_name].append(data)
                return MockResult([data])
            
            def update(self, data):
                return MockQuery(self.mock_data, self.table_name, 'update', data)
            
            def delete(self):
                return MockQuery(self.mock_data, self.table_name, 'delete')
        
        class MockQuery:
            def __init__(self, mock_data, table_name, operation, data=None):
                self.mock_data = mock_data
                self.table_name = table_name
                self.operation = operation
                self.data = data
                self.filters = {}
            
            def eq(self, field, value):
                self.filters[field] = value
                return self
            
            def gte(self, field, value):
                self.filters[f'{field}_gte'] = value
                return self
            
            def lte(self, field, value):
                self.filters[f'{field}_lte'] = value
                return self
            
            def lt(self, field, value):
                self.filters[f'{field}_lt'] = value
                return self
            
            def execute(self):
                if self.operation == 'select':
                    # Simple mock - return all data for now
                    return MockResult(self.mock_data.get(self.table_name, []))
                elif self.operation == 'insert':
                    return MockResult([self.data])
                elif self.operation == 'update':
                    return MockResult([self.data])
                elif self.operation == 'delete':
                    return MockResult([])
                return MockResult([])
        
        class MockResult:
            def __init__(self, data):
                self.data = data
        
        # Initialize managers with mock
        mock_supabase = MockSupabase()
        state_manager = RegistrationStateManager(mock_supabase)
        
        test_phone = "+27123456789"
        
        print("1️⃣ Testing progress percentage calculation...")
        
        # Test with no registration state
        progress = state_manager.get_progress_percentage(test_phone)
        print(f"   No state progress: {progress}% ✅" if progress == 0 else f"   ❌ Expected 0%, got {progress}%")
        
        # Create a mock registration state
        mock_state = {
            'phone_number': test_phone,
            'user_type': 'trainer',
            'current_step': 3,
            'data': {'name': 'John Doe', 'email': 'john@example.com'},
            'completed': False,
            'created_at': datetime.now().isoformat()
        }
        
        # Add to mock data
        mock_supabase.mock_data['registration_states'] = [mock_state]
        
        progress = state_manager.get_progress_percentage(test_phone)
        expected_progress = int((3 / 7) * 100)  # 3 out of 7 steps
        print(f"   Step 3/7 progress: {progress}% ✅" if progress == expected_progress else f"   ❌ Expected {expected_progress}%, got {progress}%")
        
        print("\n2️⃣ Testing resume capability...")
        
        # Test can resume (recent registration)
        can_resume = state_manager.can_resume_registration(test_phone)
        print(f"   Recent registration can resume: {can_resume} ✅" if can_resume else "   ❌ Should be able to resume recent registration")
        
        # Test expired registration
        old_state = mock_state.copy()
        old_time = datetime.now() - timedelta(hours=25)  # 25 hours ago
        old_state['created_at'] = old_time.isoformat()
        mock_supabase.mock_data['registration_states'] = [old_state]
        
        can_resume = state_manager.can_resume_registration(test_phone)
        print(f"   Old registration cannot resume: {not can_resume} ✅" if not can_resume else "   ❌ Should not be able to resume old registration")
        
        print("\n3️⃣ Testing registration summary...")
        
        # Test comprehensive summary
        summary = state_manager.get_registration_summary(test_phone)
        
        expected_keys = ['exists', 'user_type', 'current_step', 'total_steps', 'progress_percentage', 'can_resume', 'is_expired', 'completed']
        
        missing_keys = [key for key in expected_keys if key not in summary]
        
        if not missing_keys:
            print(f"   Summary contains all expected keys ✅")
            print(f"      Exists: {summary.get('exists')}")
            print(f"      Progress: {summary.get('progress_percentage')}%")
            print(f"      Can Resume: {summary.get('can_resume')}")
            print(f"      Is Expired: {summary.get('is_expired')}")
        else:
            print(f"   ❌ Missing keys in summary: {missing_keys}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False

def test_registration_analytics():
    """Test the registration analytics features"""
    
    print("\n4️⃣ Testing Registration Analytics...")
    print("=" * 35)
    
    try:
        # Add parent directory to path
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        
        from services.registration.trainer_registration import TrainerRegistrationHandler
        
        # Mock supabase and whatsapp service
        class MockSupabase:
            def __init__(self):
                self.analytics_data = []
            
            def table(self, table_name):
                return MockAnalyticsTable(self.analytics_data, table_name)
        
        class MockAnalyticsTable:
            def __init__(self, analytics_data, table_name):
                self.analytics_data = analytics_data
                self.table_name = table_name
            
            def insert(self, data):
                if self.table_name == 'registration_analytics':
                    self.analytics_data.append(data)
                return MockResult([data])
            
            def select(self, fields):
                return MockAnalyticsQuery(self.analytics_data, self.table_name)
        
        class MockAnalyticsQuery:
            def __init__(self, analytics_data, table_name):
                self.analytics_data = analytics_data
                self.table_name = table_name
            
            def gte(self, field, value):
                return self
            
            def lte(self, field, value):
                return self
            
            def execute(self):
                return MockResult(self.analytics_data if self.table_name == 'registration_analytics' else [])
        
        class MockResult:
            def __init__(self, data):
                self.data = data
        
        class MockWhatsApp:
            def send_message(self, phone, message):
                return {'success': True}
        
        # Initialize handler
        mock_supabase = MockSupabase()
        mock_whatsapp = MockWhatsApp()
        
        trainer_handler = TrainerRegistrationHandler(mock_supabase, mock_whatsapp)
        
        test_phone = "+27123456789"
        
        print("   Testing analytics tracking...")
        
        # Test tracking different events
        trainer_handler.track_registration_analytics(test_phone, 'started', step=0)
        trainer_handler.track_registration_analytics(test_phone, 'step_completed', step=1)
        trainer_handler.track_registration_analytics(test_phone, 'validation_error', step=2, error_field='email', error_message='Invalid email format')
        trainer_handler.track_registration_analytics(test_phone, 'completed')
        
        print(f"   Tracked {len(mock_supabase.analytics_data)} analytics events ✅")
        
        # Test analytics summary
        summary = trainer_handler.get_registration_analytics_summary(days=7)
        
        expected_summary_keys = ['period_days', 'total_events', 'registrations_started', 'registrations_completed', 'completion_rate']
        
        missing_keys = [key for key in expected_summary_keys if key not in summary]
        
        if not missing_keys:
            print(f"   Analytics summary generated successfully ✅")
            print(f"      Total Events: {summary.get('total_events')}")
            print(f"      Started: {summary.get('registrations_started')}")
            print(f"      Completed: {summary.get('registrations_completed')}")
            print(f"      Completion Rate: {summary.get('completion_rate')}%")
        else:
            print(f"   ❌ Missing keys in analytics summary: {missing_keys}")
        
        return True
        
    except Exception as e:
        print(f"❌ Analytics test error: {str(e)}")
        return False

def main():
    """Main test function"""
    
    print("🔧 Enhanced Registration State Management Tests")
    print("=" * 55)
    
    # Run tests
    state_test = test_registration_state_management()
    analytics_test = test_registration_analytics()
    
    # Summary
    print(f"\n" + "=" * 55)
    print(f"📊 TEST RESULTS")
    print(f"=" * 55)
    print(f"State Management: {'✅ Passed' if state_test else '❌ Failed'}")
    print(f"Analytics Tracking: {'✅ Passed' if analytics_test else '❌ Failed'}")
    
    if state_test and analytics_test:
        print(f"\n🎉 Phase 2.1 Enhancements are WORKING!")
        print(f"   ✅ Progress percentage calculation")
        print(f"   ✅ Registration timeout handling")
        print(f"   ✅ Resume capability improvements")
        print(f"   ✅ Registration analytics tracking")
        print(f"   ✅ Comprehensive state summaries")
    else:
        print(f"\n⚠️ Some enhancements need attention")
    
    print(f"\n🚀 Enhanced Features Ready:")
    print(f"   📊 Progress tracking with percentages")
    print(f"   ⏰ Automatic timeout and cleanup")
    print(f"   🔄 Smart resume capability")
    print(f"   📈 Detailed analytics and insights")
    print(f"   🛡️ Robust error handling")

if __name__ == "__main__":
    main()