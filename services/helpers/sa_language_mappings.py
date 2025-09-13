"""
South African language mappings for common phrases and responses
"""

LANGUAGE_MAPPINGS = {
    'en': {
        'greeting': 'Hi there!',
        'error': 'Eish! Something went wrong.',
        'success': 'Perfect!',
        'confirmation': 'Is this correct?'
    },
    'af': {
        'greeting': 'Goeie dag!',
        'error': 'Jammer! Iets het verkeerd gegaan.',
        'success': 'Perfek!',
        'confirmation': 'Is dit reg?'
    },
    'zu': {
        'greeting': 'Sawubona!',
        'error': 'Ncesi! Kukhona okungahambanga kahle.',
        'success': 'Kuhle!',
        'confirmation': 'Kunjalo?'
    }
}

def get_phrase(language: str, key: str) -> str:
    """Get phrase in specified language, fallback to English if not found"""
    return LANGUAGE_MAPPINGS.get(language, LANGUAGE_MAPPINGS['en']).get(key, LANGUAGE_MAPPINGS['en'][key])