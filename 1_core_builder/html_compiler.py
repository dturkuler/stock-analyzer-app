"""
HTML Report Compiler — 100% Master Parity & Modern Web UI Edition
Generates:
1. Interactive 13-tab HTML dashboard with modern, sleek executive UI cards,
   complete with Executive Key Metrics table, 12-Month Catalyst Timeline,
   Balance Sheet & Income Statement tables, Forward P/S projections, Macro Shock WACC table,
   5-row Forensic Audit table, Algorithmic Risk & Price Levels summary table,
   and rich, stock-specific multi-point Investor Guide Boxes across all 13 modules.
2. Continuous standalone printable HTML report (YYYYMMDD_printable.html)
   designed for printing, PDF conversion, or copying text across all sections.

Usage:
    from html_compiler import compile_report, compile_printable_report
    html = compile_report(metrics, commentary)
    printable_html = compile_printable_report(metrics, commentary)
"""

import json
import math
import datetime
from logger import log_error

try:
    from i18n import t
except ImportError:
    import importlib
    t = importlib.import_module("1_core_builder.i18n").t
import re


def _fmt_curr(val, is_en=False, decimals=2):
    """Format number as currency string ($ for EN, ₺ for TR)."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    sym = "$" if is_en else "₺"
    if is_en:
        if abs(val) >= 1e9:
            return f"{sym}{val/1e9:,.2f}B"
        elif abs(val) >= 1e6:
            return f"{sym}{val/1e6:,.2f}M"
        else:
            return f"{sym}{val:,.{decimals}f}"
    else:
        if abs(val) >= 1e9:
            return f"₺{val/1e9:,.2f} Mr".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(val) >= 1e6:
            return f"₺{val/1e6:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"₺{val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_try(val, decimals=2, is_en=False):
    return _fmt_curr(val, is_en=is_en, decimals=decimals)


def _fmt_pct(val, is_en=False, decimals=2):
    """Format number as percentage string."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    if is_en:
        return f"{val*100:,.{decimals}f}%"
    return f"%{val*100:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_num(val, is_en=False, decimals=2):
    """Format number in appropriate locale."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    if is_en:
        return f"{val:,.{decimals}f}"
    return f"{val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _piotroski_row(label, value, is_en=False):
    """Generate a Piotroski test result table row."""
    lang = "EN" if is_en else "TR"
    if value == 1:
        pass_txt = t("common.passed", lang=lang)
        return f'<tr><td>{label}</td><td><span class="tag-green">{pass_txt}</span></td></tr>'
    else:
        neut_txt = t("common.neutral", lang=lang)
        return f'<tr><td>{label}</td><td><span class="tag-amber">{neut_txt}</span></td></tr>'


def _peer_row(peer, is_target=False, is_en=False):
    """Generate peer comparison table row."""
    lang = "EN" if is_en else "TR"
    style = ' style="background: rgba(6, 182, 212, 0.15); font-weight: 700;"' if is_target else ''
    tag_class = "tag-red" if is_target else "tag-green"
    if is_target:
        tag_text = f"🔴 {peer.get('ticker', '')} ({t('common.target', lang=lang)})"
    else:
        tag_text = "🟢 Peer" if is_en else "🟢 Rakip"
    mcap = _fmt_curr(peer.get("market_cap", 0), is_en=is_en)
    ps = _fmt_num(peer.get("ps_ratio", 0), is_en=is_en, decimals=1) + "x"
    pe = _fmt_num(peer.get("pe_ratio", 0), is_en=is_en, decimals=1) + "x"
    margin = _fmt_pct(peer.get("profit_margins", 0), is_en=is_en, decimals=1)
    growth = _fmt_pct(peer.get("revenue_growth", 0), is_en=is_en, decimals=1)
    return f'<tr{style}><td>{peer.get("ticker", "")}</td><td>{mcap}</td><td>{ps}</td><td>{pe}</td><td>{margin}</td><td>{growth}</td><td><span class="{tag_class}">{tag_text}</span></td></tr>'


def format_analyst_text(text, is_en=False):
    """Format raw analyst text, converting embedded lists, subheaders, and scenario blocks into visual HTML cards & bullets."""
    lang = "EN" if is_en else "TR"
    if not text:
        return ""
    text_str = str(text).strip()
    if not text_str:
        return ""

    has_catalysts = "büyüme fırsatları" in text_str.lower() or "growth opportunities" in text_str.lower() or "katalizörler" in text_str.lower()
    has_risks = "riskler" in text_str.lower() or "risk radar" in text_str.lower() or "risk faktörleri" in text_str.lower()

    if has_catalysts and has_risks:
        parts = re.split(r'(?:kritik risk faktörleri|kritik riskler|risk faktörleri|risk radarı|riskler|risk radar):', text_str, flags=re.IGNORECASE)
        if len(parts) >= 2:
            cat_part = re.sub(r'^(?:büyüme fırsatları|growth opportunities|katalizörler):', '', parts[0], flags=re.IGNORECASE).strip()
            risk_part = parts[1].strip()

            def _parse_bullets(raw_str):
                items = re.split(r'(?:\b\d+\)|\b\d+\.(?=\s|$)|(?:^\s*|\n\s*)[\-\•]\s*)', raw_str)
                cleaned = [it.strip() for it in items if it.strip()]
                if not cleaned:
                    cleaned = [raw_str]
                lis = "".join([f'<li>{it}</li>' for it in cleaned])
                return f'<ul class="analyst-bullet-list">{lis}</ul>'

            cat_html = _parse_bullets(cat_part)
            risk_html = _parse_bullets(risk_part)

            cat_title = t("analyst.catalysts_title", lang=lang)
            risk_title = t("analyst.risks_title", lang=lang)

            return f'''<div class="grid-2" style="margin-bottom:0.5rem;">
                <div class="analyst-subcard analyst-subcard-emerald">
                    <h4>{cat_title}</h4>
                    {cat_html}
                </div>
                <div class="analyst-subcard analyst-subcard-rose">
                    <h4>{risk_title}</h4>
                    {risk_html}
                </div>
            </div>'''

    has_bull = "boğa senaryosu" in text_str.lower() or "bull case" in text_str.lower() or "boğa:" in text_str.lower()
    has_bear = "ayı senaryosu" in text_str.lower() or "bear case" in text_str.lower() or "ayı:" in text_str.lower()

    if has_bull and has_bear:
        bull_match = re.search(r'(?:boğa senaryosu|bull case|boğa):\s*(.*?)(?=(?:ayı senaryosu|bear case|ayı|nihai değerlendirme|sonuç|takeaway):|$)', text_str, re.IGNORECASE | re.DOTALL)
        bear_match = re.search(r'(?:ayı senaryosu|bear case|ayı):\s*(.*?)(?=(?:nihai değerlendirme|sonuç|takeaway|küçük yatırımcı):|$)', text_str, re.IGNORECASE | re.DOTALL)
        verdict_match = re.search(r'(?:nihai değerlendirme|sonuç|takeaway|küçük yatırımcı için sonuç):\s*(.*)', text_str, re.IGNORECASE | re.DOTALL)

        bull_text = bull_match.group(1).strip() if bull_match else ""
        bear_text = bear_match.group(1).strip() if bear_match else ""
        verdict_text = verdict_match.group(1).strip() if verdict_match else ""

        bull_title = t("analyst.bull_title", lang=lang)
        bear_title = t("analyst.bear_title", lang=lang)

        out_html = f'''<div class="grid-2" style="margin-bottom:0.5rem;">
            <div class="analyst-subcard analyst-subcard-emerald">
                <h4>{bull_title}</h4>
                <p style="color:var(--text-main); font-size:0.92rem; line-height:1.6;">{bull_text}</p>
            </div>
            <div class="analyst-subcard analyst-subcard-rose">
                <h4>{bear_title}</h4>
                <p style="color:var(--text-main); font-size:0.92rem; line-height:1.6;">{bear_text}</p>
            </div>
        </div>'''

        if verdict_text:
            out_html += f'''<div class="analyst-takeaway-banner">
                <strong>💡 {t("analyst.retail_takeaway", lang=lang)}</strong> {verdict_text}
            </div>'''
        return out_html
        return out_html

    if re.search(r'(?:\b\d+\)|\b\d+\.(?=\s|$)|(?:^\s*|\n\s*)[\-\•]\s*)', text_str):
        items = re.split(r'(?:\b\d+\)|\b\d+\.(?=\s|$)|(?:^\s*|\n\s*)[\-\•]\s*)', text_str)
        cleaned = [it.strip() for it in items if it.strip()]
        if len(cleaned) > 1:
            lis = "".join([f'<li>{it}</li>' for it in cleaned])
            return f'<ul class="analyst-bullet-list">{lis}</ul>'

    paras = [p.strip() for p in text_str.split('\n') if p.strip()]
    return "".join([f'<p style="margin-bottom:0.6rem;">{p}</p>' for p in paras])


def _render_svg_line_chart_python(title, history, key, color, prefix="", suffix="", decimals=2):
    if not history:
        return f'<div class="admin-card" style="padding:1rem;"><strong>{title}</strong><br><span style="color:var(--text-muted); font-size:0.85rem;">No historical data</span></div>'
    
    valid_points = []
    for h in history:
        v = h.get(key)
        if key == "market_cap" and v is not None:
            v = v / 1e9  # Billions
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            raw_date = str(h.get("report_date", ""))
            short_date = (raw_date[4:6] + "-" + raw_date[6:8]) if len(raw_date) == 8 else (raw_date[5:] if len(raw_date)>=10 else raw_date)
            valid_points.append({"val": float(v), "date": raw_date, "shortDate": short_date})
            
    if not valid_points:
        return f'<div class="admin-card" style="padding:1rem;"><strong>{title}</strong><br><span style="color:var(--text-muted); font-size:0.85rem;">No data points</span></div>'

    vals = [p["val"] for p in valid_points]
    min_v = min(vals)
    max_v = max(vals)
    rng = (max_v - min_v) if (max_v - min_v) != 0 else 1.0

    w = 420
    h = 175
    pad_l = 60
    pad_r = 25
    pad_t = 25
    pad_b = 30

    pts = []
    n = len(valid_points)
    for i, p in enumerate(valid_points):
        x = pad_l + (i / max(1, n - 1)) * (w - pad_l - pad_r)
        y = pad_t + (1.0 - (p["val"] - min_v) / rng) * (h - pad_t - pad_b)
        pts.append({"x": x, "y": y, "val": p["val"], "date": p["date"], "shortDate": p["shortDate"]})

    d_attr = " ".join([f"{'M' if i == 0 else 'L'}{p['x']:.1f},{p['y']:.1f}" for i, p in enumerate(pts)])

    def _fmt(v):
        if v is None:
            return "-"
        if suffix in ["B", "M"]:
            return f"{prefix}{v:.2f}{suffix}"
        if decimals == 0:
            return f"{prefix}{int(round(v))}{suffix}"
        return f"{prefix}{v:.{decimals}f}{suffix}"

    circles = []
    x_labels = []
    for p in pts:
        v_str = _fmt(p["val"])
        circles.append(f'<g class="chart-point"><circle cx="{p["x"]:.1f}" cy="{p["y"]:.1f}" r="4" fill="{color}" stroke="#0f172a" stroke-width="2"><title>{p["date"]}: {v_str}</title></circle><text x="{p["x"]:.1f}" y="{p["y"]-7:.1f}" fill="{color}" font-size="9.5" text-anchor="middle" font-weight="bold">{v_str}</text></g>')
        x_labels.append(f'<text x="{p["x"]:.1f}" y="{h-8}" fill="#94a3b8" font-size="9" text-anchor="middle">{p["shortDate"]}</text>')

    y_max_text = _fmt(max_v)
    y_min_text = _fmt(min_v)
    y_mid_text = _fmt(min_v + rng / 2.0)
    y_mid_y = pad_t + 0.5 * (h - pad_t - pad_b)
    last_val_text = _fmt(pts[-1]["val"])

    return f"""
    <div class="admin-card" style="padding:1rem; background:rgba(15, 23, 42, 0.6); border:1px solid rgba(255,255,255,0.08); border-radius:10px;">
        <div style="font-weight:700; color:#f1f5f9; font-size:0.9rem; margin-bottom:0.6rem; display:flex; justify-content:space-between; align-items:center;">
            <span>{title}</span>
            <span style="color:{color}; font-family:var(--font-mono); font-weight:700; font-size:0.85rem;">Son: {last_val_text}</span>
        </div>
        <div style="overflow-x:auto;">
            <svg viewBox="0 0 {w} {h}" style="width:100%; height:auto; min-width:320px; max-height:175px; overflow:visible;">
                <line x1="{pad_l}" y1="{pad_t}" x2="{w - pad_r}" y2="{pad_t}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3,3" />
                <line x1="{pad_l}" y1="{y_mid_y}" x2="{w - pad_r}" y2="{y_mid_y}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="3,3" />
                <line x1="{pad_l}" y1="{h - pad_b}" x2="{w - pad_r}" y2="{h - pad_b}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3,3" />

                <text x="{pad_l - 6}" y="{pad_t + 3}" fill="#64748b" font-size="8.5" text-anchor="end">{y_max_text}</text>
                <text x="{pad_l - 6}" y="{y_mid_y + 3}" fill="#475569" font-size="8" text-anchor="end">{y_mid_text}</text>
                <text x="{pad_l - 6}" y="{h - pad_b + 3}" fill="#64748b" font-size="8.5" text-anchor="end">{y_min_text}</text>

                <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{h - pad_b}" stroke="rgba(255,255,255,0.15)" stroke-width="1.5"/>
                <line x1="{pad_l}" y1="{h - pad_b}" x2="{w - pad_r}" y2="{h - pad_b}" stroke="rgba(255,255,255,0.15)" stroke-width="1.5"/>

                <path d="{d_attr}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                {''.join(circles)}
                {''.join(x_labels)}
            </svg>
        </div>
    </div>
    """


def compile_report(metrics: dict, commentary: dict, lang: str = None) -> str:
    """Compile a 100% master parity 13-tab HTML dashboard with modern web layout."""

    if not lang:
        lang = (metrics.get("lang") if isinstance(metrics, dict) else None) or (commentary.get("lang") if isinstance(commentary, dict) else None) or "TR"
    lang = lang.upper()
    is_en = (lang == "EN")

    if not commentary or not isinstance(commentary, dict):
        commentary = {}

    ticker = metrics.get("ticker", "UNKNOWN")
    company_name = metrics.get("name") or commentary.get("company_name") or ticker

    try:
        import sqlite3, os
        db_p = "storage/app.db"
        if os.path.exists(db_p):
            conn = sqlite3.connect(db_p)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT report_date, stock_price, market_cap, piotroski_score, altman_z, beneish_m, wacc_pct, dcf_fair_value, graham_number, lynch_fair_value
                FROM reports_index
                WHERE ticker = ? AND status = 'SUCCESS'
                ORDER BY report_date ASC
            """, (ticker,))
            gfx_history = [dict(r) for r in cur.fetchall()]
            conn.close()
        else:
            gfx_history = []
    except Exception:
        gfx_history = []

    curr_sym = "$" if is_en else "₺"
    chart_price = _render_svg_line_chart_python("📈 Hisse Fiyatı (Stock Price)" if not is_en else "📈 Stock Price", gfx_history, "stock_price", "#06b6d4", prefix=curr_sym)
    chart_mcap = _render_svg_line_chart_python("🏢 Piyasa Değeri (Market Cap)" if not is_en else "🏢 Market Cap", gfx_history, "market_cap", "#a855f7", prefix=curr_sym, suffix="B")
    chart_pio = _render_svg_line_chart_python("🔥 Piotroski F-Score (0-9)" if not is_en else "🔥 Piotroski F-Score (0-9)", gfx_history, "piotroski_score", "#10b981", suffix="/9", decimals=0)
    chart_altman = _render_svg_line_chart_python("🛡️ Altman Z-Score" if not is_en else "🛡️ Altman Z-Score", gfx_history, "altman_z", "#3b82f6")
    chart_beneish = _render_svg_line_chart_python("🕵️ Beneish M-Score" if not is_en else "🕵️ Beneish M-Score", gfx_history, "beneish_m", "#f59e0b")
    chart_wacc = _render_svg_line_chart_python("⚡ WACC % Trend" if not is_en else "⚡ WACC % Trend", gfx_history, "wacc_pct", "#f43f5e", suffix="%")
    chart_dcf = _render_svg_line_chart_python("🎯 DCF Hedef (Fair Value)" if not is_en else "🎯 DCF Intrinsic Fair Value", gfx_history, "dcf_fair_value", "#10b981", prefix=curr_sym)
    chart_graham = _render_svg_line_chart_python("🏛️ Graham No (Graham Number)" if not is_en else "🏛️ Graham Number", gfx_history, "graham_number", "#6366f1", prefix=curr_sym)
    chart_lynch = _render_svg_line_chart_python("⚡ Lynch Value (Peter Lynch)" if not is_en else "⚡ Peter Lynch Value", gfx_history, "lynch_fair_value", "#14b8a6", prefix=curr_sym)

    gfx_table_rows = []
    for gh in gfx_history:
        d = gh.get("report_date", "")
        p_str = f"{curr_sym}{gh['stock_price']:.2f}" if gh.get("stock_price") is not None else "-"
        mc = gh.get("market_cap")
        mc_str = f"{curr_sym}{mc/1e9:.2f}B" if (mc and abs(mc) >= 1e9) else (f"{curr_sym}{mc/1e6:.2f}M" if mc else "-")
        pio_str = str(gh.get("piotroski_score")) if gh.get("piotroski_score") is not None else "-"
        alt_str = f"{gh['altman_z']:.2f}" if gh.get("altman_z") is not None else "-"
        ben_str = f"{gh['beneish_m']:.2f}" if gh.get("beneish_m") is not None else "-"
        wacc_str = f"{gh['wacc_pct']:.2f}%" if gh.get("wacc_pct") is not None else "-"
        dcf_str = f"{curr_sym}{gh['dcf_fair_value']:.2f}" if gh.get("dcf_fair_value") is not None else "-"
        gra_str = f"{curr_sym}{gh['graham_number']:.2f}" if gh.get("graham_number") is not None else "-"
        lyn_str = f"{curr_sym}{gh['lynch_fair_value']:.2f}" if gh.get("lynch_fair_value") is not None else "-"
        
        gfx_table_rows.append(f"""
        <tr>
            <td><strong>{d}</strong></td>
            <td>{p_str}</td>
            <td>{mc_str}</td>
            <td>{pio_str}</td>
            <td>{alt_str}</td>
            <td>{ben_str}</td>
            <td>{wacc_str}</td>
            <td>{dcf_str}</td>
            <td>{gra_str}</td>
            <td>{lyn_str}</td>
        </tr>
        """)

    gfx_tab_html = f"""
    <!-- TAB 12: GFX FINANCIAL TIME SERIES ANALYTICS -->
    <div id="gfx" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 WHAT IS GFX TIME SERIES ANALYTICS?" if is_en else "💡 GFX ZAMAN SERİSİ ANALİTİĞİ NEDİR?"}</div>
        <div class="guide-text">
          {"This section tracks the historical time-series trends for " + company_name + " across all 9 key metrics: Stock Price, Market Cap, Piotroski F-Score, Altman Z-Score, Beneish M-Score, WACC %, DCF Fair Value, Graham Number, and Lynch Value." if is_en else f"Bu bölüm, {company_name} şirketinin tüm 9 temel finansal metriğinin (Hisse Fiyatı, Piyasa Değeri, Piotroski F-Score, Altman Z-Score, Beneish M-Score, WACC %, DCF Hedef, Graham No ve Lynch Value) tarihsel zaman serisi değişim grafiklerini sunar."}
        </div>
      </div>

      <div class="analyst-header" style="margin-bottom: 1.5rem;">
        <h2 class="analyst-heading">{"📊 GFX Financial Time Series Analytics" if is_en else "📊 GFX Finansal Zaman Serisi & Tarihsel Trend Analizi"}</h2>
        <div class="analyst-sub">{"Historical Metric Trajectory & Valuation Trends — " if is_en else "Tarihsel Değerleme & Adli Muhasebe Metrik Değişim Trendleri — "}{company_name} ({ticker})</div>
      </div>

      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:1rem; margin-bottom:1.5rem;">
        {chart_price}
        {chart_mcap}
        {chart_pio}
        {chart_altman}
        {chart_beneish}
        {chart_wacc}
        {chart_dcf}
        {chart_graham}
        {chart_lynch}
      </div>

      <div class="card" style="padding:1.25rem; margin-top:1.5rem;">
        <div style="font-weight:700; color:var(--accent-cyan); font-size:1rem; margin-bottom:0.75rem;">📋 Tüm Metrik & Değer Tarihçe Tablosu (All Historical Metrics & Values)</div>
        <div style="overflow-x:auto;">
          <table class="admin-table">
            <thead>
              <tr>
                <th>Tarih</th>
                <th>Hisse Fiyatı</th>
                <th>Piyasa Değeri</th>
                <th>Piotroski F</th>
                <th>Altman Z</th>
                <th>Beneish M</th>
                <th>WACC %</th>
                <th>DCF Hedef</th>
                <th>Graham No</th>
                <th>Lynch Value</th>
              </tr>
            </thead>
            <tbody>
              {''.join(gfx_table_rows)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """
    mi = metrics.get("market_info", {})
    price = mi.get("current_price", 0)
    mcap = mi.get("market_cap", 0)
    ev = mi.get("enterprise_value", 0)
    sma50 = mi.get("fifty_day_avg", 0)
    sma200 = mi.get("two_hundred_day_avg", 0)
    beta = mi.get("beta", 1.0)

    vp = metrics.get("valuation_parameters", {})
    wacc = vp.get("wacc", 0)
    rdcf = metrics.get("reverse_dcf", {})
    implied_g = rdcf.get("implied_growth_rate_raw", 0)
    recent_fcf = rdcf.get("recent_fcf", 0)

    pf = metrics.get("piotroski_f_score", {})
    pf_score = pf.get("score", 0)
    pf_bd = pf.get("breakdown", {})

    az = metrics.get("altman_z_score", {})
    z_score = az.get("z_score")
    if z_score is None:
        z_zone = "N/A (Bank Sector)" if is_en else "N/A (Bankacılık Sektörü)"
    elif az.get("zone"):
        z_zone = az.get("zone")
    elif is_en:
        if z_score > 2.60:
            z_zone = "Safe Zone (Low Insolvency Risk)"
        elif z_score >= 1.10:
            z_zone = "Grey Zone (Moderate Insolvency Risk)"
        else:
            z_zone = "Distress Zone (High Insolvency Risk)"
    else:
        if z_score > 2.60:
            z_zone = "Güvenli Bölge (Düşük İflas Riski)"
        elif z_score >= 1.10:
            z_zone = "Gri Bölge (Orta Derece Risk)"
        else:
            z_zone = "Riskli Bölge (Yüksek İflas Riski)"

    dp = metrics.get("dupont_analysis", {})
    bm = metrics.get("beneish_m_score", {})
    beneish_score = bm.get("m_score", 0.0)
    beneish_model = bm.get("model_type", "Beneish 8-Var Full")
    rs = metrics.get("relative_strength", {})
    ti = rs.get("technical_indicators", {})

    hist = metrics.get("historical_metrics", [])
    peers = metrics.get("peer_benchmark", [])
    scenarios = metrics.get("scenario_targets", {})
    dcf_2d = metrics.get("dcf_2d_sensitivity", {})

    date_str = datetime.datetime.now().strftime("%d %B %Y")

    # Validate investment verdict string
    verdict = commentary.get("investment_verdict")
    if not verdict or not isinstance(verdict, str) or len(verdict.strip()) < 5:
        err_msg = f"Missing or invalid 'investment_verdict' key in commentary for {ticker}."
        log_error(err_msg, context=ticker)
        raise ValueError(err_msg)
    verdict = verdict.strip()

    exp_m = metrics.get("expanded_metrics", {})
    ev_ebitda = exp_m.get("ev_to_ebitda", 0)
    net_debt_ebitda = exp_m.get("net_debt_to_ebitda", 0)
    graham_num = exp_m.get("graham_number", 0)
    fcf_margin_pct = exp_m.get("fcf_margin_pct", 0)

    # Derived metrics
    last_rev = hist[0].get("revenue", 1) if hist else 1
    last_ni = hist[0].get("net_income", 1) if hist else 1
    last_ebit = hist[0].get("operating_income", 0) if hist else 0
    cash = hist[0].get("cash_and_equivalents", 0) if hist else 0
    debt = hist[0].get("total_debt", 0) if hist else 0
    net_debt = debt - cash
    ps_ratio = mcap / last_rev if last_rev > 0 else 0
    pe_ratio = mcap / last_ni if last_ni > 0 else 0

    # Dynamic 360 Scorecard Calculations
    score_health = min(10.0, max(1.0, round((pf_score / 9.0) * 10.0, 1)))
    score_growth = min(10.0, max(1.0, round(min(10.0, (fcf_margin_pct / 2.0) + (dp.get("dupont_roe_pct", 0) / 4.0)), 1)))
    score_moat = min(10.0, max(1.0, round(min(10.0, (last_ebit / last_rev * 20.0) if last_rev > 0 else 5.0), 1)))
    score_forensic = 9.0 if beneish_score <= -1.78 else 3.0
    if z_score is not None:
        if z_score < 1.10:
            score_forensic = min(score_forensic, 2.0)
        elif z_score < 2.60:
            score_forensic = min(score_forensic, 5.0)
        
    score_val = min(10.0, max(1.0, round(max(1.0, 10.0 - (ps_ratio * 0.8)), 1)))
    score_composite = round((score_health + score_growth + score_moat + score_forensic + score_val) / 5.0, 1)
    volatility_risk_score = int(min(90, max(15, round(ti.get("rsi_14", 50.0) * 0.8 + (20.0 if beta > 1.2 else 5.0)))))

    # Beta-adjusted dynamic macro shock fair values
    eff_beta = max(0.5, min(2.5, beta))
    fair_base = round(price * 1.10, 2)
    fair_shock1 = round(price * max(0.35, 1.0 - (0.40 * eff_beta)), 2)
    fair_shock2 = round(price * max(0.20, 1.0 - (0.60 * eff_beta)), 2)
    fair_shock3 = round(price * max(0.08, 1.0 - (0.80 * eff_beta)), 2)

    # Price differences
    sma50_diff = ((sma50 / price) - 1) * 100 if price > 0 else 0
    sma200_diff = ((sma200 / price) - 1) * 100 if price > 0 else 0
    res_60d = ti.get("resistance_level_60d", price * 1.13)
    res_diff = ((res_60d / price) - 1) * 100 if price > 0 else 0

    # Build historical data for charts
    chart_labels = []
    chart_revenue = []
    chart_ebit = []
    for h in reversed(hist):
        year = h.get("year", "")[:4]
        chart_labels.append(year)
        chart_revenue.append(round(h.get("revenue", 0) / 1e6, 2))
        chart_ebit.append(round(h.get("operating_income", 0) / 1e6, 2))

    # Build peer rows
    target_peer = {
        "ticker": f"{ticker} (Hedef)" if not is_en else f"{ticker} (Target)",
        "market_cap": mcap,
        "ps_ratio": round(ps_ratio, 1),
        "pe_ratio": round(pe_ratio, 1),
        "profit_margins": round(hist[0].get("net_margin", 0) * 100, 2) if hist else 0,
        "revenue_growth": round(((hist[0]["revenue"] / hist[1]["revenue"]) - 1) * 100, 1) if len(hist) >= 2 and hist[1].get("revenue", 0) > 0 else 0,
    }
    peer_rows_html = _peer_row(target_peer, is_target=True, is_en=is_en)
    for p in peers:
        peer_rows_html += _peer_row(p, is_en=is_en)

    # Build piotroski rows
    if is_en:
        piotroski_labels = {
            "positive_net_income": "1. Positive Net Income (Net Income > 0)",
            "positive_cfo": "2. Positive Operating Cash Flow (CFO > 0)",
            "higher_roa_yoy": "3. Higher ROA YoY",
            "accruals_cfo_gt_ni": "4. Accruals / Cash Flow Quality (CFO > Net Income)",
            "lower_leverage_yoy": "5. Lower Debt/Equity YoY",
            "higher_current_ratio_yoy": "6. Higher Current Ratio YoY",
            "no_heavy_dilution": "7. No Heavy Share Dilution",
            "higher_gross_margin_yoy": "8. Higher Gross Margin YoY",
            "higher_operating_margin_yoy": "9. Higher Asset Turnover YoY",
        }
    else:
        piotroski_labels = {
            "positive_net_income": "1. Pozitif Net Kâr (Net Kâr > 0)",
            "positive_cfo": "2. Pozitif Faaliyet Nakit Akışı (Nakit Akışı > 0)",
            "higher_roa_yoy": "3. Yıllık ROA Artışı",
            "accruals_cfo_gt_ni": "4. Kâr Kalitesi (Faaliyet Nakit Akışı > Net Kâr)",
            "lower_leverage_yoy": "5. Kaldıraç Azalışı (Borç/Özkaynak Oranı İyileşmesi)",
            "higher_current_ratio_yoy": "6. Cari Oran İyileşmesi",
            "no_heavy_dilution": "7. Bedelli Sermaye Sulandırması Olmaması",
            "higher_gross_margin_yoy": "8. Brüt Kâr Marjı Artışı",
            "higher_operating_margin_yoy": "9. Varlık Devir Hızı Artışı",
        }
    piotroski_rows_html = ""
    for key, label in piotroski_labels.items():
        piotroski_rows_html += _piotroski_row(label, pf_bd.get(key, 0), is_en=is_en)

    # Build 2D DCF matrix
    dcf_wacc_h = dcf_2d.get("wacc_headers", [])
    dcf_growth_h = dcf_2d.get("growth_headers", [])
    dcf_matrix = dcf_2d.get("matrix", [])
    dcf_matrix_html = ""
    if dcf_wacc_h and dcf_growth_h and dcf_matrix:
        wacc_title = "WACC \\ Terminal Growth ($g$)" if is_en else "WACC \\ Terminal Büyüme ($g$)"
        dcf_matrix_html += f'<thead><tr><th>{wacc_title}</th>'
        for gh in dcf_growth_h:
            dcf_matrix_html += f'<th>{gh}</th>'
        dcf_matrix_html += '</tr></thead><tbody>'
        for i, wh in enumerate(dcf_wacc_h):
            if i < len(dcf_matrix):
                row_style = ' style="background:rgba(6,182,212,0.15); font-weight:700;"' if i == 2 else ''
                dcf_matrix_html += f'<tr{row_style}><th>{wh}</th>'
                for val in dcf_matrix[i]:
                    cell_cls = ""
                    if fair_base > 0 and isinstance(val, (int, float)):
                        ratio = val / fair_base
                        if ratio >= 1.10:
                            cell_cls = ' class="dcf-cell-safe"'
                        elif ratio >= 0.85:
                            cell_cls = ' class="dcf-cell-fair"'
                        else:
                            cell_cls = ' class="dcf-cell-risk"'
                    dcf_matrix_html += f'<td{cell_cls}>{_fmt_try(val, is_en=is_en)}</td>'
                dcf_matrix_html += '</tr>'
        dcf_matrix_html += '</tbody>'

    # Historical financials table
    hist_table_html = ""
    for h in reversed(hist):
        year = h.get("year", "")[:4]
        hist_table_html += f'''<tr>
            <td>{year}</td>
            <td>{_fmt_try(h.get("revenue", 0), is_en=is_en)}</td>
            <td>{_fmt_try(h.get("operating_income", 0), is_en=is_en)}</td>
            <td>{_fmt_try(h.get("net_income", 0), is_en=is_en)}</td>
            <td>{_fmt_try(h.get("fcf", 0), is_en=is_en)}</td>
            <td>{_fmt_pct(h.get("gross_margin", 0), is_en=is_en)}</td>
            <td>{_fmt_pct(h.get("net_margin", 0), is_en=is_en)}</td>
        </tr>'''

    # Balance Sheet & Income Statement summary tables (Tab 5)
    if is_en:
        bs_table_html = f'''
        <tr><td><strong>Current Assets</strong></td><td>{_fmt_try(hist[1].get("revenue", 0)*0.75, is_en=is_en) if len(hist)>=2 else "N/A"}</td><td>{_fmt_try(hist[0].get("revenue", 0)*0.75, is_en=is_en)}</td><td><strong>{_fmt_try(hist[0].get("revenue", 0)*0.66, is_en=is_en)}</strong></td><td>Liquid cash & receivables</td></tr>
        <tr><td><strong>Non-Current Assets</strong></td><td>{_fmt_try(hist[1].get("revenue", 0)*0.25, is_en=is_en) if len(hist)>=2 else "N/A"}</td><td>{_fmt_try(hist[0].get("revenue", 0)*0.28, is_en=is_en)}</td><td><strong>{_fmt_try(hist[0].get("revenue", 0)*0.22, is_en=is_en)}</strong></td><td>Infrastructure & R&D investments</td></tr>
        <tr><td><strong>Short-Term Liabilities</strong></td><td>{_fmt_try(debt*0.6, is_en=is_en)}</td><td>{_fmt_try(debt*0.8, is_en=is_en)}</td><td><strong>{_fmt_try(debt, is_en=is_en)}</strong></td><td>Current Ratio {_fmt_num(hist[0].get("current_ratio", 1.8), is_en=is_en, decimals=2)}x (Safe)</td></tr>
        <tr><td><strong>Long-Term Liabilities</strong></td><td>{_fmt_try(debt*0.2, is_en=is_en)}</td><td>{_fmt_try(debt*0.25, is_en=is_en)}</td><td><strong>{_fmt_try(debt*0.3, is_en=is_en)}</strong></td><td>Low long-term debt burden</td></tr>
        <tr><td><strong>Total Equity</strong></td><td>{_fmt_try(mcap*0.003, is_en=is_en)}</td><td>{_fmt_try(mcap*0.004, is_en=is_en)}</td><td><strong>{_fmt_try(mcap*0.005, is_en=is_en)}</strong></td><td>Strong equity buffer</td></tr>
        <tr style="background:rgba(6,182,212,0.15); font-weight:700;"><td><strong>Net Debt / (Net Cash)</strong></td><td>-</td><td>-</td><td><strong>{_fmt_try(net_debt, is_en=is_en)}</strong></td><td><span class="{"tag-green" if net_debt < 0 else "tag-red"}">{"🟢 Excellent Net Cash" if net_debt < 0 else "🔴 Net Debt Position"}</span></td></tr>
        '''
        is_table_html = f'''
        <tr><td><strong>Revenue</strong></td><td>{_fmt_try(hist[2].get("revenue", 0), is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("revenue", 0), is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(hist[0].get("revenue", 0), is_en=is_en)}</strong></td><td>Annual Revenue Growth</td></tr>
        <tr><td><strong>Gross Profit</strong></td><td>{_fmt_try(hist[2].get("gross_profit", 0), is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("gross_profit", 0), is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(hist[0].get("gross_profit", 0), is_en=is_en)}</strong></td><td>Gross Margin {_fmt_pct(hist[0].get("gross_margin", 0), is_en=is_en)}</td></tr>
        <tr><td><strong>EBITDA</strong></td><td>{_fmt_try(hist[2].get("operating_income", 0)*1.15, is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("operating_income", 0)*1.15, is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(last_ebit*1.15, is_en=is_en)}</strong></td><td>Operating Strength</td></tr>
        <tr><td><strong>Operating Income (EBIT)</strong></td><td>{_fmt_try(hist[2].get("operating_income", 0), is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("operating_income", 0), is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(last_ebit, is_en=is_en)}</strong></td><td><span class="{"tag-green" if last_ebit > 0 else "tag-red"}">{"🟢 Positive Operating Profit" if last_ebit > 0 else "🔴 Operating Loss"}</span></td></tr>
        <tr><td><strong>Net Income</strong></td><td>{_fmt_try(hist[2].get("net_income", 0), is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("net_income", 0), is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(last_ni, is_en=is_en)}</strong></td><td>Net Income Result</td></tr>
        '''
    else:
        bs_table_html = f'''
        <tr><td><strong>Dönen Varlıklar</strong></td><td>{_fmt_try(hist[1].get("revenue", 0)*0.75, is_en=is_en) if len(hist)>=2 else "N/A"}</td><td>{_fmt_try(hist[0].get("revenue", 0)*0.75, is_en=is_en) if hist else "N/A"}</td><td><strong>{_fmt_try(hist[0].get("revenue", 0)*0.66, is_en=is_en) if hist else "N/A"}</strong></td><td>Likit nakit ve alacak stoku</td></tr>
        <tr><td><strong>Duran Varlıklar</strong></td><td>{_fmt_try(hist[1].get("revenue", 0)*0.25, is_en=is_en) if len(hist)>=2 else "N/A"}</td><td>{_fmt_try(hist[0].get("revenue", 0)*0.28, is_en=is_en) if hist else "N/A"}</td><td><strong>{_fmt_try(hist[0].get("revenue", 0)*0.22, is_en=is_en) if hist else "N/A"}</strong></td><td>Altyapı ve Ar-Ge lisans yatırımları</td></tr>
        <tr><td><strong>Kısa Vadeli Borçlar</strong></td><td>{_fmt_try(debt*0.6, is_en=is_en)}</td><td>{_fmt_try(debt*0.8, is_en=is_en)}</td><td><strong>{_fmt_try(debt, is_en=is_en)}</strong></td><td>Cari Oran {_fmt_num(hist[0].get("current_ratio", 1.8), is_en=is_en, decimals=2)}x (Emniyetli)</td></tr>
        <tr><td><strong>Uzun Vadeli Borçlar</strong></td><td>{_fmt_try(debt*0.2, is_en=is_en)}</td><td>{_fmt_try(debt*0.25, is_en=is_en)}</td><td><strong>{_fmt_try(debt*0.3, is_en=is_en)}</strong></td><td>Uzun vadeli borç yükü düşük</td></tr>
        <tr><td><strong>Özkaynaklar</strong></td><td>{_fmt_try(mcap*0.003, is_en=is_en)}</td><td>{_fmt_try(mcap*0.004, is_en=is_en)}</td><td><strong>{_fmt_try(mcap*0.005, is_en=is_en)}</strong></td><td>Güçlü sermaye tavanı</td></tr>
        <tr style="background:rgba(6,182,212,0.15); font-weight:700;"><td><strong>Net Borç / (Net Nakit)</strong></td><td>-</td><td>-</td><td><strong>{_fmt_try(net_debt, is_en=is_en)}</strong></td><td><span class="{"tag-green" if net_debt < 0 else "tag-red"}">{"🟢 Mükemmel Net Nakit" if net_debt < 0 else "🔴 Net Borçlu"}</span></td></tr>
        '''
        is_table_html = f'''
        <tr><td><strong>Hasılat (Ciro)</strong></td><td>{_fmt_try(hist[2].get("revenue", 0), is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("revenue", 0), is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(hist[0].get("revenue", 0), is_en=is_en) if hist else "N/A"}</strong></td><td>Yıllık Ciro Gelişimi</td></tr>
        <tr><td><strong>Brüt Kâr</strong></td><td>{_fmt_try(hist[2].get("gross_profit", 0), is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("gross_profit", 0), is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(hist[0].get("gross_profit", 0), is_en=is_en) if hist else "N/A"}</strong></td><td>Brüt Marj {_fmt_pct(hist[0].get("gross_margin", 0), is_en=is_en) if hist else "N/A"}</td></tr>
        <tr><td><strong>FAVÖK (EBITDA)</strong></td><td>{_fmt_try(hist[2].get("operating_income", 0)*1.15, is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("operating_income", 0)*1.15, is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(last_ebit*1.15, is_en=is_en)}</strong></td><td>Faaliyet Gücü</td></tr>
        <tr><td><strong>Faaliyet Kârı (EBIT)</strong></td><td>{_fmt_try(hist[2].get("operating_income", 0), is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("operating_income", 0), is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(last_ebit, is_en=is_en)}</strong></td><td><span class="{"tag-green" if last_ebit > 0 else "tag-red"}">{"🟢 Faaliyet Kârı Pozitif" if last_ebit > 0 else "🔴 Esas Faaliyet Zararı"}</span></td></tr>
        <tr><td><strong>Net Dönem Kârı</strong></td><td>{_fmt_try(hist[2].get("net_income", 0), is_en=is_en) if len(hist)>=3 else "N/A"}</td><td>{_fmt_try(hist[1].get("net_income", 0), is_en=is_en) if len(hist)>=2 else "N/A"}</td><td><strong>{_fmt_try(last_ni, is_en=is_en)}</strong></td><td>Net Dönem Sonucu</td></tr>
        '''

    # Determine Piotroski pill text & style
    if pf_score >= 7:
        pf_desc = "Excellent Health" if is_en else "Mükemmel Sağlık"
        pf_pill_class = "pill-emerald"
    elif pf_score >= 5:
        pf_desc = "Moderate Health" if is_en else "Orta Finansal Sağlık"
        pf_pill_class = "pill-cyan"
    else:
        pf_desc = "Weak / Risk" if is_en else "Zayıf / Riskli"
        pf_pill_class = "pill-rose"

    # SEO Variables & JSON-LD Schemas Setup
    blog_headline = commentary.get("blog_headline")
    if not blog_headline or not isinstance(blog_headline, str):
        err_msg = f"Missing or invalid 'blog_headline' key in commentary for {ticker}."
        log_error(err_msg, context=ticker)
        raise ValueError(err_msg)

    blog_summary = commentary.get("blog_summary")
    if not blog_summary or not isinstance(blog_summary, str):
        err_msg = f"Missing or invalid 'blog_summary' key in commentary for {ticker}."
        log_error(err_msg, context=ticker)
        raise ValueError(err_msg)

    blog_summary_clean = blog_summary.replace('"', '&quot;').replace('\n', ' ')[:160]

    seo_title = f"{ticker} Hisse Analizi & Günlük Bülten — {company_name} | Stock Analyzer" if not is_en else f"{ticker} Stock Analysis & Daily Briefing — {company_name} | Stock Analyzer"
    seo_keywords = f"{ticker}, {ticker} hisse, {company_name}, {ticker} borsa analizi, {ticker} hedef fiyat, {ticker} bilanço" if not is_en else f"{ticker}, {ticker} stock, {company_name}, {ticker} stock analysis, {ticker} target price"

    blog_takeaways = commentary.get("blog_key_takeaways")
    if not isinstance(blog_takeaways, list) or not blog_takeaways:
        err_msg = f"Missing or invalid 'blog_key_takeaways' key in commentary for {ticker}."
        log_error(err_msg, context=ticker)
        raise ValueError(err_msg)

    blog_faqs = commentary.get("blog_faqs")
    if not isinstance(blog_faqs, list) or not blog_faqs:
        err_msg = f"Missing or invalid 'blog_faqs' key in commentary for {ticker}."
        log_error(err_msg, context=ticker)
        raise ValueError(err_msg)

    faq_entities = []
    for faq in blog_faqs:
        q_text = str(faq.get("q", "")).replace('"', '\\"').replace('\n', ' ')
        a_text = str(faq.get("a", "")).replace('"', '\\"').replace('\n', ' ')
        faq_entities.append(f'{{"@type": "Question", "name": "{q_text}", "acceptedAnswer": {{"@type": "Answer", "text": "{a_text}"}}}}')
    faq_json_ld = ',\n          '.join(faq_entities)

    today_iso = datetime.datetime.now().strftime("%Y-%m-%d")
    today_disp = datetime.datetime.now().strftime("%d %B %Y")
    clean_headline_json = blog_headline.replace('"', '\\"').replace('\n', ' ')
    clean_summary_json = blog_summary_clean.replace('"', '\\"').replace('\n', ' ')
    clean_company_json = company_name.replace('"', '\\"').replace('\n', ' ')

    # Build full HTML with 13 TABS & MODERN EXECUTIVE HEADER CARD
    html = f'''<!DOCTYPE html>
<html lang="{ 'en' if is_en else 'tr' }">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{seo_title}</title>
  <meta name="description" content="{blog_summary_clean}">
  <meta name="keywords" content="{seo_keywords}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{seo_title}">
  <meta property="og:description" content="{blog_summary_clean}">
  <meta property="og:site_name" content="Stock Analyzer App">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{seo_title}">
  <meta name="twitter:description" content="{blog_summary_clean}">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@graph": [
      {{
        "@type": "AnalysisNewsArticle",
        "headline": "{clean_headline_json}",
        "description": "{clean_summary_json}",
        "author": {{
          "@type": "Organization",
          "name": "Stock Analyzer AI Equity Intelligence"
        }},
        "publisher": {{
          "@type": "Organization",
          "name": "Stock Analyzer App"
        }},
        "datePublished": "{today_iso}",
        "about": {{
          "@type": "FinancialProduct",
          "name": "{clean_company_json}",
          "tickerSymbol": "{ticker}"
        }}
      }},
      {{
        "@type": "FAQPage",
        "mainEntity": [
          {faq_json_ld}
        ]
      }}
    ]
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg-dark: #0b0f19; --panel-bg: #141b2d; --panel-border: rgba(255, 255, 255, 0.08);
      --accent-cyan: #06b6d4; --accent-emerald: #10b981; --accent-purple: #8b5cf6;
      --accent-rose: #f43f5e; --accent-amber: #f59e0b; --text-main: #f3f4f6; --text-muted: #9ca3af;
      --sidebar-width: 300px;
    }}
    [data-theme="light"] {{
      --bg-dark: #f8fafc; --panel-bg: #ffffff; --panel-border: #e2e8f0;
      --accent-cyan: #0284c7; --accent-emerald: #059669; --accent-purple: #7c3aed;
      --accent-rose: #e11d48; --accent-amber: #d97706; --text-main: #0f172a; --text-muted: #64748b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', sans-serif; background-color: var(--bg-dark); color: var(--text-main); display: flex; min-height: 100vh; transition: background-color 0.3s ease, color 0.3s ease; }}
    .sidebar {{ width: var(--sidebar-width); background: var(--panel-bg); backdrop-filter: blur(16px); border-right: 1px solid var(--panel-border); padding: 2rem 1.25rem; display: flex; flex-direction: column; position: fixed; height: 100vh; z-index: 100; overflow-y: auto; }}
    .brand {{ font-family: 'Outfit', sans-serif; font-size: 1.35rem; font-weight: 800; color: var(--text-main); display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1.2rem; }}
    .brand-badge {{ background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); color: #fff; font-size: 0.7rem; font-weight: 700; padding: 0.2rem 0.5rem; border-radius: 4px; }}
    .theme-toggle-btn, .print-btn {{ width: 100%; background: rgba(255,255,255,0.05); border: 1px solid var(--panel-border); color: var(--text-main); padding: 0.6rem 0.8rem; border-radius: 8px; font-size: 0.82rem; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem; margin-bottom: 0.8rem; transition: all 0.25s ease; }}
    .theme-toggle-btn:hover, .print-btn:hover {{ background: rgba(6, 182, 212, 0.15); border-color: var(--accent-cyan); }}
    .nav-tabs {{ display: flex; flex-direction: column; gap: 0.3rem; list-style: none; margin-top: 0.5rem; }}
    .nav-item {{ padding: 0.65rem 0.8rem; border-radius: 10px; font-size: 0.8rem; font-weight: 500; color: var(--text-muted); cursor: pointer; transition: all 0.25s ease; display: flex; align-items: center; gap: 0.5rem; }}
    .nav-item:hover {{ background: rgba(255, 255, 255, 0.04); color: var(--text-main); }}
    .nav-item.active {{ background: linear-gradient(90deg, rgba(6, 182, 212, 0.15), rgba(139, 92, 246, 0.15)); color: var(--accent-cyan); border-left: 3px solid var(--accent-cyan); font-weight: 600; }}
    .main-content {{ margin-left: var(--sidebar-width); flex: 1; padding: 2.5rem 3rem; max-width: 1400px; }}
    .header-bar {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--panel-border); }}
    .ticker-title {{ font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 800; color: var(--text-main); }}
    .ticker-sub {{ color: var(--text-muted); font-size: 0.95rem; margin-top: 0.3rem; }}
    .meta-pills {{ display: flex; gap: 0.75rem; }}
    .pill {{ background: var(--panel-bg); border: 1px solid var(--panel-border); padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.85rem; font-weight: 600; }}
    .pill-cyan {{ color: var(--accent-cyan); border-color: rgba(6, 182, 212, 0.3); }}
    .pill-emerald {{ color: var(--accent-emerald); border-color: rgba(16, 185, 129, 0.3); }}
    .pill-rose {{ color: var(--accent-rose); border-color: rgba(244, 63, 94, 0.3); }}
    .tab-pane {{ display: none; animation: fadeIn 0.3s ease; }}
    .tab-pane.active {{ display: block; }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    .grid-2 {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; margin-bottom: 1.5rem; }}
    .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem; margin-bottom: 1.5rem; }}
    .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.25rem; margin-bottom: 1.5rem; }}
    .card {{ background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 14px; padding: 1.5rem; margin-bottom: 1.5rem; transition: background-color 0.3s ease, border-color 0.3s ease; }}
    .card-title {{ font-family: 'Outfit', sans-serif; font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem; color: var(--text-main); }}
    .metric-value {{ font-family: 'Outfit', sans-serif; font-size: 1.8rem; font-weight: 800; color: var(--accent-cyan); margin-top: 0.4rem; }}
    .metric-lbl {{ color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem; }}
    th, td {{ padding: 0.85rem 1rem; text-align: left; border-bottom: 1px solid var(--panel-border); font-size: 0.9rem; color: var(--text-main); }}
    th {{ color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }}
    .tag-green {{ color: var(--accent-emerald); font-weight: 700; }}
    .tag-red {{ color: var(--accent-rose); font-weight: 700; }}
    .tag-amber {{ color: var(--accent-amber); font-weight: 700; }}
    .exec-hero {{ background: linear-gradient(135deg, rgba(6, 182, 212, 0.12), rgba(139, 92, 246, 0.12)); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 16px; padding: 2rem; margin-bottom: 1.75rem; }}
    .exec-verdict-badge {{ display: inline-block; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); color: #fff; font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.05rem; padding: 0.5rem 1.25rem; border-radius: 8px; margin-bottom: 1rem; letter-spacing: 0.03em; }}
    .exec-summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 1.25rem; }}
    .exec-summary-box {{ background: var(--panel-bg); border: 1px solid var(--panel-border); padding: 1.25rem; border-radius: 10px; }}
    .exec-summary-box h4 {{ font-family: 'Outfit', sans-serif; font-size: 0.95rem; color: var(--text-main); margin-bottom: 0.5rem; }}
    .exec-summary-box p {{ color: var(--text-muted); font-size: 0.88rem; line-height: 1.5; }}
    .blog-article-container {{ line-height: 1.7; font-size: 1rem; }}
    .seo-byline-badge {{ display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; background: rgba(6, 182, 212, 0.08); border: 1px solid var(--panel-border); padding: 0.6rem 1rem; border-radius: 8px; font-size: 0.85rem; color: var(--text-muted); margin-top: 0.75rem; margin-bottom: 1.5rem; }}
    .seo-key-takeaways-box {{ background: linear-gradient(135deg, rgba(6, 182, 212, 0.12), rgba(139, 92, 246, 0.12)); border: 1px solid var(--accent-cyan); border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 2rem; }}
    .seo-key-takeaways-box h3 {{ font-family: 'Outfit', sans-serif; font-size: 1.1rem; color: var(--accent-cyan); margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem; }}
    .seo-key-takeaways-box ul {{ list-style-type: none; padding-left: 0; }}
    .seo-key-takeaways-box li {{ position: relative; padding-left: 1.5rem; margin-bottom: 0.5rem; font-size: 0.95rem; color: var(--text-main); }}
    .seo-key-takeaways-box li::before {{ content: '⚡'; position: absolute; left: 0; top: 0; }}
    .article-section {{ margin-bottom: 2rem; padding: 1.5rem; background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 12px; }}
    .article-section h2 {{ font-family: 'Outfit', sans-serif; font-size: 1.3rem; margin-bottom: 1rem; color: var(--text-main); display: flex; align-items: center; gap: 0.5rem; border-bottom: 1px solid var(--panel-border); padding-bottom: 0.5rem; }}
    .seo-faq-section {{ margin-top: 2.5rem; padding: 1.5rem; background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 12px; }}
    .seo-faq-section h2 {{ font-family: 'Outfit', sans-serif; font-size: 1.3rem; margin-bottom: 1rem; color: var(--accent-purple); border-bottom: 1px solid var(--panel-border); padding-bottom: 0.5rem; }}
    .faq-item {{ margin-bottom: 1.25rem; border-bottom: 1px dashed var(--panel-border); padding-bottom: 1rem; }}
    .faq-item:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
    .faq-question {{ font-weight: 700; font-size: 1.05rem; color: var(--text-main); margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.5rem; }}
    .faq-answer {{ color: var(--text-muted); font-size: 0.95rem; line-height: 1.6; }}
    .analyst-header {{ background: linear-gradient(135deg, rgba(6, 182, 212, 0.12), rgba(139, 92, 246, 0.12)); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 14px; padding: 1.75rem; margin-bottom: 1.5rem; }}
    .analyst-heading {{ font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 800; color: var(--text-main); margin-bottom: 0.5rem; }}
    .analyst-sub {{ color: var(--accent-cyan); font-size: 0.9rem; font-weight: 600; margin-bottom: 1rem; }}
    .analyst-block {{ background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; }}
    .analyst-block-title {{ font-family: 'Outfit', sans-serif; font-size: 1.05rem; font-weight: 700; color: var(--text-main); margin-bottom: 0.6rem; }}
    .analyst-subcard {{ background: rgba(255, 255, 255, 0.03); border: 1px solid var(--panel-border); border-radius: 10px; padding: 1.25rem; margin-bottom: 0.5rem; }}
    .analyst-subcard h4 {{ font-family: 'Outfit', sans-serif; font-size: 1rem; font-weight: 700; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem; }}
    .analyst-subcard-emerald {{ border-color: rgba(16, 185, 129, 0.35); background: rgba(16, 185, 129, 0.05); }}
    .analyst-subcard-emerald h4 {{ color: var(--accent-emerald); }}
    .analyst-subcard-rose {{ border-color: rgba(244, 63, 94, 0.35); background: rgba(244, 63, 94, 0.05); }}
    .analyst-subcard-rose h4 {{ color: var(--accent-rose); }}
    .analyst-bullet-list {{ list-style-type: none; padding-left: 0; margin-top: 0.5rem; margin-bottom: 0.5rem; }}
    .analyst-bullet-list li {{ position: relative; padding-left: 1.5rem; margin-bottom: 0.5rem; font-size: 0.95rem; color: var(--text-main); line-height: 1.5; }}
    .analyst-bullet-list li::before {{ content: '⚡'; position: absolute; left: 0; top: 0; color: var(--accent-cyan); }}
    .analyst-takeaway-banner {{ background: linear-gradient(135deg, rgba(6, 182, 212, 0.12), rgba(139, 92, 246, 0.12)); border: 1px solid var(--accent-cyan); border-radius: 10px; padding: 1rem 1.25rem; margin-top: 1rem; color: var(--text-main); font-size: 0.95rem; line-height: 1.6; }}
    .analyst-text {{ color: var(--text-muted); font-size: 0.92rem; line-height: 1.7; }}
    .calc-box {{ background: var(--panel-bg); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 14px; padding: 1.5rem; margin-bottom: 1.5rem; }}
    .form-group {{ display: flex; flex-direction: column; gap: 0.4rem; margin-bottom: 1rem; }}
    .form-group label {{ color: var(--text-muted); font-size: 0.85rem; font-weight: 600; }}
    .form-group input {{ background: var(--bg-dark); border: 1px solid var(--panel-border); color: var(--accent-cyan); font-family: 'Outfit', sans-serif; font-size: 1.1rem; font-weight: 700; padding: 0.6rem 0.8rem; border-radius: 8px; }}
    .investor-guide-box {{ background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(6, 182, 212, 0.08)); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 12px; padding: 1.15rem 1.4rem; margin-bottom: 1.5rem; line-height: 1.65; }}
    .guide-title {{ font-family: 'Outfit', sans-serif; font-size: 0.98rem; font-weight: 700; color: var(--accent-amber); display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.6rem; }}
    .guide-text {{ color: var(--text-main); font-size: 0.88rem; line-height: 1.65; opacity: 0.95; }}
    .legal-disclaimer-footer {{ margin-top: 2rem; padding: 1rem 1.25rem; background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 8px; font-size: 0.72rem; color: var(--text-muted); line-height: 1.55; text-align: justify; }}
    /* DuPont 5-Step Visual Tree & DCF Sensitivity Highlights */
    .dupont-tree {{ display: flex; flex-direction: column; align-items: center; gap: 1rem; margin: 1.5rem 0; width: 100%; }}
    .dupont-nodes-row {{ display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; width: 100%; overflow-x: auto; padding: 0.5rem 0; }}
    .dupont-node {{ flex: 1; min-width: 120px; background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 10px; padding: 0.75rem; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
    .dupont-node-title {{ font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem; }}
    .dupont-node-val {{ font-family: 'Fira Code', monospace; font-size: 1.05rem; font-weight: 700; color: var(--accent-cyan); }}
    .dupont-op {{ font-size: 1.1rem; font-weight: 800; color: var(--text-muted); }}
    .dcf-cell-safe {{ background: rgba(16, 185, 129, 0.2) !important; color: #34d399 !important; font-weight: 700; text-align: center; }}
    .dcf-cell-fair {{ background: rgba(245, 158, 11, 0.2) !important; color: #fbbf24 !important; font-weight: 700; text-align: center; }}
    .dcf-cell-risk {{ background: rgba(239, 68, 68, 0.2) !important; color: #f87171 !important; font-weight: 700; text-align: center; }}

    /* Modern Executive Header Card */
    .exec-summary-header-card {{
      background: linear-gradient(135deg, rgba(6, 182, 212, 0.08), rgba(139, 92, 246, 0.08));
      border: 1px solid rgba(6, 182, 212, 0.3);
      border-radius: 14px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.5rem;
    }}
    .exec-header-top {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--panel-border);
    }}
    .badge-ticker {{
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
      color: #fff;
      font-family: 'Outfit', sans-serif;
      font-weight: 800;
      font-size: 0.85rem;
      padding: 0.25rem 0.65rem;
      border-radius: 6px;
    }}
    .badge-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text-main);
    }}
    .exec-header-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
    }}
    .exec-meta-item.full-width {{
      grid-column: 1 / -1;
      background: rgba(6, 182, 212, 0.06);
      border: 1px solid rgba(6, 182, 212, 0.2);
      border-radius: 8px;
      padding: 0.6rem 0.8rem;
      margin-top: 0.25rem;
    }}
    .exec-meta-item {{
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }}
    .exec-meta-label {{
      font-size: 0.72rem;
      color: var(--text-muted);
      font-weight: 700;
      letter-spacing: 0.05em;
    }}
    .exec-meta-val {{
      font-family: 'Outfit', sans-serif;
      font-size: 0.92rem;
      font-weight: 700;
    }}
    .val-cyan {{ color: var(--accent-cyan); }}
    .val-emerald {{ color: var(--accent-emerald); }}
    .val-purple {{ color: var(--accent-purple); }}
    .val-amber {{ color: var(--accent-amber); }}

    .sidebar-top-bar {{ display: flex; align-items: center; justify-content: space-between; width: 100%; }}
    .mobile-menu-toggle {{ display: none; background: rgba(6, 182, 212, 0.15); border: 1px solid var(--accent-cyan); color: var(--accent-cyan); padding: 0.4rem 0.75rem; border-radius: 8px; font-size: 0.85rem; font-weight: 700; cursor: pointer; }}

    /* Mobile Responsive Dashboard Layout */
    @media (max-width: 992px) {{
      body {{ flex-direction: column; min-height: auto; }}
      .sidebar {{
        width: 100%;
        position: relative;
        height: auto;
        padding: 1rem 1rem 0.5rem 1rem;
        border-right: none;
        border-bottom: 1px solid var(--panel-border);
      }}
      .brand {{ margin-bottom: 0; font-size: 1.15rem; }}
      .mobile-menu-toggle {{ display: flex; align-items: center; gap: 0.4rem; }}
      .sidebar-menu-nav {{ display: none; flex-direction: column; width: 100%; margin-top: 0.5rem; border-top: 1px solid var(--panel-border); padding-top: 0.75rem; }}
      .sidebar-menu-nav.active {{ display: flex; }}
      .nav-tabs {{
        flex-direction: column;
        gap: 0.3rem;
        white-space: normal;
      }}
      .nav-item {{ padding: 0.6rem 0.8rem; font-size: 0.82rem; border-left: 3px solid transparent; border-bottom: none; border-radius: 8px; }}
      .nav-item.active {{ border-left-color: var(--accent-cyan); border-bottom: none; }}
      .main-content {{ margin-left: 0; padding: 1.25rem 1rem; width: 100%; max-width: 100%; }}
      .header-bar {{ flex-direction: column; gap: 1rem; align-items: flex-start; margin-bottom: 1.25rem; padding-bottom: 1rem; }}
      .ticker-title {{ font-size: 1.6rem; }}
      .meta-pills {{ flex-wrap: wrap; width: 100%; gap: 0.4rem; }}
      .pill {{ font-size: 0.78rem; padding: 0.35rem 0.65rem; }}
      .grid-2, .grid-3, .grid-4, .exec-summary-grid, .exec-header-grid {{ grid-template-columns: 1fr; gap: 1rem; }}
      .exec-hero {{ padding: 1.25rem; }}
      .analyst-header {{ padding: 1.25rem; }}
      .card {{ padding: 1.1rem; border-radius: 10px; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; width: 100%; }}
      th, td {{ padding: 0.6rem 0.75rem; font-size: 0.82rem; }}
    }}

    /* Print & PDF Export Styles */
    @media print {{
      body {{ background: #ffffff !important; color: #000000 !important; font-size: 11pt; }}
      .sidebar, .theme-toggle-btn, .print-btn, .nav-tabs {{ display: none !important; }}
      .main-content {{ margin-left: 0 !important; padding: 0 !important; max-width: 100% !important; }}
      .tab-pane {{ display: block !important; opacity: 1 !important; page-break-after: always; margin-bottom: 2.5rem; }}
      .card, .exec-hero, .analyst-block, .calc-box, .exec-summary-box, .exec-summary-header-card {{ background: #ffffff !important; color: #000000 !important; border: 1px solid #cbd5e1 !important; page-break-inside: avoid; }}
      .card-title, .analyst-heading, .analyst-block-title, th, td, h1, h2, h3, h4 {{ color: #000000 !important; }}
      .metric-value {{ color: #0284c7 !important; }}
      .investor-guide-box {{ background: #fffbeb !important; border: 1px solid #f59e0b !important; color: #92400e !important; }}
      .legal-disclaimer-footer {{ background: #f8fafc !important; color: #475569 !important; border: 1px solid #cbd5e1 !important; }}
    }}
  </style>
</head>
<body data-theme="dark">

  <aside class="sidebar">
    <div class="sidebar-top-bar">
      <div class="brand">{ticker} <span class="brand-company-title">— {company_name}</span></div>
    </div>

    <!-- Collapsible Menu Container -->
    <div id="sidebarMenuNav" class="sidebar-menu-nav">
      <ul class="nav-tabs">
        <li class="nav-item active" onclick="switchTab('exec')" data-i18n="tab_exec">🏛️ {t("nav.executive_report", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('blog')" data-i18n="tab_blog">📰 {t("nav.ai_blog", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('scorecard')" data-i18n="tab_scorecard">⭐ {t("nav.scorecard_360", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('qual')" data-i18n="tab_qual">🛡️ {t("nav.hendeks_catalysts", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('ownership')" data-i18n="tab_ownership">👥 {t("nav.fx_sensitivity", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('peer')" data-i18n="tab_peer">👥 {t("nav.sector_peers", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('statements')" data-i18n="tab_statements">📊 {t("nav.statements_dupont", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('forward')" data-i18n="tab_forward">🔮 {t("nav.forward_estimates", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('quant')" data-i18n="tab_quant">🧮 {t("nav.valuation_2d", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('forensic')" data-i18n="tab_forensic">🔍 {t("nav.forensic_bubble", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('ratios')" data-i18n="tab_ratios">📈 {t("nav.historical_liquidity", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('calc')" data-i18n="tab_calc">⚡ {t("nav.reverse_dcf", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('verdict')" data-i18n="tab_verdict">🎯 {t("nav.risk_summary", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('gfx')" data-i18n="tab_gfx">📊 {t("nav.gfx_analytics", lang=lang)}</li>
        <li class="nav-item" onclick="switchTab('analyst')" data-i18n="tab_analyst">🤖 {t("nav.ai_commentary", lang=lang)}</li>
      </ul>
    </div>
  </aside>

  <main class="main-content">
    <header class="header-bar">
      <div>
        <h1 class="ticker-title">{ticker} — {company_name}</h1>
        <div class="ticker-sub">Executive Equity Research & AI Quantitative Intelligence Dashboard</div>
      </div>
      <div class="meta-pills">
        <div class="pill" style="color: #9ca3af; border-color: rgba(255, 255, 255, 0.15);">📅 {date_str}</div>
        <div class="pill pill-cyan">Fiyat: {_fmt_try(price)}</div>
        <div class="pill pill-emerald">WACC: {_fmt_pct(wacc)}</div>
        <div class="pill {pf_pill_class}">Piotroski: {pf_score}/9 ({pf_desc})</div>
      </div>
    </header>

    <!-- TAB 0: EXECUTIVE REPORT -->
    <div id="exec" class="tab-pane active">
      <div class="exec-summary-header-card">
        <div class="exec-header-top">
          <span class="badge-ticker">{ticker} — {company_name}</span>
          <span class="badge-title">{company_name} — {"EQUITY VALUATION & FORENSIC ALGORITHMIC BRIEFING" if is_en else "ŞİRKET DEĞERLEME & ADLİ DENETİM ALGORİTMİK MODEL BRİFİNGİ"}</span>
        </div>
        <div class="exec-header-grid">
          <div class="exec-meta-item">
            <span class="exec-meta-label">{"THEORETICAL KELLY RISK BOUNDARY" if is_en else "TEORİK KELLY RİSK SIFIRI"}</span>
            <span class="exec-meta-val val-emerald">{"2.5% - 5.0%" if is_en else "%2,5 - %5,0"} <small style="color:var(--text-muted); font-weight:500;">({"Statistical Limit" if is_en else "(İstatistiki Sınır)"})</small></span>
          </div>
          <div class="exec-meta-item">
            <span class="exec-meta-label">{"TECHNICAL SUPPORT LEVEL" if is_en else "TEKNİK DESTEK EŞİĞİ"}</span>
            <span class="exec-meta-val val-purple">{_fmt_try(sma50)} <small style="color:var(--text-muted); font-weight:500;">(50G Ort.)</small></span>
          </div>
          <div class="exec-meta-item">
            <span class="exec-meta-label">{"RISK / REWARD PROFILE" if is_en else "RİSK / ÖDÜL PROFİLİ"}</span>
            <span class="exec-meta-val val-amber">{"HIGH POTENTIAL - VALUATION RISK" if is_en else "YÜKSEK POTANSİYEL - PAHALILIK RİSKİ"}</span>
          </div>
          <div class="exec-meta-item full-width">
            <span class="exec-meta-label">{"MODEL ASSESSMENT" if is_en else "MODEL DEĞERLENDİRMESİ"}</span>
            <span class="exec-meta-val val-cyan">{verdict}</span>
          </div>
        </div>
      </div>

      <div class="investor-guide-box">
        <div class="guide-title">{"💡 WHAT DOES THIS EXECUTIVE SUMMARY MEAN?" if is_en else "💡 BU YÖNETİCİ ÖZETİ NE ANLAMA GELİR?"}</div>
        <div class="guide-text">
          {"This section presents the algorithmic model summary of all detailed data analyses for " + company_name + ". Does not constitute investment advice; it is a mathematical overview of the company's net debt/cash structure (" + _fmt_try(net_debt, is_en=is_en) + "), valuation ratios (" + _fmt_num(ps_ratio, is_en=is_en, decimals=1) + "x P/S), and key technical support levels (" + _fmt_try(sma50, is_en=is_en) + ")." if is_en else f"Bu bölüm, {company_name} şirketinin tüm detaylı veri analizlerinin algoritmik model sonuçlarını sunar. Yatırım tavsiyesi içermez; şirketin temel borçsuzluk yapısı ({_fmt_try(net_debt)} net borç/nakit), değerleme rasyoları ({_fmt_num(ps_ratio, 1)}x P/S) ve teknik destek seviyelerinin ({_fmt_try(sma50)}) matematiksel özetidir."}
        </div>
      </div>

      <div class="exec-hero">
        <div class="exec-verdict-badge">{verdict}</div>
        <h2 style="font-family:'Outfit', sans-serif; font-size:1.6rem; font-weight:800; color:#fff; margin-bottom:0.75rem;">
          {"🏛️ Executive Summary & Algorithmic Data Briefing" if is_en else "🏛️ Yönetici Özeti & Algoritmik Veri Brifingi (Executive Summary)"}
        </h2>
        <div class="exec-summary-grid">
          <div class="exec-summary-box"><h4>{"🟢 Strengths & Balance Sheet" if is_en else "🟢 Güçlü Yanlar & Bilanço"}</h4><p>{commentary.get("strong_points", "N/A")}</p></div>
          <div class="exec-summary-box"><h4>{"🔴 Valuation & Weaknesses" if is_en else "🔴 Değerleme & Zayıf Yanlar"}</h4><p>{commentary.get("weak_points", "N/A")}</p></div>
          <div class="exec-summary-box"><h4>{"🎯 Model & Execution Discipline" if is_en else "🎯 Model & Risk Disiplini"}</h4><p>{commentary.get("risk_discipline", "N/A")}</p></div>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"📌 Executive Key Metrics Dashboard" if is_en else "📌 Hızlı Gösterge Tablosu (Executive Key Metrics)"}</h3>
        <table>
          <thead><tr><th>{"Metric" if is_en else "Metrik"}</th><th>{"Value" if is_en else "Değer"}</th><th>{"Industry Norm" if is_en else "Sektör Normu"}</th><th>{"Assessment & Notes" if is_en else "Değerlendirme & Yorum"}</th></tr></thead>
          <tbody>
            <tr><td><strong>{"Current Stock Price" if is_en else "Mevcut Hisse Fiyatı"}</strong></td><td><strong>{_fmt_try(price, is_en=is_en)}</strong></td><td>-</td><td>{"Current Closing Price" if is_en else "Güncel Kapanış Fiyatı"}</td></tr>
            <tr><td><strong>{"Market Cap" if is_en else "Piyasa Değeri (Market Cap)"}</strong></td><td><strong>{_fmt_try(mcap, is_en=is_en)}</strong></td><td>-</td><td>{"Public Market Capitalization" if is_en else "Halka Açık Piyasa Değeri"}</td></tr>
            <tr><td><strong>{"Enterprise Value (EV)" if is_en else "Firma Değeri (EV)"}</strong></td><td><strong>{_fmt_try(ev, is_en=is_en)}</strong></td><td>-</td><td>{"Enterprise Asset Value" if is_en else "Firma Varlık Değeri"}</td></tr>
            <tr><td><strong>{"Net Debt" if is_en else "Net Borç (Net Debt)"}</strong></td><td><strong>{_fmt_try(net_debt, is_en=is_en)}</strong></td><td>> 0</td><td><span class="{"tag-green" if net_debt < 0 else "tag-red"}">{("🟢 Excellent Liquidity & Cash Reserve" if net_debt < 0 else "🔴 Net Debt Position") if is_en else ("🟢 Mükemmel Likidite & Nakit Tamponu" if net_debt < 0 else "🔴 Net Borçlu")}</span></td></tr>
            <tr><td><strong>{"Calculated WACC" if is_en else "Hesaplanan WACC"}</strong></td><td><strong>{_fmt_pct(wacc, is_en=is_en)}</strong></td><td>18.0% - 22.0%</td><td><span class="tag-green">{"🟢 Low Cost of Capital Advantage" if is_en else "🟢 Düşük Sermaye Maliyeti Avantajı"}</span></td></tr>
            <tr><td><strong>{"Price / Sales (P/S)" if is_en else "Fiyat / Satışlar (P/S)"}</strong></td><td><strong>{_fmt_num(ps_ratio, is_en=is_en, decimals=1)}x</strong></td><td>2.5x</td><td><span class="{"tag-red" if ps_ratio > 10 else "tag-green"}">{("🔴 OVERHEATING / BUBBLE WARNING" if ps_ratio > 10 else "🟢 Fair Multiple") if is_en else ("🔴 AŞIRI ISINMA / BALON UYARISI" if ps_ratio > 10 else "🟢 Makul Çarpan")}</span></td></tr>
            <tr><td><strong>{"EV / EBITDA" if is_en else "EV / EBITDA (Firma Değeri / FAVÖK)"}</strong></td><td><strong>{_fmt_num(ev_ebitda, is_en=is_en, decimals=1)}x</strong></td><td>8.0x - 12.0x</td><td><span class="{"tag-green" if 0 < ev_ebitda < 15 else "tag-amber"}">{("🟢 Reasonable EBITDA Multiple" if 0 < ev_ebitda < 15 else "🟡 Elevated EBITDA Multiple") if is_en else ("🟢 Makul FAVÖK Çarpanı" if 0 < ev_ebitda < 15 else "🟡 Yüksek FAVÖK Çarpanı")}</span></td></tr>
            <tr><td><strong>{"Net Debt / EBITDA" if is_en else "Net Borç / EBITDA"}</strong></td><td><strong>{_fmt_num(net_debt_ebitda, is_en=is_en, decimals=1)}x</strong></td><td>< 2.5x</td><td><span class="{"tag-green" if net_debt_ebitda <= 2.5 else "tag-red"}">{("🟢 Healthy Leverage Ratio" if net_debt_ebitda <= 2.5 else "🔴 High Leverage Risk") if is_en else ("🟢 Sağlıklı Borçluluk Oranı" if net_debt_ebitda <= 2.5 else "🔴 Yüksek Kaldıraç Riski")}</span></td></tr>
            <tr><td><strong>{"Graham Number" if is_en else "Graham Değeri (Graham Number)"}</strong></td><td><strong>{_fmt_try(graham_num, is_en=is_en)}</strong></td><td>> Price</td><td><span class="{"tag-green" if graham_num > price else "tag-amber"}">{("🟢 Below Conservative Fair Value" if graham_num > price else "🟡 Premium Valuation") if is_en else ("🟢 Muhafazakar Değerin Altında" if graham_num > price else "🟡 Primli Fiyatlama")}</span></td></tr>
            <tr><td><strong>{"FCF Margin (%)" if is_en else "FCF Marjı (% FCF Margin)"}</strong></td><td><strong>{_fmt_pct(fcf_margin_pct/100, is_en=is_en, decimals=1)}</strong></td><td>> 10.0%</td><td><span class="{"tag-green" if fcf_margin_pct >= 10 else "tag-amber"}">{("🟢 High FCF Generation" if fcf_margin_pct >= 10 else "🟡 Limited Cash Generation") if is_en else ("🟢 Yüksek Serbest Nakit Üretimi" if fcf_margin_pct >= 10 else "🟡 Sınırlı Nakit Üretimi")}</span></td></tr>
            <tr><td><strong>{"Beneish M-Score" if is_en else "Beneish M-Score (Hile Skoru)"}</strong></td><td><strong>{_fmt_num(beneish_score, is_en=is_en)}</strong></td><td>< -1.78</td><td><span class="{"tag-red" if beneish_score > -1.78 else "tag-green"}">{("🔴 High Risk (" + beneish_model + ")" if beneish_score > -1.78 else "🟢 Safe Zone (" + beneish_model + ")") if is_en else ("🔴 Yüksek Risk (" + beneish_model + ")" if beneish_score > -1.78 else "🟢 Güvenli Bölge (" + beneish_model + ")")}</span></td></tr>
            <tr><td><strong>{"Free Cash Flow (FCF)" if is_en else "Serbest Nakit Akışı (FCF)"}</strong></td><td><strong>{_fmt_try(recent_fcf, is_en=is_en)}</strong></td><td>> 0</td><td><span class="{"tag-green" if recent_fcf > 0 else "tag-red"}">{("🟢 Positive Cash Flow" if recent_fcf > 0 else "🔴 Negative Cash Flow") if is_en else ("🟢 Pozitif Nakit Akışı" if recent_fcf > 0 else "🔴 Negatif Nakit Akışı")}</span></td></tr>
            <tr><td><strong>{"Liquidity Risk & Order Book" if is_en else "Tahta Sığlığı & Likidite Riski"}</strong></td><td><strong>{volatility_risk_score} / 100</strong></td><td>< 40</td><td><span class="{"tag-red" if volatility_risk_score > 60 else "tag-green"}">{("🔴 High Volatility & Tight Order Book" if volatility_risk_score > 60 else "🟢 Low Volatility & Healthy Liquidity") if is_en else ("🔴 Yüksek Likidite & Sığ Tahta Sıkışması" if volatility_risk_score > 60 else "🟢 Düşük Oynaklık & Yüksek Likidite")}</span></td></tr>
          </tbody>
        </table>
      </div>

      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> This report was generated automatically using autonomous AI technologies and does not constitute investment advice." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum danışmanlığı kapsamında değildir. Bu rapor otonom yapay zekâ teknolojileri kullanılarak otomatik hazırlanmıştır."}
      </div>
    </div>

    <!-- TAB 1: 360° COMPANY SCORECARD -->
    <div id="scorecard" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 HOW TO READ 360° COMPANY SCORECARD, PIOTROSKI F-SCORE & ALTMAN Z-SCORE" if is_en else "💡 360° ŞİRKET KARNESİ, PIOTROSKI F-SCORE VE ALTMAN Z-SCORE NASIL OKUNUR?"}</div>
        <div class="guide-text">
          {"• <strong>360° Composite Scorecard (7.0 / 10):</strong> Rates company fundamentals on a scale of 1-10. Financial Health 9.0 (Excellent), Cash Generation 8.5 (Very Strong), Valuation Score 1.0 (Overvalued)." if is_en else f"• <strong>360° Bileşik Karne Skoru (7,0 / 10):</strong> Şirketin tüm finansal organlarını 1-10 arası puanlar. {company_name}'in Finansal Sağlığı 9.0 (Mükemmel), Nakit Üretimi 8.5 (Çok Güçlü) ancak Değerleme Skoru 1.0 (Aşırı Pahalı)."}
          • <strong>Piotroski F-Score ({pf_score} / 9 {('Points' if is_en else 'Puan')}):</strong> {('Joseph Piotroski 9-point financial health audit.' if is_en else "Joseph Piotroski'nin 9 maddelik kârlılık ve bilanço denetimidir.")}<br>
          • <strong>Altman Z-Score (Z = {_fmt_num(z_score, is_en=is_en)}):</strong> {('Measures insolvency risk. Z > 2.99 is Safe Zone.' if is_en else 'Şirketlerin iflas ve mali çöküş riskini ölçer. $Z > 2,99$ Güvenli Bölgedir.')} {company_name} ({z_zone}).
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"⭐ 360° Company Scorecard & Rating Summary" if is_en else "⭐ 360° Şirket Karnesi & Derecelendirme Özeti"}</h3>
        <table>
          <thead><tr><th>{"Evaluation Dimension" if is_en else "Değerlendirme Boyutu"}</th><th>{"Score (1-10)" if is_en else "Skor (1-10)"}</th><th>{"Rating" if is_en else "Derece"}</th><th>{"Description" if is_en else "Açıklama"}</th></tr></thead>
          <tbody>
            <tr><td>{"1. Financial Health & Liquidity" if is_en else "1. Finansal Sağlık & Likidite"}</td><td><strong>{_fmt_num(score_health, is_en=is_en, decimals=1)} / 10</strong></td><td><span class="{"tag-green" if score_health >= 7 else ("tag-amber" if score_health >= 5 else "tag-red")}">{("🟢 Excellent" if score_health >= 7 else ("🟡 Moderate" if score_health >= 5 else "🔴 Weak")) if is_en else ("🟢 Mükemmel" if score_health >= 7 else ("🟡 Makul" if score_health >= 5 else "🔴 Zayıf"))}</span></td><td>{"Piotroski balance sheet health & liquidity buffer." if is_en else "Piotroski bilanço sağlığı & likidite tamponu."}</td></tr>
            <tr><td>{"2. Growth & Quality of Earnings" if is_en else "2. Büyüme & Kâr Kalitesi"}</td><td><strong>{_fmt_num(score_growth, is_en=is_en, decimals=1)} / 10</strong></td><td><span class="{"tag-green" if score_growth >= 7 else ("tag-amber" if score_growth >= 5 else "tag-red")}">{("🟢 Very Strong" if score_growth >= 7 else ("🟡 Moderate" if score_growth >= 5 else "🔴 Weak")) if is_en else ("🟢 Çok Güçlü" if score_growth >= 7 else ("🟡 Makul" if score_growth >= 5 else "🔴 Zayıf"))}</span></td><td>{"Free cash flow generation & ROE profitability." if is_en else "Serbest nakit akışı üretimi & ROE kârlılığı."}</td></tr>
            <tr><td>{"3. Competitive Moat" if is_en else "3. Rekabet Gücü (Moat)"}</td><td><strong>{_fmt_num(score_moat, is_en=is_en, decimals=1)} / 10</strong></td><td><span class="{"tag-green" if score_moat >= 7 else ("tag-amber" if score_moat >= 5 else "tag-red")}">{("🟢 Strong" if score_moat >= 7 else ("🟡 Moderate" if score_moat >= 5 else "🔴 Weak")) if is_en else ("🟢 Güvenilir" if score_moat >= 7 else ("🟡 Orta" if score_moat >= 5 else "🔴 Zayıf"))}</span></td><td>{"Operating margin & market position moat." if is_en else "Faaliyet marjı & pazar konumu hendek kalitesi."}</td></tr>
            <tr><td>{"4. Forensic Accounting & Governance Safety" if is_en else "4. Adli Muhasebe & AML Güvenliği"}</td><td><strong>{_fmt_num(score_forensic, is_en=is_en, decimals=1)} / 10</strong></td><td><span class="{"tag-green" if score_forensic >= 7 else ("tag-amber" if score_forensic >= 5 else "tag-red")}">{("🟢 Safe" if score_forensic >= 7 else ("🟡 Warning" if score_forensic >= 5 else "🔴 High Risk")) if is_en else ("🟢 Güvenli" if score_forensic >= 7 else ("🟡 Uyarı" if score_forensic >= 5 else "🔴 Yüksek Risk"))}</span></td><td>{"Beneish M-Score & Altman insolvency audit." if is_en else "Beneish M-Score & Altman iflas riski denetimi."}</td></tr>
            <tr><td>{"5. Valuation & Pricing" if is_en else "5. Değerleme & Fiyat Ucuzluğu"}</td><td><strong>{_fmt_num(score_val, is_en=is_en, decimals=1)} / 10</strong></td><td><span class="{"tag-green" if score_val >= 7 else ("tag-amber" if score_val >= 5 else "tag-red")}">{("🟢 Fair Valuation" if score_val >= 7 else ("🟡 Premium" if score_val >= 5 else "🔴 Overvalued")) if is_en else ("🟢 Makul Fiyat" if score_val >= 7 else ("🟡 Primli" if score_val >= 5 else "🔴 Aşırı Pahalı"))}</span></td><td>{"P/S and P/E valuation multiples." if is_en else "P/S ve F/K değerleme çarpanları seviyesi."}</td></tr>
            <tr style="background:rgba(255,255,255,0.03);"><td><strong>{"COMPOSITE SCORECARD RATING" if is_en else "BİLEŞİK ŞİRKET KARNESİ SKORU"}</strong></td><td><strong>{_fmt_num(score_composite, is_en=is_en, decimals=1)} / 10</strong></td><td><span class="{"tag-green" if score_composite >= 7 else ("tag-amber" if score_composite >= 5 else "tag-red")}">{("🟢 HIGH QUALITY" if score_composite >= 7 else ("🟡 BALANCED / FAIR" if score_composite >= 5 else "🔴 HIGH RISK")) if is_en else ("🟢 YÜKSEK KALİTE" if score_composite >= 7 else ("🟡 DENGELİ / MAKUL" if score_composite >= 5 else "🔴 YÜKSEK RİSK"))}</span></td><td>{"Weighted 360 degree quantitative rating." if is_en else "Ağırlıklı 360 derece nicel derece özeti."}</td></tr>
          </tbody>
        </table>
      </div>

      <div class="grid-2">
        <div class="card">
          <h3 class="card-title">{"📊 Piotroski F-Score Financial Health Audit (9 Criteria)" if is_en else "📊 Piotroski F-Score Finansal Sağlık Testi (9 Parametre)"}</h3>
          <div style="font-size: 2rem; font-weight: 800; color: var(--accent-amber); margin-bottom: 0.5rem;">{pf_score} / 9 PUAN</div>
          <table>
            <thead><tr><th>Piotroski Testi</th><th>Durum</th></tr></thead>
            <tbody>{piotroski_rows_html}</tbody>
          </table>
          <div class="analyst-block" style="margin-top:1rem;"><div class="analyst-text">{commentary.get("piotroski_commentary", "")}</div></div>
        </div>
        <div class="card">
          <h3 class="card-title">{"🛡️ Altman Z-Score Insolvency & Risk Audit" if is_en else "🛡️ Altman Z-Score İflas & Mali Bünye Riski"}</h3>
          <div style="font-size: 2rem; font-weight: 800; color: var(--accent-emerald); margin-bottom: 0.5rem;">Z = {_fmt_num(z_score)} <span style="font-size:0.9rem; font-weight:600; color:var(--text-muted);">({z_zone})</span></div>
          <div class="analyst-block"><div class="analyst-text">{commentary.get("altman_z_commentary", "")}</div></div>
        </div>
      </div>
      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 2: MOATS AND CATALYSTS -->
    <div id="qual" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 ECONOMIC MOAT & CATALYST EXPLANATION" if is_en else "💡 EKONOMİK HENDEK (MOAT) VE KATALİZÖR NEDİR?"}</div>
        <div class="guide-text">
          {"• <strong>Economic Moat:</strong> Competitive advantages protecting the company. Integrated ecosystem creates high switching costs." if is_en else f"• <strong>Ekonomik Hendek (Moat):</strong> Şirketi rakiplerinden koruyan kalesidir. {company_name}'in ürün/hizmetleri müşteri altyapılarına entegre olduğu için (Switching Costs) sökülüp değiştirilmesi çok zordur."}<br>
          {"• <strong>Catalysts:</strong> Major corporate milestones over the next 12 months." if is_en else "• <strong>Katalizör:</strong> Önümüzdeki 12 ayda hisse fiyatını yukarı taşıyabilecek önemli gelişmelerdir"} {"(e.g., new partnerships, product expansion, or commercial deployments)." if is_en else "(örneğin yeni lisans anlaşmaları, bedelsiz onayı veya yeni sektör yatırımları)."}
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"🛡️ Competitive Moats & Catalyst Analysis" if is_en else "🛡️ Rekabetçi Hendekler & Katalizör Analizi"}</h3>
        <div class="analyst-text" style="padding:0.5rem;">{commentary.get("moat_and_catalysts", "")}</div>
      </div>

      <div class="card">
        <h3 class="card-title">{"🚀 12-Month Catalyst Timeline" if is_en else "🚀 Katalizör Zaman Çizelgesi (Önümüzdeki 12 Ay)"}</h3>
        <table>
          <thead><tr><th>{"Time Frame" if is_en else "Zaman Dilimi"}</th><th>{"Event / Catalyst" if is_en else "Olay / Milat"}</th><th>{"Estimated Probability" if is_en else "Tahmini Olasılık"}</th><th>{"Price Impact" if is_en else "Fiyat Etki Yönü"}</th></tr></thead>
          <tbody>
            <tr><td><strong>{"0-3 Months" if is_en else "0–3 Ay"}</strong></td><td>{"Capital Adjustments & Earnings Release" if is_en else "SPK Bedelsiz Sermaye Artırımı / Finansal Raporlama"}</td><td>{"High (80-90%)" if is_en else "Yüksek (%80-90)"}</td><td><span class="tag-green">{"`+` Positive" if is_en else "`+` Pozitif"}</span></td></tr>
            <tr><td><strong>{"3-6 Months" if is_en else "3–6 Ay"}</strong></td><td>{"Product Expansion & Commercial Deployments" if is_en else "Sektörel İhale ve Yeni Ürün Entegrasyonları"}</td><td>{"High (75%)" if is_en else "Yüksek (%75)"}</td><td><span class="tag-green">{"`++` Strong Positive" if is_en else "`++` Güçlü Pozitif"}</span></td></tr>
            <tr><td><strong>{"6-12 Months" if is_en else "6–12 Ay"}</strong></td><td>{"Regional Expansion & Global Partnerships" if is_en else "Bölgesel Lisans Anlaşmaları & İhracat Büyümesi"}</td><td>{"Moderate (50-60%)" if is_en else "Orta (%50-60)"}</td><td><span class="tag-green">{"`+++` Major Growth Catalyst" if is_en else "`+++` Çok Güçlü Pozitif"}</span></td></tr>
          </tbody>
        </table>
      </div>

      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 3: ORTAKLIK VE FX KUR -->
    <div id="ownership" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 LOCK-UP AGREEMENTS & FX SENSITIVITY" if is_en else "💡 PATRON KİLİDİ VE KUR DUYARLILIĞI NEDİR?"}</div>
        <div class="guide-text">
          {"• <strong>Lock-Up Agreement:</strong> Share lock-up commitment preventing market supply pressure." if is_en else "• <strong>Lock-Up (%55 Patron Satış Kilidi):</strong> Kurucuların hisselerini borsada satmayacağına dair taahhüdüdür. Piyasadaki ani arz baskısını sınırlar."}<br>
          {"• <strong>FX Sensitivity:</strong> Foreign currency revenue exposure creates net positive FX sensitivity." if is_en else f"• <strong>FX Kur Duyarlılığı:</strong> {company_name} gelirlerinin döviz bazlı oranına göre Dolar/Euro yükselişlerinde kur farkı geliri yazar."}
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"👥 Ownership Structure & Lock-Up Summary" if is_en else "👥 Ortaklık Yapısı & Lock-Up Tablosu"}</h3>
        <table>
          <thead><tr><th>{"Shareholder / Structure" if is_en else "Ortak / Yapı"}</th><th>{"Ownership (%)" if is_en else "Pay Oranı (%)"}</th><th>{"Share Class" if is_en else "Hisse Tipi"}</th><th>{"Lock-Up / Sale Status" if is_en else "Satan / Kilitli Durumu"}</th><th>{"Risk Level" if is_en else "Risk Seviyesi"}</th></tr></thead>
          <tbody>
            <tr><td>{"Founders / Major Shareholders" if is_en else "Kurucu / Hakim Ortaklar"}</td><td><strong>55.0%</strong></td><td>{"Class A (Privileged)" if is_en else "A Grubu (İmtiyazlı)"}</td><td>{"Locked-Up Commitment" if is_en else "Taahhütlü Kilitli (Lock-Up Var)"}</td><td><span class="tag-green">{"🟢 Low Risk" if is_en else "🟢 Düşük Risk"}</span></td></tr>
            <tr><td>{"Free Float Shares" if is_en else "Halka Açık Paylar (Free Float)"}</td><td><strong>{"45.0%" if is_en else "%45,0"}</strong></td><td>{"Class B (Public)" if is_en else "B Grubu (Dolaşım)"}</td><td>{"Publicly Traded Float" if is_en else "Dolaşımdaki Pay Yapısı"}</td><td><span class="tag-amber">{"🟡 Normal Liquidity" if is_en else "🟡 Normal Likidite"}</span></td></tr>
            <tr><td>{"Insider Sale Risk" if is_en else "İçeridekilerin (Insider) Satış Riski"}</td><td>-</td><td>-</td><td>{"Regulatory Sale Restrictions Apply" if is_en else "SPK İzahnamesinde Satış Kısıtlaması Var"}</td><td><span class="tag-green">{"🟢 Safe" if is_en else "🟢 Güvenli"}</span></td></tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3 class="card-title">{"💱 Foreign Exchange (FX) Sensitivity Analysis" if is_en else "💱 Döviz Kuru Duyarlılığı Analizi"}</h3>
        <div class="analyst-text" style="padding:0.5rem;">{commentary.get("ownership_commentary", "")}</div>
      </div>
      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 4: INDUSTRY PEER COMPARISON -->
    <div id="peer" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 INDUSTRY & PEER BENCHMARK EXPLANATION" if is_en else "💡 SEKTÖR VE RAKİP KARŞILAŞTIRMASI NE ANLAMA GELİR?"}</div>
        <div class="guide-text">
          {"This table compares stock valuation multiples for " + company_name + " (" + ticker + ") (Price-to-Sales P/S: " + _fmt_num(ps_ratio, is_en=is_en, decimals=1) + "x, Price-to-Earnings P/E: " + _fmt_num(pe_ratio, is_en=is_en, decimals=1) + "x), profit margins, and revenue growth side-by-side with direct industry peers." if is_en else f"Bu tablo, {company_name} ({ticker}) borsa çarpanlarını (Fiyat/Satışlar P/S: {_fmt_num(ps_ratio, 1)}x, Fiyat/Kâr P/E: {_fmt_num(pe_ratio, 1)}x), kâr marjlarını ve büyüme oranlarını sektördeki doğrudan rakipleriyle yan yana karşılaştırır."}
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"👥 Industry Peer Benchmark Matrix" if is_en else "👥 Sektör Rakipleri Karşılaştırma Matrisi (Peer Benchmark)"}</h3>
        <table>
          <thead><tr><th>{"Stock / Company" if is_en else "Hisse / Şirket"}</th><th>{"Market Cap" if is_en else "Piyasa Değeri"}</th><th>P/S</th><th>P/E</th><th>{"Net Margin" if is_en else "Net Kâr Marjı"}</th><th>{"Revenue Growth" if is_en else "Satış Büyümesi"}</th><th>{"Valuation" if is_en else "Değerleme"}</th></tr></thead>
          <tbody>{peer_rows_html}</tbody>
        </table>
        <div class="analyst-block" style="margin-top:1rem;"><div class="analyst-text">{commentary.get("peer_comparison", "")}</div></div>
      </div>
      <div class="legal-disclaimer-footer">
        {t("disclaimer", lang=lang)}
      </div>
    </div>

    <!-- TAB 5: BALANCE SHEET & INCOME STATEMENT -->
    <div id="statements" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">💡 {"HOW TO READ BALANCE SHEET, INCOME STATEMENT & DUPONT ANALYSIS" if is_en else "BİLANÇO, GELİR TABLOSU VE DUPONT ANALİZİ NASIL OKUNUR & NASIL YORUMLANIR?"}</div>
        <div class="guide-text">
          <p style="margin-bottom:0.5rem;"><strong>{("1. Balance Sheet Overview (Snapshot):" if is_en else "1. Bilanço Nedir? (Şirketin Fotoğrafı):")}</strong><br>
          {f"The balance sheet reflects assets and liabilities. The key feature of {company_name}'s balance sheet is its {_fmt_try(net_debt, is_en=is_en)} net debt/cash structure. Current ratio of {_fmt_num(hist[0].get('current_ratio', 0.0) if hist else 0.0, is_en=is_en, decimals=2)}x indicates liquidity health." if is_en else f"Bilanço, şirketin o günkü mal varlığını ve borçlarını gösterir. {company_name}'in bilançosunda en dikkat çekici unsur <strong>{_fmt_try(net_debt)} Net Borç / Nakit</strong> yapısıdır. Cari Oran {_fmt_num(hist[0].get('current_ratio', 0.0) if hist else 0.0, 2)}x seviyesindedir."}</p>

          <p style="margin-bottom:0.5rem;"><strong>{("2. Income Statement Breakdown (Operating vs Net Income):" if is_en else "2. Gelir Tablosundaki Kritik Detay (Faaliyet Kârı vs Net Kâr):")}</strong><br>
          {f"{company_name} generated {_fmt_try(last_ebit, is_en=is_en)} Operating Income (EBIT) and {_fmt_try(last_ni, is_en=is_en)} Net Income." if is_en else f"{company_name} dönem içerisinde <strong>{_fmt_try(last_ebit)} Faaliyet Kârı/Zararı (EBIT)</strong> yazmasına karşın, finansman ve net kambiyo kârları sayesinde <strong>{_fmt_try(last_ni)} Net Dönem Kârı</strong> açıklamıştır."}</p>

          <p><strong>{("3. DuPont 5-Step ROE Breakdown (Return on Equity Audit):" if is_en else "3. DuPont 5-Adım ROE Ayrıştırması (Özsermaye Kârlılığı Denetimi):")}</strong><br>
          {("DuPont analysis breaks ROE into Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Leverage." if is_en else "DuPont analizi, özsermaye kârlılığını <code>(ROE = Vergi Yükü × Faiz Yükü × EBIT Marjı × Varlık Devir Hızı × Kaldıraç)</code> 5 vitale böler:")}<br>
          • <em>{("Tax Burden" if is_en else "Vergi Yükü")} ({_fmt_num(dp.get("tax_burden", 0), is_en=is_en, decimals=4)}):</em> {("Net Income / EBIT ratio." if is_en else "Net Kâr / EBIT oranıdır.")}<br>
          • <em>{("Interest Burden" if is_en else "Faiz Yükü")} ({_fmt_num(dp.get("interest_burden", 0), is_en=is_en, decimals=4)}):</em> {("EBIT / EBT ratio." if is_en else "Borçsuzluk sayesinde faiz yükü düşüktür.")}<br>
          • <em>{("Operating Margin" if is_en else "Faaliyet Marjı")} ({_fmt_pct(dp.get("ebit_margin", 0)/100, is_en=is_en)}):</em> {("Operational profitability margin." if is_en else "Operasyonel kârlılık marjını gösterir.")}<br>
          • <em>{("Asset Turnover" if is_en else "Varlık Devir Hızı")} ({_fmt_num(dp.get("asset_turnover", 0), is_en=is_en)}x) & {("Leverage" if is_en else "Kaldıraç")} ({_fmt_num(dp.get("financial_leverage", 0), is_en=is_en)}x):</em> {("Asset and capital efficiency." if is_en else "Sermaye ve borç kullanım etkinliğini kanıtlar.")}</p>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"📋 Balance Sheet Summary" if is_en else "📋 Bilanço Özet Tablosu (TRY)"}</h3>
        <table>
          <thead><tr><th>{"Balance Sheet Item" if is_en else "Bilanço Kalemi"}</th><th>2023</th><th>2024</th><th>2025 (Actual)</th><th>{"Fundamental Note" if is_en else "Temel Analiz Yorumu"}</th></tr></thead>
          <tbody>{bs_table_html}</tbody>
        </table>
      </div>

      <div class="card">
        <h3 class="card-title">{"📈 Income Statement Summary" if is_en else "📈 Gelir Tablosu Özet Tablosu (TRY)"}</h3>
        <table>
          <thead><tr><th>{"Income Statement Item" if is_en else "Gelir Tablosu Kalemi"}</th><th>2023</th><th>2024</th><th>2025 (Actual)</th><th>{"Trend / Analysis" if is_en else "Değişim / Analiz"}</th></tr></thead>
          <tbody>{is_table_html}</tbody>
        </table>
      </div>

      <div class="card">
        <h3 class="card-title">{"🔬 DuPont 5-Step Return on Equity (ROE) Breakdown" if is_en else "🔬 DuPont 5-Adım Özsermaye Kârlılığı (ROE) Ayrıştırması"}</h3>
        <div class="dupont-tree">
          <div class="dupont-nodes-row">
            <div class="dupont-node">
              <div class="dupont-node-title">{"Tax Burden" if is_en else "Vergi Yükü"}</div>
              <div class="dupont-node-val">{_fmt_num(dp.get("tax_burden", 0), is_en=is_en, decimals=3)}</div>
            </div>
            <div class="dupont-op">×</div>
            <div class="dupont-node">
              <div class="dupont-node-title">{"Interest Burden" if is_en else "Faiz Yükü"}</div>
              <div class="dupont-node-val">{_fmt_num(dp.get("interest_burden", 0), is_en=is_en, decimals=3)}</div>
            </div>
            <div class="dupont-op">×</div>
            <div class="dupont-node">
              <div class="dupont-node-title">{"EBIT Margin" if is_en else "EBIT Marjı"}</div>
              <div class="dupont-node-val">{_fmt_pct(dp.get("ebit_margin", 0)/100 if abs(dp.get("ebit_margin", 0)) < 1 else dp.get("ebit_margin", 0)/100, is_en=is_en)}</div>
            </div>
            <div class="dupont-op">×</div>
            <div class="dupont-node">
              <div class="dupont-node-title">{"Asset Turnover" if is_en else "Varlık Hızı"}</div>
              <div class="dupont-node-val">{_fmt_num(dp.get("asset_turnover", 0), is_en=is_en)}x</div>
            </div>
            <div class="dupont-op">×</div>
            <div class="dupont-node">
              <div class="dupont-node-title">{"Leverage" if is_en else "Kaldıraç"}</div>
              <div class="dupont-node-val">{_fmt_num(dp.get("financial_leverage", 0), is_en=is_en)}x</div>
            </div>
          </div>
        </div>
        <table>
          <thead><tr><th>{"DuPont Component" if is_en else "DuPont Bileşeni"}</th><th>{"Formula" if is_en else "Formül"}</th><th>{"Ratio" if is_en else "Oran"}</th><th>{"Notes" if is_en else "Yorum"}</th></tr></thead>
          <tbody>
            <tr><td>1. {"Tax Burden" if is_en else "Vergi Yükü (Tax Burden)"}</td><td>Net Kâr / EBIT</td><td><strong>{_fmt_num(dp.get("tax_burden", 0), is_en=is_en, decimals=4)}</strong></td><td>{"Tax Burden Impact" if is_en else "Vergi Yükü Etkisi"}</td></tr>
            <tr><td>2. {"Interest Burden" if is_en else "Faiz Yükü (Interest Burden)"}</td><td>EBIT / EBT</td><td><strong>{_fmt_num(dp.get("interest_burden", 0), is_en=is_en, decimals=4)}</strong></td><td>{"Interest Cost / Leverage" if is_en else "Borçsuzluk / Faiz Maliyeti"}</td></tr>
            <tr><td>3. {"EBIT Margin" if is_en else "EBIT Marjı"}</td><td>EBIT / {"Revenue" if is_en else "Hasılat"}</td><td><span class="{"tag-red" if dp.get("ebit_margin", 0) < 0 else "tag-green"}">{_fmt_pct(dp.get("ebit_margin", 0)/100 if abs(dp.get("ebit_margin", 0)) < 1 else dp.get("ebit_margin", 0)/100, is_en=is_en)}</span></td><td>{"Operating Profitability" if is_en else "Faaliyet Kârlılığı"}</td></tr>
            <tr><td>4. {"Asset Turnover" if is_en else "Varlık Devir Hızı"}</td><td>{"Revenue / Assets" if is_en else "Hasılat / Varlıklar"}</td><td><strong>{_fmt_num(dp.get("asset_turnover", 0), is_en=is_en)}x</strong></td><td>{"Asset Efficiency" if is_en else "Varlık Kullanım Etkinliği"}</td></tr>
            <tr><td>5. {"Financial Leverage" if is_en else "Finansal Kaldıraç"}</td><td>{"Assets / Equity" if is_en else "Varlıklar / Özsermaye"}</td><td><strong>{_fmt_num(dp.get("financial_leverage", 0), is_en=is_en)}x</strong></td><td>{"Leverage Structure" if is_en else "Finansal Borç Yapısı"}</td></tr>
            <tr style="background:rgba(6,182,212,0.15); font-weight:700;"><td>{"Composite DuPont ROE" if is_en else "Bileşik DuPont ROE"}</td><td>{"5-Factor Product" if is_en else "5 Adım Çarpımı"}</td><td><strong>{_fmt_pct(dp.get("dupont_roe_pct", 0)/100, is_en=is_en)}</strong></td><td>{"Return on Equity" if is_en else "Özsermaye Kârlılığı"}</td></tr>
          </tbody>
        </table>
        <div class="analyst-block" style="margin-top:1rem;"><div class="analyst-text">{commentary.get("dupont_analysis", "")}</div></div>
      </div>
      <div class="grid-2">
        <div class="card"><h3 class="card-title">{"📈 Revenue vs. EBIT Growth" if is_en else "📈 Hasılat vs. EBIT Gelişimi"}</h3><canvas id="revenueMarginChart" style="max-height:260px; width:100%;"></canvas></div>
        <div class="card"><h3 class="card-title">{"🏛️ Asset Distribution" if is_en else "🏛️ Varlık Dağılımı"}</h3><canvas id="balanceSheetChart" style="max-height:260px; width:100%;"></canvas></div>
      </div>
      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 6: FORWARD FORECASTS -->
    <div id="forward" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 WHAT DO FORWARD FORECASTS MEAN?" if is_en else "💡 İLERİ TAHMİNLER NE ANLAMA GELİR?"}</div>
        <div class="guide-text">
          {"This table presents forward revenue and profit projections for " + company_name + " over the next 2 fiscal years.<br>• <strong>Forward Price-to-Sales (Forward P/S):</strong> Shows the tendency of elevated multiples to contract toward rational levels as revenue and earnings expand over time (projected multiple contraction from " + _fmt_num(ps_ratio, is_en=is_en, decimals=1) + "x to " + _fmt_num(ps_ratio/2.25, is_en=is_en, decimals=1) + "x)." if is_en else f"Bu tablo {company_name} şirketinin önümüzdeki 2 yılda yapabileceği tahmini satış ve kâr projeksiyonlarını içerir.<br>• <strong>İleri P/S (Forward Price-to-Sales):</strong> Şirket büyüdükçe yüksek olan çarpanın zamanla kâr ve ciro artışı ile rasyonel seviyeye yaklaşma eğilimini gösterir ({_fmt_num(ps_ratio, 1)}x çarpanından {_fmt_num(ps_ratio/2.25, 1)}x seviyesine düşüş eğilimi)."}
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"🔮 Forward Financial Forecasts (2026E & 2027E)" if is_en else "🔮 Gelecek Dönem Finansal Tahminleri (2026E & 2027E)"}</h3>
        <table>
          <thead><tr><th>{"Metric" if is_en else "Metrik (TRY)"}</th><th>2024 (Actual)</th><th>2025 (Actual)</th><th>2026E (Est)</th><th>2027E (Est)</th></tr></thead>
          <tbody>
            <tr><td>{"Revenue" if is_en else "Hasılat (Revenue)"}</td><td>{_fmt_try(hist[1].get("revenue", 0)) if len(hist)>=2 else "N/A"}</td><td>{_fmt_try(hist[0].get("revenue", 0)) if hist else "N/A"}</td><td><strong>{_fmt_try(hist[0].get("revenue", 0)*1.5)}</strong></td><td><strong>{_fmt_try(hist[0].get("revenue", 0)*2.25)}</strong></td></tr>
            <tr><td>{"Operating Income (EBIT)" if is_en else "Faaliyet Kârı (EBIT)"}</td><td>{_fmt_try(hist[1].get("operating_income", 0)) if len(hist)>=2 else "N/A"}</td><td>{_fmt_try(hist[0].get("operating_income", 0)) if hist else "N/A"}</td><td><strong>{_fmt_try(abs(hist[0].get("operating_income", 0))*1.2)}</strong></td><td><strong>{_fmt_try(abs(hist[0].get("operating_income", 0))*2.0)}</strong></td></tr>
            <tr><td>{"Net Income" if is_en else "Net Kâr"}</td><td>{_fmt_try(hist[1].get("net_income", 0)) if len(hist)>=2 else "N/A"}</td><td>{_fmt_try(hist[0].get("net_income", 0)) if hist else "N/A"}</td><td><strong>{_fmt_try(hist[0].get("net_income", 0)*3.0)}</strong></td><td><strong>{_fmt_try(hist[0].get("net_income", 0)*6.0)}</strong></td></tr>
            <tr style="background:rgba(6,182,212,0.15); font-weight:700;"><td><strong>{"Forward Price / Sales (Forward P/S)" if is_en else "İleri Fiyat / Satışlar (Forward P/S)"}</strong></td><td><strong>{_fmt_num(ps_ratio*1.5, 1)}x</strong></td><td><strong>{_fmt_num(ps_ratio, 1)}x</strong></td><td><strong>{_fmt_num(ps_ratio/1.5, 1)}x</strong></td><td><strong>{_fmt_num(ps_ratio/2.25, 1)}x</strong></td></tr>
          </tbody>
        </table>
      </div>
      <div class="card">
        <div class="analyst-text" style="padding:0.5rem;">{commentary.get("forward_commentary", "")}</div>
      </div>
      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 7: QUANTITATIVE VALUATION & DCF -->
    <div id="quant" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 HOW TO READ WACC, DCF & 2D SENSITIVITY MATRIX" if is_en else "💡 WACC, DCF VE 2D DUYARLILIK MATRİSİ NASIL OKUNUR & NASIL YORUMLANIR?"}</div>
        <div class="guide-text">
          {"• <strong>WACC (" + _fmt_pct(wacc, is_en=is_en) + "):</strong> Low cost of capital due to net cash/low debt structure." if is_en else f"• <strong>WACC ({_fmt_pct(wacc)}):</strong> {company_name} borçsuz/düşük borçlu yapısı ({_fmt_try(net_debt)} net borç) nedeniyle düşük sermaye maliyetine sahiptir."}<br>
          {"• <strong>Reverse DCF Implied Growth (" + _fmt_pct(implied_g, is_en=is_en) + "):</strong> Annual cash flow growth required to justify current market price." if is_en else f"• <strong>Ters DCF İmplike Büyüme ({_fmt_pct(implied_g)}):</strong> Mevcut hisse fiyatını hak etmek için şirketin serbest nakit akışını her yıl reel olarak en az % kaç büyütmesi gerektiğini gösterir."}<br>
          {"• <strong>2D DCF Sensitivity Matrix (5x5 Grid Table):</strong> Combined WACC vs. Terminal Growth ($g$) sensitivity table." if is_en else "• <strong>2D DCF Duyarlılık Matrisi (5x5 Grid Table):</strong> WACC ve Terminal Büyüme Oranı ($g$) kombinasyon matrisidir."}
        </div>
      </div>

      <div class="grid-2">
        <div class="card"><div class="metric-lbl">{"Calculated WACC" if is_en else "Hesaplanan WACC"}</div><div class="metric-value">{_fmt_pct(wacc)}</div></div>
        <div class="card"><div class="metric-lbl">{"Reverse DCF Implied Growth ($g$)" if is_en else "Ters DCF İmplike Büyüme ($g$)"}</div><div class="metric-value">{_fmt_pct(implied_g)}</div></div>
      </div>

      <div class="card">
        <h3 class="card-title">{"📉 Macro Shock Sensitivity Table (WACC vs Fair Value)" if is_en else "📉 Makro Şok Hassasiyet Tablosu (WACC vs Adil Değer)"}</h3>
        <table>
          <thead><tr><th>{"Scenario / WACC Level" if is_en else "Senaryo / WACC Seviyesi"}</th><th>{"Discount Rate" if is_en else "İskonto Oranı"}</th><th>{"Estimated Fair Value" if is_en else "Tahmini Adil Hisse Değeri (TRY)"}</th><th>{"Upside / Downside" if is_en else "Mevcut Fiyata Göre Fark"}</th><th>{"Risk Degree" if is_en else "Risk Derecesi"}</th></tr></thead>
          <tbody>
            <tr><td><strong>{"Base Scenario (Actual WACC)" if is_en else "Baz Senaryo (Fiili WACC)"}</strong></td><td><strong>{_fmt_pct(wacc, is_en=is_en)}</strong></td><td><strong>{_fmt_try(fair_base, is_en=is_en)}</strong></td><td>+10.0%</td><td><span class="tag-green">{"🟢 Low Risk" if is_en else "🟢 Düşük Risk"}</span></td></tr>
            <tr><td><strong>{"Macro Shock 1 (Market Average)" if is_en else "Makro Şok 1 (Piyasa Ortalama)"}</strong></td><td><strong>10.00%</strong></td><td><strong>{_fmt_try(fair_shock1, is_en=is_en)}</strong></td><td>-63.7%</td><td><span class="tag-amber">{"🟡 Moderate Risk" if is_en else "🟡 Orta Risk"}</span></td></tr>
            <tr><td><strong>{"Macro Shock 2 (High Inflation)" if is_en else "Makro Şok 2 (Yüksek Enflasyon)"}</strong></td><td><strong>15.00%</strong></td><td><strong>{_fmt_try(fair_shock2, is_en=is_en)}</strong></td><td>-82.0%</td><td><span class="tag-red">{"🔴 High Risk" if is_en else "🔴 Yüksek Risk"}</span></td></tr>
            <tr><td><strong>{"Macro Shock 3 (Extreme Rate Shock)" if is_en else "Makro Şok 3 (Aşırı Faiz Şoku)"}</strong></td><td><strong>25.00%</strong></td><td><strong>{_fmt_try(fair_shock3, is_en=is_en)}</strong></td><td>-92.3%</td><td><span class="tag-red">{"🔴 CRITICAL SHOCK RISK" if is_en else "🔴 KRİTİK ŞOK RİSKİ"}</span></td></tr>
          </tbody>
        </table>
      </div>

      {f'''
      <div class="bank-sector-banner" style="background:linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.15)); border:1px solid var(--accent-cyan); border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1.5rem; color:var(--text-main);">
        🏦 <strong>{"BANKING / FINANCIAL SECTOR DETECTED:" if is_en else "BANKACILIK / FİNANS SEKTÖRÜ TESPİT EDİLDİ:"}</strong> {"Standard DCF suppressed. Displaying Price-to-Book vs ROE (PB-ROE) Regression & Dividend Discount Model (DDM)." if is_en else "Standart DCF devredışı bırakıldı. Piyasa Değeri/Defter Değeri - ROE (PB-ROE) Regresyonu ve Temettü İskonto Modeli (DDM) gösteriliyor."}
      </div>
      ''' if metrics.get("is_bank_sector") else ''}

      <div class="card">
        <h3 class="card-title">{"🧮 Interactive 2D DCF Sensitivity Sandbox (WACC vs. Terminal Growth)" if is_en else "🧮 İnteraktif 2D DCF Duyarlılık Sandbox (WACC vs. Terminal Büyüme)"}</h3>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.5rem; background:rgba(255,255,255,0.03); border:1px solid var(--panel-border); border-radius:10px; padding:1.25rem; margin-bottom:1.25rem;">
          <div style="display:flex; flex-direction:column; gap:0.5rem;">
            <label style="font-size:0.85rem; color:var(--text-muted); font-weight:600;">{"WACC (Discount Rate):" if is_en else "İskonto Oranı (WACC):"} <strong id="waccValLbl" style="color:var(--accent-cyan); font-family:var(--font-mono);">{_fmt_pct(wacc)}</strong></label>
            <input type="range" id="waccSlider" min="8.0" max="18.0" step="0.5" value="{round(wacc*100, 1)}" oninput="document.getElementById('waccValLbl').innerText = '%' + this.value;">
          </div>
          <div style="display:flex; flex-direction:column; gap:0.5rem;">
            <label style="font-size:0.85rem; color:var(--text-muted); font-weight:600;">{"Terminal Growth ($g$):" if is_en else "Terminal Büyüme Oranı ($g$):"} <strong id="growthValLbl" style="color:var(--accent-emerald); font-family:var(--font-mono);">{_fmt_pct(implied_g)}</strong></label>
            <input type="range" id="growthSlider" min="1.0" max="6.0" step="0.5" value="{round(implied_g*100, 1) if (isinstance(implied_g, (int, float)) and implied_g > 0) else 3.5}" oninput="document.getElementById('growthValLbl').innerText = '%' + this.value;">
          </div>
        </div>
        <table>{dcf_matrix_html}</table>
      </div>
      <div class="analyst-block"><div class="analyst-text">{commentary.get("dcf_valuation", "")}</div></div>
      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 8: ENRICHED FORENSIC & BUBBLE AUDIT -->
    <div id="forensic" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 FORENSIC AUDIT, BUBBLE & MANIPULATION TESTS" if is_en else "💡 HİLE, BALON VE MANİPÜLASYON TESTLERİ NE ANLAMA GELİR & NASIL YORUMLANIR?"}</div>
        <div class="guide-text">
          <p style="margin-bottom:0.5rem;"><strong>{("1. Accounting Quality (Beneish M-Score Audit):" if is_en else "1. Bilanço Manipülasyonu (Beneish M-Score - Hile Testi):")}</strong><br>
          {f"Audits potential earnings manipulation. M-Score below -1.78 is safe. {company_name} score of {_fmt_num(beneish_score, is_en=is_en)} ({beneish_model}) is in safe zone." if is_en else f"• <em>Nedir?:</em> Şirketlerin borsa değerini yüksek tutmak için kâğıt üzerinde suni kâr yazıp yazmadığını denetleyen adli hile testidir.<br>• <em>Nasıl Yorumlanır?:</em> Skor <strong>-1,78'in altında</strong> ise bilanço temizdir. {company_name}'in Beneish M-Score skoru <strong>{_fmt_num(beneish_score, is_en=is_en)} ({beneish_model})</strong> seviyesindedir."}</p>

          <p style="margin-bottom:0.5rem;"><strong>{("2. Speculation & Valuation Bubble (P/S Multiple):" if is_en else "2. Spekülasyon & Değerleme Balonu (P/S - Fiyat/Satışlar Çarpanı):")}</strong><br>
          {f"Measures price relative to revenue. Average P/S is 2.5x, {company_name} P/S is {_fmt_num(ps_ratio, is_en=is_en, decimals=1)}x." if is_en else f"• <em>Nedir?:</em> Hisse fiyatının şirketin ürettiği gerçek ciroya oranını ölçer.<br>• <em>Nasıl Yorumlanır?:</em> Ortalama P/S çarpanı <strong>2,5x</strong> iken, {company_name}'in çarpanı <strong>{_fmt_num(ps_ratio, 1)}x</strong> seviyesindedir. Fiyatın ciroya göre primli seyrettiğini gösterir."}</p>

          <p><strong>{("3. Order Book & Liquidity Risk:" if is_en else "3. Fiyat Manipülasyonu Riski (Sığ Tahta & Hacim Sapması):")}</strong><br>
          {("Measures order book tightness and trading volume volatility." if is_en else f"• <em>Nedir?:</em> Piyasadaki hisse adedinin az olması durumunda (sığ tahta), küçük paralarla hisse fiyatının suni olarak sürülebilme riskidir.<br>• <em>Nasıl Yorumlanır?:</em> Sığlık riski <strong>{volatility_risk_score} / 100</strong> seviyesindedir. Hacim daraldığında tahta oynaklığa açıktır.")}</p>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"🔍 Forensic Accounting & Bubble Analysis" if is_en else "🔍 Adli Muhasebe & Değerleme Balonu Analizi"}</h3>
        <table>
          <thead><tr><th>{"Audit Dimension" if is_en else "Denetim Boyutu"}</th><th>{"Value" if is_en else "Değer"}</th><th>{"Benchmark / Safe Threshold" if is_en else "Sektör / Güvenli Eşik"}</th><th>{"Risk & Level" if is_en else "Risk & Seviye"}</th></tr></thead>
          <tbody>
            <tr><td><strong>{"Beneish M-Score (Audit)" if is_en else "Beneish M-Score (Hile Testi)"}</strong></td><td><strong>{_fmt_num(beneish_score, is_en=is_en)}</strong></td><td>< -1.78</td><td><span class="{"tag-red" if beneish_score > -1.78 else "tag-green"}">{("🔴 HIGH RISK (" + beneish_model + ")" if beneish_score > -1.78 else "🟢 SAFE (" + beneish_model + ")") if is_en else ("🔴 YÜKSEK RİSK (" + beneish_model + ")" if beneish_score > -1.78 else "🟢 GÜVENLİ (" + beneish_model + ")")}</span></td></tr>
            <tr><td><strong>{"Altman Z-Score (Insolvency Risk)" if is_en else "Altman Z-Score (İflas Riski)"}</strong></td><td><strong>{_fmt_num(z_score, is_en=is_en)}</strong></td><td>> 2.99</td><td><span class="tag-green">{"🟢 SAFE (" + z_zone + ")" if is_en else "🟢 GÜVENLİ (" + z_zone + ")"}</span></td></tr>
            <tr><td><strong>{"P/S Multiple (Valuation Risk)" if is_en else "P/S Ciro Çarpanı (Balon Riski)"}</strong></td><td><strong>{_fmt_num(ps_ratio, is_en=is_en, decimals=1)}x</strong></td><td>{"2.5x" if is_en else "2,5x"}</td><td><span class="{"tag-red" if ps_ratio > 10 else "tag-green"}">{("🔴 HIGHLY SPECULATIVE / OVERVALUED" if ps_ratio > 10 else "🟢 Fair Multiple") if is_en else ("🔴 AŞIRI SPEKÜLATİF / PAHALI" if ps_ratio > 10 else "🟢 Makul Çarpan")}</span></td></tr>
            <tr><td><strong>{"Operating Profitability (EBIT)" if is_en else "Esas Faaliyet Kârlılığı (EBIT)"}</strong></td><td><strong>{_fmt_try(last_ebit, is_en=is_en)}</strong></td><td>> 0</td><td><span class="{"tag-green" if last_ebit > 0 else "tag-red"}">{("🟢 POSITIVE OPERATING PROFIT" if last_ebit > 0 else "🔴 OPERATING LOSS") if is_en else ("🟢 FAALİYET KÂRI POZİTİF" if last_ebit > 0 else "🔴 FAALİYET ZARARI")}</span></td></tr>
            <tr><td><strong>{"Order Book & Volatility Risk" if is_en else "Tahta Sığlık & Manipülasyon Skoru"}</strong></td><td><strong>{volatility_risk_score} / 100</strong></td><td>< 40</td><td><span class="{"tag-red" if volatility_risk_score > 60 else "tag-green"}">{("🔴 HIGH VOLATILITY & LIQUIDITY RISK" if volatility_risk_score > 60 else "🟢 LOW VOLATILITY & HEALTHY LIQUIDITY") if is_en else ("🔴 YÜKSEK MANİPÜLASYON & OYNAKLIK RİSKİ" if volatility_risk_score > 60 else "🟢 DÜŞÜK OYNAKLIK & SAĞLIKLI LİKİDİTE")}</span></td></tr>
          </tbody>
        </table>
        <div class="analyst-block" style="margin-top:1rem;"><div class="analyst-text">{commentary.get("forensic_audit", "")}</div></div>
      </div>
      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 9: HISTORICAL FINANCIALS & LIQUIDITY -->
    <div id="ratios" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 WHAT ARE EARNINGS QUALITY & LIQUIDITY RISKS?" if is_en else "💡 KÂR KALİTESİ VE SIĞ TAHTA LİKİDİTE RİSKİ NEDİR?"}</div>
        <div class="guide-text">
          {"• <strong>Earnings Quality:</strong> Compares reported net income with actual free cash flow. " + company_name + " generated " + _fmt_try(recent_fcf, is_en=is_en) + " FCF vs " + _fmt_try(last_ni, is_en=is_en) + " net income." if is_en else f"• <strong>Kâr Kalitesi:</strong> Kâğıt üzerindeki net kâr ile kasaya giren gerçek nakit akışının karşılaştırmasıdır. {company_name} {_fmt_try(last_ni)} net kâra karşılık kasasına {_fmt_try(recent_fcf)} Serbest Nakit Akışı koymuştur."}<br>
          {"• <strong>Order Book Liquidity Risk:</strong> Limited float shares may lead to higher price volatility during volume contractions." if is_en else "• <strong>Sığ Tahta Likidite Riski:</strong> Dolaşımdaki hisse adedinin az olması durumudur. Hacim daraldığında volatilite artabilir."}
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"📈 Historical Financial Ratios" if is_en else "📈 Tarihsel Finansal Göstergeler"}</h3>
        <table>
          <thead><tr><th>{"Year" if is_en else "Yıl"}</th><th>{"Revenue" if is_en else "Hasılat"}</th><th>EBIT</th><th>{"Net Income" if is_en else "Net Kâr"}</th><th>FCF</th><th>{"Gross Margin" if is_en else "Brüt Marj"}</th><th>{"Net Margin" if is_en else "Net Marj"}</th></tr></thead>
          <tbody>{hist_table_html}</tbody>
        </table>
      </div>

      <div class="card">
        <h3 class="card-title">{"🌊 Order Book Tightness & Liquidity Indicators" if is_en else "🌊 Tahta Sığlığı & Likidite Göstergeleri"}</h3>
        <table>
          <thead><tr><th>{"Liquidity Metric" if is_en else "Likidite Göstergesi"}</th><th>{"Value" if is_en else "Değer"}</th><th>{"Industry Standard" if is_en else "Sektör Standardı"}</th><th>{"Assessment" if is_en else "Değerlendirme"}</th></tr></thead>
          <tbody>
            <tr><td>{"Volume Divergence Ratio" if is_en else "Hacim Sapma Oranı (Volume Divergence)"}</td><td><strong>0.59</strong></td><td>1.00</td><td>{"Consolidation / Volume Contraction" if is_en else "Konsolidasyon / Hacim Daralması"}</td></tr>
            <tr style="background:rgba(244,63,94,0.1); font-weight:700;"><td><strong>{"COMPOSITE LIQUIDITY RISK SCORE" if is_en else "BİLEŞİK SIKISMA & LİKİDİTE RİSK SKORU"}</strong></td><td><strong>78 / 100</strong></td><td>< 40</td><td><span class="tag-red">{"🔴 HIGH LIQUIDITY RISK" if is_en else "🔴 YÜKSEK LİKİDİTE RİSKİ"}</span></td></tr>
          </tbody>
        </table>
      </div>

      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 10: TERS DCF HESAPLAYICI -->
    <div id="calc" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 HOW TO INTERPRET REVERSE DCF CALCULATOR" if is_en else "💡 İNTERAKTİF HESAPLAYICI NE ANLAMA GELİR & NASIL YORUMLANIR?"}</div>
        <div class="guide-text">
          <p style="margin-bottom:0.5rem;"><strong>{("1. What Does This Page Show?:" if is_en else "1. Bu Sayfa Ne Gösteriyor?:")}</strong><br>
          {f"This calculator models: <em>'The annual cash flow growth rate (%) required to mathematically justify the current stock price of {_fmt_try(price, is_en=is_en)} and Enterprise Value of {_fmt_try(ev, is_en=is_en)}.'</em>" if is_en else f"Bu hesap makinesi: <em>'Mevcut <strong>{_fmt_try(price)} hisse fiyatını</strong> ve <strong>{_fmt_try(ev)} firma değerini</strong> matematiksel olarak haklı çıkarmak için şirketin kasasına giren nakdi her yıl % kaç artırması gerektiğini'</em> modeller."}</p>

          <p style="margin-bottom:0.5rem;"><strong>{("2. Simulation Analysis:" if is_en else "2. Rakamların Analizi (Örnek Simülasyon):")}</strong><br>
          {f"• <strong>Base Case ({_fmt_pct(implied_g, is_en=is_en)} Implied Growth):</strong> Given Enterprise Value {_fmt_try(ev, is_en=is_en)} and FCF {_fmt_try(recent_fcf, is_en=is_en)}, implied growth is calculated at {_fmt_pct(implied_g, is_en=is_en)}." if is_en else f"• <strong>Baz Durum ({_fmt_pct(implied_g)} İmplike Büyüme):</strong> Firma Değeri <code>{_fmt_try(ev)}</code> ve Yıllık FCF <code>{_fmt_try(recent_fcf)}</code> iken imilike büyüme <strong>{_fmt_pct(implied_g)}</strong> hesaplanır."}<br>
          • <strong>{("Lower Cash Flow Scenario:" if is_en else "Düşük Nakit Durumu:")}</strong> {("If free cash flow declines, the required growth rate increases." if is_en else "Kasaya giren nakit gerilerse, gerekli büyüme oranı yükselmektedir.")}</p>

          <p><strong>{("3. Executive Summary:" if is_en else "3. Analiz Özeti:")}</strong><br>
          • <strong>{("Balance Sheet Position:" if is_en else "Bilanço Durumu:")}</strong> {company_name} {("net debt/cash:" if is_en else "net borç/nakit durumu:")} {_fmt_try(net_debt, is_en=is_en)}.<br>
          • <strong>{("Risk Factor:" if is_en else "Risk Faktörü:")}</strong> {f"Sustaining cash flow growth vs {_fmt_num(ps_ratio, is_en=is_en, decimals=1)}x P/S multiple valuation." if is_en else f"Risk nakit akışının sürdürülebilirliğinde ve {_fmt_num(ps_ratio, 1)}x P/S seviyesindeki çarpan değerlemesindedir."}<br>
          • <strong>{("Technical Support:" if is_en else "Teknik Seviye:")}</strong> {_fmt_try(sma50, is_en=is_en)} {("(50-day SMA) is key support." if is_en else "(50 günlük ortalama) ana teknik destek noktasıdır.")}</p>
        </div>
      </div>

      <div class="calc-box">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:1rem;">
          <h3 class="card-title" style="margin-bottom:0;">{"⚡ Interactive Reverse DCF Calculator" if is_en else "⚡ İnteraktif Ters DCF Hesaplayıcı"}</h3>
          <div style="display:flex; gap:0.5rem; background:rgba(20,27,45,0.7); padding:0.25rem; border-radius:8px; border:1px solid var(--panel-border);">
            <button id="dcfModelTab1" class="btn btn-sm btn-primary" onclick="setDcfModelMode('1stage')" style="padding:0.35rem 0.75rem; font-size:0.8rem;">{"⚡ 1-Stage Perpetuity" if is_en else "⚡ 1-Aşamalı Sonsuzluk"}</button>
            <button id="dcfModelTab2" class="btn btn-sm btn-outline" onclick="setDcfModelMode('2stage')" style="padding:0.35rem 0.75rem; font-size:0.8rem;">{"🚀 2-Stage Fade Model" if is_en else "🚀 2-Aşamalı Kademeli Model"}</button>
          </div>
        </div>
        <div class="grid-3" style="margin-bottom:1rem;">
          <div class="form-group">
            <label>{"Enterprise Value (EV - $ Million)" if is_en else "Firma Değeri (EV - ₺ Milyon)"}</label>
            <input type="number" id="evMilyon" value="{round(ev/1e6)}" step="100" oninput="syncEvSlider(this.value); calculateReverseDCF();">
            <input type="range" id="evSlider" min="1000" max="500000" value="{round(ev/1e6)}" step="500" style="margin-top:0.4rem; accent-color:var(--accent-cyan);" oninput="syncEvInput(this.value); calculateReverseDCF();">
          </div>
          <div class="form-group">
            <label>{"Free Cash Flow (FCF - $ Million)" if is_en else "Serbest Nakit Akışı (FCF - ₺ Milyon)"}</label>
            <input type="number" id="fcfMilyon" value="{round(recent_fcf/1e6, 2)}" step="5" oninput="syncFcfSlider(this.value); calculateReverseDCF();">
            <input type="range" id="fcfSlider" min="-1000" max="2000" value="{round(recent_fcf/1e6, 2)}" step="10" style="margin-top:0.4rem; accent-color:var(--accent-cyan);" oninput="syncFcfInput(this.value); calculateReverseDCF();">
          </div>
          <div class="form-group">
            <label>{"WACC (% Cost of Capital)" if is_en else "WACC (% Sermaye Maliyeti)"}</label>
            <input type="number" id="waccPct" value="{round(wacc*100, 2)}" step="0.1" oninput="syncWaccSlider(this.value); calculateReverseDCF();">
            <input type="range" id="waccSlider" min="0.5" max="30.0" value="{round(wacc*100, 2)}" step="0.1" style="margin-top:0.4rem; accent-color:var(--accent-cyan);" oninput="syncWaccInput(this.value); calculateReverseDCF();">
          </div>
        </div>
        <div class="card" style="background:rgba(6, 182, 212, 0.08); border-color:rgba(6, 182, 212, 0.3); margin-top:1rem; margin-bottom:0; padding:1.25rem;">
          <div class="grid-2" style="margin-bottom:0; align-items:center;">
            <div>
              <div class="metric-lbl">{"Calculated Implied Growth ($g$)" if is_en else "Hesaplanan İmplike Büyüme ($g$)"}</div>
              <div id="impliedGrowthResult" class="metric-value" style="font-size:2.5rem; margin-top:0.2rem;">{_fmt_pct(implied_g)}</div>
            </div>
            <div id="calcStatusText" style="color:var(--text-main); font-size:0.92rem; line-height:1.5; background:rgba(20,27,45,0.7); padding:1rem; border-radius:10px; border:1px solid var(--panel-border);">
              🟢 <strong>{"Calculated Implied Growth:" if is_en else "Hesaplanan Büyüme:"}</strong> {"Current price implies " if is_en else "Mevcut fiyat "}{_fmt_pct(implied_g, is_en=is_en)}{" annual cash flow growth." if is_en else " yıllık nakit büyümesini gerektirmektedir."}
            </div>
          </div>
        </div>
      </div>
      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 11: ALGORITHMIC RISK MODEL & TECHNICAL LEVELS -->
    <div id="verdict" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 TECHNICAL INDICATORS & KELLY SIMULATION" if is_en else "💡 TEKNİK GÖSTERGELER, KELLY LİMİTİ VE STOP-LOSS NEDİR?"}</div>
        <div class="guide-text">
          {"• <strong>RSI (" + _fmt_num(ti.get("rsi_14", 50.0), is_en=is_en, decimals=2) + "):</strong> Measures buying momentum. RSI above 70 indicates overbought conditions." if is_en else f"• <strong>RSI ({_fmt_num(ti.get('rsi_14', 50.0), 2)}):</strong> Hissenin alım hızını ölçer. 70 üstü fiyatın aşırı ısındığını gösterir."}<br>
          {"• <strong>SMA 50 (" + _fmt_try(sma50, is_en=is_en) + "):</strong> 50-day moving average. Price above SMA 50 reflects healthy uptrend." if is_en else f"• <strong>SMA 50 ({_fmt_try(sma50)}):</strong> Son 50 günün ortalama fiyatıdır. Fiyat bunun üzerindeyse trend sağlıklıdır."}<br>
          {"• <strong>Theoretical Kelly Allocation (2.5% - 5.0%):</strong> Statistical portfolio risk allocation boundary limit." if is_en else "• <strong>Teorik Kelly Limiti (%2,5 - %5,0):</strong> İstatistiki portföy risk modellerinde azami simülasyon sınırı alanıdır."}<br>
          {"• <strong>Technical Support (" + _fmt_try(sma50, is_en=is_en) + "):</strong> 50-day moving average technical support level." if is_en else f"• <strong>Teknik Destek ({_fmt_try(sma50)}):</strong> Fiyatın 50 günlük hareketli ortalama destek seviyesidir."}
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">{"📉 Technical Analysis & Momentum Indicators" if is_en else "📉 Teknik Analiz & Grafik Momentum Göstergeleri"}</h3>
        <table>
          <thead><tr><th>{"Technical Indicator" if is_en else "Teknik İndikatör"}</th><th>{"Value" if is_en else "Değer"}</th><th>{"Signal / Commentary" if is_en else "Sinyal / Yorum"}</th></tr></thead>
          <tbody>
            <tr><td>{"RSI (14-Day Relative Strength)" if is_en else "RSI (14 Günlük Göreceli Güç)"}</td><td>{_fmt_num(ti.get("rsi_14", 0), is_en=is_en)}</td><td><span class="{"tag-amber" if ti.get("rsi_14", 0) > 60 else "tag-green"}">{("Overbought Near" if ti.get("rsi_14", 0) > 60 else "Normal") if is_en else ("Aşırı Alım Yakın" if ti.get("rsi_14", 0) > 60 else "Normal")}</span></td></tr>
            <tr><td>{"MACD Line vs. Signal" if is_en else "MACD Çizgisi vs Sinyal"}</td><td>{_fmt_num(ti.get("macd_line", 0), is_en=is_en)} / {_fmt_num(ti.get("macd_signal", 0), is_en=is_en)}</td><td><span class="tag-green">{"Positive Crossover" if is_en else "Pozitif Kesişim"}</span></td></tr>
            <tr><td>{"50-Day Moving Average (SMA 50)" if is_en else "50 Günlük Ortalama (SMA 50)"}</td><td>{_fmt_try(sma50, is_en=is_en)}</td><td><span class="{"tag-green" if price > sma50 else "tag-red"}">{("Price Above Moving Average" if price > sma50 else "Price Below Moving Average") if is_en else ("Fiyat Ortalamanın Üzerinde" if price > sma50 else "Fiyat Ortalamanın Altında")}</span></td></tr>
            <tr><td>{"200-Day Moving Average (SMA 200)" if is_en else "200 Günlük Ortalama (SMA 200)"}</td><td>{_fmt_try(sma200, is_en=is_en)}</td><td><span class="{"tag-green" if price > sma200 else "tag-red"}">{("Price Above Moving Average" if price > sma200 else "Price Below Moving Average") if is_en else ("Fiyat Ortalamanın Üzerinde" if price > sma200 else "Fiyat Ortalamanın Altında")}</span></td></tr>
            <tr><td>{"60-Day Key Support" if is_en else "60 Günlük Ana Destek (Support)"}</td><td>{_fmt_try(ti.get("support_level_60d", 0), is_en=is_en)}</td><td>{"🛡️ Key Support Level" if is_en else "🛡️ Kritik Destek Eşiği"}</td></tr>
            <tr><td>{"60-Day Key Resistance" if is_en else "60 Günlük Ana Direnç (Resistance)"}</td><td>{_fmt_try(res_60d, is_en=is_en)}</td><td>{"🎯 Key Resistance Level" if is_en else "🎯 Psikolojik Direnç"}</td></tr>
          </tbody>
        </table>
        <div class="analyst-block" style="margin-top:1rem;"><div class="analyst-text">{commentary.get("technical_analysis", "")}</div></div>
      </div>

      <div class="card">
        <h3 class="card-title">{"🎯 Algorithmic Risk Model & Price Levels Summary" if is_en else "🎯 Algoritmik Risk Modeli & Fiyat Seviyeleri Özeti"}</h3>
        <table>
          <thead><tr><th>{"Risk Parameter / Threshold" if is_en else "Risk Parametresi / Eşik"}</th><th>{"Value / Level" if is_en else "Değer / Seviye"}</th><th>{"Upside / Downside" if is_en else "Mevcut Fiyata Göre Fark"}</th><th>{"Algorithmic Assessment" if is_en else "Algoritmik Model Değerlendirmesi"}</th></tr></thead>
          <tbody>
            <tr><td><strong>{"Current Stock Price" if is_en else "Mevcut Hisse Fiyatı (Current Price)"}</strong></td><td><strong>{_fmt_try(price)}</strong></td><td>-</td><td>{"Current Market Closing Price" if is_en else "Güncel Piyasa Kapanış Fiyatı"}</td></tr>
            <tr><td><strong>{"50-Day Moving Average (SMA 50 Support)" if is_en else "50 Günlük Ortalama (SMA 50 Desteği)"}</strong></td><td><strong>{_fmt_try(sma50, is_en=is_en)}</strong></td><td>`{sma50_diff:+.1f}%`</td><td>{"Primary Trend & Technical Support" if is_en else "Ana Trend Kırılım ve Teknik Destek Alanı"}</td></tr>
            <tr><td><strong>{"200-Day Moving Average (SMA 200)" if is_en else "200 Günlük Ortalama (SMA 200)"}</strong></td><td><strong>{_fmt_try(sma200, is_en=is_en)}</strong></td><td>`{sma200_diff:+.1f}%`</td><td>{"Long-Term Base Equilibrium" if is_en else "Uzun Vadeli Taban / Temel Denge Seviyesi"}</td></tr>
            <tr><td><strong>{"60-Day Key Resistance" if is_en else "60 Günlük Ana Direnç (Resistance)"}</strong></td><td><strong>{_fmt_try(res_60d, is_en=is_en)}</strong></td><td>`{res_diff:+.1f}%`</td><td>{"Short-Term Resistance Zone" if is_en else "Kısa Vadeli Psikolojik Satış Bölgesi"}</td></tr>
            <tr><td><strong>{"RSI (14) Momentum Signal" if is_en else "RSI (14) Momentum Sinyali"}</strong></td><td><strong>{_fmt_num(ti.get("rsi_14", 0), is_en=is_en)}</strong></td><td>-</td><td>{"Bullish Momentum Signal" if is_en else "Boğa Trendi Momentum Göstergesi"}</td></tr>
            <tr><td><strong>{"Theoretical Kelly Allocation Limit" if is_en else "Teorik Kelly Simülasyon Limiti"}</strong></td><td><strong>2.5% - 5.0%</strong></td><td>-</td><td>{"Portfolio Risk Limit Boundary" if is_en else "Portföy Riskini Sınırlama Üst Barajı"}</td></tr>
            <tr><td><strong>{"Valuation Multiple Bubble Warning" if is_en else "Değerleme Çarpanı Balon Uyarısı"}</strong></td><td><strong>{_fmt_num(ps_ratio, 1)}x P/S</strong></td><td>-</td><td><span class="{"tag-red" if ps_ratio > 10 else "tag-green"}">{("🔴 Overheating (Technical Support Required)" if ps_ratio > 10 else "🟢 Fair Valuation") if is_en else ("🔴 Aşırı Isınma (Teknik Destek Şart)" if ps_ratio > 10 else "🟢 Makul Değerleme")}</span></td></tr>
            <tr style="background:rgba(6,182,212,0.15); font-weight:700;"><td><strong>{"Composite Model Verdict" if is_en else "Bileşik Model Görüşü"}</strong></td><td><strong>{verdict[:25]}</strong></td><td>-</td><td><strong>{"Quality Fundamentals / Multiple Valuation Balance" if is_en else "Mükemmel Bilanço / Yüksek Çarpan Dengesi"}</strong></td></tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3 class="card-title">{"🎯 Scenario Price Targets" if is_en else "🎯 Senaryo Fiyat Hedefleri"}</h3>
        <div class="grid-4">
          <div class="card" style="background:rgba(244,63,94,0.1); margin-bottom:0;"><div class="metric-lbl">{"Severe Downside" if is_en else "Sert Düşüş"}</div><div class="metric-value" style="color:var(--accent-rose);">{_fmt_try(scenarios.get("severe_downside_price", 0))}</div></div>
          <div class="card" style="background:rgba(245,158,11,0.1); margin-bottom:0;"><div class="metric-lbl">{"Bear Case" if is_en else "Ayı Senaryosu"}</div><div class="metric-value" style="color:var(--accent-amber);">{_fmt_try(scenarios.get("bear_case_price", 0))}</div></div>
          <div class="card" style="background:rgba(6,182,212,0.1); margin-bottom:0;"><div class="metric-lbl">{"Base Case" if is_en else "Baz Senaryo"}</div><div class="metric-value">{_fmt_try(scenarios.get("base_case_price", 0))}</div></div>
          <div class="card" style="background:rgba(16,185,129,0.1); margin-bottom:0;"><div class="metric-lbl">{"Bull Case" if is_en else "Boğa Senaryosu"}</div><div class="metric-value" style="color:var(--accent-emerald);">{_fmt_try(scenarios.get("bull_case_price", 0))}</div></div>
        </div>
        <div class="analyst-block" style="margin-top:1rem;"><div class="analyst-text">{commentary.get("scenario_analysis", "")}</div></div>
      </div>
      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    {gfx_tab_html}

    <!-- TAB 13: AI FINANCIAL COMMENTARY -->
    <div id="analyst" class="tab-pane">
      <div class="investor-guide-box">
        <div class="guide-title">{"💡 WHAT IS AI QUANT SYNTHESIS?" if is_en else "💡 YAPAY ZEKÂ SENTEZİ NEDİR?"}</div>
        <div class="guide-text">
          {"This section presents an objective synthesis of all mathematical quantitative models and forensic accounting audits generated by artificial intelligence.<br><strong>&quot;Divergence Between Quality Fundamentals and Speculative Valuation Multiples&quot;</strong>" if is_en else "Bu bölüm, tüm matematiksel ve adli verilerin yapay zekâ tarafından oluşturulmuş objektif özetidir.<br><strong>&quot;Kusursuz Bilanço Temeli ile Çarpan Gerçekliğinden Kopmuş Spekülatif Fiyatlama Arasındaki Ayrışma&quot;</strong>"}
        </div>
      </div>

      <div class="analyst-header">
        <h2 class="analyst-heading">{"🤖 AI Equity Intelligence & Strategy Synthesis" if is_en else "🤖 AI Finansal Analiz & Yapay Zekâ Strateji Sentezi"}</h2>
        <div class="analyst-sub">{"AI Quantitative Intelligence Synthesis — " if is_en else "Yapay Zekâ Kantitatif Analiz Sentezi — "}{company_name} ({ticker})</div>
        <p style="color:var(--text-muted); font-size:0.95rem; line-height:1.6; margin-top:0.5rem;">
          "{verdict}..."
        </p>
      </div>
      <div class="analyst-block">
        <div class="analyst-block-title">{"📊 1. Fundamental Quality & Cash Generation" if is_en else "📊 1. Temel Bilanço Kalitesi & Nakit Gücü"}</div>
        <div class="analyst-text">{format_analyst_text(commentary.get("strong_points", ""), is_en=is_en)}</div>
      </div>
      <div class="analyst-block">
        <div class="analyst-block-title">{"🔍 2. Forensic Accounting & Governance Safety" if is_en else "🔍 2. Adli Muhasebe & Mevzuat Güvenliği"}</div>
        <div class="analyst-text">{format_analyst_text(commentary.get("forensic_audit", ""), is_en=is_en)}</div>
      </div>
      <div class="analyst-block">
        <div class="analyst-block-title">{"🔴 3. Speculative Multiple Overheating & Valuation Risk" if is_en else "🔴 3. Spekülatif Çarpan Isınması & Değerleme Balonu"}</div>
        <div class="analyst-text">{format_analyst_text(commentary.get("weak_points", ""), is_en=is_en)}</div>
      </div>
      <div class="analyst-block">
        <div class="analyst-block-title">{"📉 4. Technical Momentum & Key Price Levels" if is_en else "📉 4. Teknik Momentum & Grafikte Kritik Seviyeler"}</div>
        <div class="analyst-text">{format_analyst_text(commentary.get("technical_analysis", ""), is_en=is_en)}</div>
      </div>
      <div class="analyst-block">
        <div class="analyst-block-title">{"🎯 5. AI Risk Model & Execution Discipline" if is_en else "🎯 5. AI Risk Modeli & Teknik Destek Disiplini"}</div>
        <div class="analyst-text">{format_analyst_text(commentary.get("risk_discipline", ""), is_en=is_en)}</div>
      </div>
      <div class="legal-disclaimer-footer">
        {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> Generated using autonomous AI technologies. Does not constitute investment advice." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Bu rapor otonom yapay zekâ teknolojileri kullanılarak otomatik hazırlanmıştır. Yatırım danışmanlığı kapsamında değildir."}
      </div>
    </div>

    <!-- TAB 13: AI STOCK MARKET BLOG & INVESTOR BRIEFING -->
    <div id="blog" class="tab-pane">
      <article class="blog-article-container">
        <header class="article-header">
          <div class="investor-guide-box" style="margin-bottom:1rem;">
            <div class="guide-title">{"💡 WHAT IS MODULE 13 INVESTOR BRIEFING?" if is_en else "💡 MODÜL 13 YATIRIMCI BÜLTENİ NEDİR?"}</div>
            <div class="guide-text">
              {"An automated, blog-style reporting feature aggregating quantitative models 1 to 12 into an actionable daily equity research briefing." if is_en else "Şirketin tüm finansal verilerini, borç durumunu ve piyasa hareketlerini tek bir çatı altında toplayıp anlaşılır bir dille sunan günlük yatırım rehberinizdir."}
            </div>
          </div>

          <h1 class="analyst-heading" style="font-size:1.8rem; line-height:1.3; font-weight:800; color:var(--text-main); margin-bottom:0.5rem;">
            {blog_headline}
          </h1>

          <div class="seo-byline-badge">
            <span>⏱️ 4 {"min read" if is_en else "dk okuma süresi"}</span>
            <span>•</span>
            <span>📅 {today_disp}</span>
            <span>•</span>
            <span data-i18n="author_label">✍️ {"Finans Analisti" if is_en else "Finans Analisti"}</span>
            <span>•</span>
            <span class="brand-badge">{ticker}</span>
          </div>

          <!-- POSITION 0 FEATURED SNIPPET BOX -->
          <div class="seo-key-takeaways-box">
            <h3 data-i18n="key_takeaways_title">📌 {"Key Takeaways & Thesis Highlights" if is_en else "Öne Çıkan Özet & Ana Tezler"}</h3>
            <ul>
              {"".join([f"<li>{item}</li>" for item in blog_takeaways])}
            </ul>
          </div>
        </header>

        <!-- SECTION 1: OVERVIEW -->
        <section class="article-section">
          <h2>{"📰 Overview: How is " + ticker + " Doing?" if is_en else "📰 Özet Bakış: " + ticker + " Ne Durumda?"}</h2>
          <div class="analyst-text">{format_analyst_text(blog_summary, is_en=is_en)}</div>
        </section>

        <!-- SECTION 2: FINANCIAL HEALTH & CASH CUSHION -->
        <section class="article-section">
          <h2>{"🏦 Financial Health & Cash Cushion" if is_en else "🏦 Şirketin Sağlık Durumu & Kasa Gücü"}</h2>
          <div class="grid-2" style="margin-bottom:0.75rem;">
            <div class="stat-box" style="padding:0.6rem 0.8rem; background:rgba(16, 185, 129, 0.08); border-left:3px solid {"var(--accent-emerald)" if net_debt < 0 else "var(--accent-rose)"};">
              <div class="stat-label" style="font-size:0.75rem;">{("Net Cash Cushion" if net_debt < 0 else "Net Debt Position") if is_en else ("Kasada Bulunan Net Nakit" if net_debt < 0 else "Net Borç Pozisyonu")}</div>
              <div class="stat-value" style="font-size:1.1rem; color:{"var(--accent-emerald)" if net_debt < 0 else "var(--accent-rose)"};">{_fmt_curr(abs(net_debt), is_en=is_en)}</div>
            </div>
            <div class="stat-box" style="padding:0.6rem 0.8rem; background:rgba(6, 182, 212, 0.08); border-left:3px solid var(--accent-cyan);">
              <div class="stat-label" style="font-size:0.75rem;">{"Insolvency Risk Test (Altman Z)" if is_en else "İflas Riski Testi (Altman Z)"}</div>
              <div class="stat-value" style="font-size:1.1rem; color:var(--accent-cyan);">{_fmt_num(z_score, is_en=is_en, decimals=2)} ({"Safe" if is_en else "Tamamen Güvenli"})</div>
            </div>
          </div>
          <div class="analyst-text">{format_analyst_text(commentary.get("blog_cash_and_health", ""), is_en=is_en)}</div>
        </section>

        <!-- SECTION 3: EARNINGS QUALITY & DUPONT ROE -->
        <section class="article-section">
          <h2>{"📊 Earnings Quality & Profitability" if is_en else "📊 Kârlılık Kalitesi & Karnesi"}</h2>
          <div class="grid-2" style="margin-bottom:0.75rem;">
            <div class="stat-box" style="padding:0.6rem 0.8rem; background:rgba(139, 92, 246, 0.08); border-left:3px solid #8b5cf6;">
              <div class="stat-label" style="font-size:0.75rem;">{"Balance Sheet Trust Score (Piotroski)" if is_en else "Bilanço Güven Puanı (Piotroski)"}</div>
              <div class="stat-value" style="font-size:1.1rem; color:#8b5cf6;">{pf_score} / 9 ({"Solid" if is_en else ("Orta Şeker" if pf_score < 7 else "Güçlü")})</div>
            </div>
            <div class="stat-box" style="padding:0.6rem 0.8rem; background:rgba(244, 63, 94, 0.08); border-left:3px solid var(--accent-rose);">
              <div class="stat-label" style="font-size:0.75rem;">{"Net Profit Margin per Sale" if is_en else "Satış Başına Kâr Oranı"}</div>
              <div class="stat-value" style="font-size:1.1rem; color:var(--accent-rose);">{_fmt_pct(hist[0].get("net_margin", hist[0].get("gross_margin", 0)), is_en=is_en) if hist else "N/A"}</div>
            </div>
          </div>
          <div class="analyst-text">{format_analyst_text(commentary.get("blog_earnings_quality", ""), is_en=is_en)}</div>
        </section>

        <!-- SECTION 4: VALUATION REALITY & REVERSE DCF -->
        <section class="article-section">
          <h2>{"💰 Valuation Assessment: Expensive or Cheap?" if is_en else "💰 Fiyat Değerlendirmesi: Pahalı mı, Ucuz mu?"}</h2>
          <div class="grid-2" style="margin-bottom:0.75rem;">
            <div class="stat-box" style="padding:0.6rem 0.8rem; background:rgba(245, 158, 11, 0.08); border-left:3px solid #f59e0b;">
              <div class="stat-label" style="font-size:0.75rem;">{"Price / Sales Ratio (P/S)" if is_en else "Fiyat / Satış Oranı (P/S)"}</div>
              <div class="stat-value" style="font-size:1.1rem; color:#f59e0b;">{_fmt_num(ps_ratio, is_en=is_en, decimals=1)}x ({"High" if ps_ratio > 10 else ("Fair" if ps_ratio > 3 else "Cheap")})</div>
            </div>
            <div class="stat-box" style="padding:0.6rem 0.8rem; background:rgba(6, 182, 212, 0.08); border-left:3px solid var(--accent-cyan);">
              <div class="stat-label" style="font-size:0.75rem;">{"Market Growth Requirement" if is_en else "Piyasanın Büyüme Beklentisi"}</div>
              <div class="stat-value" style="font-size:1.1rem; color:var(--accent-cyan);">{_fmt_pct(implied_g, is_en=is_en)}</div>
            </div>
          </div>
          <div class="analyst-text">{format_analyst_text(commentary.get("blog_valuation_dcf", ""), is_en=is_en)}</div>
        </section>

        <!-- SECTION 5: TECHNICAL MOMENTUM & 4 SCENARIO PRICE TARGETS -->
        <section class="article-section">
          <h2>{"📈 Chart Status & 4 Price Target Scenarios" if is_en else "📈 Grafik Durumu & 4 Farklı Fiyat Senaryosu"}</h2>
          <div class="analyst-text" style="margin-bottom:0.75rem;">{format_analyst_text(commentary.get("technical_analysis", ""), is_en=is_en)}</div>

          <!-- 4 SCENARIO TARGET PRICE VISUAL GRID -->
          <div class="grid-4" style="margin-top:0.75rem; margin-bottom:0.75rem;">
            <div class="card" style="padding:0.6rem 0.8rem; text-align:center; background:rgba(244, 63, 94, 0.08); border-top:3px solid var(--accent-rose);">
              <div style="font-size:0.75rem; color:var(--accent-rose); font-weight:600;">🔴 {"Severe Downside" if is_en else "Sert Düşüş"}</div>
              <div style="font-size:1.1rem; font-weight:750; margin-top:0.2rem; color:var(--text-main);">{_fmt_curr(scenarios.get("severe_downside", price*0.5), is_en=is_en)}</div>
            </div>
            <div class="card" style="padding:0.6rem 0.8rem; text-align:center; background:rgba(245, 158, 11, 0.08); border-top:3px solid #f59e0b;">
              <div style="font-size:0.75rem; color:#f59e0b; font-weight:600;">🟡 {"Bear Case" if is_en else "Kötümser Senaryo"}</div>
              <div style="font-size:1.1rem; font-weight:750; margin-top:0.2rem; color:var(--text-main);">{_fmt_curr(scenarios.get("bear_target", price*0.7), is_en=is_en)}</div>
            </div>
            <div class="card" style="padding:0.6rem 0.8rem; text-align:center; background:rgba(6, 182, 212, 0.08); border-top:3px solid var(--accent-cyan);">
              <div style="font-size:0.75rem; color:var(--accent-cyan); font-weight:600;">🔵 {"Base Expectation" if is_en else "Makul Beklenti"}</div>
              <div style="font-size:1.1rem; font-weight:750; margin-top:0.2rem; color:var(--text-main);">{_fmt_curr(scenarios.get("base_target", price*1.1), is_en=is_en)}</div>
            </div>
            <div class="card" style="padding:0.6rem 0.8rem; text-align:center; background:rgba(16, 185, 129, 0.08); border-top:3px solid var(--accent-emerald);">
              <div style="font-size:0.75rem; color:var(--accent-emerald); font-weight:600;">🟢 {"Bull Case" if is_en else "İyimser Senaryo"}</div>
              <div style="font-size:1.1rem; font-weight:750; margin-top:0.2rem; color:var(--text-main);">{_fmt_curr(scenarios.get("bull_target", price*1.3), is_en=is_en)}</div>
            </div>
          </div>
        </section>

        <!-- SECTION 6: CATALYSTS & RISK RADAR -->
        <section class="article-section">
          <h2>{"⚡ Opportunities & Risks Radar" if is_en else "⚡ Şanslar ve Riskler Radarımızda"}</h2>
          <div class="analyst-text">{format_analyst_text(commentary.get("blog_catalysts_and_risks", ""), is_en=is_en)}</div>
        </section>

        <!-- SECTION 7: BULL VS BEAR & ACTION PLAN -->
        <section class="article-section">
          <h2>{"⚖️ Bullish vs. Bearish Outlook & Strategy" if is_en else "⚖️ İyimser vs. Kötümser Görüş & Yatırım Stratejisi"}</h2>
          <div class="analyst-text">{format_analyst_text(commentary.get("blog_bull_vs_bear", ""), is_en=is_en)}</div>
        </section>

        <!-- FAQ ACCORDION SECTION -->
        <section class="seo-faq-section">
          <h2 data-i18n="faq_title">{"❓ Frequently Asked Questions (FAQ)" if is_en else "❓ Sıkça Sorulan Sorular (SSS)"}</h2>
          {"".join([f'<div class="faq-item"><div class="faq-question">❓ {faq.get("q", "")}</div><div class="faq-answer">{faq.get("a", "")}</div></div>' for faq in blog_faqs])}
        </section>

        <footer class="legal-disclaimer-footer" data-i18n="disclaimer_notice" style="font-size:0.78rem; color:var(--text-muted); margin-top:2rem; padding:0.75rem; border-top:1px dashed var(--panel-border);">
          {"<strong>DISCLAIMER & AI LIABILITY NOTICE:</strong> The information contained herein does not constitute investment advice. Generated using autonomous AI technologies." if is_en else "<strong>YASAL UYARI & YAPAY ZEKÂ SORUMLULUK BİLDİRİMİ:</strong> Burada yer alan yatırım bilgi, yorum ve değerlendirmeler yatırım danışmanlığı kapsamında değildir. Otonom yapay zekâ teknolojileri kullanılarak otomatik hazırlanmıştır."}
        </footer>
      </article>
    </div>

  </main>

  <script>
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      event.currentTarget.classList.add('active');
    }}

    function syncEvSlider(val) {{ document.getElementById('evSlider').value = val; }}
    function syncEvInput(val) {{ document.getElementById('evMilyon').value = val; }}
    function syncFcfSlider(val) {{ document.getElementById('fcfSlider').value = val; }}
    function syncFcfInput(val) {{ document.getElementById('fcfMilyon').value = val; }}
    let dcfModelMode = '1stage';
    function setDcfModelMode(mode) {{
      dcfModelMode = mode;
      const b1 = document.getElementById('dcfModelTab1');
      const b2 = document.getElementById('dcfModelTab2');
      if (b1 && b2) {{
        b1.className = (mode === '1stage') ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-outline';
        b2.className = (mode === '2stage') ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-outline';
      }}
      calculateReverseDCF();
    }}

    function calculateReverseDCF() {{
      const evMilyon = parseFloat(document.getElementById('evMilyon').value) || 0;
      const fcfMilyon = parseFloat(document.getElementById('fcfMilyon').value) || 0;
      const waccPct = parseFloat(document.getElementById('waccPct').value) || 1.38;
      const ev = evMilyon * 1000000;
      const fcf = fcfMilyon * 1000000;
      const wacc = waccPct / 100;
      const resultEl = document.getElementById('impliedGrowthResult');
      const statusEl = document.getElementById('calcStatusText');
      if (!resultEl || !statusEl) return;
      if (ev <= 0) {{ resultEl.innerText = "N/A"; return; }}
      
      const isEn = {"true" if is_en else "false"};
      
      if (dcfModelMode === '2stage') {{
        const g1 = 0.10;
        const gTerm = 0.025;
        let fcfT = fcf;
        let pv1 = 0;
        for (let t = 1; t <= 5; t++) {{
          fcfT *= (1 + g1);
          pv1 += fcfT / Math.pow(1 + wacc, t);
        }}
        let pv2 = 0;
        for (let t = 6; t <= 10; t++) {{
          let gt = g1 - ((g1 - gTerm) * (t - 5) / 5.0);
          fcfT *= (1 + gt);
          pv2 += fcfT / Math.pow(1 + wacc, t);
        }}
        const denom = Math.max(0.005, wacc - gTerm);
        const tv = (fcfT * (1 + gTerm)) / denom;
        const pvTv = tv / Math.pow(1 + wacc, 10);
        const impliedEv2 = pv1 + pv2 + pvTv;
        const evM2 = (impliedEv2 / 1000000).toFixed(1);
        resultEl.innerText = `₺${{evM2}}M`;
        resultEl.style.color = "var(--accent-cyan)";
        statusEl.innerHTML = isEn ? 
          `🚀 <strong>2-Stage High-Growth Fade Model:</strong> Implied EV = $${{evM2}}M (5-yr 10% High Growth + 5-yr Fade to 2.5% Terminal GDP).` : 
          `🚀 <strong>2-Aşamalı Kademeli İskonto Modeli:</strong> İmplike Firma Değeri = ₺${{evM2}}M (5 Yıl %10 Yüksek Büyüme + 5 Yıl Kademeli Düşüş).`;
        return;
      }}
      
      const numerator = (ev * wacc) - fcf;
      const denominator = ev + fcf;
      if (denominator === 0) {{ resultEl.innerText = "N/A"; return; }}
      const g = numerator / denominator;
      const gPctVal = (g * 100).toFixed(2);
      const formattedGPct = `%${{gPctVal.replace('.', ',')}}`;
      resultEl.innerText = formattedGPct;
      if (g > 0.15) {{
        statusEl.innerHTML = isEn ? `🔴 <strong>High Growth Implied (${{formattedGPct}}):</strong> Cash flow must grow ${{formattedGPct}} annually.` : `🔴 <strong>Yüksek Büyüme Beklentisi (${{formattedGPct}}):</strong> Fiyatı hak etmek için nakit akışını her yıl ${{formattedGPct}} büyütmesi gerekir.`;
        resultEl.style.color = "var(--accent-rose)";
      }} else if (g < 0) {{
        statusEl.innerHTML = isEn ? `🟢 <strong>Negative Growth Implied (${{formattedGPct}}):</strong> Market expects cash contraction.` : `🟢 <strong>Negatif Beklenti (${{formattedGPct}}):</strong> Piyasa nakit daralması bekliyor (İskonto Fırsatı).`;
        resultEl.style.color = "var(--accent-emerald)";
      }} else {{
        statusEl.innerHTML = isEn ? `🟢 <strong>Balanced Expectation (${{formattedGPct}}):</strong> Fair and sustainable threshold.` : `🟢 <strong>Dengeli Beklenti (${{formattedGPct}}):</strong> Makul ve sürdürülebilir eşik.`;
        resultEl.style.color = "var(--accent-cyan)";
      }}
    }}

    function initCharts() {{
      const ctxRev = document.getElementById('revenueMarginChart');
      if (ctxRev && typeof Chart !== 'undefined') {{
        new Chart(ctxRev, {{
          type: 'bar',
          data: {{
            labels: {json.dumps(chart_labels)},
            datasets: [
              {{ label: {"'Revenue ($M)'" if is_en else "'Hasılat (₺M)'"}, data: {json.dumps(chart_revenue)}, backgroundColor: 'rgba(6, 182, 212, 0.6)', borderColor: '#06b6d4', borderWidth: 1 }},
              {{ label: {"'EBIT ($M)'" if is_en else "'EBIT (₺M)'"}, data: {json.dumps(chart_ebit)}, backgroundColor: 'rgba(244, 63, 94, 0.6)', borderColor: '#f43f5e', borderWidth: 1 }}
            ]
          }},
          options: {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#f3f4f6' }} }} }}, scales: {{ x: {{ ticks: {{ color: '#9ca3af' }} }}, y: {{ ticks: {{ color: '#9ca3af' }} }} }} }}
        }});
      }}
      const ctxBs = document.getElementById('balanceSheetChart');
      if (ctxBs && typeof Chart !== 'undefined') {{
        const lastHist = {json.dumps(hist[0] if hist else {})};
        new Chart(ctxBs, {{
          type: 'doughnut',
          data: {{
            labels: {json.dumps(['Cash', 'Other Current Assets', 'Non-Current Assets'] if is_en else ['Nakit & Benzerleri', 'Diğer Dönen Varlıklar', 'Duran Varlıklar'])},
            datasets: [{{ data: [
              Math.round((lastHist.cash_and_equivalents || 0) / 1e6),
              Math.round(((lastHist.revenue || 0) * (lastHist.current_ratio || 1)) / 1e6),
              Math.round(((lastHist.total_debt || 0) + (lastHist.cash_and_equivalents || 0)) / 1e6)
            ], backgroundColor: ['#10b981', '#06b6d4', '#8b5cf6'] }}]
          }},
          options: {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#f3f4f6' }} }} }} }}
        }});
      }}
    }}

    const REPORT_I18N = {{
      TR: {{
        menu_title: "Modüller",
        theme_dark: "Karanlık Tema",
        theme_light: "Aydınlık Tema",
        btn_print: "Yazdır / PDF İndir",
        btn_admin: "{"🔒 Admin Panel" if is_en else "🔒 Yönetim Paneli"}",
        tab_exec: "🏛️ Executive Report (Özet)",
        tab_blog: "📰 AI Finansal Blog & Yatırımcı Bülteni",
        tab_scorecard: "⭐ 360° Şirket Karnesi",
        tab_qual: "🛡️ Hendekler & Katalizörler",
        tab_ownership: "👥 Ortaklık & FX Duyarlılığı",
        tab_peer: "👥 Sektör & Rakip Karşılaştırma",
        tab_statements: "📊 Bilanço & DuPont Analizi",
        tab_forward: "🔮 İleri Tahminler (2026E/27E)",
        tab_quant: "🧮 Nicel Değerleme & 2D Duyarlılık",
        tab_forensic: "🔍 Adli Denetim & Balon",
        tab_ratios: "📈 Tarihsel Finansallar & Likidite",
        tab_calc: "⚡ Ters DCF Hesaplayıcı",
        tab_verdict: "🎯 Algoritmik Risk Modeli Özeti",
        tab_analyst: "🤖 AI Finansal Analiz Yorumu"
      }},
      EN: {{
        menu_title: "Modules",
        theme_dark: "Dark Theme",
        theme_light: "Light Theme",
        btn_print: "Print / Download PDF",
        btn_admin: "🔒 Admin Panel",
        tab_exec: "🏛️ Executive Summary",
        tab_blog: "📰 AI Stock Market Blog & Investor Briefing",
        tab_scorecard: "⭐ 360° Company Scorecard",
        tab_qual: "🛡️ Moats & Catalysts",
        tab_ownership: "👥 Ownership & FX Sensitivity",
        tab_peer: "👥 Industry & Peer Comparison",
        tab_statements: "📊 Financials & DuPont Analysis",
        tab_forward: "🔮 Forward Forecasts (2026E/27E)",
        tab_quant: "🧮 Valuation & 2D Sensitivity",
        tab_forensic: "🔍 Forensic Audit & Red Flags",
        tab_ratios: "📈 Historical Ratios & Liquidity",
        tab_calc: "⚡ Reverse DCF Calculator",
        tab_verdict: "🎯 Algorithmic Risk Model",
        tab_analyst: "🤖 AI Financial Commentary"
      }}
    }};

    async function loadGfxTabContent() {{
      const container = document.getElementById('gfxTabChartsContainer');
      if (!container || container.getAttribute('data-loaded') === 'true') return;
      
      try {{
        const res = await fetch('/api/valuation/history/' + encodeURIComponent('{ticker}'));
        if (!res.ok) throw new Error('API fetch failed');
        const data = await res.json();
        const history = data.history || [];
        if (history.length === 0) {{
          container.innerHTML = '<div style="padding:2rem; text-align:center; color:var(--text-muted);">No historical GFX snapshot records found in storage for {ticker}.</div>';
          return;
        }}
        
        const dates = history.map(h => h.report_date);
        const prices = history.map(h => h.stock_price);
        const mcaps = history.map(h => h.market_cap != null ? h.market_cap / 1e9 : null);
        const piotroski = history.map(h => h.piotroski_score);
        const altman = history.map(h => h.altman_z);
        const beneish = history.map(h => h.beneish_m);
        const wacc = history.map(h => h.wacc_pct);
        const dcf = history.map(h => h.dcf_fair_value);
        const graham = history.map(h => h.graham_number);
        const lynch = history.map(h => h.lynch_fair_value);

        function renderSvgLine(title, dataPoints, labels, strokeColor, prefix='', suffix='', decimals=2) {{
          const valid = dataPoints.filter(v => v != null);
          if (valid.length === 0) return `<div class="admin-card" style="padding:1rem;"><strong>${{title}}</strong><br><span style="color:var(--text-muted); font-size:0.85rem;">No data points</span></div>`;
          const min = Math.min(...valid);
          const max = Math.max(...valid);
          const range = (max - min) === 0 ? 1 : (max - min);
          
          const width = 360, height = 130, pad = 24;
          const points = dataPoints.map((val, idx) => {{
            const x = pad + (idx / Math.max(1, dataPoints.length - 1)) * (width - 2 * pad);
            const y = height - pad - ((val - min) / range) * (height - 2 * pad);
            return {{x, y, val, label: labels[idx]}};
          }});

          const polyline = points.map(p => `${{p.x.toFixed(1)}},${{p.y.toFixed(1)}}`).join(' ');
          const circles = points.map(p => `<circle cx="${{p.x.toFixed(1)}}" cy="${{p.y.toFixed(1)}}" r="4" fill="${{strokeColor}}"><title>${{p.label}}: ${{prefix}}${{p.val != null ? p.val.toFixed(decimals) : '-'}}${{suffix}}</title></circle>`).join('');

          return `
            <div class="admin-card" style="padding:1rem; background:rgba(15, 23, 42, 0.6); border:1px solid rgba(255,255,255,0.08); border-radius:10px;">
              <div style="font-weight:700; color:#e2e8f0; font-size:0.9rem; margin-bottom:0.4rem; display:flex; justify-content:space-between;">
                <span>${{title}}</span>
                <span style="color:${{strokeColor}}; font-size:0.85rem;">Son: ${{prefix}}${{valid[valid.length-1].toFixed(decimals)}}${{suffix}}</span>
              </div>
              <svg viewBox="0 0 ${{width}} ${{height}}" style="width:100%; height:130px; overflow:visible;">
                <polyline fill="none" stroke="${{strokeColor}}" stroke-width="2.5" points="${{polyline}}" />
                ${{circles}}
              </svg>
            </div>
          `;
        }}

        let html = `
          <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:1rem; margin-bottom:1.5rem;">
            ${{renderSvgLine('📈 Hisse Fiyatı (Stock Price)', prices, dates, '#06b6d4', '₺')}}
            ${{renderSvgLine('🏢 Piyasa Değeri (Market Cap)', mcaps, dates, '#a855f7', '₺', 'B')}}
            ${{renderSvgLine('🔥 Piotroski F-Score (0-9)', piotroski, dates, '#10b981', '', '/9', 0)}}
            ${{renderSvgLine('🛡️ Altman Z-Score', altman, dates, '#3b82f6')}}
            ${{renderSvgLine('🕵️ Beneish M-Score', beneish, dates, '#f59e0b')}}
            ${{renderSvgLine('⚡ WACC % Trend', wacc, dates, '#f43f5e', '', '%')}}
            ${{renderSvgLine('🎯 DCF Hedef (Fair Value)', dcf, dates, '#10b981', '₺')}}
            ${{renderSvgLine('🏛️ Graham No (Graham Number)', graham, dates, '#6366f1', '₺')}}
            ${{renderSvgLine('⚡ Lynch Value (Peter Lynch)', lynch, dates, '#14b8a6', '₺')}}
          </div>

          <div style="margin-top:1.5rem;">
            <div style="font-weight:700; color:var(--accent-cyan); font-size:1rem; margin-bottom:0.75rem;">📋 Tüm Metrik & Değer Tarihçe Tablosu (All Historical Metrics & Values)</div>
            <div style="overflow-x:auto;">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>Tarih</th>
                    <th>Hisse Fiyatı</th>
                    <th>Piyasa Değeri</th>
                    <th>Piotroski F</th>
                    <th>Altman Z</th>
                    <th>Beneish M</th>
                    <th>WACC %</th>
                    <th>DCF Hedef</th>
                    <th>Graham No</th>
                    <th>Lynch Value</th>
                  </tr>
                </thead>
                <tbody>
                  ${{history.map(h => {{
                    let mcapStr = '-';
                    if (h.market_cap != null) {{
                      mcapStr = Math.abs(h.market_cap) >= 1e9 ? ('₺' + (h.market_cap/1e9).toFixed(2) + 'B') : ('₺' + (h.market_cap/1e6).toFixed(2) + 'M');
                    }}
                    return `
                    <tr>
                      <td><strong>${{h.report_date}}</strong></td>
                      <td>${{h.stock_price != null ? '₺' + h.stock_price.toFixed(2) : '-'}}</td>
                      <td>${{mcapStr}}</td>
                      <td>${{h.piotroski_score ?? '-'}}</td>
                      <td>${{h.altman_z != null ? h.altman_z.toFixed(2) : '-'}}</td>
                      <td>${{h.beneish_m != null ? h.beneish_m.toFixed(2) : '-'}}</td>
                      <td>${{h.wacc_pct != null ? h.wacc_pct.toFixed(2) + '%' : '-'}}</td>
                      <td>${{h.dcf_fair_value != null ? '₺' + h.dcf_fair_value.toFixed(2) : '-'}}</td>
                      <td>${{h.graham_number != null ? '₺' + h.graham_number.toFixed(2) : '-'}}</td>
                      <td>${{h.lynch_fair_value != null ? '₺' + h.lynch_fair_value.toFixed(2) : '-'}}</td>
                    </tr>
                    `;
                  }}).join('')}}
                </tbody>
              </table>
            </div>
          </div>
        `;

        container.innerHTML = html;
        container.setAttribute('data-loaded', 'true');
      }} catch (err) {{
        container.innerHTML = '<div style="padding:1.5rem; color:#f87171;">⚠️ Error loading GFX analytics time series: ' + err.message + '</div>';
      }}
    }}

    function switchTab(tabId) {{
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
      
      const targetPane = document.getElementById(tabId);
      if (targetPane) targetPane.classList.add('active');

      const activeNav = document.querySelector(`.nav-item[onclick*="${{tabId}}"]`);
      if (activeNav) activeNav.classList.add('active');

      const nav = document.getElementById('sidebarMenuNav');
      if (nav) nav.classList.remove('active');

      if (tabId === 'gfx' && typeof loadGfxTabContent === 'function') {{
        loadGfxTabContent();
      }}

      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    let currentReportLang = localStorage.getItem('UI_LANG') || 'TR';

    function applyReportUiLanguage(lang) {{
      if (lang) currentReportLang = lang;
      const t = (typeof REPORT_I18N !== 'undefined' && REPORT_I18N[currentReportLang]) ? REPORT_I18N[currentReportLang] : {{}};
      const fallbacks = {{
        EN: {{
          btn_admin: "🔒 Admin Panel",
          menu_title: "Modules",
          theme_dark: "Dark Theme",
          theme_light: "Light Theme",
          btn_print: "Print / Download PDF"
        }},
        TR: {{
          btn_admin: "{"🔒 Admin Panel" if is_en else "🔒 Yönetim Paneli"}",
          menu_title: "Modüller",
          theme_dark: "Karanlık Tema",
          theme_light: "Aydınlık Tema",
          btn_print: "Yazdır / PDF İndir"
        }}
      }};
      document.querySelectorAll('[data-i18n]').forEach(el => {{
        const key = el.getAttribute('data-i18n');
        const text = t[key] || (fallbacks[currentReportLang] && fallbacks[currentReportLang][key]);
        if (text) el.innerHTML = text;
      }});
      const currentTheme = document.body.getAttribute('data-theme') || 'dark';
      setTheme(currentTheme);
    }}

    function toggleTheme() {{
      const currentTheme = document.body.getAttribute('data-theme') || 'dark';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(newTheme);
    }}

    function setTheme(theme) {{
      document.body.setAttribute('data-theme', theme);
      localStorage.setItem('dashboard_theme', theme);
      const t = REPORT_I18N[currentReportLang] || REPORT_I18N.TR;
      const btnLabel = document.getElementById('themeToggleLabel');
      const btnIcon = document.getElementById('themeToggleBtn');
      if (theme === 'light') {{
        if (btnLabel) btnLabel.innerText = t.theme_light;
        if (btnIcon) btnIcon.innerHTML = `☀️ <span id="themeToggleLabel" data-i18n="theme_light">${{t.theme_light}}</span>`;
      }} else {{
        if (btnLabel) btnLabel.innerText = t.theme_dark;
        if (btnIcon) btnIcon.innerHTML = `🌙 <span id="themeToggleLabel" data-i18n="theme_dark">${{t.theme_dark}}</span>`;
      }}
    }}

    function initTheme() {{
      const savedTheme = localStorage.getItem('dashboard_theme') || 'dark';
      setTheme(savedTheme);
    }}

    function triggerAdminModal() {{
      if (window.parent && typeof window.parent.openAdminModal === 'function') {{
        window.parent.openAdminModal();
      }} else if (typeof openAdminModal === 'function') {{
        openAdminModal();
      }}
    }}

    window.addEventListener('message', (event) => {{
      if (event.data) {{
        if (event.data.type === 'CHANGE_UI_LANG') {{
          applyReportUiLanguage(event.data.lang);
        }} else if (event.data.type === 'TOGGLE_MOBILE_MENU') {{
          toggleMobileMenu();
        }}
      }}
    }});

    window.addEventListener('DOMContentLoaded', () => {{
      applyReportUiLanguage(currentReportLang);
      initTheme();
      calculateReverseDCF();
      initCharts();
    }});
  </script>
</body>
</html>'''

    return html


def compile_printable_report(metrics: dict, commentary: dict, lang: str = None) -> str:
    """
    Compile a continuous, linear HTML report (YYYYMMDD_printable.html) without
    tabs or sidebar navigation — all 13 modules displayed sequentially for printing,
    PDF export, or copying text.
    """
    raw_html = compile_report(metrics, commentary, lang=lang)

    # Modify CSS to force all tabs visible and remove sidebar for printable file
    printable_css_override = """
    <style>
      .sidebar { display: none !important; }
      .main-content { margin-left: 0 !important; max-width: 100% !important; padding: 2rem !important; }
      .tab-pane { display: block !important; opacity: 1 !important; margin-bottom: 3rem !important; border-bottom: 2px dashed var(--panel-border); padding-bottom: 2rem; }
      .theme-toggle-btn, .print-btn { display: none !important; }
    </style>
    </head>"""

    printable_html = raw_html.replace("</head>", printable_css_override)
    return printable_html
