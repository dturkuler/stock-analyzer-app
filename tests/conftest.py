"""
Shared Test Configuration and Mock Data Fixtures
Location: tests/conftest.py
"""

import os
import sys

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CORE_BUILDER_DIR = os.path.join(PROJECT_ROOT, "1_core_builder")
if CORE_BUILDER_DIR not in sys.path:
    sys.path.insert(0, CORE_BUILDER_DIR)

WEB_SERVER_DIR = os.path.join(PROJECT_ROOT, "3_web_server")
if WEB_SERVER_DIR not in sys.path:
    sys.path.insert(0, WEB_SERVER_DIR)


def get_mock_metrics():
    """Return a comprehensive mock metrics dictionary matching fetch_yfinance.py output structure."""
    return {
        "ticker": "TEST.IS",
        "name": "Test Company AS",
        "market_info": {
            "market_cap": 1000000000.0,
            "enterprise_value": 1200000000.0,
            "current_price": 50.0,
            "fifty_day_avg": 48.0,
            "two_hundred_day_avg": 45.0,
            "beta": 1.1,
            "shares_outstanding": 20000000,
            "short_percent_of_float": 0.02,
            "days_to_cover": 1.5,
            "currency_code": "TRY",
            "currency_symbol": "₺"
        },
        "expanded_metrics": {
            "ebitda": 150000000.0,
            "ev_to_ebitda": 8.0,
            "net_debt_to_ebitda": 1.33,
            "trailing_eps": 4.5,
            "book_value_per_share": 25.0,
            "graham_number": 50.31,
            "fcf_margin_pct": 12.5
        },
        "historical_metrics": [
            {
                "year": "2025",
                "revenue": 500000000.0,
                "gross_profit": 200000000.0,
                "operating_income": 120000000.0,
                "net_income": 90000000.0,
                "basic_eps": 4.5,
                "operating_cash_flow": 110000000.0,
                "capex": 25000000.0,
                "fcf": 85000000.0,
                "sbc": 2000000.0,
                "sbc_adjusted_fcf": 83000000.0,
                "total_debt": 250000000.0,
                "cash_and_equivalents": 50000000.0,
                "net_debt": 200000000.0,
                "gross_margin": 0.40,
                "operating_margin": 0.24,
                "net_margin": 0.18,
                "fcf_margin": 0.17,
                "current_ratio": 1.8,
                "debt_to_equity": 0.5,
                "roe": 0.18,
                "roic": 0.15
            },
            {
                "year": "2024",
                "revenue": 420000000.0,
                "gross_profit": 160000000.0,
                "operating_income": 95000000.0,
                "net_income": 70000000.0,
                "basic_eps": 3.5,
                "operating_cash_flow": 90000000.0,
                "capex": 20000000.0,
                "fcf": 70000000.0,
                "sbc": 1500000.0,
                "sbc_adjusted_fcf": 68500000.0,
                "total_debt": 220000000.0,
                "cash_and_equivalents": 40000000.0,
                "net_debt": 180000000.0,
                "gross_margin": 0.38,
                "operating_margin": 0.226,
                "net_margin": 0.166,
                "fcf_margin": 0.166,
                "current_ratio": 1.6,
                "debt_to_equity": 0.55,
                "roe": 0.16,
                "roic": 0.14
            }
        ],
        "relative_strength": {
            "stock_3m_perf": 12.5,
            "stock_1y_perf": 25.0,
            "benchmark_3m_perf": 5.0,
            "benchmark_1y_perf": 15.0,
            "technical_indicators": {
                "rsi_14d": 58.5,
                "macd_line": 1.2,
                "macd_signal": 0.8,
                "resistance_level_60d": 55.0,
                "support_level_60d": 44.0
            }
        },
        "piotroski_f_score": {
            "score": 8,
            "breakdown": {
                "positive_net_income": 1,
                "positive_cfo": 1,
                "higher_roa_yoy": 1,
                "accruals_cfo_gt_ni": 1,
                "lower_leverage_yoy": 1,
                "higher_current_ratio_yoy": 1,
                "no_heavy_dilution": 1,
                "higher_gross_margin_yoy": 1,
                "higher_operating_margin_yoy": 0
            }
        },
        "altman_z_score": {
            "z_score": 3.85,
            "zone": "Güvenli Bölge (Safe Zone)"
        },
        "dupont_analysis": {
            "tax_burden": 0.75,
            "interest_burden": 0.90,
            "ebit_margin": 0.24,
            "asset_turnover": 0.50,
            "financial_leverage": 1.78,
            "calculated_roe": 0.18
        },
        "dcf_2d_sensitivity": {
            "wacc_headers": ["%18,0", "%20,0", "%22,0"],
            "growth_headers": ["%2,0", "%2,5", "%3,0"],
            "matrix": [
                [55.0, 58.0, 62.0],
                [48.0, 50.0, 53.0],
                [42.0, 44.0, 46.0]
            ]
        },
        "peer_benchmark": [
            {
                "ticker": "PEER1.IS",
                "market_cap": 800000000.0,
                "ps_ratio": 1.6,
                "pe_ratio": 11.2,
                "profit_margins": 14.5,
                "revenue_growth": 18.0
            }
        ],
        "valuation_parameters": {
            "risk_free_rate": 0.0425,
            "beta": 1.1,
            "equity_risk_premium": 0.06,
            "cost_of_equity": 0.1085,
            "cost_of_debt": 0.12,
            "equity_weight": 0.80,
            "debt_weight": 0.20,
            "wacc": 0.102,
            "rule_of_40": 34.0
        },
        "standard_dcf_model": {
            "median_revenue_growth_assumed": 0.12,
            "median_fcf_margin_assumed": 0.16,
            "projected_fcf": [95000000.0, 106000000.0, 119000000.0, 133000000.0, 149000000.0],
            "projected_pv": [86000000.0, 87000000.0, 88000000.0, 89000000.0, 90000000.0],
            "terminal_value": 1500000000.0,
            "pv_terminal_value": 920000000.0,
            "implied_dcf_equity_value": 1160000000.0,
            "implied_share_price": 58.0
        },
        "reverse_dcf": {
            "recent_fcf": 85000000.0,
            "recent_sbc_adjusted_fcf": 83000000.0,
            "implied_growth_rate_raw": 0.085,
            "implied_growth_rate_sbc_adjusted": 0.082,
            "terminal_growth_rate": 0.025
        },
        "scenario_targets": {
            "bear_case_price": 35.0,
            "severe_downside_price": 25.0,
            "base_case_price": 58.0,
            "bull_case_price": 75.0
        },
        "suggested_portfolio_weighting": {
            "high_conviction_pct": 7.5,
            "med_conviction_pct": 4.2,
            "low_conviction_pct": 1.8
        }
    }


def get_mock_commentary():
    """Return a mock qualitative commentary dictionary."""
    return {
        "company_name": "Test Company AS",
        "executive_summary": "Test Company AS exhibits robust balance sheet fundamentals with high FCF yield.",
        "strong_points": "Strong cash flow generation and low net debt.",
        "weak_points": "Exposure to macroeconomic inflation risk.",
        "risk_discipline": "Kelly criterion suggests up to 7.5% portfolio allocation.",
        "scorecard_commentary": "Piotroski 8/9 and Altman Z-Score 3.85 place company in safe zone.",
        "piotroski_commentary": "8 out of 9 tests passed cleanly.",
        "altman_z_commentary": "Altman Z-Score indicates zero insolvency risk.",
        "moat_and_catalysts": "High switching costs and strong market share.",
        "ownership_commentary": "Stable institutional ownership structure.",
        "peer_comparison": "Trades at a discount relative to industry peers.",
        "dupont_analysis": "18% ROE driven by 24% EBIT margin and balanced leverage.",
        "forward_commentary": "Solid revenue growth trajectory for 2026E/2027E.",
        "dcf_valuation": "Base case DCF intrinsic fair value calculated at ₺58.00.",
        "technical_analysis": "RSI 58.5 indicates neutral-bullish momentum above 50-day SMA.",
        "forensic_audit": "Beneish M-Score of -2.85 confirms no earnings manipulation.",
        "scenario_analysis": "Base target ₺58.00, Bull target ₺75.00, Bear floor ₺35.00.",
        "investment_verdict": "DENGELİ MODEL GÖRÜŞÜ (GÜÇLÜ NAKİT / MAKUL DEĞERLEME DENGESİ)"
    }
