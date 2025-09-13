<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0037 -->
<!-- Max Tokens: 8000 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS
The project needs to enhance Refiloe's intent detection and language support. The current implementation in services/refiloe.py can be improved by:
1. Adding more South African language keywords
2. Improving intent detection with confidence scores
3. Adding language detection capabilities

## CHANGES NEEDED

### EDIT: services/refiloe.py

**Change 1:** Expand INTENT_KEYWORDS with more SA languages
Location: Lines 15-23
```python
# REMOVE:
    INTENT_KEYWORDS = {
        'client_registration': ['register', 'sign up', 'join', 'skryf in', 'ngodiso', 'bhalisa', 'ingoda', 'rejistara', 'ngoliso'],
        'client_profile_update': ['update profile', 'edit profile', 'change details', 'verander', 'hleng', 'buyekeza', 'fetola', 'shintja'],
        'payment_request': ['pay', 'payment', 'invoice', 'EFT', 'rand', 'R', 'ZAR', 'betaal', 'khokha', 'patala', 'lefela', 'bhatala'],
        'calendar_request': ['book', 'schedule', 'appointment', 'bespreek', 'ukubhukisha', 'tshwaya', 'hlela', 'beya', 'dibuka'],
        'gamification_request': ['points', 'rewards', 'achievements', 'punte', 'amanqaku', 'meputso', 'dimaka', 'umbuyekezo', 'imivuzo'],
        'habits_request': ['habit', 'track', 'progress', 'gewoonte', 'umkhuba', 'mokgwa', 'meetlo', 'isiko', 'inkuliso'],
        'help_request': ['help', 'support', 'assist', 'hulp', 'nceda', 'thusa', 'siza', 'nncedo']
    }

# ADD:
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
```

**Change 2:** Improve intent detection with confidence scoring
Location: Lines 45-49
```python
# REMOVE:
    def detect_intent(self, message_text: str) -> str:
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in message_text for keyword in keywords):
                return intent
        return 'unknown'

# ADD:
    def detect_intent(self, message_text: str) -> tuple[str, float]:
        best_intent = 'unknown'
        highest_confidence = 0.0
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            matches = sum(keyword in message_text for keyword in keywords)
            if matches > 0:
                confidence = matches / len(message_text.split())
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_intent = intent
        
        return best_intent, highest_confidence
```

### NEW FILE: services/helpers/language_detector.py
```python
from typing import Dict, List, Tuple
import re

class SALanguageDetector:
    """Detects South African languages in text"""
    
    LANGUAGE_MARKERS = {
        'en': ['the', 'is', 'are', 'what', 'when', 'how'],
        'af': ['die', 'is', 'wat', 'wanneer', 'hoe', 'en'],
        'xh': ['le', 'phi', 'njani', 'nini', 'ukuba'],
        'zu': ['le', 'phi', 'kanjani', 'nini', 'ukuthi'],
        'st': ['ke', 'eng', 'jwang', 'neng', 'hore'],
        'tn': ['ke', 'eng', 'jang', 'leng', 'gore']
    }

    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detects the most likely language of the input text
        Returns tuple of (language_code, confidence_score)
        """
        text = text.lower()
        scores: Dict[str, int] = {lang: 0 for lang in self.LANGUAGE_MARKERS}
        
        words = set(re.findall(r'\w+', text))
        
        for lang, markers in self.LANGUAGE_MARKERS.items():
            for marker in markers:
                if marker in words:
                    scores[lang] += 1
        
        if not any(scores.values()):
            return 'en', 0.0
            
        best_lang = max(scores.items(), key=lambda x: x[1])
        confidence = best_lang[1] / len(words)
        
        return best_lang[0], confidence
```

## SUMMARY
- Enhanced intent detection with more comprehensive South African language support
- Added confidence scoring to intent detection
- Created new language detection helper
- Expanded keyword sets for major SA languages (English, Afrikaans, Xhosa, Zulu, Sotho, Tswana)

CONTINUE_NEEDED: Yes - Next steps would be to integrate the language detector with Refiloe's message handling and add language-specific response formatting.