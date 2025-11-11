"""
Profile Privacy Service
Ensures proper multi-trainer profile privacy and data isolation
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pytz
from utils.logger import log_info, log_error, log_warning


class ProfilePrivacyService:
    """
    Manages profile privacy for multi-trainer scenarios.

    Key Features:
    - Shared client profile data (name, goals, health, experience)
    - Trainer-specific data isolation (pricing, private notes)
    - Session history filtering by trainer
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')

    # =============================================================================
    # SHARED PROFILE ACCESS (All Trainers Can See)
    # =============================================================================

    def get_shared_client_profile(self, client_id: str, trainer_id: str) -> Optional[Dict]:
        """
        Get shared client profile data that all trainers can see.

        Includes: name, goals, experience level, health conditions, availability
        Excludes: pricing, private notes from other trainers

        Args:
            client_id: Client's ID
            trainer_id: Requesting trainer's ID (for verification)

        Returns:
            Dict with shared profile data or None if not authorized
        """
        try:
            # Verify trainer has relationship with client
            if not self._verify_trainer_client_relationship(trainer_id, client_id):
                log_warning(f"Trainer {trainer_id} attempted unauthorized access to client {client_id} profile")
                return None

            # Get shared profile fields only
            result = self.db.table('clients').select(
                'client_id, name, email, whatsapp, '
                'experience_level, fitness_goals, health_conditions, '
                'availability, preferred_training_times, dietary_preferences, '
                'age, gender, status, created_at'
            ).eq('client_id', client_id).execute()

            if result.data:
                log_info(f"Trainer {trainer_id} accessed shared profile for client {client_id}")
                return result.data[0]

            return None

        except Exception as e:
            log_error(f"Error getting shared client profile: {str(e)}")
            return None

    # =============================================================================
    # TRAINER-SPECIFIC DATA (Private per Trainer-Client Relationship)
    # =============================================================================

    def get_trainer_specific_data(self, trainer_id: str, client_id: str) -> Optional[Dict]:
        """
        Get trainer-specific data for a client relationship.

        Includes: custom pricing, private notes, session count

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID

        Returns:
            Dict with trainer-specific data or None if relationship doesn't exist
        """
        try:
            result = self.db.table('trainer_client_list').select(
                'custom_price_per_session, private_notes, sessions_count, '
                'connection_status, created_at, approved_at'
            ).eq('trainer_id', trainer_id).eq('client_id', client_id).execute()

            if result.data:
                log_info(f"Retrieved trainer-specific data for trainer {trainer_id} and client {client_id}")
                return result.data[0]

            return None

        except Exception as e:
            log_error(f"Error getting trainer-specific data: {str(e)}")
            return None

    def set_trainer_custom_pricing(self, trainer_id: str, client_id: str,
                                   custom_price: float) -> Tuple[bool, str]:
        """
        Set custom pricing for trainer-client relationship.
        This pricing is ONLY visible to this specific trainer.

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID
            custom_price: Custom price per session

        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify relationship exists
            if not self._verify_trainer_client_relationship(trainer_id, client_id):
                return False, "No relationship exists between trainer and client"

            # Update pricing in trainer_client_list (trainer-specific)
            self.db.table('trainer_client_list').update({
                'custom_price_per_session': custom_price,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('trainer_id', trainer_id).eq('client_id', client_id).execute()

            log_info(f"Set custom pricing R{custom_price} for trainer {trainer_id} and client {client_id}")
            return True, f"Custom pricing set to R{custom_price}"

        except Exception as e:
            log_error(f"Error setting custom pricing: {str(e)}")
            return False, str(e)

    def get_trainer_pricing_for_client(self, trainer_id: str, client_id: str) -> Optional[float]:
        """
        Get trainer's specific pricing for a client.
        Falls back to trainer's default pricing if no custom price set.

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID

        Returns:
            Price per session or None
        """
        try:
            # First check for custom pricing in relationship
            rel_data = self.get_trainer_specific_data(trainer_id, client_id)

            if rel_data and rel_data.get('custom_price_per_session'):
                log_info(f"Using custom price for trainer {trainer_id} and client {client_id}")
                return float(rel_data['custom_price_per_session'])

            # Fall back to trainer's default pricing
            trainer = self.db.table('trainers').select('pricing_per_session').eq(
                'trainer_id', trainer_id
            ).execute()

            if trainer.data and trainer.data[0].get('pricing_per_session'):
                log_info(f"Using default trainer price for trainer {trainer_id}")
                return float(trainer.data[0]['pricing_per_session'])

            return None

        except Exception as e:
            log_error(f"Error getting trainer pricing: {str(e)}")
            return None

    def set_private_notes(self, trainer_id: str, client_id: str,
                         notes: str) -> Tuple[bool, str]:
        """
        Set private notes for trainer-client relationship.
        These notes are ONLY visible to this specific trainer.

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID
            notes: Private notes

        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify relationship exists
            if not self._verify_trainer_client_relationship(trainer_id, client_id):
                return False, "No relationship exists between trainer and client"

            # Update notes in trainer_client_list (trainer-specific)
            self.db.table('trainer_client_list').update({
                'private_notes': notes,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('trainer_id', trainer_id).eq('client_id', client_id).execute()

            log_info(f"Updated private notes for trainer {trainer_id} and client {client_id}")
            return True, "Private notes updated"

        except Exception as e:
            log_error(f"Error setting private notes: {str(e)}")
            return False, str(e)

    def get_private_notes(self, trainer_id: str, client_id: str) -> Optional[str]:
        """
        Get trainer's private notes for a client.

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID

        Returns:
            Private notes or None
        """
        try:
            rel_data = self.get_trainer_specific_data(trainer_id, client_id)

            if rel_data:
                return rel_data.get('private_notes', '')

            return None

        except Exception as e:
            log_error(f"Error getting private notes: {str(e)}")
            return None

    # =============================================================================
    # SESSION HISTORY (Filtered by Trainer)
    # =============================================================================

    def get_trainer_client_sessions(self, trainer_id: str, client_id: str,
                                    limit: int = 50) -> List[Dict]:
        """
        Get session history for specific trainer-client relationship.
        Each trainer only sees their own sessions with the client.

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID
            limit: Maximum number of sessions to return

        Returns:
            List of session dicts
        """
        try:
            # Verify relationship
            if not self._verify_trainer_client_relationship(trainer_id, client_id):
                log_warning(f"Trainer {trainer_id} attempted unauthorized access to client {client_id} sessions")
                return []

            # Get sessions for this specific trainer-client pair
            result = self.db.table('bookings').select('*').eq(
                'trainer_id', trainer_id
            ).eq('client_id', client_id).order(
                'session_datetime', desc=True
            ).limit(limit).execute()

            log_info(f"Retrieved {len(result.data)} sessions for trainer {trainer_id} and client {client_id}")
            return result.data if result.data else []

        except Exception as e:
            log_error(f"Error getting trainer-client sessions: {str(e)}")
            return []

    # =============================================================================
    # CLIENT DASHBOARD (Multi-Trainer View)
    # =============================================================================

    def get_client_multi_trainer_view(self, client_id: str) -> Dict:
        """
        Get client's view of all their trainers with separate data per trainer.

        Returns:
            {
                'trainers': [
                    {
                        'trainer_id': str,
                        'trainer_name': str,
                        'custom_pricing': float,  # This trainer's pricing for client
                        'session_count': int,  # Sessions with this trainer
                        'last_session': datetime,  # Last session with this trainer
                        'connected_date': datetime
                    },
                    ...
                ],
                'total_trainers': int
            }
        """
        try:
            # Get all active trainer relationships
            relationships = self.db.table('client_trainer_list').select('*').eq(
                'client_id', client_id
            ).eq('connection_status', 'active').execute()

            if not relationships.data:
                return {'trainers': [], 'total_trainers': 0}

            trainers_data = []

            for rel in relationships.data:
                trainer_id = rel.get('trainer_id')

                # Get trainer basic info
                trainer = self.db.table('trainers').select(
                    'trainer_id, name, first_name, last_name, specialization'
                ).eq('trainer_id', trainer_id).execute()

                if not trainer.data:
                    continue

                trainer_info = trainer.data[0]

                # Get trainer-specific data from trainer_client_list
                trainer_specific = self.db.table('trainer_client_list').select(
                    'custom_price_per_session, sessions_count, created_at'
                ).eq('trainer_id', trainer_id).eq('client_id', client_id).execute()

                # Get last session with this trainer
                last_session_result = self.db.table('bookings').select(
                    'session_datetime'
                ).eq('trainer_id', trainer_id).eq('client_id', client_id).order(
                    'session_datetime', desc=True
                ).limit(1).execute()

                last_session = None
                if last_session_result.data:
                    last_session = last_session_result.data[0].get('session_datetime')

                # Compile trainer data
                trainer_data = {
                    'trainer_id': trainer_id,
                    'trainer_name': trainer_info.get('name') or
                                   f"{trainer_info.get('first_name', '')} {trainer_info.get('last_name', '')}".strip(),
                    'specialization': trainer_info.get('specialization', ''),
                    'custom_pricing': None,
                    'session_count': 0,
                    'last_session': last_session,
                    'connected_date': rel.get('created_at')
                }

                if trainer_specific.data:
                    ts_data = trainer_specific.data[0]
                    trainer_data['custom_pricing'] = ts_data.get('custom_price_per_session')
                    trainer_data['session_count'] = ts_data.get('sessions_count', 0)

                trainers_data.append(trainer_data)

            log_info(f"Retrieved multi-trainer view for client {client_id}: {len(trainers_data)} trainers")

            return {
                'trainers': trainers_data,
                'total_trainers': len(trainers_data)
            }

        except Exception as e:
            log_error(f"Error getting client multi-trainer view: {str(e)}")
            return {'trainers': [], 'total_trainers': 0}

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    def _verify_trainer_client_relationship(self, trainer_id: str, client_id: str) -> bool:
        """
        Verify that trainer has an active relationship with client.

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID

        Returns:
            True if active relationship exists, False otherwise
        """
        try:
            result = self.db.table('trainer_client_list').select('id').eq(
                'trainer_id', trainer_id
            ).eq('client_id', client_id).eq(
                'connection_status', 'active'
            ).execute()

            return bool(result.data)

        except Exception as e:
            log_error(f"Error verifying trainer-client relationship: {str(e)}")
            return False
