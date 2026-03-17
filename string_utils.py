"""String manipulation utility functions."""

import re
from typing import Any


def reverse_string(s: str) -> str:
    """
    Returns the reversed string.
    
    Args:
        s: The string to reverse.
        
    Returns:
        The reversed string.
        
    Example:
        >>> reverse_string("hello")
        'olleh'
    """
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    return s[::-1]


def camel_to_snake(name: str) -> str:
    """
    Converts camelCase to snake_case.
    
    Args:
        name: The camelCase string to convert.
        
    Returns:
        The snake_case version of the input.
        
    Example:
        >>> camel_to_snake("camelCaseString")
        'camel_case_string'
    """
    if not isinstance(name, str):
        raise TypeError("Input must be a string")
    
    # Insert underscore before uppercase letters and lowercase everything
    pattern = r'(?<!^)(?=[A-Z])'
    snake_case = re.sub(pattern, '_', name).lower()
    return snake_case


def snake_to_camel(name: str) -> str:
    """
    Converts snake_case to camelCase.
    
    Args:
        name: The snake_case string to convert.
        
    Returns:
        The camelCase version of the input.
        
    Example:
        >>> snake_to_camel("snake_case_string")
        'snakeCaseString'
    """
    if not isinstance(name, str):
        raise TypeError("Input must be a string")
    
    # Split by underscore and capitalize each part except the first
    parts = name.split('_')
    if not parts:
        return ''
    camel_case = parts[0] + ''.join(part.capitalize() for part in parts[1:])
    return camel_case


def truncate(s: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncates string with suffix if needed.
    
    Args:
        s: The string to truncate.
        max_length: Maximum allowed length of the result.
        suffix: Suffix to add when truncating (default: "...").
        
    Returns:
        The truncated string (with suffix if truncated).
        
    Example:
        >>> truncate("Hello world", 8)
        'Hello...'
    """
    if not isinstance(s, str):
        raise TypeError("First argument must be a string")
    if not isinstance(max_length, int):
        raise TypeError("max_length must be an integer")
    if max_length < 0:
        raise ValueError("max_length must be non-negative")
    if not isinstance(suffix, str):
        raise TypeError("suffix must be a string")
    
    if len(s) <= max_length:
        return s
    
    # Calculate available space for the actual content
    if len(suffix) >= max_length:
        # If suffix is longer than max_length, truncate suffix
        return suffix[:max_length]
    
    # Truncate string and add suffix
    truncated_length = max_length - len(suffix)
    return s[:truncated_length] + suffix


def count_words(s: str) -> int:
    """
    Counts words in a string.
    
    Args:
        s: The string to count words in.
        
    Returns:
        The number of words in the string.
        
    Example:
        >>> count_words("Hello world")
        2
    """
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    
    # Strip to handle leading/trailing whitespace
    stripped = s.strip()
    if not stripped:
        return 0
    
    # Split by whitespace (one or more spaces, tabs, newlines, etc.)
    words = re.split(r'\s+', stripped)
    return len(words)


def is_palindrome(s: str) -> bool:
    """
    Checks if string is palindrome (ignore case and non-alphanumeric).
    
    Args:
        s: The string to check.
        
    Returns:
        True if the string is a palindrome, False otherwise.
        
    Example:
        >>> is_palindrome("A man a plan a canal Panama")
        True
    """
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    
    # Remove non-alphanumeric characters and convert to lowercase
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    
    # Check if cleaned string is palindrome
    return cleaned == cleaned[::-1]
