"""
Unit Tests for fetch_yfinance.py (Quantitative Financial Models)
Location: tests/test_fetch_yfinance.py
"""

import unittest
import math
from tests.conftest import get_mock_metrics
from fetch_yfinance import (
    safe_get,
    compute_piotroski_f_score,
    compute_altman_z_score,
    compute_dupont_analysis,
    compute_2d_dcf_sensitivity
)


class TestFetchYFinanceModels(unittest.TestCase):

    def setUp(self):
        self.mock_metrics = get_mock_metrics()
        self.hist = self.mock_metrics["historical_metrics"]

    def test_safe_get_valid(self):
        import pandas as pd
        df = pd.DataFrame({"Revenue": [100.0, 90.0]}, index=["Revenue", "GrossProfit"])
        val = safe_get(df, "Revenue")
        self.assertEqual(val, 100.0)

    def test_safe_get_missing(self):
        import pandas as pd
        df = pd.DataFrame({"Revenue": [100.0]}, index=["Revenue"])
        val = safe_get(df, "NonExistentKey")
        self.assertEqual(val, 0.0)

    def test_compute_piotroski_f_score(self):
        result = compute_piotroski_f_score(self.hist)
        self.assertIn("score", result)
        self.assertIn("breakdown", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 9)
        self.assertIsInstance(result["breakdown"], dict)

    def test_compute_altman_z_score(self):
        mcap = self.mock_metrics["market_info"]["market_cap"]
        result = compute_altman_z_score(self.hist, mcap)
        self.assertIn("z_score", result)
        self.assertIn("zone", result)
        self.assertIn("model", result)
        self.assertEqual(result["model"], "Altman Z (Developed Market Model)")
        self.assertIsInstance(result["z_score"], (int, float))

    def test_compute_altman_z_score_emerging_bist(self):
        mcap = self.mock_metrics["market_info"]["market_cap"]
        result = compute_altman_z_score(self.hist, mcap, ticker_symbol="THYAO.IS")
        self.assertIn("z_score", result)
        self.assertIn("zone", result)
        self.assertIn("model", result)
        self.assertEqual(result["model"], "Altman Z'' (Emerging Market / BIST Model)")

    def test_compute_beneish_m_score(self):
        from fetch_yfinance import compute_beneish_m_score
        result = compute_beneish_m_score(self.hist)
        self.assertIn("m_score", result)
        self.assertIn("zone", result)
        self.assertIn("model_type", result)
        self.assertIn("breakdown", result)
        self.assertIsInstance(result["m_score"], float)

    def test_compute_2stage_dcf(self):
        from fetch_yfinance import compute_2stage_dcf
        result = compute_2stage_dcf(recent_fcf=1000000.0, wacc=0.10, g1=0.12, g_term=0.025, net_debt=200000.0)
        self.assertIn("implied_fair_value", result)
        self.assertIn("stage1_pv", result)
        self.assertIn("stage2_pv", result)
        self.assertIn("terminal_pv", result)
        self.assertIn("model_type", result)
        self.assertGreater(result["implied_fair_value"], 0.0)
        self.assertEqual(result["model_type"], "2-Stage High-Growth Fade")

    def test_compute_dupont_analysis(self):
        result = compute_dupont_analysis(self.hist)
        self.assertIn("tax_burden", result)
        self.assertIn("interest_burden", result)
        self.assertIn("ebit_margin", result)
        self.assertIn("asset_turnover", result)
        self.assertIn("financial_leverage", result)
        self.assertIn("dupont_roe_pct", result)

    def test_compute_2d_dcf_sensitivity(self):
        fcf = 85000000.0
        net_debt = 200000000.0
        shares = 20000000
        wacc = 0.10
        result = compute_2d_dcf_sensitivity(fcf, net_debt, shares, wacc)
        self.assertIn("wacc_headers", result)
        self.assertIn("growth_headers", result)
        self.assertIn("matrix", result)
        self.assertEqual(len(result["matrix"]), 5)
        self.assertEqual(len(result["matrix"][0]), 5)

    def test_expanded_metrics_structure(self):
        exp = self.mock_metrics.get("expanded_metrics", {})
        self.assertIn("ev_to_ebitda", exp)
        self.assertIn("net_debt_to_ebitda", exp)
        self.assertIn("graham_number", exp)
        self.assertIn("fcf_margin_pct", exp)
        self.assertGreater(exp["graham_number"], 0)


    def test_multilingual_commentary(self):
        from llm_commentary import _fallback_commentary
        metrics = get_mock_metrics()
        tr_comm = _fallback_commentary("AAPL", metrics, lang="TR")
        en_comm = _fallback_commentary("AAPL", metrics, lang="EN")

        self.assertIn("finansal bünye", tr_comm.get("strong_points", ""))
        self.assertIn("financial position", en_comm.get("strong_points", ""))
        self.assertEqual(len(tr_comm), 27)
        self.assertEqual(len(en_comm), 27)


if __name__ == "__main__":
    unittest.main()
