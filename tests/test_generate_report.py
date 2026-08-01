"""
Unit Tests for generate_report.py Pipeline Orchestrator
Location: tests/test_generate_report.py
"""

import os
import unittest
import tempfile
from generate_report import log_analysis, ANALYSIS_LOG_FILE
from logger import log_error, ERRORS_LOG_FILE


class TestGenerateReportPipeline(unittest.TestCase):

    def test_log_analysis_writes_file(self):
        test_msg = "TEST_PIPELINE_LOG_MESSAGE"
        log_analysis(test_msg)
        self.assertTrue(os.path.exists(ANALYSIS_LOG_FILE))
        with open(ANALYSIS_LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn(test_msg, content)

    def test_log_error_writes_errors_file(self):
        test_err_msg = "TEST_ERROR_LOG_MESSAGE"
        log_error(test_err_msg, context="TEST_TICKER")
        self.assertTrue(os.path.exists(ERRORS_LOG_FILE))
        with open(ERRORS_LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn(test_err_msg, content)
            self.assertIn("[TEST_TICKER]", content)


if __name__ == "__main__":
    unittest.main()
