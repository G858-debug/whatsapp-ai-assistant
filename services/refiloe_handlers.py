from typing import Dict, Any
from services.helpers.whatsapp_helpers import format_response
from services.helpers.sa_language_helper import get_language_response
from models.client import Client
import logging

logger = logging.getLogger(__name__)

def handle_client_registration(message: Dict[str, Any]) -> str:
    """Handle new client registration requests"""
    try:
        phone = message.get('from', '')
        if not phone:
            return format_response("Invalid phone number received")
            
        # Check if client already exists
        existing_client = Client.get_by_phone(phone)
        if existing_client:
            return format_response("You are already registered! Need help? Just ask.")
            
        # Start registration flow
        return format_response(
            "Welcome to Refiloe! Let's get you registered.\n"
            "Please share your:\n"
            "1. Full name\n"
            "2. Preferred language (English/Afrikaans/Xhosa/Zulu/Sotho)\n"
            "3. Fitness goals"
        )
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return format_response("Sorry, there was an error with registration. Please try again.")

def handle_client_profile_update(message: Dict[str, Any]) -> str:
    """Handle client profile update requests"""
    try:
        phone = message.get('from', '')
        client = Client.get_by_phone(phone)
        
        if not client:
            return format_response("Please register first before updating your profile.")
            
        return format_response(
            "What would you like to update?\n"
            "1. Name\n"
            "2. Language preference\n"
            "3. Fitness goals\n"
            "Reply with the number of your choice."
        )
        
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return format_response("Sorry, there was an error. Please try again later.")