from typing import Dict, Any
from services.helpers.whatsapp_helpers import format_response
from services.helpers.validation_helpers import validate_client_data
from models.client import Client
import logging

logger = logging.getLogger(__name__)

def handle_client_registration(message: Dict[str, Any]) -> str:
    """
    Handle new client registration requests
    """
    try:
        # Extract phone number from message
        phone = message.get('from', '')
        
        # Check if client already exists
        existing_client = Client.get_by_phone(phone)
        if existing_client:
            return format_response("You are already registered! Need help with something else?")
            
        # Start registration flow
        return format_response(
            "Welcome to Refiloe! Let's get you registered.\n\n"
            "Please reply with your:\n"
            "1. Full Name\n"
            "2. Preferred Language (English, Afrikaans, Xhosa, Zulu, Sotho)\n"
            "3. Fitness Goals"
        )
        
    except Exception as e:
        logger.error(f"Error in client registration: {str(e)}")
        return format_response("Sorry, there was an error with registration. Please try again later.")

def handle_client_profile_update(message: Dict[str, Any]) -> str:
    """
    Handle client profile update requests
    """
    try:
        phone = message.get('from', '')
        client = Client.get_by_phone(phone)
        
        if not client:
            return format_response("Please register first before updating your profile.")
            
        return format_response(
            "What would you like to update?\n\n"
            "1. Name\n"
            "2. Language Preference\n"
            "3. Fitness Goals\n\n"
            "Reply with the number of your choice."
        )
        
    except Exception as e:
        logger.error(f"Error in profile update: {str(e)}")
        return format_response("Sorry, there was an error. Please try again later.")