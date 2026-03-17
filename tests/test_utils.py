"""
Tests for utils.py module.
"""

import unittest

from utils import double, fibonacci, format_name, is_prime


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""

    def test_double(self):
        """Test double function."""
        self.assertEqual(double(5), 10)
        self.assertEqual(double(0), 0)
        self.assertEqual(double(-3), -6)
        self.assertEqual(double(2.5), 5.0)

    def test_format_name(self):
        """Test format_name function."""
        self.assertEqual(format_name("john", "doe"), "John Doe")
        self.assertEqual(format_name("alice", "smith"), "Alice Smith")
        self.assertEqual(format_name("bob", "jones"), "Bob Jones")

    def test_is_prime(self):
        """Test is_prime function."""
        # Prime numbers
        self.assertTrue(is_prime(2))
        self.assertTrue(is_prime(3))
        self.assertTrue(is_prime(5))
        self.assertTrue(is_prime(7))
        self.assertTrue(is_prime(11))
        self.assertTrue(is_prime(13))
        self.assertTrue(is_prime(17))
        self.assertTrue(is_prime(19))
        self.assertTrue(is_prime(23))
        self.assertTrue(is_prime(29))

        # Non-prime numbers
        self.assertFalse(is_prime(1))
        self.assertFalse(is_prime(0))
        self.assertFalse(is_prime(-5))
        self.assertFalse(is_prime(4))
        self.assertFalse(is_prime(6))
        self.assertFalse(is_prime(8))
        self.assertFalse(is_prime(9))
        self.assertFalse(is_prime(10))
        self.assertFalse(is_prime(15))
        self.assertFalse(is_prime(25))
        self.assertFalse(is_prime(100))

    def test_fibonacci(self):
        """Test fibonacci function."""
        self.assertEqual(fibonacci(0), [])
        self.assertEqual(fibonacci(1), [0])
        self.assertEqual(fibonacci(2), [0, 1])
        self.assertEqual(fibonacci(3), [0, 1, 1])
        self.assertEqual(fibonacci(5), [0, 1, 1, 2, 3])
        self.assertEqual(fibonacci(7), [0, 1, 1, 2, 3, 5, 8])
        self.assertEqual(fibonacci(10), [0, 1, 1, 2, 3, 5, 8, 13, 21, 34])


if __name__ == "__main__":
    unittest.main()
