"""
WhatsApp Flow Data Exchange Handler

This module handles WhatsApp Flow data exchange requests for progressive form data collection.
It manages flow sessions, stores data as the user progresses through the flow, and provides
utilities to retrieve collected data.

Note: This handler does NOT handle encryption/decryption - that is done in the webhook route.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# In-memory storage for flow sessions
# In production, consider using Redis or another persistent store
flow_sessions: Dict[str, Dict[str, Any]] = {}  # Stores data by flow_token
session_timestamps: Dict[str, datetime] = {}  # Track when sessions were created


def cleanup_old_sessions(max_age_hours: int = 2) -> int:
    """
    Remove sessions older than the specified age.

    Args:
        max_age_hours: Maximum age of sessions in hours (default: 2)

    Returns:
        Number of sessions cleaned up
    """
    try:
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=max_age_hours)

        # Find expired sessions
        expired_tokens = [
            token for token, timestamp in session_timestamps.items()
            if timestamp < cutoff_time
        ]

        # Remove expired sessions
        cleanup_count = 0
        for token in expired_tokens:
            if token in flow_sessions:
                del flow_sessions[token]
                cleanup_count += 1
            if token in session_timestamps:
                del session_timestamps[token]

        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} expired flow sessions (older than {max_age_hours} hours)")

        return cleanup_count

    except Exception as e:
        logger.error(f"Error during session cleanup: {str(e)}")
        return 0


def handle_flow_data_exchange(decrypted_data: Dict[str, Any], flow_token: str) -> Dict[str, Any]:
    """
    Handle WhatsApp Flow data exchange requests.

    This function processes different flow actions and manages session data.
    The decrypted_data should already be decrypted by the webhook route.

    Args:
        decrypted_data: The decrypted flow request data
        flow_token: Unique token identifying this flow session

    Returns:
        Response dictionary to be encrypted and sent back to WhatsApp

    Actions handled:
        - ping: Health check
        - INIT: Initialize new flow session
        - data_exchange: Store and process form data
        - navigate: Store data and handle navigation
        - Any other action: Treated as data_exchange
    """
    try:
        # Cleanup old sessions at the start of each request
        cleanup_old_sessions()

        # Extract action from decrypted data
        action = decrypted_data.get('action', '').lower()
        screen = decrypted_data.get('screen', '')
        flow_data = decrypted_data.get('data', {})
        version = decrypted_data.get('version', '3.0')

        logger.info(f"Processing flow action: {action}, screen: {screen}, token: {flow_token}")

        # Handle different actions
        if action == 'ping':
            # Health check - return active status
            logger.info("Received ping request")
            return {
                "version": version,
                "data": {
                    "status": "active"
                }
            }

        elif action == 'init':
            # Initialize new flow session
            flow_sessions[flow_token] = {}
            session_timestamps[flow_token] = datetime.now()
            logger.info(f"Initialized flow session: {flow_token}")

            # For client onboarding flows, retrieve trainer data from flow_tokens table
            initial_data = {}
            if flow_token and 'client_onboarding_invitation' in flow_token:
                try:
                    from app import app
                    db = app.config['supabase']

                    # Query flow_tokens table to get stored trainer data
                    token_result = db.table('flow_tokens').select('data').eq(
                        'flow_token', flow_token
                    ).execute()

                    if token_result.data and token_result.data[0].get('data'):
                        token_data = token_result.data[0]['data']
                        trainer_name = token_data.get('trainer_name', '')
                        selected_price = token_data.get('selected_price')

                        logger.info(f"Retrieved client onboarding data: trainer_name={trainer_name}, selected_price={selected_price}")

                        # Add to initial data
                        initial_data['trainer_name'] = trainer_name
                        initial_data['selected_price'] = str(selected_price) if selected_price else '500'
                        initial_data['flow_token'] = flow_token

                        logger.info(f"Injected initial data for client onboarding: {initial_data}")
                    else:
                        logger.warning(f"No flow_tokens data found for token: {flow_token}")
                except Exception as e:
                    logger.error(f"Error retrieving flow_tokens data: {str(e)}")

            # Return screen routing information with initial data
            return {
                "version": version,
                "screen": "welcome",
                "data": initial_data
            }

        elif action == 'data_exchange':
            # Get existing session or create new one
            if flow_token not in flow_sessions:
                flow_sessions[flow_token] = {}
                session_timestamps[flow_token] = datetime.now()
                logger.info(f"Created new session during data_exchange: {flow_token}")

            # Update session with incoming data
            if flow_data:
                # Merge incoming data with existing session data
                flow_sessions[flow_token].update(flow_data)

                # Log what data was received
                logger.info(f"Received data for session {flow_token}: {json.dumps(flow_data, indent=2)}")
                logger.info(f"Current session data: {json.dumps(flow_sessions[flow_token], indent=2)}")
            else:
                logger.info(f"No data in data_exchange request for session {flow_token}")

            # Update timestamp
            session_timestamps[flow_token] = datetime.now()

            # Check if this is a pricing calculation request from HEALTH_NOTES screen
            if screen == "HEALTH_NOTES" and flow_data.get("operation") == "calculate_pricing":
                logger.info(f"Processing pricing calculation from HEALTH_NOTES screen for session {flow_token}")

                # Get pricing data
                pricing_choice = flow_data.get("pricing_choice", "use_default")
                trainer_default_price = flow_data.get("trainer_default_price", "R500")
                custom_price_amount = flow_data.get("custom_price_amount", "")

                logger.info(f"Pricing calculation - choice: {pricing_choice}, default: {trainer_default_price}, custom: {custom_price_amount}")

                # Clean up price strings (remove "R" if present)
                trainer_default_price = trainer_default_price.replace("R", "").strip()
                custom_price_amount = custom_price_amount.replace("R", "").strip() if custom_price_amount else ""

                # Calculate actual price
                if pricing_choice == "use_default":
                    calculated_price = f"R{trainer_default_price}"
                else:
                    calculated_price = f"R{custom_price_amount}" if custom_price_amount else f"R{trainer_default_price}"

                logger.info(f"Calculated price: {calculated_price}")

                # Add calculated price to the data
                flow_data["calculated_price"] = calculated_price

                # Update session with calculated price
                flow_sessions[flow_token]["calculated_price"] = calculated_price

                # Return navigation response to CONFIRMATION screen
                response = {
                    "version": version,
                    "screen": "CONFIRMATION",
                    "data": flow_data  # This includes all original data plus calculated_price
                }

                logger.info(f"Returning pricing calculation response: {json.dumps(response, indent=2)}")
                return response

            return {
                "version": version,
                "data": {}
            }

        elif action == 'calculate_pricing':
            # Handle pricing calculation from HEALTH_NOTES screen
            logger.info(f"Processing calculate_pricing action for session {flow_token}")

            # Get existing session or create new one
            if flow_token not in flow_sessions:
                flow_sessions[flow_token] = {}
                session_timestamps[flow_token] = datetime.now()
                logger.info(f"Created new session during calculate_pricing: {flow_token}")

            # Merge all incoming data into session first
            all_data = {}

            # Get data from the decrypted_data root level (where form fields are sent)
            for key, value in decrypted_data.items():
                if key not in ['action', 'screen', 'flow_token', 'version', 'data']:
                    all_data[key] = value

            # Also get data from the nested 'data' object if present
            if flow_data:
                all_data.update(flow_data)

            # Store in session
            flow_sessions[flow_token].update(all_data)
            session_timestamps[flow_token] = datetime.now()

            # Extract pricing fields
            pricing_choice = all_data.get('pricing_choice', '')
            trainer_default_price = all_data.get('trainer_default_price', '')
            custom_price_amount = all_data.get('custom_price_amount', '')

            logger.info(f"Pricing calculation - choice: {pricing_choice}, default: {trainer_default_price}, custom: {custom_price_amount}")

            # Calculate the actual price based on the pricing_choice
            calculated_price = ""

            if pricing_choice == "use_default":
                # Use the trainer's default price
                calculated_price = trainer_default_price
            elif pricing_choice == "custom_price":
                # Use custom price if provided, otherwise fall back to default
                if custom_price_amount and custom_price_amount.strip():
                    calculated_price = custom_price_amount
                else:
                    # Fallback to trainer default if custom is empty
                    calculated_price = trainer_default_price
            else:
                # Fallback to default price if pricing_choice is unexpected
                calculated_price = trainer_default_price

            logger.info(f"Calculated price: {calculated_price}")

            # Add calculated_price to the data
            all_data['calculated_price'] = calculated_price

            # Update session with calculated price
            flow_sessions[flow_token]['calculated_price'] = calculated_price

            # Return response navigating to CONFIRMATION screen with all data including calculated_price
            response = {
                "version": version,
                "screen": "CONFIRMATION",
                "data": all_data
            }

            logger.info(f"Returning calculate_pricing response: {json.dumps(response, indent=2)}")

            return response

        else:
            # Any other action (like "navigate", "BACK", etc.)
            # Treat as data_exchange - store any data that came with it
            if flow_token not in flow_sessions:
                flow_sessions[flow_token] = {}
                session_timestamps[flow_token] = datetime.now()
                logger.info(f"Created new session during action '{action}': {flow_token}")

            # Store any data that came with the request
            if flow_data:
                flow_sessions[flow_token].update(flow_data)
                logger.info(f"Stored data for action '{action}' in session {flow_token}: {json.dumps(flow_data, indent=2)}")

            # Update timestamp
            session_timestamps[flow_token] = datetime.now()

            logger.info(f"Processed action '{action}' for session {flow_token}")

            return {
                "version": version,
                "data": {}
            }

    except Exception as e:
        logger.error(f"Error handling flow data exchange: {str(e)}", exc_info=True)
        # Return error response
        return {
            "version": "3.0",
            "data": {
                "error": "Internal server error"
            }
        }


def get_collected_data(flow_token: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve all data collected for a specific flow session.

    Args:
        flow_token: The unique token identifying the flow session

    Returns:
        Dictionary containing all collected data, or None if session doesn't exist
    """
    try:
        if flow_token not in flow_sessions:
            logger.warning(f"Attempted to retrieve data for non-existent session: {flow_token}")
            return None

        data = flow_sessions[flow_token]
        logger.info(f"Retrieved data for session {flow_token}: {len(data)} fields")
        return data

    except Exception as e:
        logger.error(f"Error retrieving collected data for {flow_token}: {str(e)}")
        return None


def get_session_info(flow_token: str) -> Optional[Dict[str, Any]]:
    """
    Get session metadata and information.

    Args:
        flow_token: The unique token identifying the flow session

    Returns:
        Dictionary containing session info, or None if session doesn't exist
    """
    try:
        if flow_token not in flow_sessions:
            return None

        return {
            'flow_token': flow_token,
            'created_at': session_timestamps.get(flow_token),
            'data_fields': list(flow_sessions[flow_token].keys()),
            'field_count': len(flow_sessions[flow_token])
        }

    except Exception as e:
        logger.error(f"Error retrieving session info for {flow_token}: {str(e)}")
        return None


def delete_session(flow_token: str) -> bool:
    """
    Delete a flow session and all its data.

    Args:
        flow_token: The unique token identifying the flow session

    Returns:
        True if session was deleted, False if it didn't exist
    """
    try:
        if flow_token not in flow_sessions:
            logger.warning(f"Attempted to delete non-existent session: {flow_token}")
            return False

        del flow_sessions[flow_token]
        if flow_token in session_timestamps:
            del session_timestamps[flow_token]

        logger.info(f"Deleted flow session: {flow_token}")
        return True

    except Exception as e:
        logger.error(f"Error deleting session {flow_token}: {str(e)}")
        return False


def get_all_sessions() -> Dict[str, Dict[str, Any]]:
    """
    Get information about all active sessions.

    Returns:
        Dictionary mapping flow_tokens to session info
    """
    try:
        all_sessions = {}
        for token in flow_sessions.keys():
            all_sessions[token] = get_session_info(token)

        logger.info(f"Retrieved info for {len(all_sessions)} active sessions")
        return all_sessions

    except Exception as e:
        logger.error(f"Error retrieving all sessions: {str(e)}")
        return {}
