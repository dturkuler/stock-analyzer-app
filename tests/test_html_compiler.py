"""
Unit Tests for html_compiler.py (HTML Dashboard & Printable PDF Generator)
Location: tests/test_html_compiler.py
"""

import unittest
from tests.conftest import get_mock_metrics, get_mock_commentary
from html_compiler import (
    _fmt_try,
    _fmt_pct,
    _fmt_num,
    compile_report,
    compile_printable_report,
    sanitize_report_date
)



class TestHTMLCompiler(unittest.TestCase):

    def setUp(self):
        self.metrics = get_mock_metrics()
        self.commentary = get_mock_commentary()

    def test_fmt_try_formatting(self):
        self.assertEqual(_fmt_try(None), "N/A")
        self.assertIn("M", _fmt_try(5000000.0))
        self.assertIn("Mr", _fmt_try(2000000000.0))

    def test_fmt_pct_formatting(self):
        self.assertEqual(_fmt_pct(None), "N/A")
        self.assertIn("%", _fmt_pct(0.185))

    def test_fmt_num_formatting(self):
        self.assertEqual(_fmt_num(None), "N/A")
        self.assertEqual(_fmt_num(12.5), "12,50")

    def test_compile_report_contains_key_elements(self):
        html = compile_report(self.metrics, self.commentary)
        self.assertIsInstance(html, str)
        self.assertIn("TEST.IS", html)
        self.assertIn("Test Company AS", html)
        self.assertIn("Piotroski", html)
        self.assertIn("Altman Z", html)
        self.assertIn("DuPont", html)
        self.assertIn("EV / EBITDA", html)
        self.assertIn("Graham Değeri", html)
        self.assertIn("<!DOCTYPE html>", html)

    def test_compile_printable_report(self):
        printable_html = compile_printable_report(self.metrics, self.commentary)
        self.assertIsInstance(printable_html, str)
        self.assertIn("TEST.IS", printable_html)
        self.assertIn("@media print", printable_html)

    def test_sanitize_report_date(self):
        self.assertEqual(sanitize_report_date("2026-08-01_TR"), "2026-08-01")
        self.assertEqual(sanitize_report_date("2026-08-01_EN"), "2026-08-01")
        self.assertEqual(sanitize_report_date("2026-08-01_TR.html"), "2026-08-01")
        self.assertEqual(sanitize_report_date("2026-08-01_printable.html"), "2026-08-01")
        self.assertEqual(sanitize_report_date("2026-08-01"), "2026-08-01")
        self.assertEqual(sanitize_report_date(""), "")


if __name__ == "__main__":
    unittest.main()
