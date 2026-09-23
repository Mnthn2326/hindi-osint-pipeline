"""Unit tests for pure helper functions in ingestion/news_rss.py."""

import unittest
from datetime import datetime

from ingestion.news_rss import _compute_hash, _build_raw_text, _parse_published


class TestNewsRSS(unittest.TestCase):
    
    def test_compute_hash(self):
        """Test SHA-256 hashing."""
        h1 = _compute_hash("title1", "link1")
        h2 = _compute_hash("title1", "link1")
        h3 = _compute_hash("title2", "link1")
        
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertEqual(len(h1), 64)  # SHA-256 hex length

    def test_build_raw_text(self):
        """Test text assembly logic from RSS entry dictionary."""
        # Only title
        self.assertEqual(_build_raw_text({"title": "Hello"}), "Hello")
        
        # Title and summary
        self.assertEqual(
            _build_raw_text({"title": "Hello", "summary": "World"}),
            "Hello\n\nWorld"
        )
        
        # Title and description (fallback)
        self.assertEqual(
            _build_raw_text({"title": "Hello", "description": "Desc"}),
            "Hello\n\nDesc"
        )
        
        # Strips whitespace
        self.assertEqual(
            _build_raw_text({"title": "  Hello  ", "summary": "  World  "}),
            "Hello\n\nWorld"
        )
        
        # Empty
        self.assertEqual(_build_raw_text({}), "")

    def test_parse_published(self):
        """Test timestamp parsing."""
        # Valid published_parsed
        entry1 = {"published_parsed": (2026, 9, 23, 12, 0, 0, 0, 0, 0)}
        dt1 = _parse_published(entry1)
        self.assertEqual(dt1, datetime(2026, 9, 23, 12, 0, 0))
        
        # Valid updated_parsed fallback
        entry2 = {"updated_parsed": (2026, 1, 1, 0, 0, 0, 0, 0, 0)}
        dt2 = _parse_published(entry2)
        self.assertEqual(dt2, datetime(2026, 1, 1, 0, 0, 0))
        
        # Missing
        self.assertIsNone(_parse_published({}))
        
        # Invalid format (graceful handling)
        self.assertIsNone(_parse_published({"published_parsed": "invalid"}))


if __name__ == "__main__":
    unittest.main()
