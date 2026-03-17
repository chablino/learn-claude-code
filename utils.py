"""
Utility functions for common tasks.
"""


def double(value):
    """Double a numeric value."""
    return value * 2


def format_name(first_name, last_name):
    """Format a full name with proper capitalization."""
    return f"{first_name.capitalize()} {last_name.capitalize()}"


def is_prime(number):
    """Check if a number is prime."""
    if number <= 1:
        return False
    if number <= 3:
        return True
    if number % 2 == 0 or number % 3 == 0:
        return False
    i = 5
    while i * i <= number:
        if number % i == 0 or number % (i + 2) == 0:
            return False
        i += 6
    return True


def fibonacci(n):
    """Generate Fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    if n == 2:
        return [0, 1]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i - 1] + fib[i - 2])
    return fib
