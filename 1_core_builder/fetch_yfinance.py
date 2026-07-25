#!/usr/bin/env python3
import sys
import os
import subprocess

def auto_install_dependencies():
    required_packages = ["yfinance", "pandas", "numpy", "requests", "curl_cffi", "beautifulsoup4"]
    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[*] Missing dependencies detected: {missing}. Installing automatically...", file=sys.stderr)
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("[*] Dependencies installed successfully!", file=sys.stderr)
        except Exception as e:
            print(f"[!] Warning: Failed to auto-install packages: {e}", file=sys.stderr)

auto_install_dependencies()

import json
import argparse
import yfinance as yf  # type: ignore
import pandas as pd
import numpy as np

def fetch_risk_free_rate():
    """Fetch 10-Yr US Treasury Yield. Falls back to 4.25% if unavailable."""
    try:
        tnx = yf.Ticker("^TNX")
        history = tnx.history(period="1d")
        if not history.empty:
            yield_val = history['Close'].iloc[-1]
            return float(yield_val) / 100.0
    except Exception as e:
        print(f"Warning: Failed to fetch risk-free rate from ^TNX: {e}. Falling back to 4.25%.", file=sys.stderr)
    return 0.0425

def safe_get(df, index_names, col_idx=0):
    """Safely retrieves a value from a pandas DataFrame by list of potential index names."""
    if df is None or getattr(df, 'empty', True):
        return 0.0
    if isinstance(index_names, str):
        index_names = [index_names]
        
    for name in index_names:
        name_clean = str(name).lower().replace(" ", "").replace("_", "")
        for idx in df.index:
            idx_clean = str(idx).lower().replace(" ", "").replace("_", "")
            if idx_clean == name_clean:
                try:
                    val = df.loc[idx]
                    if hasattr(val, 'iloc'):
                        if len(val) > col_idx:
                            res = val.iloc[col_idx]
                            return float(res) if not pd.isna(res) else 0.0
                        return 0.0
                    return float(val) if not pd.isna(val) else 0.0
                except Exception:
                    return 0.0
    return 0.0

def calculate_relative_strength(ticker_symbol, info, language="TR"):
    """Calculate stock, local benchmark index, and sector ETF returns over 3 months and 1 year."""
    try:
        parts = ticker_symbol.upper().split('.')
        suffix = parts[-1] if len(parts) > 1 else ""
        
        suffix_mapping = {
            "IS": "XU100.IS",  # Turkey BIST 100
            "DE": "^GDAXI",  # Germany DAX
            "L": "^FTSE",    # UK FTSE 100
            "T": "^N225",    # Japan Nikkei 225
            "PA": "^FCHI",   # France CAC 40
            "HK": "^HSI",    # Hong Kong Hang Seng
            "TO": "^GSPTSE", # Canada TSX Composite
            "AX": "^AXJO",   # Australia ASX 200
            "SS": "000001.SS", # China Shanghai Composite
            "SZ": "399001.SZ", # China Shenzhen Component
            "BO": "^BSESN",  # India BSE Sensex
            "NS": "^NSEI",   # India NSE Nifty 50
            "MI": "FTSEMIB.MI", # Italy FTSE MIB
            "MC": "^IBEX",   # Spain IBEX 35
        }
        
        benchmark_ticker = suffix_mapping.get(suffix, "^GSPC") # Fallback to S&P 500
        benchmark_name = "S&P 500" if benchmark_ticker == "^GSPC" else (f"BIST 100" if benchmark_ticker == "XU100.IS" else f"{benchmark_ticker} Index")
        
        sector_mapping = {
            "technology": "XLK",
            "software": "XLK",
            "financial services": "XLF",
            "healthcare": "XLV",
            "consumer cyclical": "XLY",
            "industrials": "XLI"
        }
        
        sector_name = info.get("sector", "")
        sector_ticker = sector_mapping.get(sector_name.lower()) if sector_name else None
        
        stock = yf.Ticker(ticker_symbol)
        benchmark = yf.Ticker(benchmark_ticker)
        
        s_hist = stock.history(period="1y")
        bench_hist = benchmark.history(period="1y")
        
        if s_hist.empty or bench_hist.empty:
            return {}
            
        close_today = s_hist['Close'].iloc[-1]
        bench_today = bench_hist['Close'].iloc[-1]
        
        idx_3m = min(len(s_hist) - 1, 63)
        close_3m = s_hist['Close'].iloc[-idx_3m]
        bench_idx_3m = min(len(bench_hist) - 1, 63)
        bench_3m = bench_hist['Close'].iloc[-bench_idx_3m]
        
        idx_1y = min(len(s_hist) - 1, 252)
        close_1y = s_hist['Close'].iloc[-idx_1y]
        bench_idx_1y = min(len(bench_hist) - 1, 252)
        bench_1y = bench_hist['Close'].iloc[-bench_idx_1y]
        
        stock_3m_ret = (close_today - close_3m) / close_3m
        bench_3m_ret = (bench_today - bench_3m) / bench_3m
        
        stock_1y_ret = (close_today - close_1y) / close_1y
        bench_1y_ret = (bench_today - bench_1y) / bench_1y
        
        stock_recent_vol = s_hist['Volume'].iloc[-5:].mean()
        bench_recent_vol = bench_hist['Volume'].iloc[-5:].mean()
        stock_avg_vol = s_hist['Volume'].iloc[-60:].mean()
        bench_avg_vol = bench_hist['Volume'].iloc[-60:].mean()
        
        stock_vol_ratio = stock_recent_vol / stock_avg_vol if stock_avg_vol > 0 else 1.0
        bench_vol_ratio = bench_recent_vol / bench_avg_vol if bench_avg_vol > 0 else 1.0
        volume_divergence = stock_vol_ratio / bench_vol_ratio if bench_vol_ratio > 0 else 1.0
        
        if language.upper() == "EN":
            if volume_divergence > 1.5:
                interpretation = "Significant Positive Divergence (Idiosyncratic accumulation)"
            elif volume_divergence < 0.7:
                interpretation = "Significant Negative Divergence (Market neglect / consolidation)"
            else:
                interpretation = "Parallel Volume Flow (Driven by market-wide liquidity)"
        else:
            if volume_divergence > 1.5:
                interpretation = "Belirgin Pozitif Sapma (Kurumsal birikim / özgün hareket)"
            elif volume_divergence < 0.7:
                interpretation = "Belirgin Negatif Sapma (Piyasa ilgisizliği / konsolidasyon)"
            else:
                interpretation = "Paralel Hacim Akışı (Piyasa geneli likidite kaynaklı)"
            
        delta = s_hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = float(100 - (100 / (1 + rs.iloc[-1]))) if not rs.empty and not pd.isna(rs.iloc[-1]) else 50.0

        ema12 = s_hist['Close'].ewm(span=12, adjust=False).mean()
        ema26 = s_hist['Close'].ewm(span=26, adjust=False).mean()
        macd_line = float((ema12 - ema26).iloc[-1])
        macd_signal = float((ema12 - ema26).ewm(span=9, adjust=False).mean().iloc[-1])

        support_level = float(s_hist['Low'].iloc[-60:].min())
        resistance_level = float(s_hist['High'].iloc[-60:].max())

        return {
            "benchmark_ticker": benchmark_ticker,
            "benchmark_name": benchmark_name,
            "stock_3m_return": stock_3m_ret,
            "benchmark_3m_return": bench_3m_ret,
            "relative_strength_3m": stock_3m_ret - bench_3m_ret,
            "stock_1y_return": stock_1y_ret,
            "benchmark_1y_return": bench_1y_ret,
            "relative_strength_1y": stock_1y_ret - bench_1y_ret,
            "stock_recent_volume_vs_avg": stock_vol_ratio,
            "benchmark_recent_volume_vs_avg": bench_vol_ratio,
            "volume_divergence_ratio": volume_divergence,
            "volume_divergence_interpretation": interpretation,
            "technical_indicators": {
                "rsi_14": round(rsi_14, 2),
                "macd_line": round(macd_line, 2),
                "macd_signal": round(macd_signal, 2),
                "support_level_60d": round(support_level, 2),
                "resistance_level_60d": round(resistance_level, 2)
            }
        }
    except Exception as e:
        print(f"Warning: Failed to calculate relative strength: {e}", file=sys.stderr)
        return {}

def compute_piotroski_f_score(history_metrics):
    """Computes Piotroski F-Score (0 to 9 points) from history metrics."""
    if not history_metrics or len(history_metrics) < 2:
        return {"score": 5, "rating": "Moderate Health", "breakdown": {}}
    
    m0 = history_metrics[0]
    m1 = history_metrics[1]
    
    score = 0
    breakdown = {}
    
    f1 = 1 if m0.get("net_income", 0) > 0 else 0
    score += f1
    breakdown["positive_net_income"] = f1
    
    f2 = 1 if m0.get("operating_cash_flow", 0) > 0 else 0
    score += f2
    breakdown["positive_cfo"] = f2
    
    f3 = 1 if m0.get("net_income", 0) > m1.get("net_income", 0) else 0
    score += f3
    breakdown["higher_roa_yoy"] = f3
    
    f4 = 1 if m0.get("operating_cash_flow", 0) > m0.get("net_income", 0) else 0
    score += f4
    breakdown["accruals_cfo_gt_ni"] = f4
    
    f5 = 1 if m0.get("debt_to_equity", 0) <= m1.get("debt_to_equity", 0) else 0
    score += f5
    breakdown["lower_leverage_yoy"] = f5
    
    f6 = 1 if m0.get("current_ratio", 0) >= m1.get("current_ratio", 0) else 0
    score += f6
    breakdown["higher_current_ratio_yoy"] = f6
    
    f7 = 1 if m0.get("sbc", 0) <= m1.get("sbc", 0) else 0
    score += f7
    breakdown["no_heavy_dilution"] = f7
    
    f8 = 1 if m0.get("gross_margin", 0) >= m1.get("gross_margin", 0) else 0
    score += f8
    breakdown["higher_gross_margin_yoy"] = f8
    
    f9 = 1 if m0.get("operating_margin", 0) >= m1.get("operating_margin", 0) else 0
    score += f9
    breakdown["higher_operating_margin_yoy"] = f9
    
    rating = "Strong Financial Health (8-9)" if score >= 8 else ("Moderate Health (5-7)" if score >= 5 else "Weak/Distressed Health (0-4)")
    return {"score": score, "rating": rating, "breakdown": breakdown}

def compute_altman_z_score(history_metrics, market_cap):
    """Computes Altman Z-Score for non-manufacturing / emerging market firms."""
    if not history_metrics:
        return {"z_score": 2.5, "zone": "Grey Zone"}
    
    m = history_metrics[0]
    total_assets = m.get("revenue", 1) * 1.5
    rev = m.get("revenue", 0)
    ebit = m.get("operating_income", 0)
    net_inc = m.get("net_income", 0)
    total_debt = m.get("total_debt", 1)
    
    x1 = (m.get("cash_and_equivalents", 0) / total_assets) if total_assets > 0 else 0.1
    x2 = (net_inc / total_assets) if total_assets > 0 else 0.05
    x3 = (ebit / total_assets) if total_assets > 0 else 0.05
    x4 = (market_cap / total_debt) if total_debt > 0 else 2.0
    x5 = (rev / total_assets) if total_assets > 0 else 0.8
    
    z_score = round(1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5, 2)
    
    if z_score < 1.81:
        zone = "Distress Zone (High Insolvency Risk)"
    elif z_score <= 2.99:
        zone = "Grey Zone (Moderate Insolvency Risk)"
    else:
        zone = "Safe Zone (Low Insolvency Risk)"
        
    return {"z_score": z_score, "zone": zone}

def compute_dupont_analysis(history_metrics):
    """Computes DuPont 5-Step ROE Decomposition."""
    if not history_metrics:
        return {}
    m = history_metrics[0]
    rev = m.get("revenue", 1.0)
    ebit = m.get("operating_income", 0.0)
    net_inc = m.get("net_income", 0.0)
    
    tax_burden = round(net_inc / ebit, 4) if ebit != 0 else 1.0
    interest_burden = 1.0
    ebit_margin = round(ebit / rev, 4) if rev > 0 else 0.0
    asset_turnover = 0.8
    financial_leverage = round(1.0 + m.get("debt_to_equity", 0.0), 2)
    
    calculated_roe = round(tax_burden * interest_burden * ebit_margin * asset_turnover * financial_leverage * 100, 2)
    
    return {
        "tax_burden": tax_burden,
        "interest_burden": interest_burden,
        "ebit_margin": ebit_margin,
        "asset_turnover": asset_turnover,
        "financial_leverage": financial_leverage,
        "dupont_roe_pct": calculated_roe
    }

def compute_2d_dcf_sensitivity(recent_fcf, net_debt, shares_outstanding, base_wacc, base_g=0.025):
    """Computes 5x5 WACC vs Terminal Growth DCF Sensitivity Matrix."""
    wacc_steps = [max(0.005, base_wacc - 0.04), max(0.005, base_wacc - 0.02), base_wacc, base_wacc + 0.02, base_wacc + 0.04]
    g_steps = [0.015, 0.020, base_g, 0.030, 0.035]
    
    matrix = []
    for w in wacc_steps:
        row = []
        for g in g_steps:
            if w > g:
                fcf_5y = sum([recent_fcf * ((1 + 0.05) ** i) / ((1 + w) ** i) for i in range(1, 6)])
                term_val = (recent_fcf * ((1 + 0.05) ** 5) * (1 + g)) / (w - g)
                pv_term = term_val / ((1 + w) ** 5)
                eq_val = (fcf_5y + pv_term) - net_debt
                px = eq_val / shares_outstanding if shares_outstanding > 0 else 0.0
                row.append(round(px, 2))
            else:
                row.append(0.0)
        matrix.append(row)
        
    return {
        "wacc_headers": [f"%{round(w*100, 2)}" for w in wacc_steps],
        "growth_headers": [f"%{round(g*100, 2)}" for g in g_steps],
        "matrix": matrix
    }

def fetch_peer_benchmark_data(ticker_symbol, sector_name="Technology"):
    """Fetches benchmark comparison data for sector peers."""
    parts = ticker_symbol.upper().split('.')
    suffix = f".{parts[-1]}" if len(parts) > 1 else ""
    
    if suffix == ".IS":
        peers = ["KONTR.IS", "LOGO.IS", "LINK.IS", "MOBTL.IS"]
    else:
        peers = ["AAPL", "MSFT", "GOOGL", "NVDA"]
        
    peer_data = []
    for p in peers:
        if p == ticker_symbol.upper():
            continue
        try:
            pt = yf.Ticker(p)
            pi = pt.info or {}
            peer_data.append({
                "ticker": p,
                "name": pi.get("shortName") or p,
                "market_cap": pi.get("marketCap", 0),
                "pe_ratio": round(pi.get("trailingPE", 0) or 0, 2),
                "ps_ratio": round(pi.get("priceToSalesTrailing12Months", 0) or 0, 2),
                "profit_margins": round((pi.get("profitMargins", 0) or 0) * 100, 2),
                "revenue_growth": round((pi.get("revenueGrowth", 0) or 0) * 100, 2)
            })
        except Exception as pe:
            print(f"Warning: Failed to fetch peer {p}: {pe}", file=sys.stderr)
            
    return peer_data

def run_analysis(ticker_symbol, output_path, language="TR"):
    print(f"Initializing sourcing for ticker: {ticker_symbol} (Language: {language})...")
    
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info or {}
    
    market_cap = info.get("marketCap", 0.0)
    enterprise_value = info.get("enterpriseValue", 0.0)
    current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
    fifty_day_avg = info.get("fiftyDayAverage", 0.0)
    two_hundred_day_avg = info.get("twoHundredDayAverage", 0.0)
    beta = info.get("beta")
    if beta is None or beta == 0.0:
        beta = 1.0
        
    short_percent = info.get("shortPercentOfFloat", 0.0)
    days_to_cover = info.get("shortRatio", 0.0)
    shares_outstanding = info.get("sharesOutstanding", 0.0)
    
    currency_code = info.get("financialCurrency") or info.get("currency") or "USD"
    currency_symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
        "TRY": "₺", "CAD": "C$", "AUD": "A$", "CNY": "¥",
        "HKD": "HK$", "INR": "₹", "BRL": "R$", "RUB": "₽",
        "ZAR": "R", "CHF": "CHF", "KRW": "₩", "SEK": "kr"
    }
    currency_symbol = currency_symbols.get(currency_code.upper(), "$")
    
    financials = ticker.financials
    balance_sheet = ticker.balance_sheet
    cashflow = ticker.cashflow
    
    years = []
    revenues = []
    gross_profits = []
    operating_incomes = []
    net_incomes = []
    basic_epss = []
    op_cashflows = []
    capexs = []
    sbcs = []
    total_assets_list = []
    total_liabs_list = []
    current_assets_list = []
    current_liabs_list = []
    cash_equivalents_list = []
    total_debts = []
    interest_expenses = []
    
    cols = financials.columns if financials is not None else []
    for i, col in enumerate(cols[:3]):
        year_str = col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else (str(col.date()) if hasattr(col, 'date') else str(col)[:10])
        years.append(year_str)
        
        rev = safe_get(financials, ["TotalRevenue", "Revenue"], i)
        gp = safe_get(financials, ["GrossProfit"], i)
        op_inc = safe_get(financials, ["OperatingIncome", "OperatingIncomeOrLoss"], i)
        net_inc = safe_get(financials, ["NetIncome"], i)
        eps = safe_get(financials, ["BasicEPS", "DilutedEPS"], i)
        interest = safe_get(financials, ["InterestExpense"], i)
        
        op_cf = safe_get(cashflow, ["OperatingCashFlow", "CashFlowFromOperatingActivities"], i)
        capex = abs(safe_get(cashflow, ["CapitalExpenditure", "CapitalExpenditures"], i))
        sbc = safe_get(cashflow, ["StockBasedCompensation", "ShareBasedCompensation"], i)
        
        total_assets = safe_get(balance_sheet, ["TotalAssets"], i)
        total_liab = safe_get(balance_sheet, ["TotalLiabilitiesNetMinorityInterest", "TotalLiabilities"], i)
        curr_assets = safe_get(balance_sheet, ["CurrentAssets", "TotalCurrentAssets"], i)
        curr_liab = safe_get(balance_sheet, ["CurrentLiabilities", "TotalCurrentLiabilities"], i)
        cash_eq = safe_get(balance_sheet, ["CashAndCashEquivalents", "CashCashEquivalentsAndShortTermInvestments"], i)
        
        total_debt = safe_get(balance_sheet, ["TotalDebt"], i)
        if total_debt == 0.0:
            long_term_debt = safe_get(balance_sheet, ["LongTermDebt"], i)
            short_term_debt = safe_get(balance_sheet, ["ShortLongTermDebt", "CurrentDebt"], i)
            total_debt = long_term_debt + short_term_debt
            
        revenues.append(rev)
        gross_profits.append(gp)
        operating_incomes.append(op_inc)
        net_incomes.append(net_inc)
        basic_epss.append(eps)
        op_cashflows.append(op_cf)
        capexs.append(capex)
        sbcs.append(sbc)
        total_assets_list.append(total_assets)
        total_liabs_list.append(total_liab)
        current_assets_list.append(curr_assets)
        current_liabs_list.append(curr_liab)
        cash_equivalents_list.append(cash_eq)
        total_debts.append(total_debt)
        interest_expenses.append(interest)

    rf = fetch_risk_free_rate()
    erp = 0.050
    cost_of_equity = rf + (beta * erp)
    
    recent_debt = total_debts[0] if len(total_debts) > 0 else 0.0
    recent_interest = interest_expenses[0] if len(interest_expenses) > 0 else 0.0
    recent_cash = cash_equivalents_list[0] if len(cash_equivalents_list) > 0 else 0.0
    net_debt = recent_debt - recent_cash
    
    if recent_debt > 0 and recent_interest > 0:
        cost_of_debt = recent_interest / recent_debt
    else:
        cost_of_debt = 0.06
        
    tax_rate = 0.21
    total_cap = market_cap + recent_debt
    if total_cap > 0:
        equity_weight = market_cap / total_cap
        debt_weight = recent_debt / total_cap
    else:
        equity_weight = 1.0
        debt_weight = 0.0
        
    wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - tax_rate))
    
    history_metrics = []
    for idx in range(len(years)):
        rev_val = revenues[idx]
        gp_val = gross_profits[idx]
        op_inc_val = operating_incomes[idx]
        net_inc_val = net_incomes[idx]
        op_cf_val = op_cashflows[idx]
        capex_val = capexs[idx]
        sbc_val = sbcs[idx]
        debt_val = total_debts[idx]
        assets_val = total_assets_list[idx]
        liabs_val = total_liabs_list[idx]
        curr_assets_val = current_assets_list[idx]
        curr_liabs_val = current_liabs_list[idx]
        cash_val = cash_equivalents_list[idx]
        
        fcf = op_cf_val - capex_val
        sbc_adj_fcf = fcf - sbc_val
        
        gross_margin = gp_val / rev_val if rev_val > 0 else 0.0
        operating_margin = op_inc_val / rev_val if rev_val > 0 else 0.0
        net_margin = net_inc_val / rev_val if rev_val > 0 else 0.0
        fcf_margin = fcf / rev_val if rev_val > 0 else 0.0
        
        current_ratio = curr_assets_val / curr_liabs_val if curr_liabs_val > 0 else 0.0
        book_equity = assets_val - liabs_val
        debt_to_equity = debt_val / book_equity if book_equity > 0 else 0.0
        net_debt_val = debt_val - cash_val
        roe = net_inc_val / book_equity if book_equity > 0 else 0.0
        
        invested_capital = debt_val + book_equity - cash_val
        roic = op_inc_val * (1 - tax_rate) / invested_capital if invested_capital > 0 else 0.0
        
        history_metrics.append({
            "year": years[idx],
            "revenue": rev_val,
            "gross_profit": gp_val,
            "operating_income": op_inc_val,
            "net_income": net_inc_val,
            "basic_eps": basic_epss[idx],
            "operating_cash_flow": op_cf_val,
            "capex": capex_val,
            "fcf": fcf,
            "sbc": sbc_val,
            "sbc_adjusted_fcf": sbc_adj_fcf,
            "total_debt": debt_val,
            "cash_and_equivalents": cash_val,
            "net_debt": net_debt_val,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "net_margin": net_margin,
            "fcf_margin": fcf_margin,
            "current_ratio": current_ratio,
            "debt_to_equity": debt_to_equity,
            "roe": roe,
            "roic": roic
        })
        
    rel_strength = calculate_relative_strength(ticker_symbol, info, language=language)
    
    recent_fcf = float(history_metrics[0]["fcf"]) if len(history_metrics) > 0 else 0.0
    recent_rev = float(history_metrics[0]["revenue"]) if len(history_metrics) > 0 else 0.0
    
    growth_rates = []
    fcf_margins = []
    for h in history_metrics:
        fcf_margins.append(float(h["fcf_margin"]))
        
    for j in range(len(history_metrics) - 1):
        rev_next = float(history_metrics[j+1]["revenue"])
        rev_curr = float(history_metrics[j]["revenue"])
        if rev_next > 0:
            growth_rates.append((rev_curr - rev_next) / rev_next)
            
    median_growth = float(np.median(growth_rates)) if len(growth_rates) > 0 else 0.05
    median_fcf_margin = float(np.median(fcf_margins)) if len(fcf_margins) > 0 else 0.15
    
    dcf_growth = max(0.01, min(median_growth, 0.20))
    dcf_margin = max(0.05, min(median_fcf_margin, 0.40))
    
    projected_fcf = []
    projected_pv = []
    temp_rev = recent_rev
    for year_idx in range(1, 6):
        temp_rev = temp_rev * (1 + dcf_growth)
        fcf_est = temp_rev * dcf_margin
        pv = fcf_est / ((1 + wacc) ** year_idx)
        projected_fcf.append(fcf_est)
        projected_pv.append(pv)
        
    terminal_g = 0.025
    terminal_fcf = projected_fcf[-1] * (1 + terminal_g)
    terminal_value = terminal_fcf / (wacc - terminal_g)
    pv_terminal_value = terminal_value / ((1 + wacc) ** 5)
    
    implied_dcf_ev = sum(projected_pv) + pv_terminal_value
    implied_dcf_equity_value = implied_dcf_ev - net_debt
    implied_dcf_share_price = implied_dcf_equity_value / shares_outstanding if shares_outstanding > 0 else 0.0
    
    implied_g_raw = 0.0
    implied_g_sbc_adj = 0.0
    recent_sbc_adj_fcf = float(history_metrics[0]["sbc_adjusted_fcf"]) if len(history_metrics) > 0 else 0.0
    
    if enterprise_value > 0:
        if recent_fcf > 0:
            implied_g_raw = (enterprise_value * wacc - recent_fcf) / (enterprise_value + recent_fcf)
        if recent_sbc_adj_fcf > 0:
            implied_g_sbc_adj = (enterprise_value * wacc - recent_sbc_adj_fcf) / (enterprise_value + recent_sbc_adj_fcf)
            
    recent_rev_growth = growth_rates[0] if len(growth_rates) > 0 else 0.0
    rule_of_40_val = (recent_rev_growth + fcf_margins[0]) * 100.0 if len(fcf_margins) > 0 else 0.0
    
    scenario_targets = {
        "bear_case_price": current_price * 0.70,
        "severe_downside_price": current_price * 0.50,
        "base_case_price": implied_dcf_share_price if implied_dcf_share_price > 0 else current_price * 1.10,
        "bull_case_price": (implied_dcf_share_price if implied_dcf_share_price > 0 else current_price) * 1.30
    }
    
    base_upside = max(0.01, (scenario_targets["base_case_price"] - current_price) / current_price)
    base_downside = max(0.01, (current_price - scenario_targets["bear_case_price"]) / current_price)
    asymmetry_ratio = base_upside / base_downside
    
    wacc_penalty = max(0.5, 1.0 - max(0.0, wacc - 0.08))
    
    suggested_weighting = {}
    for tier, (p_win, limit_cap) in {
        "high": (0.70, 10.0),
        "med": (0.55, 5.0),
        "low": (0.40, 2.0)
    }.items():
        q_loss = 1.0 - p_win
        kelly = p_win - (q_loss / asymmetry_ratio)
        kelly = max(0.0, kelly)
        suggested_val = kelly * limit_cap * wacc_penalty
        suggested_weighting[f"{tier}_conviction_pct"] = round(min(limit_cap, suggested_val), 2)
        
    piotroski = compute_piotroski_f_score(history_metrics)
    altman_z = compute_altman_z_score(history_metrics, market_cap)
    dupont = compute_dupont_analysis(history_metrics)
    dcf_2d_matrix = compute_2d_dcf_sensitivity(recent_fcf, net_debt, shares_outstanding, wacc)
    peer_benchmark = fetch_peer_benchmark_data(ticker_symbol, sector_name=info.get("sector", "Technology"))
    
    c_name = info.get("longName") or info.get("shortName")
    if not c_name:
        try:
            import sqlite3
            db_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "storage", "app.db"))
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                res = conn.execute("SELECT company_name FROM watchlist WHERE ticker=?", (ticker_symbol,)).fetchone()
                if res and res[0]:
                    c_name = res[0]
                conn.close()
        except Exception:
            pass
    if not c_name:
        c_name = ticker_symbol

    import math
    ebitda_val = info.get("ebitda") or (history_metrics[0].get("operating_income", 0) * 1.15 if len(history_metrics) > 0 else 0.0)
    ev_to_ebitda = float(enterprise_value / ebitda_val) if ebitda_val and ebitda_val > 0 else 0.0
    net_debt_to_ebitda = float(net_debt / ebitda_val) if ebitda_val and ebitda_val > 0 else 0.0

    eps_val = float(info.get("trailingEps") or (history_metrics[0].get("basic_eps", 0) if len(history_metrics) > 0 else 0.0))
    bvps_val = float(info.get("bookValue") or 0.0)
    graham_number = math.sqrt(22.5 * eps_val * bvps_val) if (eps_val > 0 and bvps_val > 0) else 0.0
    fcf_margin_val = float(recent_fcf / recent_rev) if recent_rev > 0 else 0.0

    expanded_metrics = {
        "ebitda": ebitda_val,
        "ev_to_ebitda": round(ev_to_ebitda, 2),
        "net_debt_to_ebitda": round(net_debt_to_ebitda, 2),
        "trailing_eps": round(eps_val, 2),
        "book_value_per_share": round(bvps_val, 2),
        "graham_number": round(graham_number, 2),
        "fcf_margin_pct": round(fcf_margin_val * 100.0, 2)
    }

    data = {
        "ticker": ticker_symbol,
        "name": c_name,
        "market_info": {
            "market_cap": market_cap,
            "enterprise_value": enterprise_value,
            "current_price": current_price,
            "fifty_day_avg": fifty_day_avg,
            "two_hundred_day_avg": two_hundred_day_avg,
            "beta": beta,
            "shares_outstanding": shares_outstanding,
            "short_percent_of_float": short_percent,
            "days_to_cover": days_to_cover,
            "currency_code": currency_code,
            "currency_symbol": currency_symbol
        },
        "expanded_metrics": expanded_metrics,
        "historical_metrics": history_metrics,
        "relative_strength": rel_strength,
        "piotroski_f_score": piotroski,
        "altman_z_score": altman_z,
        "dupont_analysis": dupont,
        "dcf_2d_sensitivity": dcf_2d_matrix,
        "peer_benchmark": peer_benchmark,
        "valuation_parameters": {
            "risk_free_rate": rf,
            "beta": beta,
            "equity_risk_premium": erp,
            "cost_of_equity": cost_of_equity,
            "cost_of_debt": cost_of_debt,
            "equity_weight": equity_weight,
            "debt_weight": debt_weight,
            "wacc": wacc,
            "rule_of_40": rule_of_40_val
        },
        "standard_dcf_model": {
            "median_revenue_growth_assumed": dcf_growth,
            "median_fcf_margin_assumed": dcf_margin,
            "projected_fcf": projected_fcf,
            "projected_pv": projected_pv,
            "terminal_value": terminal_value,
            "pv_terminal_value": pv_terminal_value,
            "implied_dcf_equity_value": implied_dcf_equity_value,
            "implied_share_price": implied_dcf_share_price
        },
        "reverse_dcf": {
            "recent_fcf": recent_fcf,
            "recent_sbc_adjusted_fcf": recent_sbc_adj_fcf,
            "implied_growth_rate_raw": implied_g_raw,
            "implied_growth_rate_sbc_adjusted": implied_g_sbc_adj,
            "terminal_growth_rate": terminal_g
        },
        "scenario_targets": scenario_targets,
        "suggested_portfolio_weighting": suggested_weighting
    }
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"Data saved successfully to: {output_path}")
    print(f"Computed WACC: {wacc:.2%}, Piotroski F-Score: {piotroski['score']}/9, Altman Z-Score: {altman_z['z_score']} ({altman_z['zone']})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch yfinance data metrics.")
    parser.add_argument("ticker", type=str, help="Stock ticker symbol")
    parser.add_argument("--output", type=str, default="_workspace/01_quant_metrics.json", help="Output file path")
    parser.add_argument("--language", type=str, default="TR", choices=["TR", "EN"], help="Target report language (TR or EN)")
    args = parser.parse_args()
    
    try:
        run_analysis(args.ticker, args.output, language=args.language)
    except Exception as e:
        print(f"Error during analysis execution: {e}", file=sys.stderr)
        sys.exit(1)
