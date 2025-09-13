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