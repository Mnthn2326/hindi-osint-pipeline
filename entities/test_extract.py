"""Unit tests for pure helper functions in entities/extract.py."""

import unittest

from entities.extract import resolve_entity


class TestExtract(unittest.TestCase):
    
    def setUp(self):
        self.alias_map = {
            "पीएम मोदी": 1,
            "भारत": 2,
            "रिजर्व बैंक": 3
        }

    def test_resolve_entity_exact_match(self):
        """Test exact matches resolve correctly."""
        self.assertEqual(resolve_entity("पीएम मोदी", self.alias_map), 1)
        self.assertEqual(resolve_entity("भारत", self.alias_map), 2)
        
    def test_resolve_entity_case_insensitive(self):
        """Test exact matches are case-insensitive."""
        self.alias_map["nifty 50"] = 4
        self.assertEqual(resolve_entity("NIFTY 50", self.alias_map), 4)

    def test_resolve_entity_substring_alias_in_word(self):
        """Test when the alias is a substring of the extracted word."""
        # alias="पीएम मोदी", word="माननीय पीएम मोदी जी"
        self.assertEqual(resolve_entity("माननीय पीएम मोदी जी", self.alias_map), 1)
        
    def test_resolve_entity_substring_word_in_alias(self):
        """Test when the extracted word is a substring of the alias."""
        # alias="रिजर्व बैंक", word="रिजर्व"
        self.assertEqual(resolve_entity("रिजर्व", self.alias_map), 3)

    def test_resolve_entity_no_match(self):
        """Test when there is no overlap."""
        self.assertIsNone(resolve_entity("अज्ञात", self.alias_map))


if __name__ == "__main__":
    unittest.main()
