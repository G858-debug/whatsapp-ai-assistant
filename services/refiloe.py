from services.ai_intent_handler import handle_intent
from services.refiloe_handlers import handle_client_registration, handle_client_profile_update
from services.payment_manager import handle_payment_request
from services.calendar_service import handle_calendar_request
from services.gamification_manager import handle_gamification_request
from services.habits import handle_habits_request

class Refiloe:
    def handle_message(self, message):
        intent = self.detect_intent(message)
        if intent == 'client_registration':
            handle_client_registration(message)
        elif intent == 'client_profile_update':
            handle_client_profile_update(message)
        elif intent == 'payment_request':
            handle_payment_request(message)
        elif intent == 'calendar_request':
            handle_calendar_request(message)
        elif intent == 'gamification_request':
            handle_gamification_request(message)
        elif intent == 'habits_request':
            handle_habits_request(message)
        else:
            handle_intent(message)

    def detect_intent(self, message):
        # Implement intent detection logic here
        return 'client_registration'