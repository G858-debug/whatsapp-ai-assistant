<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0048 -->
<!-- Max Tokens: 8000 -->
## ANALYSIS
Looking at the codebase, `services/refiloe.py` needs some key improvements:
1. Missing error handler import
2. Missing language response helper
3. Better error handling structure needed
4. Type hints need improvement

## CHANGES NEEDED

### EDIT: services/refiloe.py

**Change 1:** Add missing imports
Location: After line 10
```python
# ADD:
from services.helpers.error_handlers import handle_whatsapp_error
from services.helpers.sa_language_helper import get_language_response
```

**Change 2:** Improve type hints and error handling
Location: Lines 68-87
```python
# REMOVE (lines 68-87):
    def handle_message(self, message: Dict[str, Any]) -> str:
        try:
            intent = self.detect_intent(message.get('text', '').lower())
            
            intent_handlers = {
                'client_registration': handle_client_registration,
                'client_profile_update': handle_client_profile_update,
                'payment_request': handle_payment_request,
                'calendar_request': handle_calendar_request,
                'gamification_request': handle_gamification_request,
                'habits_request': handle_habits_request
            }
            
            handler = intent_handlers.get(intent, handle_intent)
            return handler(message)
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            error_msg = get_language_response('error_message', message.get('language', 'en'))
            return format_response(error_msg)

# ADD:
    def handle_message(self, message: Dict[str, Any]) -> str:
        """Handle incoming WhatsApp messages and route to appropriate handler"""
        try:
            if not message.get('text'):
                return format_response(get_language_response('invalid_message', 
                    message.get('language', 'en')))
                
            intent = self.detect_intent(message['text'].lower())
            
            intent_handlers: Dict[str, Callable] = {
                'client_registration': handle_client_registration,
                'client_profile_update': handle_client_profile_update,
                'payment_request': handle_payment_request,
                'calendar_request': handle_calendar_request,
                'gamification_request': handle_gamification_request,
                'habits_request': handle_habits_request
            }
            
            handler = intent_handlers.get(intent, handle_intent)
            return handler(message)
            
        except Exception as e:
            return handle_whatsapp_error(e, message.get('language', 'en'))
```

**Change 3:** Improve intent detection type hints
Location: Lines 89-93
```python
# REMOVE (lines 89-93):
    def detect_intent(self, message_text: str) -> str:
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in message_text for keyword in keywords):
                return intent
        return 'unknown'

# ADD:
    def detect_intent(self, message_text: str) -> str:
        """Detect intent from message text using keyword matching"""
        message_text = message_text.strip().lower()
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in message_text for keyword in keywords):
                return intent
        return 'unknown'
```

## SUMMARY
- Added missing imports for error handling and language helpers
- Improved type hints throughout the file
- Added better input validation for messages
- Improved error handling using dedicated handler
- Added docstrings for key methods
- Enhanced intent detection with better text preprocessing

These changes make the code more robust, type-safe, and better at handling errors while maintaining the core functionality.