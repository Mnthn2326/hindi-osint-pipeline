"""Unit tests for pure helper functions in ingestion/news_rss.py."""

import hashlib
import unittest
from datetime import datetime

from ingestion.news_rss import _build_raw_text, _compute_hash, _parse_published


class TestNewsRSSHelpers(unittest.TestCase):

    def test_compute_hash_deterministic(self):
        """Test SHA-256 hash generation is deterministic and correct."""
        title = "भारत की जीत"
        link = "https://example.com/news/1"
        expected = hashlib.sha256(f"{title}|{link}".encode("utf-8")).hexdigest()
        self.assertEqual(_compute_hash(title, link), expected)

    def test_compute_hash_different_inputs(self):
        """Test different title/link pairs produce distinct hashes."""
        h1 = _compute_hash("Title A", "https://example.com/a")
        h2 = _compute_hash("Title B", "https://example.com/a")
        h3 = _compute_hash("Title A", "https://example.com/b")
        self.assertNotEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_build_raw_text_full(self):
        """Test raw text formatting with both title and summary."""
        entry = {
            "title": "मुख्य समाचार",
            "summary": "यह समाचार का संक्षिप्त विवरण है।",
        }
        expected = "मुख्य समाचार\n\nयह समाचार का संक्षिप्त विवरण है।"
        self.assertEqual(_build_raw_text(entry), expected)

    def test_build_raw_text_description_fallback(self):
        """Test description field fallback when summary is missing."""
        entry = {
            "title": "मुख्य समाचार",
            "description": "विवरण पाठ",
        }
        expected = "मुख्य समाचार\n\nविवरण पाठ"
        self.assertEqual(_build_raw_text(entry), expected)

    def test_build_raw_text_title_only(self):
        """Test raw text formatting with title only."""
        entry = {"title": "केवल शीर्षक"}
        self.assertEqual(_build_raw_text(entry), "केवल शीर्षक")

    def test_build_raw_text_empty(self):
        """Test raw text formatting with empty entry."""
        entry = {}
        self.assertEqual(_build_raw_text(entry), "")

    def test_parse_published_valid_published_parsed(self):
        """Test parsing valid published_parsed time struct."""
        time_struct = (2026, 9, 23, 14, 30, 0, 2, 266, 0)
        entry = {"published_parsed": time_struct}
        parsed = _parse_published(entry)
        self.assertEqual(parsed, datetime(2026, 9, 23, 14, 30, 0))

    def test_parse_published_valid_updated_parsed(self):
        """Test parsing fallback updated_parsed time struct."""
        time_struct = (2026, 9, 23, 15, 45, 0, 2, 266, 0)
        entry = {"updated_parsed": time_struct}
        parsed = _parse_published(entry)
        self.assertEqual(parsed, datetime(2026, 9, 23, 15, 45, 0))

    def test_parse_published_invalid(self):
        """Test invalid or missing date structure returns None."""
        self.assertIsNone(_parse_published({}))
        self.assertIsNone(_parse_published({"published_parsed": "invalid"}))


if __name__ == "__main__":
    unittest.main()
