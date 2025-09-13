<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0034 -->
<!-- Max Tokens: 8000 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS
Looking at the code, the Refiloe WhatsApp assistant needs enhancements to better handle South African context and multilingual support. The current intent detection is basic and needs expansion for local languages and context.

## CHANGES NEEDED

### EDIT: services/refiloe.py

**Change 1:** Expand intent keywords with more South African languages and context
Location: Lines 15-22
```python
# REMOVE (lines 15-22):
    INTENT_KEYWORDS = {
        'client_registration': ['register', 'sign up', 'join', 'skryf in', 'ngodiso'],
        'client_profile_update': ['update profile', 'edit profile', 'change details', 'verander', 'hleng'],
        'payment_request': ['pay', 'payment', 'invoice', 'EFT', 'rand', 'R', 'ZAR', 'betaal'],
        'calendar_request': ['book', 'schedule', 'appointment', 'bespreek', 'ukubhukisha'],
        'gamification_request': ['points', 'rewards', 'achievements', 'punte', 'amanqaku'],
        'habits_request': ['habit', 'track', 'progress', 'gewoonte', 'umkhuba']
    }

# ADD:
    INTENT_KEYWORDS = {
        'client_registration': ['register', 'sign up', 'join', 'skryf in', 'ngodiso', 'bhalisa', 'ingoda', 'rejistara'],
        'client_profile_update': ['update profile', 'edit profile', 'change details', 'verander', 'hleng', 'buyekeza', 'fetola'],
        'payment_request': ['pay', 'payment', 'invoice', 'EFT', 'rand', 'R', 'ZAR', 'betaal', 'khokha', 'patala', 'lefela'],
        'calendar_request': ['book', 'schedule', 'appointment', 'bespreek', 'ukubhukisha', 'tshwaya', 'hlela', 'beya'],
        'gamification_request': ['points', 'rewards', 'achievements', 'punte', 'amanqaku', 'meputso', 'dimaka', 'umbuyekezo'],
        'habits_request': ['habit', 'track', 'progress', 'gewoonte', 'umkhuba', 'mokgwa', 'meetlo', 'isiko'],
        'help_request': ['help', 'support', 'assist', 'hulp', 'nceda', 'thusa', 'siza']
    }
```

**Change 2:** Enhance intent detection with confidence scoring
Location: Lines 44-48
```python
# REMOVE (lines 44-48):
    def detect_intent(self, message_text: str) -> str:
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in message_text for keyword in keywords):
                return intent
        return 'unknown'

# ADD:
    def detect_intent(self, message_text: str) -> tuple[str, float]:
        message_text = message_text.lower()
        best_intent = 'unknown'
        highest_confidence = 0.0
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            confidence = 0.0
            for keyword in keywords:
                if keyword in message_text:
                    # Higher confidence for exact matches
                    if keyword == message_text.strip():
                        confidence = max(confidence, 1.0)
                    else:
                        confidence = max(confidence, 0.7)
                # Partial matches
                elif any(part in message_text for part in keyword.split()):
                    confidence = max(confidence, 0.4)
            
            if confidence > highest_confidence:
                highest_confidence = confidence
                best_intent = intent
        
        return best_intent, highest_confidence
```

### NEW FILE: services/helpers/sa_language_helper.py
```python
from typing import Dict, List

class SALanguageHelper:
    """Helper class for South African language support"""
    
    LANGUAGES = {
        'en': 'English',
        'af': 'Afrikaans',
        'zu': 'isiZulu',
        'xh': 'isiXhosa',
        'st': 'Sesotho',
        'tn': 'Setswana',
        'nso': 'Sepedi',
        'ts': 'Xitsonga',
        'ss': 'siSwati',
        've': 'Tshivenda',
        'nr': 'isiNdebele'
    }
    
    COMMON_PHRASES = {
        'greeting': {
            'en': 'Hello',
            'af': 'Hallo',
            'zu': 'Sawubona',
            'xh': 'Molo',
            'st': 'Dumela',
            'tn': 'Dumela',
            'nso': 'Thobela',
        },
        'thank_you': {
            'en': 'Thank you',
            'af': 'Dankie',
            'zu': 'Ngiyabonga',
            'xh': 'Enkosi',
            'st': 'Ke a leboha',
            'tn': 'Ke a leboga',
            'nso': 'Ke a leboga',
        }
    }
    
    @staticmethod
    def get_greeting(language_code: str) -> str:
        return SALanguageHelper.COMMON_PHRASES['greeting'].get(language_code, 'Hello')
    
    @staticmethod
    def get_thank_you(language_code: str) -> str:
        return SALanguageHelper.COMMON_PHRASES['thank_you'].get(language_code, 'Thank you')
```

## SUMMARY
- Enhanced intent detection with more South African language keywords
- Added confidence scoring for better intent matching
- Created new language helper for multilingual support
- Added support for all 11 official SA languages
- Improved keyword matching with exact and partial match handling

CONTINUE_NEEDED: Yes - Next steps would include integrating the language helper with the main Refiloe class and adding more sophisticated NLP features.