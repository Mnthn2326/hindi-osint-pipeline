"""Unit tests for pure helper functions in preprocessing/clean.py."""

import unittest

from preprocessing.clean import clean_text, is_hindi_or_codemixed


class TestClean(unittest.TestCase):

    def test_clean_text_html_stripping(self):
        """Test that HTML tags are removed and entities unescaped."""
        raw = "<p>यह एक &lt;b&gt;परीक्षण&lt;/b&gt; है!</p>"
        expected = "यह एक परीक्षण है!"
        self.assertEqual(clean_text(raw), expected)

    def test_clean_text_whitespace_normalization(self):
        """Test that excessive whitespace and newlines are collapsed."""
        raw = "यह    एक\n\n\n बहुत  \t\t खराब  वाक्य है।"
        expected = "यह एक बहुत खराब वाक्य है।"
        self.assertEqual(clean_text(raw), expected)

    def test_is_hindi_pure_devanagari(self):
        """Test that pure Devanagari Hindi text is correctly identified."""
        text = "यह एक शुद्ध हिंदी वाक्य है जो देवनागरी लिपि में लिखा गया है।"
        self.assertTrue(is_hindi_or_codemixed(text))

    def test_is_hindi_codemixed(self):
        """Test that code-mixed English/Hindi text is kept if Devanagari is present."""
        # This might be detected as 'en' or 'mr' or 'hi', but it contains Devanagari
        text = "Breaking news: शेयर बाजार में आज heavy crash देखने को मिला।"
        self.assertTrue(is_hindi_or_codemixed(text))

    def test_is_hindi_garbage_input(self):
        """Test that garbage input failing langdetect falls back gracefully."""
        # Completely meaningless non-alphabet characters or numbers
        text = "12345 67890 !@#$%^&*()"
        # Does not have Devanagari, should return False
        self.assertFalse(is_hindi_or_codemixed(text))

    def test_is_hindi_non_hindi_language(self):
        """Test that entirely English text without Devanagari is rejected."""
        text = "This is a completely English sentence about the stock market."
        self.assertFalse(is_hindi_or_codemixed(text))


if __name__ == "__main__":
    unittest.main()
