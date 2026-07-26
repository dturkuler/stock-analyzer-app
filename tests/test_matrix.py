"""
Unit Tests for Stock Matrix API Endpoint & 360° Composite Score Calculation
"""

import unittest
import json
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "3_web_server")))

from main import get_stock_matrix


class TestStockMatrix(unittest.TestCase):
    def test_matrix_endpoint_returns_list(self):
        data = get_stock_matrix("TR")
        self.assertIsInstance(data, list)

        if len(data) > 0:
            item = data[0]
            self.assertIn("ticker", item)
            self.assertIn("name", item)
            self.assertIn("price", item)
            self.assertIn("piotroski_score", item)
            self.assertIn("altman_z_score", item)
            self.assertIn("dupont_roe_pct", item)
            self.assertIn("composite_score", item)
            self.assertIn("verdict_code", item)
            self.assertIn("verdict_label", item)
            self.assertGreaterEqual(item["composite_score"], 0.0)
            self.assertLessEqual(item["composite_score"], 10.0)


if __name__ == "__main__":
    unittest.main()
