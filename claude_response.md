<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0047 -->
<!-- Max Tokens: 8000 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS
The initial project structure looks solid, but there are a few issues to address:
1. Missing `refiloe_handlers.py` which is imported in `services/refiloe.py`
2. Need to improve error handling and response formatting
3. Should add multi-language support helpers

## CHANGES NEEDED

### NEW FILE: services/refiloe_handlers.py
```python
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
```

### EDIT: services/refiloe.py

**Change 1:** Add error message translations
Location: Line 86
```python
# REMOVE:
            return format_response("I apologize, but I encountered an error. Please try again later.")

# ADD:
            error_msg = get_language_response('error_message', message.get('language', 'en'))
            return format_response(error_msg)
```

## SUMMARY
- Created new `refiloe_handlers.py` with implementation for client registration and profile update handlers
- Added multi-language support for error messages
- Improved error handling with proper logging
- Added basic client management functionality

CONTINUE_NEEDED: Yes, next steps should include:
1. Implementing the Client model
2. Adding language detection service
3. Creating SA-specific validation helpers