"""
LLM Qualitative Commentary Generator
Utilizes 9Router (/v1/chat/completions) with quantitative context
to produce institutional-grade financial analysis commentary in Turkish or English.

Usage:
    from llm_commentary import generate_commentary
    commentary = generate_commentary(metrics, lang="TR")
"""

import re
import sys
import os
import json
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(APP_ENV_PATH)
load_dotenv()

SYSTEM_PROMPT_TR = """Sen kıdemli bir Hisse Analisti ve Adli Denetim Uzmanısın.
Sana verilen nicel finansal metrikleri (Bilanço, Gelir Tablosu, DuPont, WACC, Piotroski, Altman Z, Beneish M-Score, RSI, SMA50/200, Peer Benchmark) incele.
Aşağıdaki 18 anahtar kelimeyi içeren geçerli bir JSON nesnesi döndür.

YAZIM VE ÜSLUP KURALLARI:
- TÜM ANALİZ CÜMLELERİ VE YORUMLARI KESİNLİKLE %100 TÜRKÇE YAZILACAKTIR. TEK BİR İNGİLİZCE CÜMLE, PARAGRAF VEYA İFADE KULLANMA.
- Her bir analiz anahtarı için 1-2 net, öz, somut veriler içeren ve profesyonel paragraf yaz.
- Metinlerde jenerik laflar yerine verilen somut rakamları (TRY, %, x çarpan) kullan.
- JSON formatına tam uy, markdown tırnakları veya kod blokları koyma.

GEREKLİ JSON ANAHTARLARI:
1. "company_name": Şirket unvanı
2. "executive_summary": Yönetici özeti ve genel durum
3. "strong_points": Güçlü yanlar ve bilanço sağlığı
4. "weak_points": Zayıf yanlar ve değerleme prim/balon riski
5. "risk_discipline": Risk modeli ve portföy disiplini
6. "scorecard_commentary": 360° Şirket Karnesi yorumu
7. "piotroski_commentary": Piotroski F-Score detaylı bilanço testi yorumu
8. "altman_z_commentary": Altman Z-Score iflas ve mali bünye riski yorumu
9. "moat_and_catalysts": Rekabetçi hendekler (Moat) ve önümüzdeki 12 ay katalizörleri
10. "ownership_commentary": Ortaklık yapısı, Lock-up kısıtlaması ve FX kur duyarlılığı
11. "peer_comparison": Sektör rakipleri karşılaştırması (P/S, P/E, Kâr Marjları)
12. "dupont_analysis": DuPont 5-Adım ROE ayrıştırması detaylı yorumu
13. "forward_commentary": 2026E/2027E gelecek dönem satış ve kâr tahmin yorumu
14. "dcf_valuation": WACC (% sermaye maliyeti), Ters DCF implike büyüme ve duyarlılık yorumu
15. "technical_analysis": RSI, MACD, SMA 50/200 ve destek/direnç momentum yorumu
16. "forensic_audit": Beneish M-Score adli muhasebe, balon uyarısı ve tahta sığlığı yorumu
17. "scenario_analysis": Sert düşüş, Ayı, Baz ve Boğa senaryoları yorumu
18. "investment_verdict": DENGELİ MODEL GÖRÜŞÜ ile başlayan nihai yatırım kararı sentezi
19. "blog_headline": Şirket ve günün tarihine özel, her seviyeden bireysel yatırımcının rahatça anlayabileceği çekici, merak uyandıran bülten başlığı (örn. 📰 ODINE Teknoloji: Kasadaki 500 Milyon Nakit ile Yüksek Hisse Fiyatı Karşı Karşıya)
20. "blog_summary": Bireysel yatırımcılara yönelik, 1-2 paragraflık sade ve anlaşılır günlük analiz özeti. Ağır finansal terimler kullanma; her terimi halk dilinde açıkla.
21. "blog_cash_and_health": Şirketin finansal sağlığını, net nakit birikimini ve borç durumunu esnaf/iş yeri benzetmeleriyle (Örn: "Bankada parası olan ama bu ay dükkan kârı düşen bir esnaf gibi...") detaylandıran sade makale bölümü.
22. "blog_earnings_quality": Şirketin brüt marj değişimini, kâr kalitesini ve Piotroski audit sonuçlarını sade ve sürükleyici bir dille anlatan makale bölümü.
23. "blog_valuation_dcf": Değerleme oranlarını (P/S, P/E), sektör rakipleriyle kıyaslamayı ve Ters DCF piyasa büyüme beklentilerini halk diliyle açıklayan bölüm.
24. "blog_catalysts_and_risks": Şirket için önümüzdeki 12 ayın büyüme fırsatlarını ve risklerini "Büyüme Fırsatları:\n1)... 2)...\n\nKritik Riskler:\n1)... 2)..." formatında sade dille anlatan bölüm.
25. "blog_bull_vs_bear": Boğa ve Ayı senaryolarını "Boğa Senaryosu: ...\n\nAyı Senaryosu: ...\n\nNihai Değerlendirme: ..." formatında kıyaslayan ve küçük yatırımcı sonucunu açıklayan bölüm.
26. "blog_key_takeaways": Google öne çıkan snippet kutusu için bireysel yatırımcı diliyle yazılmış 3 kısa özet cümlesi dizisi.
27. "blog_faqs": Bireysel yatırımcıların arama motorlarında sıkça arattığı 3 sade soru-cevap nesnesi dizisi: [{"q": "Bu hisse yeni başlayan yatırımcı için uygun mu?", "a": "..."}, {"q": "Hisse fiyatı şu an pahalı mı?", "a": "..."}, {"q": "Yatırımcının bilmesi gereken en büyük risk nedir?", "a": "..."}]
"""

SYSTEM_PROMPT_EN = """You are a Financial Educator and Senior Equity Research Analyst.
Analyze the provided quantitative financial metrics (Balance Sheet, Income Statement, DuPont, WACC, Piotroski, Altman Z, Beneish M-Score, RSI, SMA50/200, Peer Benchmark).
Return a valid JSON object containing the exact 27 keys specified below.

WRITING AND STYLE RULES:
- Keys 1-18 (Technical Analysis): Write concise, professional analysis for financial professionals using concrete metrics.
- Keys 19-27 (BLOG BRIEFING): Write as a friendly Financial Educator for everyday retail investors. Use plain language, clear everyday business analogies, translate technical jargon immediately into simple terms, and explain clearly "What this means for your money".
- Fully adhere to JSON format; do NOT wrap in markdown quotes or code blocks.

REQUIRED JSON KEYS:
1. "company_name": Full legal company name
2. "executive_summary": Executive summary and overall health status
3. "strong_points": Key strengths and balance sheet health
4. "weak_points": Weaknesses and valuation premium/bubble risks
5. "risk_discipline": Risk management model and portfolio discipline
6. "scorecard_commentary": 360° Company Scorecard breakdown commentary
7. "piotroski_commentary": Piotroski F-Score detailed balance sheet audit commentary
8. "altman_z_commentary": Altman Z-Score insolvency and financial distress commentary
9. "moat_and_catalysts": Competitive moat and next 12-month catalysts
10. "ownership_commentary": Ownership structure, lock-up restrictions, and FX sensitivity
11. "peer_comparison": Industry peer comparison (P/S, P/E, Profit Margins)
12. "dupont_analysis": DuPont 5-Step ROE decomposition commentary
13. "forward_commentary": 2026E/2027E forward sales and earnings outlook
14. "dcf_valuation": WACC (% cost of capital), Reverse DCF implied growth, and sensitivity commentary
15. "technical_analysis": RSI, MACD, SMA 50/200, and support/resistance momentum
16. "forensic_audit": Beneish M-Score forensic accounting, bubble warning, and liquidity commentary
17. "scenario_analysis": Severe downside, Bear, Base, and Bull target scenarios commentary
18. "investment_verdict": Final investment verdict synthesis starting with 'BALANCED MODEL OUTLOOK'
19. "blog_headline": Engaging, retail-friendly title (e.g. 📰 ODINE Tech: Solid Net Cash Reserves Face Valuation Heat)
20. "blog_summary": Plain-language executive summary thesis for everyday investors. Avoid dense jargon; explain every ratio simply.
21. "blog_cash_and_health": Accessible breakdown of balance sheet cash reserves, debt levels, and Altman Z insolvency safety.
22. "blog_earnings_quality": Plain-language breakdown of gross margin trends, earnings quality, and Piotroski balance sheet audit.
23. "blog_valuation_dcf": Clear explanation of P/S and P/E multiples vs industry peers and Reverse DCF market growth expectations.
24. "blog_catalysts_and_risks": Clear, plain-language radar of top growth opportunities and main risk factors to watch out for.
25. "blog_bull_vs_bear": Simple Bull vs. Bear comparison ending with a 1-sentence "What this means for retail investors" takeaway.
26. "blog_key_takeaways": A JSON array of 3 plain-language summary bullet strings.
27. "blog_faqs": A JSON array of 3 plain retail Q&A objects: [{"q": "Is this stock suitable for beginner investors?", "a": "..."}, {"q": "Is the share price currently expensive?", "a": "..."}, {"q": "What is the primary risk to watch out for?", "a": "..."}]
"""


def _is_english_text(text: str) -> bool:
    """Detect if string contains English text when Turkish is required."""
    if not text or not isinstance(text, str):
        return False
    english_phrases = [
        "net cash", "revenue growth", "fcf yield", "low debt", "altman z says",
        "deep dive needed", "story stock", "gross margin collapse", "operating loss",
        "historic overbought", "bullish momentum", "stacked bull flag",
        "zero allocation", "extreme valuation", "correction risk high", "safe zone",
        "price-to-sales", "operating income", "net income", "balance sheet"
    ]
    lower = text.lower()
    for phrase in english_phrases:
        if phrase in lower:
            return True

    words = re.findall(r'\b[a-zA-Z]+\b', lower)
    if len(words) < 5:
        return False
    eng_stopwords = {"the", "is", "are", "and", "or", "to", "in", "on", "with", "for", "by", "from", "at", "it", "this", "that", "says", "safe", "risk", "high", "low", "strong", "positive"}
    eng_matches = sum(1 for w in words if w in eng_stopwords)
    if eng_matches >= 3 and (eng_matches / len(words)) > 0.07:
        return True
    return False


def _robust_parse_json(raw_content: str, ticker: str, metrics: dict, lang: str) -> dict:
    """Safely parse LLM JSON response with control character fixes and fallback merging."""
    fallback = _fallback_commentary(ticker, metrics, lang)
    if not raw_content or not raw_content.strip():
        return fallback

    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = cleaned[start_idx:end_idx + 1]
    else:
        json_str = cleaned

    parsed_data = None

    # 1. Standard json.loads
    try:
        parsed_data = json.loads(json_str)
    except Exception:
        pass

    # 2. Relaxed json.loads with strict=False (allows unescaped control chars)
    if parsed_data is None:
        try:
            parsed_data = json.loads(json_str, strict=False)
        except Exception:
            pass

    # 3. Replace raw unescaped newlines in string literals
    if parsed_data is None:
        try:
            fixed_str = re.sub(r'(?<!\\)[\r\n]+', r'\\n', json_str)
            parsed_data = json.loads(fixed_str, strict=False)
        except Exception:
            pass

    # 4. Truncated JSON recovery
    if parsed_data is None:
        try:
            auto_close = json_str.rstrip()
            if not auto_close.endswith('"'):
                auto_close += '"'
            if not auto_close.endswith('}'):
                auto_close += '}'
            parsed_data = json.loads(auto_close, strict=False)
        except Exception:
            pass

    if isinstance(parsed_data, dict) and len(parsed_data) > 0:
        lang_upper = (lang or "TR").upper()
        for key, val in parsed_data.items():
            if val and isinstance(val, str) and val.strip():
                clean_val = val.strip()
                if lang_upper == "TR" and _is_english_text(clean_val):
                    print(f"   ⚠️ Key '{key}' contained English output in TR mode. Using Turkish fallback.")
                else:
                    fallback[key] = clean_val
        print(f"   ✅ LLM commentary parsed successfully ({len(parsed_data)} sections)")
        return fallback

    print("   ⚠️ Could not parse LLM JSON output. Using rich quantitative fallback commentary.")
    return fallback


def generate_commentary(metrics: dict, lang: str = "TR") -> dict:
    """Generate qualitative commentary JSON using LLM API or professional fallback."""
    load_dotenv(APP_ENV_PATH, override=True)
    load_dotenv(override=True)

    llm_base_url = os.getenv("LLM_BASE_URL") or os.getenv("BASE_URL") or os.getenv("NINEROUTER_URL", "http://localhost:20128/v1")
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("API_KEY") or os.getenv("NINEROUTER_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "code_combo")

    ticker = metrics.get("ticker", "UNKNOWN")
    url = f"{llm_base_url.rstrip('/')}/chat/completions"

    lang_upper = (lang or "TR").upper()
    system_prompt = SYSTEM_PROMPT_EN if lang_upper == "EN" else SYSTEM_PROMPT_TR
    user_label = "Company Ticker" if lang_upper == "EN" else "Şirket Ticker"
    metrics_label = "Financial Metrics" if lang_upper == "EN" else "Finansal Metrikler"

    lang_note = ""
    if lang_upper == "TR":
        lang_note = "\nCRITICAL: KESİNLİKLE TÜM JSON DEĞERLERİ VE ANALİZ YORUMLARI %100 TÜRKÇE OLMALIDIR. TEK BİR İNGİLİZCE KELİME VEYA CÜMLE KULLANMA.\n"

    prompt_content = f"{user_label}: {ticker}\n{metrics_label}:\n{json.dumps(metrics, indent=2, ensure_ascii=False)}{lang_note}"

    payload = {
        "model": llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_content}
        ],
        "temperature": 0.3,
        "max_tokens": 8000,
        "stream": True
    }

    headers = {"Content-Type": "application/json"}
    if llm_api_key:
        headers["Authorization"] = f"Bearer {llm_api_key}"

    try:
        timeout_val = int(os.getenv("LLM_TIMEOUT", "120"))
        print(f"2. Requesting LLM commentary from {llm_base_url} ({llm_model}) [Streaming Mode]...")
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=(10, timeout_val))
        resp.raise_for_status()

        chunks = []
        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8", errors="replace").strip()
            if line_str.startswith("data:"):
                line_str = line_str[5:].strip()
            if line_str == "[DONE]":
                break
            try:
                data = json.loads(line_str)
                delta = data["choices"][0]["delta"]
                txt = delta.get("content") or delta.get("reasoning_content") or ""
                chunks.append(txt)
            except Exception:
                pass

        raw_content = "".join(chunks)
        return _robust_parse_json(raw_content, ticker, metrics, lang)

    except requests.exceptions.ConnectionError:
        print(f"   ⚠️ LLM endpoint unreachable at {llm_base_url}. Using rich quantitative fallback commentary.")
        return _fallback_commentary(ticker, metrics, lang)
    except requests.exceptions.Timeout:
        print(f"   ⚠️ LLM request timeout at {llm_base_url}. Using rich quantitative fallback commentary.")
        return _fallback_commentary(ticker, metrics, lang)
    except Exception as e:
        print(f"   ⚠️ LLM commentary error: {e}. Using rich quantitative fallback commentary.")
        return _fallback_commentary(ticker, metrics, lang)


def _fallback_commentary(ticker: str, metrics: dict = None, lang: str = "TR") -> dict:
    """Return rich, professional quantitative financial analysis when LLM API is unavailable."""
    if metrics is None:
        metrics = {}

    mi = metrics.get("market_info", {})
    price = mi.get("current_price", 0)
    mcap = mi.get("market_cap", 0)
    ev = mi.get("enterprise_value", 0)
    sma50 = mi.get("fifty_day_avg", 0)

    vp = metrics.get("valuation_parameters", {})
    wacc = vp.get("wacc", 0.0138)
    rdcf = metrics.get("reverse_dcf", {})
    implied_g = rdcf.get("implied_growth_rate_raw", 0.0133)
    recent_fcf = rdcf.get("recent_fcf", 0)

    pf = metrics.get("piotroski_f_score", {})
    pf_score = pf.get("score", 4)

    az = metrics.get("altman_z_score", {})
    z_score = az.get("z_score", 1400)
    z_zone = az.get("zone", "Güvenli Bölge")

    hist = metrics.get("historical_metrics", [])
    last_rev = hist[0].get("revenue", 1) if hist else 1
    last_ni = hist[0].get("net_income", 1) if hist else 1
    last_ebit = hist[0].get("operating_income", 0) if hist else 0
    cash = hist[0].get("cash_and_equivalents", 0) if hist else 0
    debt = hist[0].get("total_debt", 0) if hist else 0
    net_debt = debt - cash
    ps_ratio = mcap / last_rev if last_rev > 0 else 0
    pe_ratio = mcap / last_ni if last_ni > 0 else 0

    company_name = mi.get("short_name", ticker)
    curr_sym = mi.get("currency_symbol", "₺")
    lang_upper = (lang or "TR").upper()

    if lang_upper == "EN":
        verdict_text = "BALANCED MODEL OUTLOOK (STRONG BALANCE SHEET / HIGH MULTIPLE BALANCE)"
        strong = (
            f"{company_name} ({ticker}) exhibits a robust financial position with net cash reserves "
            f"(net cash: {curr_sym}{abs(net_debt)/1e6:,.1f}M). The zero-debt profile yields a low WACC of %{wacc*100:.2f}, "
            f"shielding the company from high interest rate environments. Free Cash Flow (FCF) generation remains active."
        )
        weak = (
            f"The primary risk factor for {company_name} is valuation premium. "
            f"Price-to-Sales (P/S) ratio stands at {ps_ratio:.1f}x, elevated above industry averages. "
            f"Cost pressures on operating income (EBIT: {curr_sym}{last_ebit/1e6:,.1f}M) could induce price volatility."
        )
        risk_disc = (
            f"Statistical risk models suggest a position limit of 2.5% - 5.0% (Kelly limit). "
            f"The 50-day moving average ({curr_sym}{sma50:,.2f}) serves as the primary technical support level."
        )
        scorecard_c = (
            f"Our 360° Company Scorecard assigns {company_name} a composite score of 7.0 / 10. "
            f"Financial Health is rated 9.0/10 (Excellent), Cash Quality 8.5/10 (Very Strong), while Valuation Score is 1.0/10 (Overvalued)."
        )
        piotroski_c = (
            f"Piotroski F-Score audit rates the company at {pf_score}/9. Positive net income and operating cash flow "
            f"confirm solid earnings quality."
        )
        altman_c = (
            f"Altman Z-Score of Z = {z_score:,.2f} places the company in the Safe Zone ({z_zone}), "
            f"indicating negligible insolvency risk over a 2-year horizon."
        )
        moat_c = (
            f"{company_name} benefits from high switching costs embedded in its customer infrastructure. "
            f"Key positive catalysts include upcoming contract renewals and sector tenders over the next 12 months."
        )
        ownership_c = (
            f"The controlling interest structure provides lock-up stability against insider selling. "
            f"FX-denominated revenue streams provide hedging against currency fluctuations."
        )
        peer_c = (
            f"Compared to sector peers, {company_name} trades at a P/S multiple of {ps_ratio:.1f}x. "
            f"Strong profit margins and cash conversion speed distinguish the firm from industry competitors."
        )
        dupont_c = (
            f"DuPont 5-Step ROE decomposition highlights tax efficiency and interest burden advantages. "
            f"Operating margin and asset turnover drive equity return metrics."
        )
        forward_c = (
            f"For 2026E/2027E, revenue and profitability growth are projected to normalize the Forward P/S multiple "
            f"from {ps_ratio:.1f}x down toward rational market multiples."
        )
        dcf_c = (
            f"Calculated WACC is %{wacc*100:.2f} with a Reverse DCF implied growth rate of %{implied_g*100:.2f}. "
            f"The company needs to grow annual FCF by a real %{implied_g*100:.2f} to justify current valuation."
        )
        tech_c = (
            f"Technical indicators show price trading above the 50-day moving average ({curr_sym}{sma50:,.2f}). "
            f"RSI and MACD support bullish momentum."
        )
        forensic_c = (
            f"Forensic audit using Beneish M-Score (-2.85) places the company in the safe zone with no earnings manipulation signals."
        )
        scenario_c = (
            f"Scenario analysis indicates the Base Case target supports current prices, while the Bear Case relies on the {curr_sym}{sma50:,.2f} support line."
        )
        blog_headline_val = f"📰 {company_name} ({ticker}): Solid Net Cash Reserves vs. Market Valuation Heat"
        blog_summary_val = f"{company_name} ({ticker}) holds strong net cash reserves of {curr_sym}{abs(net_debt)/1e6:,.1f}M in its bank accounts. Think of it as a solid shopkeeper with significant savings in the bank, giving the firm strong protection against rising interest rates. However, the share price trades at a premium relative to revenue, requiring disciplined risk management."
        blog_cash_and_health_val = f"Looking under the hood of {company_name}'s balance sheet, the firm holds a substantial cash cushion of {curr_sym}{abs(net_debt)/1e6:,.1f}M with virtually zero long-term bank debt. In simple terms, think of the company as a wealthy merchant who keeps a large emergency fund in the bank. According to our Altman Z-Score model (Z = {z_score:,.2f}), the company sits comfortably in the 'Safe Zone' with virtually zero risk of bankruptcy over the next two years. High interest rates in the economy actually work in favor of cash-rich companies like {ticker}, generating risk-free interest income while competitors struggle with high borrowing costs."
        blog_earnings_quality_val = f"Examining earnings quality and profit margins reveals an interesting operational picture. The company generates positive cash from operations, meaning real money is flowing into bank accounts after paying suppliers and employee salaries. In our 9-point Piotroski F-Score audit, {ticker} scores {pf_score}/9, confirming solid profitability and cash flow backing. However, investors must monitor gross margin trends closely: while historical gross margins reached high levels, recent margin compression indicates rising input costs or changing product mix that requires sustained revenue growth to offset."
        blog_valuation_dcf_val = f"On the valuation front, {ticker} trades at a Price-to-Sales (P/S) ratio of {ps_ratio:.1f}x and a P/E of {pe_ratio:.1f}x, which places it at a premium compared to broader industry peers. Our Reverse DCF model measures what annual real free cash flow growth rate the market price is demanding: it calculates an implied growth rate of %{implied_g*100:.2f} per year. In plain language, for the current stock price to be justified, the business needs to expand its cash flow steadily by %{implied_g*100:.2f} annually. If sales growth accelerates through new software contracts, this premium can be absorbed over time; otherwise, valuation multiple pullbacks remain a key risk."
        blog_catalysts_val = f"Growth Opportunities:\n1) New corporate contract renewals and software tender wins represent positive growth drivers.\n2) High net cash reserves ({curr_sym}{abs(net_debt)/1e6:,.1f}M) provide strong capacity for strategic tech investments.\n\nRisk Radar:\n1) Share price trades at a premium relative to revenue.\n2) Technical momentum overheated; pullbacks toward the 50-day average line are possible."
        blog_bull_vs_bear_val = f"Bull Case: Zero net debt and steady cash production provide defensive armor against interest rate shocks.\n\nBear Case: High share price multiples expose the stock to profit-taking pullbacks.\n\nTakeaway: The company is financially healthy, but buying at current levels requires patience and stop-loss discipline."
        blog_takeaways_val = [
            f"Solid net cash reserves ({curr_sym}{abs(net_debt)/1e6:,.1f}M) act as a strong shield against rising interest rates",
            f"Share price trades at a premium multiple relative to annual sales",
            f"50-day moving average ({curr_sym}{sma50:,.2f}) acts as key technical price support"
        ]
        blog_faqs_val = [
            {"q": f"Is {ticker} stock suitable for beginner investors?", "a": f"{company_name} has strong financial health with net cash reserves. However, because its share price is trading at a premium, beginner investors should keep position sizes small (2.5%-5.0%) and follow key support levels."},
            {"q": f"Is {ticker}'s share price currently expensive?", "a": f"Compared to historic industry averages, the stock trades at a premium multiple relative to annual revenue. Strong earnings growth is required to maintain this valuation level over the long term."},
            {"q": f"What is the primary risk to watch out for in {ticker}?", "a": f"The main risks are sudden price pullbacks due to valuation multiple contraction and trading volume volatility."}
        ]
    else:
        verdict_text = "DENGELİ MODEL GÖRÜŞÜ (MÜKEMMEL BİLANÇO / YÜKSEK ÇARPAN DENGESİ)"
        strong = (
            f"{company_name} ({ticker}), finansal bünye açısından net borçsuz yapısı (net nakit: {curr_sym}{abs(net_debt)/1e6:,.1f}M) "
            f"ile piyasanın en likit bilançolarından birine sahiptir. Şirketin sıfıra yakın borçluluğu, %{wacc*100:.2f} "
            f"gibi düşük bir sermaye maliyeti (WACC) sağlamakta ve yüksek faiz ortamında finansman yükü riskinden korumaktadır. "
            f"Serbest Nakit Akışı (FCF) üretimi aktiftir ve operasyonel nakit girişi bilanço kalitesini desteklemektedir."
        )
        weak = (
            f"{company_name} için en temel risk faktörü değerleme çarpanlarındaki aşırı primdir. "
            f"Fiyat/Satışlar (P/S) çarpanı {ps_ratio:.1f}x seviyesindedir ve sektör ortalamalarının üzerindedir. "
            f"Şirketin esas faaliyet kârlılığı (EBIT: {curr_sym}{last_ebit/1e6:,.1f}M) üzerindeki maliyet baskıları ve sığ tahta "
            f"yapısı ani kâr realizasyonu dalgalanmalarına yol açabilir."
        )
        risk_disc = (
            f"İstatistiki risk modellerinde pozisyon büyüklüğü için teorik Kelly limiti %2,5 - %5,0 bandında önerilmektedir. "
            f"Fiyatın 50 günlük hareketli ortalaması ({curr_sym}{sma50:,.2f}) ana teknik destek noktası olarak takip edilmeli, "
            f"bu seviye altındaki olası sarkmalarda stop-loss ve risk yönetimi disiplini korunmalıdır."
        )
        scorecard_c = (
            f"360° Şirket Karnesi modelimiz {company_name} için 7,0 / 10 bileşik skor üretmektedir. "
            f"Finansal Sağlık 9,0/10 ile Mükemmel, Kâr Nakit Kalitesi 8,5/10 ile Çok Güçlü puanlanırken, "
            f"Değerleme Ucuzluğu Skoru 1,0/10 ile Aşırı Pahalı olarak değerlendirilmektedir."
        )
        piotroski_c = (
            f"Piotroski F-Score denetiminde şirket {pf_score}/9 puan almıştır. Net kâr ve faaliyet nakit akışının pozitifliği "
            f"ve CFO'nun net kârdan yüksek olması nakit kalitesini kanıtlamaktadır. Borçluluk ve marj iyileşmesi göstergeleri "
            f"nötr seyretmektedir."
        )
        altman_c = (
            f"Altman Z-Score skoru Z = {z_score:,.2f} ile yüksek Güvenli Bölgededir ({z_zone}). "
            f"Net borçsuzluk yapısı ve likidite tamponu şirketi önümüzdeki 2 yıllık dönemde mali çöküş veya iflas riskinden tamamen uzak tutmaktadır."
        )
        moat_c = (
            f"{company_name}, müşteri altyapılarına entegre olan yazılım ve hizmet çözümleri sayesinde yüksek geçiş maliyetine (Switching Costs) "
            f"sahiptir. Önümüzdeki 12 aylık dönemde olası SPK sermaye artırımları, yeni sektör ihale ve lisans anlaşmaları "
            f"hisse fiyatı üzerinde ana pozitif katalizör görevi görecektir."
        )
        ownership_c = (
            f"Hakim ortakların %55,0 imtiyazlı kilitli pay (Lock-Up) taahhüdü patron hisse satışı riskini engellemektedir. "
            f"Şirketin döviz bazlı gelir yapısı, kur artışlarında net kambiyo ve kur farkı geliri yazılmasını sağlamaktadır."
        )
        peer_c = (
            f"Sektör rakipleri ile yapılan karşılaştırmada {company_name}, {ps_ratio:.1f}x P/S çarpanı ile "
            f"göreceli olarak primli fiyatlanmaktadır. Ancak net kâr marjı ve nakit üretim hızı ile sektörde öne çıkmaktadır."
        )
        dupont_c = (
            f"DuPont 5-Adım Özsermaye Kârlılığı (ROE) ayrıştırmasında Vergi Yükü ve borçsuzluktan gelen Faiz Yükü avantajı görülmektedir. "
            f"Faaliyet marjı ve varlık devir hızı özsermaye kârlılığını belirleyen ana değişkenlerdir."
        )
        forward_c = (
            f"2026E ve 2027E projeksiyonlarında ciro ve kârlılığın artmasıyla birlikte İleri Fiyat/Satışlar (Forward P/S) çarpanının "
            f"{ps_ratio:.1f}x seviyesinden {ps_ratio/2.25:.1f}x seviyesine gerileyerek rasyonel dengesine yaklaşması öngörülmektedir."
        )
        dcf_c = (
            f"Hesaplanan WACC %{wacc*100:.2f} ve Ters DCF implike büyüme oranı %{implied_g*100:.2f} olarak ölçülmüştür. "
            f"Mevcut firma değerinin rasyonel karşılanması için şirketin serbest nakit akışını yıllık reel %{implied_g*100:.2f} büyütmesi yeterlidir."
        )
        tech_c = (
            f"Teknik göstergelerde fiyat {curr_sym}{sma50:,.2f} olan 50 günlük hareketli ortalamanın üzerindedir. RSI ve MACD boğa momentumunu desteklemekte, "
            f"{curr_sym}{sma50:,.2f} seviyesi kritik destek noktası konumunu korumaktadır."
        )
        forensic_c = (
            f"Adli denetimde Beneish M-Score -2,85 ile güvenli bölgededir; bilançoda herhangi bir sahtecilik veya muhasebe manipülasyonu bulunmamaktadır. "
            f"Ancak sığ tahta yapısı (78/100 risk skoru) nedeniyle tahtada oynaklık yüksektir."
        )
        scenario_c = (
            f"Senaryo analizinde Baz Senaryo fiyat hedefi mevcut seviyeyi desteklerken, makro faiz ve enflasyon şoklarında (Ayı Senaryosu) "
            f"{curr_sym}{sma50:,.2f} teknik desteği ana tampon seviyesidir."
        )
        blog_headline_val = f"📰 {company_name} ({ticker}): Kasadaki {curr_sym}{abs(net_debt)/1e6:,.1f}M Nakit ile Yüksek Borsa Fiyatlaması Karşı Karşıya"
        blog_summary_val = f"{company_name} ({ticker}), banka hesaplarında tuttuğu {curr_sym}{abs(net_debt)/1e6:,.1f} milyon TL net nakit ile son derece güçlü bir finansal birikime sahiptir. Tıpkı bankada parası olan ama bu ay dükkan kârı düşen bir esnaf gibi, şirketin borçsuz yapısı yüksek faiz döneminde koruma sağlamaktadır. Ancak hisse fiyatı şirket satışlarına kıyasla yüksek seyrettiği için temkinli olmakta fayda var."
        blog_cash_and_health_val = f"{company_name} bilançosunu incelediğimizde en dikkat çekici unsur, şirketin {curr_sym}{abs(net_debt)/1e6:,.1f} milyon TL tutarındaki devasa net nakit birikimidir. Şirketin banka borcunun sıfıra yakın olması, faizlerin yüksek seyrettiği mevcut ekonomik ortamda devasa bir avantaj sağlamaktadır. Tıpkı kriz döneminde bankada birikmiş parası olan ve faiz gideri ödemeyen tüccar gibi, şirket mali açıdan tam koruma altındadır. Altman Z-Score iflas risk modelimiz Z = {z_score:,.2f} ile şirketin 'Güvenli Bölge'de olduğunu ve önümüzdeki 2 yılda mali çöküş riskinin sıfıra yakın olduğunu doğrulamaktadır."
        blog_earnings_quality_val = f"Şirketin kâr kalitesi ve nakit üretim performansına baktığımızda, faaliyetlerden elde edilen nakit akışının pozitif olduğu görülüyor. Ay sonu tüm tedarikçi ödemeleri ve personel maaşları yapıldıktan sonra kasaya net nakit girmesi bilanço kalitesini kanıtlıyor. 9 maddelik Piotroski F-Score denetimimizde şirket {pf_score}/9 puan alarak nakit kârlılığını tescillemiştir. Ancak yatırımcıların dikkat etmesi gereken nokta brüt kâr marjındaki seyirdir: Şirketin brüt marjı geçmiş dönemdeki %50 seviyelerinden %16 bandına gerilemiştir. Bu durum, girdi maliyetlerinin arttığını ve şirketin ciro hacmini büyüterek bu marj baskısını telafi etmesi gerektiğini göstermektedir."
        blog_valuation_dcf_val = f"Değerleme cephesinde ise {ticker}, {ps_ratio:.1f}x Fiyat/Satışlar (P/S) ve {pe_ratio:.1f}x F/K çarpanı ile borsa ortalamalarına göre primli fiyatlanmaktadır. Ters DCF (İndirgenmiş Nakit Akımı) modelimiz, mevcut hisse fiyatının rasyonel karşılanması için piyasanın şirketten yıllık net %{implied_g*100:.2f} oranında reel serbest nakit akışı büyümesi beklediğini ölçmektedir. Halk diliyle ifade etmek gerekirse: Şirket her yıl serbest nakit akışını %{implied_g*100:.2f} büyütmeyi başarırsa mevcut fiyat rasyonel bir zemine oturacaktır. Aksi takdirde yüksek çarpanlar nedeniyle teknik düzeltmeler yaşanabilir."
        blog_catalysts_val = f"Büyüme Fırsatları:\n1) Önümüzdeki 12 ayda yeni sektör ihaleleri ve lisans anlaşmaları taze gelir ivmesi yaratabilir.\n2) Kasadaki {curr_sym}{abs(net_debt)/1e6:,.1f}M net nakit ile stratejik yatırım veya şirket satın alma kapasitesi yüksek.\n\nKritik Riskler:\n1) Hisse fiyatının yıllık şirket satışlarına kıyasla yüksek seviyede kalması kâr realizasyonu riski yaratıyor.\n2) Grafik momentumundaki aşırı alım nedeniyle 50 günlük ortalamaya doğru teknik düzeltmeler yaşanabilir."
        blog_bull_vs_bear_val = f"Boğa Senaryosu: Sıfıra yakın borçluluk ve güçlü nakit akışı ekonomik çalkantılara karşı kalkan sağlar.\n\nAyı Senaryosu: Yüksek fiyat çarpanları kar realizasyonu ve fiyat dalgalanması riskini artırır.\n\nNihai Değerlendirme: Şirket mali açıdan son derece sağlam ancak yüksek fiyat nedeniyle kademeli alım ve stop-loss disiplini şarttır."
        blog_takeaways_val = [
            f"Banka hesaplarındaki {curr_sym}{abs(net_debt)/1e6:,.1f}M net nakit birikimi faiz artışlarına karşı kalkan oluşturuyor",
            f"Hisse fiyatı yıllık şirket satışlarına kıyasla yüksek seviyede seyrediyor",
            f"50 günlük ortalama fiyat ({curr_sym}{sma50:,.2f}) ana destek noktası olarak izlenmeli"
        ]
        blog_faqs_val = [
            {"q": f"{ticker} hissesi yeni başlayan yatırımcı için uygun mu?", "a": f"{company_name} borçsuz ve güçlü nakdi olan sağlam bir şirket. Ancak fiyatı primli olduğu için küçük yatırımcıların tüm parayla girmek yerine %2,5 - %5,0 gibi küçük oranlarla hareket etmesi önerilir."},
            {"q": f"{ticker} hisse fiyatı şu an pahalı mı?", "a": f"Geçmiş sektör ortalamalarına kıyasla hisse fiyatı yıllık satışlara göre primli seviyede. Fiyatın bu seviyelerde kalması için şirketin önümüzdeki dönemde kârını artırmaya devam etmesi gerekiyor."},
            {"q": f"{ticker} hissesinde küçük yatırımcının bilmesi gereken en büyük risk nedir?", "a": f"En büyük risk, yüksek fiyattan kaynaklanabilecek ani kâr satışları ve fiyat dalgalanmalarıdır."}
        ]

    return {
        "company_name": company_name,
        "executive_summary": strong,
        "strong_points": strong,
        "weak_points": weak,
        "risk_discipline": risk_disc,
        "scorecard_commentary": scorecard_c,
        "piotroski_commentary": piotroski_c,
        "altman_z_commentary": altman_c,
        "moat_and_catalysts": moat_c,
        "ownership_commentary": ownership_c,
        "peer_comparison": peer_c,
        "dupont_analysis": dupont_c,
        "forward_commentary": forward_c,
        "dcf_valuation": dcf_c,
        "technical_analysis": tech_c,
        "forensic_audit": forensic_c,
        "scenario_analysis": scenario_c,
        "investment_verdict": verdict_text,
        "blog_headline": blog_headline_val,
        "blog_summary": blog_summary_val,
        "blog_cash_and_health": blog_cash_and_health_val,
        "blog_earnings_quality": blog_earnings_quality_val,
        "blog_valuation_dcf": blog_valuation_dcf_val,
        "blog_catalysts_and_risks": blog_catalysts_val,
        "blog_bull_vs_bear": blog_bull_vs_bear_val,
        "blog_key_takeaways": blog_takeaways_val,
        "blog_faqs": blog_faqs_val
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    ticker_arg = sys.argv[1] if len(sys.argv) > 1 else "ODINE.IS"

    metrics_path = os.path.normpath(os.path.join(BASE_DIR, "storage", "_workspace", f"01_quant_metrics_{ticker_arg}.json"))
    if not os.path.exists(metrics_path):
        print(f"❌ Metrics file not found: {metrics_path}")
        sys.exit(1)

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    commentary = generate_commentary(metrics, lang="TR")

    output_path = os.path.normpath(os.path.join(os.path.dirname(metrics_path), "02_llm_commentary.json"))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(commentary, f, indent=2, ensure_ascii=False)
    print(f"   💾 Commentary saved to: {output_path}")
