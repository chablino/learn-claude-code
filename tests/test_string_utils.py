"""Unit tests for string_utils module."""

import unittest
from string_utils import (
    reverse_string,
    camel_to_snake,
    snake_to_camel,
    truncate,
    count_words,
    is_palindrome
)


class TestReverseString(unittest.TestCase):
    """Tests for reverse_string function."""
    
    def test_reverse_simple(self):
        self.assertEqual(reverse_string("hello"), "olleh")
    
    def test_reverse_empty(self):
        self.assertEqual(reverse_string(""), "")
    
    def test_reverse_single_char(self):
        self.assertEqual(reverse_string("a"), "a")
    
    def test_reverse_with_spaces(self):
        self.assertEqual(reverse_string("hello world"), "dlrow olleh")
    
    def test_reverse_with_punctuation(self):
        self.assertEqual(reverse_string("hello!"), "!olleh")
    
    def test_reverse_unicode(self):
        self.assertEqual(reverse_string("café"), "éfac")
    
    def test_reverse_type_error(self):
        with self.assertRaises(TypeError):
            reverse_string(123)
    
    def test_reverse_type_error_none(self):
        with self.assertRaises(TypeError):
            reverse_string(None)


class TestCamelToSnake(unittest.TestCase):
    """Tests for camel_to_snake function."""
    
    def test_simple_camel(self):
        self.assertEqual(camel_to_snake("camelCase"), "camel_case")
    
    def test_multiple_caps(self):
        self.assertEqual(camel_to_snake("camelCaseString"), "camel_case_string")
    
    def test_single_word(self):
        self.assertEqual(camel_to_snake("word"), "word")
    
    def test_all_lowercase(self):
        self.assertEqual(camel_to_snake("alreadylower"), "alreadylower")
    
    def test_acronyms(self):
        self.assertEqual(camel_to_snake("HTTPRequest"), "http_request")
    
    def test_leading_capital(self):
        self.assertEqual(camel_to_snake("TestString"), "test_string")
    
    def test_empty_string(self):
        self.assertEqual(camel_to_snake(""), "")
    
    def test_type_error(self):
        with self.assertRaises(TypeError):
            camel_to_snake(123)
    
    def test_type_error_none(self):
        with self.assertRaises(TypeError):
            camel_to_snake(None)


class TestSnakeToCamel(unittest.TestCase):
    """Tests for snake_to_camel function."""
    
    def test_simple_snake(self):
        self.assertEqual(snake_to_camel("snake_case"), "snakeCase")
    
    def test_multiple_underscores(self):
        self.assertEqual(snake_to_camel("snake_case_string"), "snakeCaseString")
    
    def test_single_word(self):
        self.assertEqual(snake_to_camel("word"), "word")
    
    def test_leading_underscore(self):
        self.assertEqual(snake_to_camel("_private"), "_private")
    
    def test_trailing_underscore(self):
        self.assertEqual(snake_to_camel("something_"), "something_")
    
    def test_empty_string(self):
        self.assertEqual(snake_to_camel(""), "")
    
    def test_multiple_consecutive_underscores(self):
        self.assertEqual(snake_to_camel("multiple__underscores"), "multiple__underscores")
    
    def test_type_error(self):
        with self.assertRaises(TypeError):
            snake_to_camel(123)
    
    def test_type_error_none(self):
        with self.assertRaises(TypeError):
            snake_to_camel(None)


class TestTruncate(unittest.TestCase):
    """Tests for truncate function."""
    
    def test_no_truncation_needed(self):
        self.assertEqual(truncate("hello", 10), "hello")
    
    def test_exact_length(self):
        self.assertEqual(truncate("hello", 5), "hello")
    
    def test_simple_truncation(self):
        self.assertEqual(truncate("hello world", 8), "hello...")
    
    def test_truncation_with_custom_suffix(self):
        self.assertEqual(truncate("hello world", 8, "!!!"), "hello!!!")
    
    def test_truncation_one_char_plus_suffix(self):
        self.assertEqual(truncate("hello", 5, "..."), "hello")
        self.assertEqual(truncate("hello", 4, "..."), "...")
        self.assertEqual(truncate("hello", 3, "..."), "...")
    
    def test_suffix_longer_than_max(self):
        self.assertEqual(truncate("hello", 2, "..."), "..")
        self.assertEqual(truncate("hello", 1, "..."), ".")
    
    def test_empty_string(self):
        self.assertEqual(truncate("", 5), "")
    
    def test_empty_suffix(self):
        self.assertEqual(truncate("hello world", 5, ""), "hello")
    
    def test_zero_max_length(self):
        self.assertEqual(truncate("hello", 0), "")
        self.assertEqual(truncate("hello", 0, "..."), "...")
    
    def test_type_error_string(self):
        with self.assertRaises(TypeError):
            truncate(123, 5)
    
    def test_type_error_max_length(self):
        with self.assertRaises(TypeError):
            truncate("hello", "5")
    
    def test_type_error_suffix(self):
        with self.assertRaises(TypeError):
            truncate("hello", 5, 123)
    
    def test_value_error_negative_max(self):
        with self.assertRaises(ValueError):
            truncate("hello", -1)
    
    def test_truncation_preserves_unicode(self):
        self.assertEqual(truncate("café", 4, "..."), "ca...")


class TestCountWords(unittest.TestCase):
    """Tests for count_words function."""
    
    def test_count_simple(self):
        self.assertEqual(count_words("hello world"), 2)
    
    def test_count_single_word(self):
        self.assertEqual(count_words("hello"), 1)
    
    def test_count_empty(self):
        self.assertEqual(count_words(""), 0)
    
    def test_count_only_spaces(self):
        self.assertEqual(count_words("   "), 0)
    
    def test_count_with_extra_spaces(self):
        self.assertEqual(count_words("hello   world"), 2)
    
    def test_count_with_tabs(self):
        self.assertEqual(count_words("hello\tworld"), 2)
    
    def test_count_with_newlines(self):
        self.assertEqual(count_words("hello\nworld"), 2)
    
    def test_count_with_mixed_whitespace(self):
        self.assertEqual(count_words("hello \t\n world"), 2)
    
    def test_count_multiple_sentences(self):
        self.assertEqual(count_words("Hello! How are you? Fine."), 5)
    
    def test_count_leading_trailing_whitespace(self):
        self.assertEqual(count_words("  hello world  "), 2)
    
    def test_type_error(self):
        with self.assertRaises(TypeError):
            count_words(123)
    
    def test_type_error_none(self):
        with self.assertRaises(TypeError):
            count_words(None)


class TestIsPalindrome(unittest.TestCase):
    """Tests for is_palindrome function."""
    
    def test_simple_palindrome(self):
        self.assertTrue(is_palindrome("racecar"))
    
    def test_simple_not_palindrome(self):
        self.assertFalse(is_palindrome("hello"))
    
    def test_case_insensitive(self):
        self.assertTrue(is_palindrome("RaceCar"))
        self.assertTrue(is_palindrome("RACECAR"))
    
    def test_with_spaces(self):
        self.assertTrue(is_palindrome("a man a plan a canal panama"))
    
    def test_with_punctuation(self):
        self.assertTrue(is_palindrome("A man, a plan, a canal: Panama!"))
    
    def test_single_char(self):
        self.assertTrue(is_palindrome("a"))
    
    def test_empty_string(self):
        self.assertTrue(is_palindrome(""))
    
    def test_only_non_alphanumeric(self):
        self.assertTrue(is_palindrome("!@#$%^"))
    
    def test_mixed_non_alphanumeric(self):
        self.assertTrue(is_palindrome("A1B2@B2A1!"))
    
    def test_not_palindrome_with_punctuation(self):
        self.assertFalse(is_palindrome("hello, world!"))
    
    def test_unicode(self):
        self.assertTrue(is_palindrome("été"))
    
    def test_type_error(self):
        with self.assertRaises(TypeError):
            is_palindrome(123)
    
    def test_type_error_none(self):
        with self.assertRaises(TypeError):
            is_palindrome(None)


if __name__ == '__main__':
    unittest.main()
