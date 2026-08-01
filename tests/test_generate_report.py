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

    def test_pipeline_sourcing_failure_exits_with_code_1(self):
        """Verify that generate_report exits with status code 1 on data sourcing error."""
        from generate_report import generate_report
        with self.assertRaises(SystemExit) as cm:
            generate_report("INVALID_NONEXISTENT_TICKER_9999", lang="TR")
        self.assertEqual(cm.exception.code, 1)

    def test_valid_stock_analysis_produces_zero_errors(self):
        """Verify that stock analysis on mock/valid data executes without writing errors to errors.log."""
        from html_compiler import compile_report
        mock_metrics = {
            "ticker": "TEST_VALID",
            "company_name": "Test Company A.S.",
            "market_info": {"price": 100.0, "market_cap": 1e9, "enterprise_value": 1.2e9, "beta": 1.1},
            "piotroski_f_score": {"score": 7, "breakdown": {}},
            "altman_z_score": {"z_score": 3.5, "zone": "Safe Zone (Z > 2.99)"},
            "valuation_parameters": {"wacc": 0.20, "risk_free_rate": 0.15, "equity_risk_premium": 0.08, "cost_of_equity": 0.22, "cost_of_debt": 0.15, "equity_weight": 0.8, "debt_weight": 0.2, "rule_of_40": 25.0},
            "historical_metrics": [
                {"year": "2025", "revenue": 500e6, "net_income": 50e6, "operating_income": 80e6, "cash_and_equivalents": 100e6, "total_debt": 40e6, "net_margin": 0.10, "current_ratio": 1.5},
                {"year": "2024", "revenue": 400e6, "net_income": 40e6, "operating_income": 60e6, "cash_and_equivalents": 80e6, "total_debt": 50e6, "net_margin": 0.10, "current_ratio": 1.4},
                {"year": "2023", "revenue": 300e6, "net_income": 30e6, "operating_income": 40e6, "cash_and_equivalents": 50e6, "total_debt": 60e6, "net_margin": 0.10, "current_ratio": 1.3}
            ],
            "relative_strength": {"technical_indicators": {"rsi_14": 55.0, "macd_line": 1.2, "macd_signal": 0.8, "sma_50": 95.0, "sma_200": 85.0, "support_level_60d": 90.0, "resistance_level_60d": 110.0}},
            "reverse_dcf": {"implied_growth_rate_raw": 0.15, "recent_fcf": 45e6},
            "scenario_targets": {"base_case_price": 115.0, "bear_case_price": 85.0, "bull_case_price": 140.0, "severe_downside_price": 60.0},
            "dupont_analysis": {"tax_burden": 0.8, "interest_burden": 0.9, "ebit_margin": 0.16, "asset_turnover": 0.5, "financial_leverage": 1.5, "dupont_roe_pct": 18.5},
            "beneish_m_score": {"m_score": -2.4, "model_type": "Beneish 8-Var Full"},
            "expanded_metrics": {"ev_to_ebitda": 10.5, "net_debt_to_ebitda": 0.5, "graham_number": 120.0, "fcf_margin_pct": 9.0}
        }
        mock_commentary = {k: f"Valid analysis section for {k}" for k in [
            "company_name", "executive_summary", "strong_points", "weak_points", "risk_discipline",
            "scorecard_commentary", "piotroski_commentary", "altman_z_commentary", "moat_and_catalysts",
            "ownership_commentary", "peer_comparison", "dupont_analysis", "forward_commentary",
            "dcf_valuation", "technical_analysis", "forensic_audit", "scenario_analysis", "investment_verdict",
            "blog_headline", "blog_summary", "blog_cash_and_health", "blog_earnings_quality",
            "blog_valuation_dcf", "blog_catalysts_and_risks", "blog_bull_vs_bear"
        ]}
        mock_commentary["company_name"] = "Test Company A.S."
        mock_commentary["verdict_rating"] = "🟢 GÜÇLÜ MODEL ALIM"
        mock_commentary["blog_key_takeaways"] = ["Key Takeaway 1", "Key Takeaway 2"]
        mock_commentary["blog_faqs"] = [{"q": "FAQ 1?", "a": "Answer 1"}]
        
        err_file_before = len(open(ERRORS_LOG_FILE, "r", encoding="utf-8").read()) if os.path.exists(ERRORS_LOG_FILE) else 0
        html = compile_report(mock_metrics, mock_commentary, lang="TR")
        self.assertIn("Test Company A.S.", html)
        err_file_after = len(open(ERRORS_LOG_FILE, "r", encoding="utf-8").read()) if os.path.exists(ERRORS_LOG_FILE) else 0
        self.assertEqual(err_file_before, err_file_after, "Stock analysis must not log errors to errors.log on valid data")


if __name__ == "__main__":
    unittest.main()
