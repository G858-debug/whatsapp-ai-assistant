"""
Client Checker Service
Robust service to check client status for trainer-client relationship scenarios

Usage Example:
    from services.relationships.client_checker import ClientChecker, SCENARIO_NEW

    # Initialize with Supabase client
    checker = ClientChecker(supabase_client)

    # Check client status
    result = checker.check_client_status('+27821234567', 'TRAINER001')

    # Handle scenarios
    if result['scenario'] == SCENARIO_NEW:
        # Client doesn't exist - can create new
        print(f"Can create new client: {result['message']}")

    elif result['scenario'] == SCENARIO_AVAILABLE:
        # Client exists but has no trainer - can add
        client_name = result['client_data']['name']
        print(f"Can add existing client: {client_name}")

    elif result['scenario'] == SCENARIO_ALREADY_YOURS:
        # Already this trainer's client
        status = result['relationship']['connection_status']
        print(f"Already your client, status: {status}")

    elif result['scenario'] == SCENARIO_HAS_OTHER_TRAINER:
        # Has different trainer
        other_trainer = result['trainer_info']['name']
        print(f"Client already has trainer: {other_trainer}")

Response Structure:
    {
        'scenario': str,           # One of: new, available, already_yours, has_other_trainer
        'client_data': Dict|None,  # Client information if exists
        'trainer_info': Dict|None, # Trainer information if applicable
        'relationship': Dict|None, # Relationship data if exists
        'normalized_phone': str,   # Normalized phone number used for lookup
        'message': str,            # Human-readable description
        'error': bool             # True if an error occurred
    }
"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from utils.phone_utils import normalize_phone_number

# Scenario constants
SCENARIO_NEW = "new"
SCENARIO_AVAILABLE = "available"
SCENARIO_ALREADY_YOURS = "already_yours"
SCENARIO_HAS_OTHER_TRAINER = "has_other_trainer"


class ClientChecker:
    """
    Handles all client status checking scenarios when a trainer tries to add a client.

    Scenarios:
    1. SCENARIO_NEW: Client doesn't exist in the system
    2. SCENARIO_AVAILABLE: Client exists but has no active trainer
    3. SCENARIO_ALREADY_YOURS: Client exists and is already this trainer's client
    4. SCENARIO_HAS_OTHER_TRAINER: Client exists and has a different active trainer
    """

    def __init__(self, supabase_client):
        """
        Initialize the ClientChecker service.

        Args:
            supabase_client: Supabase database client
        """
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        log_info("ClientChecker service initialized")

    def check_client_status(self, phone_number: str, trainer_id: str) -> Dict:
        """
        Check client status and determine which scenario applies.

        Args:
            phone_number: Client's phone number (can be in any format: +27, 27, 0)
            trainer_id: Trainer's ID who wants to add the client

        Returns:
            Dict containing:
                - scenario: One of the SCENARIO_* constants
                - client_data: Client information if exists, None otherwise
                - trainer_info: Current trainer info if applicable, None otherwise
                - relationship: Relationship data if exists, None otherwise
                - normalized_phone: Normalized phone number used for lookup
                - message: Human-readable description of the scenario
        """
        try:
            # Normalize phone number for consistent lookup
            normalized_phone = normalize_phone_number(phone_number)

            if not normalized_phone:
                log_error(f"Invalid phone number provided: {phone_number}")
                return {
                    'scenario': None,
                    'client_data': None,
                    'trainer_info': None,
                    'relationship': None,
                    'normalized_phone': None,
                    'message': 'Invalid phone number format',
                    'error': True
                }

            log_info(f"Checking client status for phone: {phone_number} (normalized: {normalized_phone}), trainer: {trainer_id}")

            # Step 1: Check if client exists in the system
            client_data = self._get_client_by_phone(normalized_phone)

            if not client_data:
                # SCENARIO 1: Client doesn't exist - ready to create new
                log_info(f"SCENARIO_NEW: Client with phone {normalized_phone} does not exist")
                return {
                    'scenario': SCENARIO_NEW,
                    'client_data': None,
                    'trainer_info': None,
                    'relationship': None,
                    'normalized_phone': normalized_phone,
                    'message': 'Client does not exist in the system. Ready to create new client.',
                    'error': False
                }

            # Client exists - get their client_id for relationship checks
            client_id = client_data.get('client_id')
            log_info(f"Client found: {client_id} - {client_data.get('name')}")

            # Step 2: Check for active relationships
            active_relationships = self._get_active_relationships(client_id)

            if not active_relationships:
                # SCENARIO 2: Client exists but has no active trainer
                log_info(f"SCENARIO_AVAILABLE: Client {client_id} exists but has no active trainer")
                return {
                    'scenario': SCENARIO_AVAILABLE,
                    'client_data': client_data,
                    'trainer_info': None,
                    'relationship': None,
                    'normalized_phone': normalized_phone,
                    'message': f'Client exists ({client_data.get("name")}) but has no active trainer. Can be added.',
                    'error': False
                }

            # Step 3: Check if this trainer already has relationship with this client
            current_relationship = self._check_trainer_client_relationship(trainer_id, client_id)

            if current_relationship:
                # SCENARIO 3: This trainer already has this client
                log_info(f"SCENARIO_ALREADY_YOURS: Trainer {trainer_id} already has client {client_id} (status: {current_relationship.get('connection_status')})")

                # Get trainer info for completeness
                trainer_info = self._get_trainer_info(trainer_id)

                return {
                    'scenario': SCENARIO_ALREADY_YOURS,
                    'client_data': client_data,
                    'trainer_info': trainer_info,
                    'relationship': current_relationship,
                    'normalized_phone': normalized_phone,
                    'message': f'Client ({client_data.get("name")}) is already your client. Relationship status: {current_relationship.get("connection_status")}',
                    'error': False
                }

            # Step 4: Client has a different trainer
            # Get the other trainer's info
            other_trainer_id = active_relationships[0].get('trainer_id')
            other_trainer_info = self._get_trainer_info(other_trainer_id)
            other_relationship = active_relationships[0]

            log_info(f"SCENARIO_HAS_OTHER_TRAINER: Client {client_id} has different trainer {other_trainer_id}")

            return {
                'scenario': SCENARIO_HAS_OTHER_TRAINER,
                'client_data': client_data,
                'trainer_info': other_trainer_info,
                'relationship': other_relationship,
                'normalized_phone': normalized_phone,
                'message': f'Client ({client_data.get("name")}) already has an active trainer: {other_trainer_info.get("name", "Unknown")}',
                'error': False
            }

        except Exception as e:
            log_error(f"Error checking client status: {str(e)}")
            return {
                'scenario': None,
                'client_data': None,
                'trainer_info': None,
                'relationship': None,
                'normalized_phone': None,
                'message': f'Error checking client status: {str(e)}',
                'error': True
            }

    def _get_client_by_phone(self, normalized_phone: str) -> Optional[Dict]:
        """
        Get client data by normalized phone number.

        Args:
            normalized_phone: Normalized phone number

        Returns:
            Client data dict or None if not found
        """
        try:
            result = self.db.table('clients').select('*').eq(
                'whatsapp', normalized_phone
            ).execute()

            if result.data and len(result.data) > 0:
                log_info(f"Client found with phone {normalized_phone}: {result.data[0].get('client_id')}")
                return result.data[0]

            log_info(f"No client found with phone {normalized_phone}")
            return None

        except Exception as e:
            log_error(f"Error getting client by phone {normalized_phone}: {str(e)}")
            return None

    def _get_active_relationships(self, client_id: str) -> list:
        """
        Get all active relationships for a client.

        Args:
            client_id: Client's ID

        Returns:
            List of active relationship dicts
        """
        try:
            result = self.db.table('client_trainer_list').select('*').eq(
                'client_id', client_id
            ).eq('connection_status', 'active').execute()

            relationships = result.data if result.data else []

            if relationships:
                log_info(f"Found {len(relationships)} active relationship(s) for client {client_id}")
            else:
                log_info(f"No active relationships found for client {client_id}")

            return relationships

        except Exception as e:
            log_error(f"Error getting active relationships for client {client_id}: {str(e)}")
            return []

    def _check_trainer_client_relationship(self, trainer_id: str, client_id: str) -> Optional[Dict]:
        """
        Check if specific trainer-client relationship exists.

        Args:
            trainer_id: Trainer's ID
            client_id: Client's ID

        Returns:
            Relationship dict or None if not found
        """
        try:
            result = self.db.table('trainer_client_list').select('*').eq(
                'trainer_id', trainer_id
            ).eq('client_id', client_id).execute()

            if result.data and len(result.data) > 0:
                relationship = result.data[0]
                log_info(f"Relationship found between trainer {trainer_id} and client {client_id}: {relationship.get('connection_status')}")
                return relationship

            log_info(f"No relationship found between trainer {trainer_id} and client {client_id}")
            return None

        except Exception as e:
            log_error(f"Error checking trainer-client relationship: {str(e)}")
            return None

    def _get_trainer_info(self, trainer_id: str) -> Optional[Dict]:
        """
        Get trainer information by trainer_id.

        Args:
            trainer_id: Trainer's ID

        Returns:
            Trainer data dict or None if not found
        """
        try:
            result = self.db.table('trainers').select(
                'trainer_id, name, first_name, last_name, specialization, experience_years, whatsapp'
            ).eq('trainer_id', trainer_id).execute()

            if result.data and len(result.data) > 0:
                log_info(f"Trainer info retrieved for {trainer_id}")
                return result.data[0]

            log_info(f"No trainer found with ID {trainer_id}")
            return None

        except Exception as e:
            log_error(f"Error getting trainer info for {trainer_id}: {str(e)}")
            return None


# Convenience function for quick access
def check_client_status(supabase_client, phone_number: str, trainer_id: str) -> Dict:
    """
    Convenience function to check client status without instantiating the class.

    Args:
        supabase_client: Supabase database client
        phone_number: Client's phone number
        trainer_id: Trainer's ID

    Returns:
        Status dict with scenario and related data
    """
    checker = ClientChecker(supabase_client)
    return checker.check_client_status(phone_number, trainer_id)
