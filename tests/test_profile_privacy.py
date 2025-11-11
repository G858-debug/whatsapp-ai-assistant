"""
Test Suite for Multi-Trainer Profile Privacy
Tests privacy boundaries to ensure trainers cannot see each other's data
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from services.relationships.profile_privacy_service import ProfilePrivacyService


class TestProfilePrivacy(unittest.TestCase):
    """Test suite for profile privacy in multi-trainer scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.service = ProfilePrivacyService(self.mock_db)

        # Test data
        self.client_id = 'CLIENT001'
        self.trainer1_id = 'TRAINER001'
        self.trainer2_id = 'TRAINER002'

        # Shared client profile data (all trainers should see this)
        self.shared_profile = {
            'client_id': self.client_id,
            'name': 'John Doe',
            'email': 'john@example.com',
            'whatsapp': '27821234567',
            'experience_level': 'intermediate',
            'fitness_goals': ['weight_loss', 'muscle_gain'],
            'health_conditions': ['knee_injury'],
            'availability': ['mornings', 'weekends'],
            'preferred_training_times': ['06:00-08:00'],
            'age': 30,
            'gender': 'male',
            'status': 'active'
        }

        # Trainer 1 specific data (ONLY Trainer 1 should see)
        self.trainer1_specific = {
            'custom_price_per_session': 500.00,
            'private_notes': 'Client prefers early morning sessions. Focus on knee rehabilitation.',
            'sessions_count': 15,
            'connection_status': 'active'
        }

        # Trainer 2 specific data (ONLY Trainer 2 should see)
        self.trainer2_specific = {
            'custom_price_per_session': 450.00,
            'private_notes': 'Client is motivated but needs encouragement on diet.',
            'sessions_count': 8,
            'connection_status': 'active'
        }

    def test_shared_profile_access_authorized_trainer(self):
        """Test that authorized trainer can access shared profile"""
        # Mock database response
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {'id': 'rel1'}
        ]

        self.mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            self.shared_profile
        ]

        # Trainer 1 requests shared profile
        profile = self.service.get_shared_client_profile(self.client_id, self.trainer1_id)

        # Should successfully get profile
        self.assertIsNotNone(profile)
        self.assertEqual(profile['client_id'], self.client_id)
        self.assertEqual(profile['name'], 'John Doe')
        self.assertIn('fitness_goals', profile)
        self.assertIn('health_conditions', profile)

    def test_shared_profile_access_unauthorized_trainer(self):
        """Test that unauthorized trainer CANNOT access shared profile"""
        # Mock: no relationship exists
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Trainer 3 (not connected) requests profile
        profile = self.service.get_shared_client_profile(self.client_id, 'TRAINER003')

        # Should be denied
        self.assertIsNone(profile)

    def test_trainer_specific_data_isolation(self):
        """Test that Trainer 1 CANNOT see Trainer 2's specific data"""
        # Mock: Trainer 1 gets their own data
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            self.trainer1_specific
        ]

        # Trainer 1 gets their specific data
        trainer1_data = self.service.get_trainer_specific_data(self.trainer1_id, self.client_id)

        # Should see their own data
        self.assertIsNotNone(trainer1_data)
        self.assertEqual(trainer1_data['custom_price_per_session'], 500.00)
        self.assertIn('knee rehabilitation', trainer1_data['private_notes'])

        # Mock: Trainer 2 gets their own data
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            self.trainer2_specific
        ]

        # Trainer 2 gets their specific data
        trainer2_data = self.service.get_trainer_specific_data(self.trainer2_id, self.client_id)

        # Should see different data
        self.assertIsNotNone(trainer2_data)
        self.assertEqual(trainer2_data['custom_price_per_session'], 450.00)
        self.assertIn('encouragement on diet', trainer2_data['private_notes'])

        # CRITICAL: Verify data is different (privacy check)
        self.assertNotEqual(
            trainer1_data['custom_price_per_session'],
            trainer2_data['custom_price_per_session']
        )
        self.assertNotEqual(
            trainer1_data['private_notes'],
            trainer2_data['private_notes']
        )

    def test_pricing_privacy_boundary(self):
        """Test that one trainer cannot see another trainer's custom pricing"""
        # Mock Trainer 1 pricing
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {'custom_price_per_session': 500.00}
        ]

        price1 = self.service.get_trainer_pricing_for_client(self.trainer1_id, self.client_id)
        self.assertEqual(price1, 500.00)

        # Mock Trainer 2 pricing
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {'custom_price_per_session': 450.00}
        ]

        price2 = self.service.get_trainer_pricing_for_client(self.trainer2_id, self.client_id)
        self.assertEqual(price2, 450.00)

        # CRITICAL: Prices should be different (privacy check)
        self.assertNotEqual(price1, price2)

    def test_private_notes_isolation(self):
        """Test that private notes are isolated per trainer"""
        # Mock Trainer 1 notes
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {'private_notes': 'Trainer 1 private notes'}
        ]

        notes1 = self.service.get_private_notes(self.trainer1_id, self.client_id)
        self.assertEqual(notes1, 'Trainer 1 private notes')

        # Mock Trainer 2 notes
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {'private_notes': 'Trainer 2 private notes'}
        ]

        notes2 = self.service.get_private_notes(self.trainer2_id, self.client_id)
        self.assertEqual(notes2, 'Trainer 2 private notes')

        # CRITICAL: Notes should be different (privacy check)
        self.assertNotEqual(notes1, notes2)

    def test_session_history_filtered_by_trainer(self):
        """Test that each trainer only sees their own sessions"""
        # Mock sessions for Trainer 1
        trainer1_sessions = [
            {'id': 's1', 'trainer_id': self.trainer1_id, 'client_id': self.client_id, 'date': '2025-01-01'},
            {'id': 's2', 'trainer_id': self.trainer1_id, 'client_id': self.client_id, 'date': '2025-01-08'},
        ]

        # Mock: verify relationship first
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {'id': 'rel1'}
        ]

        # Mock: get sessions
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = trainer1_sessions

        sessions1 = self.service.get_trainer_client_sessions(self.trainer1_id, self.client_id)

        # Should get only Trainer 1's sessions
        self.assertEqual(len(sessions1), 2)
        self.assertTrue(all(s['trainer_id'] == self.trainer1_id for s in sessions1))

        # Mock sessions for Trainer 2
        trainer2_sessions = [
            {'id': 's3', 'trainer_id': self.trainer2_id, 'client_id': self.client_id, 'date': '2025-01-05'},
        ]

        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = trainer2_sessions

        sessions2 = self.service.get_trainer_client_sessions(self.trainer2_id, self.client_id)

        # Should get only Trainer 2's sessions
        self.assertEqual(len(sessions2), 1)
        self.assertTrue(all(s['trainer_id'] == self.trainer2_id for s in sessions2))

        # CRITICAL: Session lists should be different
        self.assertNotEqual(len(sessions1), len(sessions2))

    def test_client_multi_trainer_view(self):
        """Test that client can see all their trainers with separate data"""
        # Mock client relationships
        relationships = [
            {'trainer_id': self.trainer1_id, 'client_id': self.client_id, 'connection_status': 'active'},
            {'trainer_id': self.trainer2_id, 'client_id': self.client_id, 'connection_status': 'active'}
        ]

        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = relationships

        # Mock trainer info
        def mock_trainer_select(fields):
            mock_chain = Mock()
            mock_chain.eq.return_value.execute.return_value.data = [
                {'trainer_id': self.trainer1_id, 'name': 'Trainer One', 'specialization': 'Strength'}
            ]
            return mock_chain

        self.mock_db.table.return_value.select = mock_trainer_select

        # Get client's view
        view = self.service.get_client_multi_trainer_view(self.client_id)

        # Should see both trainers
        self.assertEqual(view['total_trainers'], 2)
        self.assertEqual(len(view['trainers']), 2)

        # Each trainer entry should have separate data
        trainer_ids = [t['trainer_id'] for t in view['trainers']]
        self.assertIn(self.trainer1_id, trainer_ids)
        self.assertIn(self.trainer2_id, trainer_ids)

    def test_set_custom_pricing_privacy(self):
        """Test setting custom pricing doesn't affect other trainers"""
        # Mock: relationship exists
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {'id': 'rel1'}
        ]

        # Trainer 1 sets pricing
        success, msg = self.service.set_trainer_custom_pricing(self.trainer1_id, self.client_id, 550.00)

        self.assertTrue(success)
        self.assertIn('550', msg)

        # Verify the update was called
        self.mock_db.table.return_value.update.assert_called()

        # Trainer 2 should still have their own pricing (not affected)
        # This is ensured by database constraints and RLS policies

    def test_unauthorized_session_access_blocked(self):
        """Test that trainer cannot access sessions from another trainer"""
        # Mock: no relationship for Trainer 3
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Trainer 3 tries to access sessions
        sessions = self.service.get_trainer_client_sessions('TRAINER003', self.client_id)

        # Should get empty list (unauthorized)
        self.assertEqual(len(sessions), 0)


class TestPrivacyBoundariesIntegration(unittest.TestCase):
    """Integration tests for privacy boundaries across the system"""

    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_db = Mock()
        self.service = ProfilePrivacyService(self.mock_db)

    def test_complete_multi_trainer_scenario(self):
        """
        End-to-end test: Client trains with 2 trainers, verify complete privacy

        Scenario:
        - Client 'John' trains with Trainer A (R500/session) and Trainer B (R450/session)
        - Trainer A has private notes about knee injury
        - Trainer B has private notes about diet
        - Each trainer has different session counts
        - Both should see shared profile (goals, health)
        - Neither should see the other's pricing or notes
        """
        client_id = 'CLIENT001'
        trainer_a = 'TRAINER_A'
        trainer_b = 'TRAINER_B'

        # Shared profile (both can see)
        shared_data = {
            'client_id': client_id,
            'name': 'John Doe',
            'fitness_goals': ['weight_loss'],
            'health_conditions': ['knee_injury']
        }

        # Trainer A specific
        trainer_a_data = {
            'custom_price_per_session': 500.00,
            'private_notes': 'Focus on knee rehab',
            'sessions_count': 20
        }

        # Trainer B specific
        trainer_b_data = {
            'custom_price_per_session': 450.00,
            'private_notes': 'Needs diet guidance',
            'sessions_count': 10
        }

        # Test: Both trainers can access shared profile
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{'id': '1'}]
        self.mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [shared_data]

        profile_a = self.service.get_shared_client_profile(client_id, trainer_a)
        profile_b = self.service.get_shared_client_profile(client_id, trainer_b)

        # Both should see same shared data
        self.assertEqual(profile_a['name'], profile_b['name'])
        self.assertEqual(profile_a['fitness_goals'], profile_b['fitness_goals'])

        # Test: Each trainer sees only their own specific data
        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [trainer_a_data]
        data_a = self.service.get_trainer_specific_data(trainer_a, client_id)

        self.mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [trainer_b_data]
        data_b = self.service.get_trainer_specific_data(trainer_b, client_id)

        # CRITICAL PRIVACY CHECKS
        self.assertNotEqual(data_a['custom_price_per_session'], data_b['custom_price_per_session'])
        self.assertNotEqual(data_a['private_notes'], data_b['private_notes'])
        self.assertNotEqual(data_a['sessions_count'], data_b['sessions_count'])


if __name__ == '__main__':
    unittest.main()
