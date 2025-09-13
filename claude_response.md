<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0033 -->
<!-- Max Tokens: 8000 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS
From reviewing the provided files, there are a few key areas that need improvement in the Refiloe WhatsApp assistant:

1. The intent detection is too simplistic and needs better context handling
2. We should add South African-specific language/currency handling
3. Error handling needs to be more informative for South African users

## CHANGES NEEDED

### EDIT: services/refiloe.py

**Change 1:** Expand intent keywords with South African context
Location: Lines 15-22
```python
# REMOVE:
    INTENT_KEYWORDS = {
        'client_registration': ['register', 'sign up', 'join'],
        'client_profile_update': ['update profile', 'edit profile', 'change details'],
        'payment_request': ['pay', 'payment', 'invoice'],
        'calendar_request': ['book', 'schedule', 'appointment'],
        'gamification_request': ['points', 'rewards', 'achievements'],
        'habits_request': ['habit', 'track', 'progress']
    }

# ADD:
    INTENT_KEYWORDS = {
        'client_registration': ['register', 'sign up', 'join', 'skryf in', 'ngodiso'],
        'client_profile_update': ['update profile', 'edit profile', 'change details', 'verander', 'hleng'],
        'payment_request': ['pay', 'payment', 'invoice', 'EFT', 'rand', 'R', 'ZAR', 'betaal'],
        'calendar_request': ['book', 'schedule', 'appointment', 'bespreek', 'ukubhukisha'],
        'gamification_request': ['points', 'rewards', 'achievements', 'punte', 'amanqaku'],
        'habits_request': ['habit', 'track', 'progress', 'gewoonte', 'umkhuba']
    }
```

**Change 2:** Improve error handling with South African context
Location: Lines 40-42
```python
# REMOVE:
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            return format_response("I apologize, but I encountered an error. Please try again later.")

# ADD:
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            return format_response(
                "Eish, I'm having some technical issues! 🙈 "
                "Please try again or contact support at +27 support number. "
                "You can also try sending your message in English, Afrikaans, or isiZulu."
            )
```

### NEW FILE: services/helpers/sa_context.py
```python
"""Helper functions for South African context handling"""

def format_rand_amount(amount: float) -> str:
    """Format amount in South African Rand"""
    return f"R {amount:.2f}"

def validate_sa_phone(phone: str) -> bool:
    """Validate South African phone number format"""
    import re
    pattern = r'^\+27[0-9]{9}$'
    return bool(re.match(pattern, phone))

def get_sa_timezone():
    """Return South African timezone"""
    from datetime import timezone, timedelta
    return timezone(timedelta(hours=2))  # SAST (UTC+2)

# Common South African languages
SA_LANGUAGES = {
    'en': 'English',
    'af': 'Afrikaans',
    'zu': 'isiZulu',
    'xh': 'isiXhosa',
    'st': 'Sesotho',
    'tn': 'Setswana'
}
```

## SUMMARY
- Added multi-language support for intent detection including Afrikaans and isiZulu keywords
- Improved error messages with South African context and colloquialisms
- Created new helper module for South African-specific functionality
- Added support for Rand currency formatting and SA phone number validation

CONTINUE_NEEDED: Yes - next steps should include:
1. Integrating the new SA context helpers into the main application
2. Adding more comprehensive language support
3. Implementing South African payment gateway specifics