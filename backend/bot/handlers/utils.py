import re
from typing import Optional

def validate_phone(phone: str) -> Optional[str]:
    """
    Проверяет и очищает номер телефона. Возвращает очищенный номер телефона (+7XXXXXXXXXX) или None, если номер недействителен.
    """
    digits = re.sub(r'[^\d]', '', phone)

    if len(digits) == 11:
        if digits.startswith('8'):
            digits = '7' + digits[1:]
        if not digits.startswith('7'):
            return None
        if not re.match(r'^7\d{10}$', digits):
            return None
    elif len(digits) == 10:
        digits = '7' + digits
    else:
        return None

    return digits