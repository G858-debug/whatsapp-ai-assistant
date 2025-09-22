def normalize_phone_number(phone):
    """Normalize phone number to match test expectations"""
    if not phone:
        return None
    
    # Remove all non-digit characters
    phone = ''.join(filter(str.isdigit, str(phone)))
    
    # Handle South African numbers
    if phone.startswith('0'):
        phone = '27' + phone[1:]
    elif not phone.startswith('27') and len(phone) == 9:
        phone = '27' + phone
    
    # Return WITHOUT + to match test expectations
    # Tests expect: '27821234567' not '+27821234567'
    return phone
