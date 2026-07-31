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

SYSTEM_PROMPT_TR = """Sen deneyimli, sıcak ve samimi bir Finans Analistisin. Amacın, 18 yaşındaki yeni yatırımcıdan 70 yaşındaki emekliye kadar herkesin hiç finans eğitimi almadan rahatça okuyup anlayabileceği sohbet havasında bir hisse analiz bülteni yazmaktır.

Sana verilen nicel finansal metrikleri (Bilanço, Gelir Tablosu, DuPont, WACC, Piotroski, Altman Z, Beneish M-Score, RSI, SMA50/200, Peer Benchmark) incele.
Aşağıdaki 27 anahtar kelimeyi içeren geçerli bir JSON nesnesi döndür.

YAZIM VE ÜSLUP KURALLARI (TAMAMEN SADE & SAMİMİ DİL):
- TÜM ANALİZ CÜMLELERİ VE YORUMLARI KESİNLİKLE %100 TÜRKÇE YAZILACAKTIR. TEK BİR İNGİLİZCE CÜMLE VEYA SOĞUK TEKNİK İFADE KULLANMA.
- "Yapay Zekâ Kıdemli Analisti" veya "Quant modelimiz" gibi soğuk, robotik ve mekanik ifadeleri KESİNLİKLE KULLANMA. Bir dost gibi konuş.
- Ağır terimleri halk diline çevir:
  * Kasadaki Net Nakit / Borç → "Kasadaki Parası & Borç Durumu"
  * Altman Z-Score → "İflas Riski Testi (Borç Doktoru)"
  * Piotroski F-Score → "9 Maddelik Bilanço Güven Puanı"
  * Fiyat/Satışlar (P/S) Çarpanı → "Hisse Fiyat Etiketi (Satışa Göre Pahalı/Ucuz mu?)"
  * Ters DCF İmplike Büyüme → "Piyasanın Şirketten Beklediği Büyüme Hızı"
  * Beneish M-Score → "Muhasebe & Dürüstlük Denetimi"
- 19-27 ARASI BÜLTEN KEY'LERİNDE (BLOG BRIEFING):
  * "blog_headline": Sürükleyici ve merak uyandıran halk dili başlığı (Örn: 📰 ODINE Analizi: Şirketin Kasası Para Dolu Ama Fiyatı Biraz Pahalı mı?)
  * "blog_key_takeaways": 3 adet net ve anlaşılır özet maddesi. Her madde "Finansal Sağlık Mükemmel:", "Fiyat Etiketi Yüksek:", "Teknik Desteğe Dikkat:" gibi kalın başlıkla başlasın.
  * "blog_faqs": 3 adet soru-cevap nesnesi array'i. İLK SORU KESİNLİKLE: {"q": "❓ [TICKER] hissesine ben olsam şu an nasıl yaklaşırdım? (Yatırımcı Perspektifi)", "a": "Somut pozisyon büyüklüğü (%2,5-%5,0), 50 günlük ortalama koruma kalkanı ve kademeli alım tavsiyesi."}
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
19. "blog_headline": Şirket ve günün tarihine özel, her seviyeden bireysel yatırımcının rahatça anlayabileceği çekici bülten başlığı (örn. 📰 ODINE Analizi: Şirketin Kasası Para Dolu Ama Fiyatı Biraz Pahalı mı?)
20. "blog_summary": Bireysel yatırımcılara yönelik, 1-2 paragraflık sade ve anlaşılır günlük analiz özeti. Ağır finansal terimler kullanma; her terimi halk dilinde açıkla.
21. "blog_cash_and_health": Şirketin finansal sağlığını ve kasadaki nakit birikimini esnaf/iş yeri benzetmeleriyle anlatan sade makale bölümü.
22. "blog_earnings_quality": Şirketin kâr kalitesini ve 9 maddelik bilanço güven puanını (Piotroski) sade dille anlatan bölüm.
23. "blog_valuation_dcf": Hisse fiyatının pahalı mı ucuz mu olduğunu (P/S, P/E) ve piyasanın büyüme beklentilerini halk diliyle açıklayan bölüm.
24. "blog_catalysts_and_risks": Şirket için önümüzdeki 12 ayın büyüme fırsatlarını ve risklerini "Büyüme Fırsatları:\n1)... 2)...\n\nKritik Riskler:\n1)... 2)..." formatında sade dille anlatan bölüm.
25. "blog_bull_vs_bear": Boğa ve Ayı senaryolarını "Boğa Senaryosu: ...\n\nAyı Senaryosu: ...\n\nKüçük Yatırımcı İçin Tavsiye: ..." formatında kıyaslayan bölüm.
26. "blog_key_takeaways": Google öne çıkan snippet kutusu için bireysel yatırımcı diliyle yazılmış 3 kısa özet cümlesi dizisi (örn. ["Finansal Sağlık Mükemmel: ...", "Fiyat Etiketi Yüksek: ...", "Teknik Desteğe Dikkat: ..."]).
27. "blog_faqs": Bireysel yatırımcıların merak ettiği 3 sade soru-cevap nesnesi dizisi. İLK SORU KESİNLİKLE ŞU OLACAKTIR: [{"q": "❓ ODINE hissesine ben olsam şu an nasıl yaklaşırdım? (Yatırımcı Perspektifi)", "a": "Şirketin batma riski olmasa da fiyatı biraz pahalı. Tüm parayla girmek yerine %2,5 ile %5,0'lik küçük bir adımla alım yapar, 50 günlük ortalamayı koruma kalkanım yapardım."}, {"q": "❓ ODINE hissesi yeni başlayan biri için uygun mu?", "a": "..."}, {"q": "❓ ODINE hissesi şu an pahalı mı?", "a": "..."}]
"""

SYSTEM_PROMPT_EN = """You are an experienced, friendly Financial Analyst explaining stocks over coffee. Your goal is to write a warm, engaging equity research blog post that anyone from an 18-year-old beginner to a 70-year-old retiree can understand without a finance degree.

Analyze the provided quantitative financial metrics (Balance Sheet, Income Statement, DuPont, WACC, Piotroski, Altman Z, Beneish M-Score, RSI, SMA50/200, Peer Benchmark).
Return a valid JSON object containing the exact 27 keys specified below.

WRITING AND STYLE RULES (RETAIL INVESTOR FRIENDLY):
- Avoid cold, mechanical AI phrasing like "AI Senior Analyst" or "Our quantitative model". Write like a helpful knowledgeable friend.
- Translate technical jargon into everyday business analogies:
  * Cash reserves $\rightarrow$ "Emergency Savings Buffer"
  * Altman Z-Score $\rightarrow$ "Insolvency Risk Test / Debt Health Checkup"
  * Piotroski F-Score $\rightarrow$ "9-Point Balance Sheet Trust Score"
  * P/S Multiple $\rightarrow$ "Price Tag per Dollar of Sales"
  * Reverse DCF $\rightarrow$ "Market Growth Speedometer"
- For Keys 19-27 (BLOG BRIEFING):
  * "blog_headline": Catchy, plain-language title (e.g. 📰 ODINE Analysis: Solid Cash Cushion vs. High Price Tag)
  * "blog_key_takeaways": Array of 3 plain-language summary bullet strings starting with bold labels ("Financial Health Excellent:", "Valuation High:", "Key Support Level:").
  * "blog_faqs": Array of 3 Q&A objects. THE FIRST QUESTION MUST BE EXACTLY: {"q": "❓ How would I personally approach [TICKER] stock right now? (Investor Perspective)", "a": "Concrete advice on position sizing (2.5%-5.0%), key 50-day moving average support, and dollar-cost averaging."}
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
19. "blog_headline": Engaging, retail-friendly title (e.g. 📰 ODINE Analysis: Solid Cash Cushion vs. High Price Tag)
20. "blog_summary": Plain-language executive summary thesis for everyday investors. Avoid dense jargon; explain every ratio simply.
21. "blog_cash_and_health": Accessible breakdown of balance sheet cash reserves, debt levels, and Altman Z insolvency safety.
22. "blog_earnings_quality": Plain-language breakdown of gross margin trends, earnings quality, and Piotroski balance sheet audit.
23. "blog_valuation_dcf": Clear explanation of P/S and P/E multiples vs industry peers and Reverse DCF market growth expectations.
24. "blog_catalysts_and_risks": Clear, plain-language radar of top growth opportunities and main risk factors to watch out for.
25. "blog_bull_vs_bear": Simple Bull vs. Bear comparison ending with a 1-sentence "What this means for retail investors" takeaway.
26. "blog_key_takeaways": A JSON array of 3 plain-language summary bullet strings.
27. "blog_faqs": A JSON array of 3 plain retail Q&A objects. THE FIRST QUESTION MUST BE EXACTLY: [{"q": "❓ How would I personally approach this stock right now? (Investor Perspective)", "a": "Practical guidance covering position sizing (2.5%-5.0% Kelly limits), key 50-day moving average support, and valuation risk management in plain language."}, {"q": "❓ Is this stock suitable for beginner investors?", "a": "..."}, {"q": "❓ Is the share price currently expensive?", "a": "..."}]
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

def _sanitize_prompt_field(value: str) -> str:
    """Sanitize a user-controlled string before embedding in LLM prompts.
    Allows alphanumeric, Turkish characters, common punctuation, and whitespace.
    Strips anything that could be used for prompt injection."""
    if not value or not isinstance(value, str):
        return ""
    # Allow: letters (including Turkish İıÖöÜüŞşÇçĞğ), digits, spaces, dots, hyphens, ampersands, parentheses, commas
    return re.sub(r'[^\w\s.\-&()/,;:\'\"#%+₺€$£¥]', '', value, flags=re.UNICODE).strip()


def generate_commentary(metrics: dict, lang: str = "TR") -> dict:
    """Generate qualitative commentary JSON using LLM API or professional fallback."""
    load_dotenv(APP_ENV_PATH, override=True)
    load_dotenv(override=True)

    llm_base_url = os.getenv("LLM_BASE_URL") or os.getenv("BASE_URL") or os.getenv("NINEROUTER_URL", "http://localhost:20128/v1")
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("API_KEY") or os.getenv("NINEROUTER_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "code_combo")

    ticker = _sanitize_prompt_field(metrics.get("ticker", "UNKNOWN"))
    url = f"{llm_base_url.rstrip('/')}/chat/completions"

    # Sanitize user-controlled fields in metrics before embedding in prompt (VULN-007)
    sanitized_metrics = dict(metrics)
    if "name" in sanitized_metrics:
        sanitized_metrics["name"] = _sanitize_prompt_field(sanitized_metrics["name"])
    if "ticker" in sanitized_metrics:
        sanitized_metrics["ticker"] = _sanitize_prompt_field(sanitized_metrics["ticker"])

    lang_upper = (lang or "TR").upper()
    system_prompt = SYSTEM_PROMPT_EN if lang_upper == "EN" else SYSTEM_PROMPT_TR
    user_label = "Company Ticker" if lang_upper == "EN" else "Şirket Ticker"
    metrics_label = "Financial Metrics" if lang_upper == "EN" else "Finansal Metrikler"

    lang_note = ""
    if lang_upper == "TR":
        lang_note = "\nCRITICAL: KESİNLİKLE TÜM JSON DEĞERLERİ VE ANALİZ YORUMLARI %100 TÜRKÇE OLMALIDIR. TEK BİR İNGİLİZCE KELİME VEYA CÜMLE KULLANMA.\n"

    prompt_content = f"{user_label}: {ticker}\n{metrics_label}:\n{json.dumps(sanitized_metrics, indent=2, ensure_ascii=False)}{lang_note}"

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
    wacc = vp.get("wacc", 0.0)
    rdcf = metrics.get("reverse_dcf", {})
    implied_g = rdcf.get("implied_growth_rate_raw", 0.0)
    recent_fcf = rdcf.get("recent_fcf", 0)

    pf = metrics.get("piotroski_f_score", {})
    pf_score = pf.get("score", 0)

    az = metrics.get("altman_z_score", {})
    z_score = az.get("z_score", 0.0)
    z_zone = az.get("zone", "Normal")
    beneish_m = metrics.get("beneish_m_score", {})
    bm_score = beneish_m.get("m_score", -2.85) if isinstance(beneish_m, dict) else -2.85

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
    is_bank = metrics.get("is_bank_sector", False)

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
            f"Our 360° Company Scorecard assigns {company_name} a quantitative rating based on Piotroski ({pf_score}/9) "
            f"and Altman Z-Score (Z = {z_score:,.2f}, {z_zone}). Valuation P/S ratio is {ps_ratio:.1f}x."
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
            f"Forensic audit using Beneish M-Score ({bm_score:.2f}) evaluates earnings quality and accounting transparency."
        )
        scenario_c = (
            f"Scenario analysis indicates the Base Case target supports current prices, while the Bear Case relies on the {curr_sym}{sma50:,.2f} support line."
        )
        if is_bank:
            blog_headline_val = f"📰 {company_name} ({ticker}): Banking ROE & Book Value Valuation Analysis"
        elif net_debt < 0:
            blog_headline_val = f"📰 {company_name} ({ticker}): Solid Net Cash Reserves ({curr_sym}{abs(net_debt)/1e6:,.1f}M) vs. Valuation Multiples"
        elif net_debt > 0 and (debt / max(1, mcap)) > 0.4:
            blog_headline_val = f"📰 {company_name} ({ticker}): Financial Leverage Audit & Debt Structure Review"
        elif pf_score >= 7:
            blog_headline_val = f"📰 {company_name} ({ticker}): High Piotroski F-Score ({pf_score}/9) & Earnings Quality Audit"
        else:
            blog_headline_val = f"📰 {company_name} ({ticker}): 360° Financial Health & Valuation Audit"
        bm_score = beneish_m.get("m_score", -2.85) if isinstance(beneish_m, dict) else -2.85
        bm_safe = "Safe Zone" if bm_score < -1.78 else "Divergence Warning"

        if net_debt < 0:
            debt_desc_en = f"holds strong net cash reserves of {curr_sym}{abs(net_debt)/1e6:,.1f}M with zero net debt"
            debt_shield_en = f"Net cash reserves of {curr_sym}{abs(net_debt)/1e6:,.1f}M provide strong protection against high interest rate environments."
        else:
            debt_desc_en = f"operates with net debt of {curr_sym}{net_debt/1e6:,.1f}M"
            debt_shield_en = f"Total net debt of {curr_sym}{net_debt/1e6:,.1f}M requires continuous cash flow monitoring to maintain debt service coverage."

        blog_summary_val = f"{company_name} ({ticker}) {debt_desc_en}. According to our quantitative models, Piotroski F-Score stands at {pf_score}/9 and Altman Z-Score is at Z = {z_score:,.2f} ({z_zone}). Valuation metrics show a P/S ratio of {ps_ratio:.1f}x."
        blog_cash_and_health_val = f"Looking under the hood of {company_name}'s balance sheet, the firm {debt_desc_en}. According to our Altman Z-Score model (Z = {z_score:,.2f}), the company sits in the '{z_zone}' category. {debt_shield_en}"
        blog_earnings_quality_val = f"Examining earnings quality and profit margins reveals an operational picture backed by an overall Piotroski F-Score of {pf_score}/9. Beneish M-Score stands at {bm_score:.2f} ({bm_safe}). Investors should monitor operating cash flow backing and gross margin trends across upcoming earnings releases."
        blog_valuation_dcf_val = f"On the valuation front, {ticker} trades at a Price-to-Sales (P/S) ratio of {ps_ratio:.1f}x and a P/E of {pe_ratio:.1f}x. Our Reverse DCF model calculates an implied annual growth rate of %{implied_g*100:.2f} required to justify current market pricing given a WACC of %{wacc*100:.2f}."
        blog_catalysts_val = f"Growth Opportunities:\n1) Core business expansion and customer contract renewals.\n2) Capital efficiency and cash flow optimization.\n\nRisk Radar:\n1) Valuation multiple contraction sensitivity.\n2) Technical price support at the 50-day moving average ({curr_sym}{sma50:,.2f})."
        blog_bull_vs_bear_val = f"Bull Case: High Piotroski score ({pf_score}/9) and Z-Score ({z_score:,.2f}) provide financial health backing.\n\nBear Case: Valuation multiples ({ps_ratio:.1f}x P/S) demand sustained high earnings growth.\n\nTakeaway: Maintain disciplined position sizing and monitor key technical support levels."
        blog_takeaways_val = [
            f"Financial health backed by Altman Z-Score of Z = {z_score:,.2f} ({z_zone})",
            f"Piotroski F-Score stands at {pf_score}/9 with P/S multiple at {ps_ratio:.1f}x",
            f"50-day moving average ({curr_sym}{sma50:,.2f}) serves as primary technical support"
        ]
        blog_faqs_val = [
            {"q": f"How would I personally approach {ticker} right now? (Investor Perspective)", "a": f"If I were managing a portfolio for {company_name}, I would maintain disciplined position sizing within a conservative 2.5% to 5.0% allocation limit. With an Altman Z-Score of Z = {z_score:,.2f} ({z_zone}), the financial health checkup is solid, but the P/S ratio of {ps_ratio:.1f}x means we should closely watch the 50-day moving average ({curr_sym}{sma50:,.2f}) as our key safety net."},
            {"q": f"Is {ticker} stock suitable for beginner investors?", "a": f"{company_name} presents an Altman Z-Score of {z_score:,.2f} ({z_zone}). Beginner investors should consider conservative position sizing (2.5%-5.0%) and follow key support levels."},
            {"q": f"What is the primary risk to watch out for in {ticker}?", "a": f"The primary risks center on valuation multiple contraction and market price volatility around key moving averages."}
        ]
    else:
        verdict_text = "DENGELİ MODEL GÖRÜŞÜ (FİNANSAL SAĞLIK VE DEĞERLEME DENGESİ)"
        if net_debt < 0:
            debt_desc_tr = f"net borçsuz yapısı (kasadaki acil durum birikimi: {curr_sym}{abs(net_debt)/1e6:,.1f}M net nakit)"
            debt_shield_tr = f"Şirketin {curr_sym}{abs(net_debt)/1e6:,.1f}M tutarındaki kasadaki nakit birikimi yüksek faiz ortamında likidite tamponu sağlamaktadır."
        else:
            debt_desc_tr = f"net borçlu yapısı (net borç: {curr_sym}{net_debt/1e6:,.1f}M)"
            debt_shield_tr = f"Şirketin {curr_sym}{net_debt/1e6:,.1f}M tutarındaki net borç pozisyonu borç servis oranlarının yakından takibini gerektirmektedir."

        bm_score = beneish_m.get("m_score", -2.85) if isinstance(beneish_m, dict) else -2.85
        bm_safe_tr = "Güvenli Bölge" if bm_score < -1.78 else "Sapma İkazı"

        strong = (
            f"{company_name} ({ticker}), finansal bünye açısından {debt_desc_tr} "
            f"ile dikkat çekmektedir. %{wacc*100:.2f} "
            f"seviyesindeki sermaye maliyeti (WACC) ve Piotroski {pf_score}/9 skoru operasyonel yapıyı desteklemektedir."
        )
        weak = (
            f"{company_name} için temel risk faktörü değerleme seviyeleridir. "
            f"Fiyat/Satışlar (P/S) etiket fiyatı {ps_ratio:.1f}x seviyesindedir. "
            f"Esas faaliyet kârlılığı (EBIT: {curr_sym}{last_ebit/1e6:,.1f}M) üzerindeki maliyet seyri yakından izlenmelidir."
        )
        risk_disc = (
            f"İstatistiki risk modellerinde pozisyon büyüklüğü için teorik Kelly limiti %2,5 - %5,0 bandında önerilmektedir. "
            f"Fiyatın 50 günlük hareketli ortalaması ({curr_sym}{sma50:,.2f}) ana teknik destek noktası olarak takip edilmelidir."
        )
        scorecard_c = (
            f"360° Şirket Karnesi modelimiz {company_name} için finansal veriler doğrultusunda kapsamlı skor üretmektedir. "
            f"Altman Z-Score Z = {z_score:,.2f} ({z_zone}) ve Piotroski F-Skoru {pf_score}/9 seviyesindedir."
        )
        piotroski_c = (
            f"Piotroski F-Score denetiminde şirket {pf_score}/9 puan almıştır. "
            f"Faaliyet nakit akışı ve kârlılık rasyoları nakit kalitesini belirleyen ana faktörlerdir."
        )
        altman_c = (
            f"Altman Z-Score skoru Z = {z_score:,.2f} ile {z_zone} konumundadır."
        )
        moat_c = (
            f"{company_name}, kendi sektöründeki müşteri ağı ve operasyonel altyapısı ile faaliyetlerini sürdürmektedir."
        )
        ownership_c = (
            f"Ortaklık yapısı ve döviz pozisyonu kur dalgalanmalarına karşı bilanço dengesini etkilemektedir."
        )
        peer_c = (
            f"Sektör rakipleri ile yapılan karşılaştırmada {company_name}, {ps_ratio:.1f}x P/S çarpanı ile değerlendirilmektedir."
        )
        dupont_c = (
            f"DuPont 5-Adım Özsermaye Kârlılığı (ROE) ayrıştırmasında Vergi Yükü, Faiz Yükü ve Faaliyet Marjı öne çıkmaktadır."
        )
        forward_c = (
            f"Gelecek dönem projeksiyonlarında ciro ve kârlılığın artmasıyla birlikte İleri Fiyat/Satışlar (Forward P/S) çarpanının "
            f"{ps_ratio:.1f}x seviyesinden dengelenmesi öngörülmektedir."
        )
        dcf_c = (
            f"Hesaplanan WACC %{wacc*100:.2f} ve Ters DCF implike büyüme oranı %{implied_g*100:.2f} olarak ölçülmüştür."
        )
        tech_c = (
            f"Teknik göstergelerde fiyat {curr_sym}{sma50:,.2f} olan 50 günlük hareketli ortalama seviyesindedir."
        )
        forensic_c = (
            f"Adli denetimde Beneish M-Score {bm_score:.2f} ile {bm_safe_tr} konumundadır."
        )
        scenario_c = (
            f"Senaryo analizinde {curr_sym}{sma50:,.2f} teknik desteği ana tampon seviyesidir."
        )
        if is_bank:
            blog_headline_val = f"📰 {company_name} ({ticker}): Bankacılık Sektörü Özsermaye Kârlılığı (ROE) ve Defter Değeri Analizi"
        elif net_debt < 0:
            blog_headline_val = f"📰 {company_name} ({ticker}): Kasadaki {curr_sym}{abs(net_debt)/1e6:,.1f}M Nakit Tamponu vs. Piyasa Çarpanı Dengesi"
        elif net_debt > 0 and (debt / max(1, mcap)) > 0.4:
            blog_headline_val = f"📰 {company_name} ({ticker}): Bilanço Borç Yapısı ve Finansal Kaldıraç Denetimi"
        elif pf_score >= 7:
            blog_headline_val = f"📰 {company_name} ({ticker}): Yüksek Piotroski Skoru ({pf_score}/9) ile Güçlü Nakit Kalitesi"
        else:
            blog_headline_val = f"📰 {company_name} ({ticker}): 360° Finansal Sağlık ve Değerleme Analizi"
        blog_summary_val = f"{company_name} ({ticker}), {debt_desc_tr} ile finansal yapısını korumaktadır. Quant model değerlendirmesinde Piotroski F-Score {pf_score}/9 ve Altman Z-Score Z = {z_score:,.2f} ({z_zone}) olarak hesaplanmıştır."
        blog_cash_and_health_val = f"{company_name} bilançosu incelendiğinde şirket {debt_desc_tr} ile hareket etmektedir. {debt_shield_tr} Altman Z-Score modelimiz (borç doktoru) Z = {z_score:,.2f} ile şirketin '{z_zone}' kategorisinde yer aldığını göstermektedir."
        blog_earnings_quality_val = f"Şirketin kâr kalitesi ve nakit akış performansı Piotroski F-Score (9 maddelik sağlık karnesi) modelinde {pf_score}/9 puan olarak ölçülmüştür. Adli bilanço denetiminde Beneish M-Score {bm_score:.2f} ({bm_safe_tr}) seviyesindedir."
        blog_valuation_dcf_val = f"Değerleme tarafında {ticker}, {ps_ratio:.1f}x Fiyat/Satışlar (P/S etiket fiyatı) ve {pe_ratio:.1f}x F/K çarpanı ile işlem görmektedir. Ters DCF (hız göstergesi) modelimiz mevcut fiyatın rasyonel karşılanması için yıllık reel %{implied_g*100:.2f} serbest nakit akışı büyümesi gerektirmektedir."
        blog_catalysts_val = f"Büyüme Fırsatları:\n1) Yeni sektör sözleşmeleri ve operasyonel hacim büyümesi.\n2) Kasadaki acil durum nakit birikiminin korunması.\n\nKritik Riskler:\n1) Çarpan gerilemesi riski.\n2) 50 günlük hareketli ortalama ({curr_sym}{sma50:,.2f}) teknik desteğinin takibi."
        blog_bull_vs_bear_val = f"Boğa Senaryosu: Yüksek Piotroski skoru ({pf_score}/9) ve Altman Z-Score ({z_score:,.2f}) finansal dayanıklılık sağlar.\n\nAyı Senaryosu: {ps_ratio:.1f}x P/S çarpanı sürdürülebilir büyüme gerektirir.\n\nNihai Değerlendirme: Kademeli alım ve stop-loss disiplini korunmalıdır."
        blog_takeaways_val = [
            f"Altman Z-Score skoru Z = {z_score:,.2f} ({z_zone}) ile finansal bünye takibi",
            f"Piotroski F-Score {pf_score}/9 ve P/S çarpanı {ps_ratio:.1f}x seviyesinde",
            f"50 günlük ortalama fiyat ({curr_sym}{sma50:,.2f}) ana destek noktası"
        ]
        blog_faqs_val = [
            {"q": f"Ben olsam {ticker} hissesine şu an nasıl yaklaşırdım? (Yatırımcı Perspektifi)", "a": f"{company_name} için bir portföy yönetiyor olsaydım, riski dağıtmak adına pozisyon büyüklüğünü %2,5 - %5,0 Kelly limitinde tutardım. Altman Z-Score Z = {z_score:,.2f} ({z_zone}) ile şirketin finansal sağlık karnesi (borç doktoru) güvenli görünse de, {ps_ratio:.1f}x P/S etiket fiyatı nedeniyle 50 günlük hareketli ortalama olan {curr_sym}{sma50:,.2f} seviyesini ana koruma kalkanım olarak takip ederdim."},
            {"q": f"{ticker} hissesi yeni başlayan yatırımcı için uygun mu?", "a": f"{company_name} için Altman Z-Score Z = {z_score:,.2f} ({z_zone}) seviyesindedir. Yeni başlayan yatırımcıların %2,5 - %5,0 gibi küçük pozisyon oranlarıyla hareket etmesi önerilir."},
            {"q": f"{ticker} hissesinde en büyük risk nedir?", "a": f"En büyük risk, çarpan gerilemesi ve hareketli ortalamalar etrafındaki fiyat dalgalanmalarıdır."}
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
