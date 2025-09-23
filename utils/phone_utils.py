# utils/phone_utils.py
"""Phone number utilities"""

def normalize_phone_number(phone: str) -> str:
    """Normalize phone number to format WITHOUT + prefix"""
    if not phone:
        return None
    
    # Remove all non-digit characters including +
    digits = ''.join(filter(str.isdigit, str(phone)))
    
    # Handle South African numbers
    if digits.startswith('0'):
        # Local format: 0821234567 -> 27821234567
        digits = '27' + digits[1:]
    elif not digits.startswith('27') and len(digits) == 9:
        # Missing prefix: 821234567 -> 27821234567
        digits = '27' + digits
    
    # Return WITHOUT + prefix (tests expect this)
    return digits
    
