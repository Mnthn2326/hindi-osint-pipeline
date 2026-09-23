"""Unit tests for consensus aggregation logic."""

import math
import unittest

from consensus.aggregate import compute_disagreement, compute_consensus


class TestConsensus(unittest.TestCase):
    
    def test_all_agree(self):
        """Test that full agreement yields 0.0 disagreement."""
        labels = ["positive", "positive", "positive"]
        confs = [0.9, 0.8, 0.95]
        
        self.assertEqual(compute_consensus(labels, confs), "positive")
        self.assertAlmostEqual(compute_disagreement(labels), 0.0, places=4)
        
    def test_fifty_fifty_split(self):
        """Test a 50/50 split and tie-breaking by confidence."""
        labels = ["positive", "positive", "negative", "negative"]
        # average pos conf = (0.9 + 0.7) / 2 = 0.8
        # average neg conf = (0.6 + 0.6) / 2 = 0.6
        # Tie break should pick positive
        confs = [0.9, 0.7, 0.6, 0.6]
        
        self.assertEqual(compute_consensus(labels, confs), "positive")
        
        score = compute_disagreement(labels)
        # 50/50 split with 3 max classes: H = 1.0, max_H = 1.58496
        # normalized = 1.0 / 1.58496 = 0.6309
        expected = 1.0 / math.log2(3)
        self.assertAlmostEqual(score, expected, places=4)
        
    def test_three_way_split(self):
        """Test a perfect 3-way split yields max disagreement (1.0)."""
        labels = ["positive", "negative", "neutral"]
        confs = [0.5, 0.5, 0.9]
        
        # Tie break should pick neutral (0.9 avg conf)
        self.assertEqual(compute_consensus(labels, confs), "neutral")
        
        score = compute_disagreement(labels)
        # H = 1.58496, max_H = 1.58496 -> normalized = 1.0
        self.assertAlmostEqual(score, 1.0, places=4)
        
    def test_empty_and_single(self):
        self.assertEqual(compute_disagreement([]), 0.0)
        self.assertEqual(compute_disagreement(["positive"]), 0.0)

if __name__ == "__main__":
    unittest.main()
