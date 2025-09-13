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