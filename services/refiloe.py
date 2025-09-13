from services.ai_intent_handler import handle_intent
from services.refiloe_handlers import handle_client_registration, handle_client_profile_update
from services.payment_manager import handle_payment_request
from services.calendar_service import handle_calendar_request
from services.gamification_manager import handle_gamification_request
from services.habits import handle_habits_request

from typing import Dict, Any
import logging
from services.helpers.whatsapp_helpers import format_response

logger = logging.getLogger(__name__)

class Refiloe:
    INTENT_KEYWORDS = {
        'client_registration': [
            'register', 'sign up', 'join', 
            'skryf in', 'registreer', # Afrikaans
            'ngodiso', 'bhalisa', 'ingoda', # Xhosa
            'rejistara', 'ngoliso', # Sotho
            'rejisetara', 'ikwadayisa', # Zulu
            'ingodiso', 'ngwadisa' # Tswana
        ],
        'client_profile_update': [
            'update profile', 'edit profile', 'change details',
            'verander profiel', 'wysig profiel', # Afrikaans 
            'hleng profayile', 'buyekeza', # Xhosa
            'fetola profaele', 'ntjhafatsa', # Sotho
            'shintja', 'buyekeza imininingwane' # Zulu
        ],
        'payment_request': [
            'pay', 'payment', 'invoice', 'EFT', 'rand', 'R', 'ZAR',
            'betaal', 'betaling', 'rekening', # Afrikaans
            'khokha', 'intlawulo', # Xhosa
            'patala', 'tefello', # Sotho
            'bhatala', 'inkokhelo' # Zulu
        ],
        'calendar_request': [
            'book', 'schedule', 'appointment',
            'bespreek', 'afspraak', # Afrikaans
            'ukubhukisha', 'idinga', # Xhosa
            'buka', 'peeletso', # Sotho
            'hlela', 'ukuhlela' # Zulu
        ],
        'gamification_request': [
            'points', 'rewards', 'achievements',
            'punte', 'belonings', # Afrikaans
            'amanqaku', 'imivuzo', # Xhosa
            'meputso', 'dikatleho', # Sotho
            'amaphuzu', 'imiklomelo' # Zulu
        ],
        'habits_request': [
            'habit', 'track', 'progress',
            'gewoonte', 'vordering', # Afrikaans
            'umkhuba', 'inkqubela', # Xhosa
            'meetlo', 'tswellopele', # Sotho
            'umkhuba', 'intuthuko' # Zulu
        ],
        'help_request': [
            'help', 'support', 'assist',
            'hulp', 'ondersteuning', # Afrikaans
            'nceda', 'uncedo', # Xhosa
            'thusa', 'thuso', # Sotho
            'siza', 'usizo' # Zulu
        ]
    }

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

    def detect_intent(self, message_text: str) -> str:
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in message_text for keyword in keywords):
                return intent
        return 'unknown'