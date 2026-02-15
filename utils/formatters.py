"""
Utility functions for text formatting and parsing
"""
import re
from typing import Optional, Tuple


def format_price(price: float) -> str:
    """
    Format price with thousand separators
    
    Args:
        price: Price in UZS
        
    Returns:
        Formatted price string
    """
    return f"{price:,.0f}".replace(',', ' ')


def parse_price_input(text: str) -> Optional[float]:
    """
    Parse price from user input
    
    Args:
        text: User input text
        
    Returns:
        Parsed price or None
    """
    try:
        # Remove all non-digit and non-decimal characters
        cleaned = re.sub(r'[^\d.]', '', text)
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def extract_phone_number(text: str) -> Optional[str]:
    """
    Extract Uzbekistan phone number from text
    
    Args:
        text: Text containing phone number
        
    Returns:
        Formatted phone number or None
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', text)
    
    # Check for Uzbekistan phone number patterns
    patterns = [
        r'^998\d{9}$',  # 998901234567
        r'^\d{9}$',     # 901234567
        r'^\d{7}$',     # 1234567 (city)
    ]
    
    for pattern in patterns:
        if re.match(pattern, digits):
            if len(digits) == 12:
                return f"+{digits}"
            elif len(digits) == 9:
                return f"+998{digits}"
            elif len(digits) == 7:
                return digits
    
    return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Markdown
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def car_title(brand: str, model: str, year: int) -> str:
    """
    Create formatted car title
    
    Args:
        brand: Car brand
        model: Car model
        year: Manufacturing year
        
    Returns:
        Formatted title
    """
    return f"{brand} {model} ({year})"


def validate_year(year: int) -> bool:
    """
    Validate manufacturing year
    
    Args:
        year: Year to validate
        
    Returns:
        True if valid
    """
    from datetime import datetime
    return 1990 <= year <= datetime.now().year + 1


def format_mileage(km: int) -> str:
    """
    Format mileage with units
    
    Args:
        km: Mileage in kilometers
        
    Returns:
        Formatted mileage
    """
    return f"{km:,} km".replace(',', ' ')


def get_car_condition_emoji(condition: str) -> str:
    """
    Get emoji for car condition
    
    Args:
        condition: Car condition
        
    Returns:
        Emoji string
    """
    conditions = {
        'yangi': '🆕',
        'ideal': '✨',
        'yaxshi': '👍',
        'o\'rtacha': '👌',
        'ta\'mirlash kerak': '🔧',
    }
    
    return conditions.get(condition.lower(), '🚗')
