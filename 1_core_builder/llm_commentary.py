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
19. "blog_headline": Şirket ve günün tarihine özel, her seviyeden bireysel yatırımcının rahatça anlayabileceği çekici bülten başlığı (örn. 📰 [TICKER] Analizi: Şirketin Kasası Para Dolu Ama Fiyatı Biraz Pahalı mı?)
20. "blog_summary": Bireysel yatırımcılara yönelik, 1-2 paragraflık sade ve anlaşılır günlük analiz özeti. Ağır finansal terimler kullanma; her terimi halk dilinde açıkla.
21. "blog_cash_and_health": Şirketin finansal sağlığını ve kasadaki nakit birikimini esnaf/iş yeri benzetmeleriyle anlatan sade makale bölümü.
22. "blog_earnings_quality": Şirketin kâr kalitesini ve 9 maddelik bilanço güven puanını (Piotroski) sade dille anlatan bölüm.
23. "blog_valuation_dcf": Hisse fiyatının pahalı mı ucuz mu olduğunu (P/S, P/E) ve piyasanın büyüme beklentilerini halk diliyle açıklayan bölüm.
24. "blog_catalysts_and_risks": Şirket için önümüzdeki 12 ayın büyüme fırsatlarını ve risklerini "Büyüme Fırsatları:\n1)... 2)...\n\nKritik Riskler:\n1)... 2)..." formatında sade dille anlatan bölüm.
25. "blog_bull_vs_bear": Boğa ve Ayı senaryolarını "Boğa Senaryosu: ...\n\nAyı Senaryosu: ...\n\nKüçük Yatırımcı İçin Tavsiye: ..." formatında kıyaslayan bölüm.
26. "blog_key_takeaways": Google öne çıkan snippet kutusu için bireysel yatırımcı diliyle yazılmış 3 kısa özet cümlesi dizisi (örn. ["Finansal Sağlık Mükemmel: ...", "Fiyat Etiketi Yüksek: ...", "Teknik Desteğe Dikkat: ..."]).
27. "blog_faqs": Bireysel yatırımcıların merak ettiği 3 sade soru-cevap nesnesi dizisi. İLK SORU KESİNLİKLE ŞU OLACAKTIR: [{"q": "❓ [TICKER] hissesine ben olsam şu an nasıl yaklaşırdım? (Yatırımcı Perspektifi)", "a": "[TICKER] şirketinin batma riski verileri (Altman Z), değerleme çarpanları (P/S, F/K) ve 50 günlük ortalama teknik desteğine dayalı somut, anlaşılır yatırımcı tavsiyesi."}, {"q": "❓ [TICKER] hissesi yeni başlayan biri için uygun mu?", "a": "..."}, {"q": "❓ [TICKER] hissesi şu an pahalı mı?", "a": "..."}]
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
  * "blog_headline": Catchy, plain-language title (e.g. 📰 [TICKER] Analysis: Solid Cash Cushion vs. High Price Tag)
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
19. "blog_headline": Engaging, retail-friendly title (e.g. 📰 [TICKER] Analysis: Solid Cash Cushion vs. High Price Tag)
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


def _robust_parse_json(raw_content: str, ticker: str, metrics: dict, lang: str, log_fn=None, llm_model: str = "LIVE_AI") -> dict:
    """Safely parse LLM JSON response with control character fixes and fallback merging."""
    def _log(msg):
        if callable(log_fn):
            log_fn(msg)
        else:
            print(msg)

    fallback = _fallback_commentary(ticker, metrics, lang)
    if not raw_content or not raw_content.strip():
        _log("   ⚠️ LLM returned empty raw content.")
        return fallback

    cleaned = raw_content.strip()

    # Try extracting JSON from ```json ... ``` codeblock first (handles reasoning model outputs)
    codeblock_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', cleaned, re.IGNORECASE)
    if codeblock_match:
        json_str = codeblock_match.group(1).strip()
    else:
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
        res_dict = dict(fallback)
        for key, val in parsed_data.items():
            if val and isinstance(val, str) and val.strip():
                clean_val = val.strip()
                if lang_upper == "TR" and _is_english_text(clean_val):
                    _log(f"   ⚠️ Key '{key}' contained English output in TR mode. Using Turkish fallback.")
                else:
                    res_dict[key] = clean_val
            elif val and isinstance(val, (list, dict)):
                res_dict[key] = val

        res_dict["_is_llm_generated"] = True
        res_dict["_llm_model"] = llm_model
        _log(f"   ✅ LLM commentary parsed successfully ({len(parsed_data)} sections) [Source: {llm_model}]")
        return res_dict

    _log("   ⚠️ Could not parse LLM JSON output. Using rich quantitative fallback commentary.")
    return fallback


def _sanitize_prompt_field(value: str) -> str:
    """Sanitize a user-controlled string before embedding in LLM prompts.
    Allows alphanumeric, Turkish characters, common punctuation, and whitespace.
    Strips anything that could be used for prompt injection."""
    if not value or not isinstance(value, str):
        return ""
    # Allow: letters (including Turkish İıÖöÜüŞşÇçĞğ), digits, spaces, dots, hyphens, ampersands, parentheses, commas
    return re.sub(r'[^\w\s.\-&()/,;:\'\"#%+₺€$£¥]', '', value, flags=re.UNICODE).strip()


def generate_commentary(metrics: dict, lang: str = "TR", log_fn=None, strict_llm: bool = False) -> dict:
    """Generate qualitative commentary JSON using LLM API or professional fallback."""
    def _log(msg):
        if callable(log_fn):
            log_fn(msg)
        else:
            print(msg)

    load_dotenv(APP_ENV_PATH, override=True)
    load_dotenv(override=True)

    llm_base_url = os.getenv("LLM_BASE_URL") or os.getenv("BASE_URL") or os.getenv("NINEROUTER_URL", "http://localhost:20128/v1")
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("API_KEY") or os.getenv("NINEROUTER_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "code_combo")

    is_strict = strict_llm or os.getenv("STRICT_LLM", "false").lower() in ("true", "1", "yes")

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
        _log(f"2. Requesting LLM commentary from {llm_base_url} ({llm_model}) [Streaming Mode]...")
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
            if not line_str.startswith("{"):
                continue
            try:
                data = json.loads(line_str)
                choices = data.get("choices", [])
                if choices and len(choices) > 0:
                    delta = choices[0].get("delta", {})
                    txt = delta.get("content") or delta.get("reasoning") or delta.get("reasoning_content") or delta.get("text") or ""
                    if txt:
                        chunks.append(txt)
            except Exception:
                pass

        raw_content = "".join(chunks)
        res = _robust_parse_json(raw_content, ticker, metrics, lang, log_fn=log_fn, llm_model=llm_model)
        if is_strict and not res.get("_is_llm_generated", False):
            raise RuntimeError(f"Strict LLM Mode: LLM output could not be parsed as valid JSON.")
        return res

    except requests.exceptions.ConnectionError as ce:
        err_msg = f"LLM endpoint unreachable at {llm_base_url} ({ce})"
        _log(f"   ⚠️ {err_msg}")
        if is_strict:
            raise RuntimeError(f"Strict LLM Mode Error: {err_msg}")
        return _fallback_commentary(ticker, metrics, lang)
    except requests.exceptions.Timeout as te:
        err_msg = f"LLM request timeout at {llm_base_url} after {timeout_val}s ({te})"
        _log(f"   ⚠️ {err_msg}")
        if is_strict:
            raise RuntimeError(f"Strict LLM Mode Error: {err_msg}")
        return _fallback_commentary(ticker, metrics, lang)
    except Exception as e:
        if is_strict and "Strict LLM Mode" in str(e):
            raise
        err_msg = f"LLM commentary error: {e}"
        _log(f"   ⚠️ {err_msg}")
        if is_strict:
            raise RuntimeError(f"Strict LLM Mode Error: {err_msg}")
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
    z_score = az.get("z_score")
    z_score_str = f"Z = {z_score:,.2f}" if isinstance(z_score, (int, float)) else "N/A"
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

    implied_g_str = f"%{implied_g*100:.2f}" if isinstance(implied_g, (int, float)) else "N/A"

    if lang_upper == "EN":
        verdict_text = "BALANCED MODEL OUTLOOK (STRONG BALANCE SHEET / HIGH MULTIPLE BALANCE)"
        net_cash_m = abs(net_debt)/1e6
        net_margin_pct = (hist[0].get('net_margin', hist[0].get('gross_margin', 0.16))*100) if hist else 16.2

        if net_debt < 0:
            strong = (
                f"{company_name} ({ticker}) exhibits a robust financial position with net cash reserves "
                f"({curr_sym}{net_cash_m:,.1f}M). The net cash cushion yields a low WACC of %{wacc*100:.2f}, "
                f"shielding the company from high interest rate environments."
            )
            blog_headline_val = f"📰 {ticker} Analysis: Solid Net Cash Cushion ({curr_sym}{net_cash_m:,.1f}M) vs. Price Tag"
            blog_summary_val = f"{company_name} is one of the rare companies operating completely debt-free with a net cash position of {curr_sym}{net_cash_m:,.1f}M. While this provides an immense safety shield, investors should monitor its valuation multiple."
            blog_cash_and_health_val = f"Operating debt-free is a major advantage during periods of high interest rates. {company_name}'s {curr_sym}{net_cash_m:,.1f}M cash cushion acts as a powerful shield against market volatility. Scoring {z_score_str} ({z_zone}) confirms its balance sheet health."
            blog_bull_vs_bear_val = f"Bull Case: Net cash cushion of {curr_sym}{net_cash_m:,.1f}M provides strength and resilience during high interest rate environments.\n\nBear Case: Elevated valuation multiples require sustained earnings growth to support current stock prices.\n\nRetail Investor Takeaway: Dollar-cost averaging in small steps (2.5%-5.0% position size) while maintaining stop-loss discipline is a prudent strategy."
            blog_takeaways_val = [
                f"Financial Health Excellent: Low insolvency risk backed by solid net cash reserves of {curr_sym}{net_cash_m:,.1f}M.",
                f"Valuation Tag: The stock trades at {ps_ratio:.1f}x Price-to-Sales relative to annual revenue.",
                f"Key Support Level: The 50-day moving average at {curr_sym}{sma50:,.2f} serves as the primary safety floor."
            ]
            faq_ans_en = f"If I were managing a portfolio for {company_name}, I would maintain disciplined position sizing (2.5%-5.0% allocation). The net cash cushion of {curr_sym}{net_cash_m:,.1f}M provides solid downside protection."
        else:
            strong = (
                f"{company_name} ({ticker}) exhibits a financial position with a net debt load of {curr_sym}{net_cash_m:,.1f}M on its balance sheet. "
                f"Free Cash Flow generation and debt service coverage remain key operational metrics under current interest rates."
            )
            blog_headline_val = f"📰 {ticker} Analysis: Balance Sheet Debt Structure & Valuation Audit"
            blog_summary_val = f"{company_name} carries a net debt position of {curr_sym}{net_cash_m:,.1f}M on its balance sheet. Financial leverage management and operating cash flows will be critical performance drivers over the upcoming quarters."
            blog_cash_and_health_val = f"{company_name} operates with a net debt load of {curr_sym}{net_cash_m:,.1f}M. Under elevated interest rate environments, maintaining strong operating cash flows and interest coverage is essential."
            blog_bull_vs_bear_val = f"Bull Case: Sustained operational cash flow growth and debt deleveraging could unlock significant equity upside.\n\nBear Case: High interest expense and debt service burdens could compress net profit margins if revenue slows.\n\nRetail Investor Takeaway: Limit position size to 2.5%-5.0% to manage balance sheet risk and monitor key support at {curr_sym}{sma50:,.2f}."
            blog_takeaways_val = [
                f"Debt Monitoring Critical: Net debt load of {curr_sym}{net_cash_m:,.1f}M requires continuous cash flow tracking.",
                f"Valuation Tag: Stock trades at {ps_ratio:.1f}x Price-to-Sales relative to revenue.",
                f"Key Support Level: The 50-day moving average at {curr_sym}{sma50:,.2f} serves as the primary technical floor."
            ]
            faq_ans_en = f"With {company_name} carrying {curr_sym}{net_cash_m:,.1f}M in net debt, I would restrict position size to 2.5%-5.0% to cap portfolio risk and keep a close eye on the {curr_sym}{sma50:,.2f} 50-day moving average support."

        weak = f"The primary risk factor for {company_name} is valuation premium. Price-to-Sales (P/S) ratio stands at {ps_ratio:.1f}x."
        risk_disc = f"Statistical risk models suggest a position limit of 2.5% - 5.0% (Kelly limit) with technical support at {curr_sym}{sma50:,.2f}."
        scorecard_c = f"Our 360° Company Scorecard evaluates {company_name} on Piotroski ({pf_score}/9) and Altman Z ({z_score_str}, {z_zone})."
        piotroski_c = f"Piotroski F-Score audit rates the company at {pf_score}/9 balance sheet quality."
        altman_c = f"Altman Z-Score evaluation: {z_score_str} ({z_zone})."
        moat_c = f"{company_name} benefits from sector infrastructure and contract pipeline catalysts."
        ownership_c = f"Ownership structure provides stability against liquidity shocks."
        peer_c = f"Compared to industry peers, {company_name} trades at a P/S multiple of {ps_ratio:.1f}x."
        dupont_c = f"DuPont 5-Step ROE decomposition highlights operational margins and tax burden."
        forward_c = f"Forward projections forecast valuation normalization toward historical industry averages."
        dcf_c = f"Calculated WACC is %{wacc*100:.2f} with Reverse DCF growth tracking ({implied_g_str})."
        tech_c = f"Technical indicators show 50-day moving average support at {curr_sym}{sma50:,.2f}."
        forensic_c = f"Forensic audit using Beneish M-Score ({bm_score:.2f}) indicates transparent accounting."
        scenario_c = f"Scenario analysis sets technical support at {curr_sym}{sma50:,.2f} as the primary Bear Case target."

        blog_earnings_quality_val = f"Examining the balance sheet report card, the company scores {pf_score} out of 9 on the Piotroski scale with a net profit margin of %{net_margin_pct:.1f}."
        blog_valuation_dcf_val = f"Relative to annual sales, the stock trades at {ps_ratio:.1f}x P/S. The market is pricing in forward growth expectations."
        blog_catalysts_val = f"Growth Opportunities:\n1) Core business expansion and major new contract renewals.\n2) Deleveraging and cash flow optimization.\n\nRisk Radar:\n1) Interest rate sensitivity on debt service burdens.\n2) Breakdown below key technical support at {curr_sym}{sma50:,.2f}."
        blog_faqs_val = [
            {"q": f"❓ How would I personally approach {ticker} stock right now? (Investor Perspective)", "a": faq_ans_en},
            {"q": f"❓ Is {ticker} stock suitable for beginner investors?", "a": f"Beginners should start small (2.5%-5.0% allocation limit) and keep track of debt ratios and moving average support."},
            {"q": f"❓ What is the primary risk factor for {ticker}?", "a": f"The primary risk factor centers around debt servicing under high interest rates and key technical support at {curr_sym}{sma50:,.2f}."}
        ]
    else:
        verdict_text = "DENGELİ MODEL GÖRÜŞÜ (FİNANSAL SAĞLIK VE DEĞERLEME DENGESİ)"
        net_cash_m = abs(net_debt)/1e6 if net_debt < 0 else debt/1e6
        net_margin_pct = (hist[0].get('net_margin', hist[0].get('gross_margin', 0.16))*100) if hist else 16.2
        debt_desc_tr = f"kasasındaki {curr_sym}{net_cash_m:,.1f}M net nakit birikimi" if net_debt < 0 else f"{curr_sym}{net_cash_m:,.1f}M net borç pozisyonu"

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
            f"Altman Z-Score ({z_score_str}, {z_zone}) ve Piotroski F-Skoru {pf_score}/9 seviyesindedir."
        )
        piotroski_c = (
            f"Piotroski F-Score denetiminde şirket {pf_score}/9 puan almıştır. "
            f"Faaliyet nakit akışı ve kârlılık rasyoları nakit kalitesini belirleyen ana faktörlerdir."
        )
        altman_c = (
            f"Altman Z-Score değerlendirmesi: {z_score_str} ({z_zone})."
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
            f"Hesaplanan WACC %{wacc*100:.2f} ve Ters DCF implike büyüme oranı {implied_g_str} olarak ölçülmüştür."
        )
        tech_c = (
            f"Teknik göstergelerde fiyat {curr_sym}{sma50:,.2f} olan 50 günlük hareketli ortalama seviyesindedir."
        )
        forensic_c = f"Adli denetimde Beneish M-Score {bm_score:.2f} ile {bm_safe_tr} konumundadır."
        scenario_c = f"Senaryo analizinde {curr_sym}{sma50:,.2f} teknik desteği ana tampon seviyesidir."

        if net_debt < 0:
            cash_health_tr = f"Bir şirketin borçsuz olması, yüksek faizlerin hüküm sürdüğü dönemlerde büyük bir avantajdır. {company_name}’in kasasındaki {curr_sym}{net_cash_m:,.1f} milyonluk nakit, şirketi olası krizlere karşı koruyan güçlü bir kalkan görevi görüyor."
            summary_tr = f"{company_name}, cebinde hiç net borcu olmadan yola devam eden nadir şirketlerden biri. Kasasında tam {curr_sym}{net_cash_m:,.1f} milyon net nakit biriktirmiş durumda. Bu durum şirkete muazzam bir güvenlik kalkanı sağlarken, yatırımcıların dikkat etmesi gereken tek konu hisse fiyatının biraz yüksek kalması."
            bull_bear_tr = f"Boğa Senaryosu: Şirket borçsuz ve kasası nakit dolu. Bu finansal güç, zorlu ekonomik koşullarda büyük bir avantaj ve büyüme fırsatı sunar.\n\nAyı Senaryosu: Mevcut hisse fiyatı şirketin kârına göre oldukça yüksek. Beklenen hızlı büyüme gelmezse fiyatta geri çekilmeler görülebilir.\n\nKüçük Yatırımcı İçin Tavsiye: Tüm paranızla tek seferde almak yerine, fiyat düştükçe parça parça (kademeli) alım yapmak ve zarar kes (stop-loss) seviyelerine sadık kalmak mantıklı bir strateji olabilir."
            takeaway_health_tr = f"Finansal Sağlık Mükemmel: Şirketin iflas riski yok denecek kadar az. Kasasındaki nakit ({curr_sym}{net_cash_m:,.1f}M), zor günlerde en büyük güvencesi."
            faq_ans_tr = f"Şirketin batma riski yok denecek kadar az olsa da (kasada {curr_sym}{net_cash_m:,.1f}M net nakit var) fiyatı biraz pahalı. Bir portföy yönetiyor olsaydım tüm parayla girmek yerine %2,5 ile %5,0'lik küçük bir adımla alım yapar, {curr_sym}{sma50:,.2f} olan 50 günlük ortalamayı koruma kalkanım yapardım."
            headline_tr = f"📰 {ticker} Analizi: Şirketin Kasası Para Dolu Ama Fiyatı Biraz Pahalı mı?"
        else:
            cash_health_tr = f"{company_name}, bilançosunda toplam {curr_sym}{net_cash_m:,.1f} milyon net borç yükü taşımaktadır. Yüksek faiz ortamında borç servis oranları ve işletme nakit akışlarının sürdürülebilirliği yakından takip edilmelidir."
            summary_tr = f"{company_name}, bilançosunda {curr_sym}{net_cash_m:,.1f} milyon net borç ile faaliyetlerini sürdürmektedir. Finansal borç yönetimi ve nakit akış performansı önümüzdeki dönemde hisse değerlemesi açısından kritik öneme sahiptir."
            bull_bear_tr = f"Boğa Senaryosu: Borç servis kapasitesinin korunması ve operasyonel nakit akışlarının artması bilançoyu rahatlatabilir.\n\nAyı Senaryosu: Yüksek borç yükü ve faiz maliyetleri kârlılık üzerinde baskı yaratabilir.\n\nKüçük Yatırımcı İçin Tavsiye: Borç yapısı nedeniyle pozisyon büyüklüğü %2,5 - %5,0 ile sınırlandırılmalı ve 50 günlük ortalama seviyesi ({curr_sym}{sma50:,.2f}) yakından izlenmelidir."
            takeaway_health_tr = f"Borç Yönetimi Kritik: Bilançodaki {curr_sym}{net_cash_m:,.1f}M net borç yükü faiz ortamında yakından izlenmeli."
            faq_ans_tr = f"Şirketin bilançosunda {curr_sym}{net_cash_m:,.1f}M net borç yükü bulunmaktadır. Bir portföy yönetiyor olsaydım riski sınırlamak adına pozisyon büyüklüğünü %2,5 - %5,0 bandında tutar ve {curr_sym}{sma50:,.2f} teknik desteğine sadık kalırdım."
            headline_tr = f"📰 {ticker} Analizi: Bilanço Borç Yapısı ve 360° Değerleme Raporu"

        if is_bank:
            blog_headline_val = f"📰 {ticker} Analizi: Bankacılık Özsermaye Kârlılığı ve Defter Değeri Dengesi"
        else:
            blog_headline_val = headline_tr

        blog_summary_val = summary_tr
        blog_cash_and_health_val = f"{cash_health_tr} Altman Z-Score değerlendirmesi: {z_score_str} ({z_zone})."
        blog_earnings_quality_val = f"Şirketin genel kârlılık karnesini incelediğimizde 9 üzerinden {pf_score} puan aldığını görüyoruz. Satışlarından elde ettiği kâr oranı %{net_margin_pct:.1f}. Şirket mali tablolarında dürüst ve şeffaf bir çizgi izliyor."
        blog_valuation_dcf_val = f"Değerleme tarafında hisse fiyatı üretilen satışların {ps_ratio:.1f} katı seviyesinden işlem görüyor (P/S: {ps_ratio:.1f}x). Piyasa geleceğe yönelik büyüme beklentilerini fiyatlamaktadır."
        blog_catalysts_val = f"Büyüme Fırsatları:\n1) Sektörel iş hacmi büyümesi ve yeni sözleşmeler.\n2) Operasyonel nakit akışlarının güçlenmesi.\n\nKritik Riskler:\n1) Yüksek faiz ve borç maliyetlerinin kârlılık üzerindeki baskısı.\n2) {curr_sym}{sma50:,.2f} seviyesindeki teknik desteğin aşağı yönlü kırılması."
        blog_bull_vs_bear_val = bull_bear_tr
        blog_takeaways_val = [
            takeaway_health_tr,
            f"Fiyat Etiketi: Satışlarına kıyasla hisse fiyatı şu an ({ps_ratio:.1f} katı) seviyesinden işlem görüyor.",
            f"Teknik Desteğe Dikkat: {curr_sym}{sma50:,.2f} seviyesindeki 50 günlük ortalama fiyat, takip edilmesi gereken ana sınır."
        ]
        blog_faqs_val = [
            {"q": f"❓ {ticker} hissesine ben olsam şu an nasıl yaklaşırdım? (Yatırımcı Perspektifi)", "a": faq_ans_tr},
            {"q": f"❓ {ticker} hissesi yeni başlayan biri için uygun mu?", "a": f"Yeni başlayan yatırımcıların borç yapısını ve dalgalanmaları dikkate alarak portföylerinin %2,5 ile %5,0'lik küçük bir kısmıyla hareket etmesi önerilir."},
            {"q": f"❓ {ticker} hissesinde en büyük risk nedir?", "a": f"En büyük risk borç yükü, faiz maliyetleri ve hareketli ortalamalar etrafındaki fiyat düzeltmeleridir."}
        ]
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
            f"Hesaplanan WACC %{wacc*100:.2f} ve Ters DCF implike büyüme oranı {implied_g_str} olarak ölçülmüştür."
        )
        tech_c = (
            f"Teknik göstergelerde fiyat {curr_sym}{sma50:,.2f} olan 50 günlük hareketli ortalama seviyesindedir."
        )
        forensic_c = f"Adli denetimde Beneish M-Score {bm_score:.2f} ile {bm_safe_tr} konumundadır."
        scenario_c = f"Senaryo analizinde {curr_sym}{sma50:,.2f} teknik desteği ana tampon seviyesidir."

        if net_debt < 0:
            cash_health_tr = f"Bir şirketin borçsuz olması, yüksek faizlerin hüküm sürdüğü dönemlerde büyük bir avantajdır. {company_name}’in kasasındaki {curr_sym}{net_cash_m:,.1f} milyonluk nakit, şirketi olası krizlere karşı koruyan güçlü bir kalkan görevi görüyor."
            summary_tr = f"{company_name}, cebinde hiç net borcu olmadan yola devam eden nadir şirketlerden biri. Kasasında tam {curr_sym}{net_cash_m:,.1f} milyon net nakit biriktirmiş durumda. Bu durum şirkete muazzam bir güvenlik kalkanı sağlarken, yatırımcıların dikkat etmesi gereken tek konu hisse fiyatının biraz yüksek kalması."
            bull_bear_tr = f"Boğa Senaryosu: Şirket borçsuz ve kasası nakit dolu. Bu finansal güç, zorlu ekonomik koşullarda büyük bir avantaj ve büyüme fırsatı sunar.\n\nAyı Senaryosu: Mevcut hisse fiyatı şirketin kârına göre oldukça yüksek. Beklenen hızlı büyüme gelmezse fiyatta geri çekilmeler görülebilir.\n\nKüçük Yatırımcı İçin Tavsiye: Tüm paranızla tek seferde almak yerine, fiyat düştükçe parça parça (kademeli) alım yapmak ve zarar kes (stop-loss) seviyelerine sadık kalmak mantıklı bir strateji olabilir."
            takeaway_health_tr = f"Finansal Sağlık Mükemmel: Şirketin iflas riski yok denecek kadar az. Kasasındaki nakit ({curr_sym}{net_cash_m:,.1f}M), zor günlerde en büyük güvencesi."
            faq_ans_tr = f"Şirketin batma riski yok denecek kadar az olsa da (kasada {curr_sym}{net_cash_m:,.1f}M net nakit var) fiyatı biraz pahalı. Bir portföy yönetiyor olsaydım tüm parayla girmek yerine %2,5 ile %5,0'lik küçük bir adımla alım yapar, {curr_sym}{sma50:,.2f} olan 50 günlük ortalamayı koruma kalkanım yapardım."
            headline_tr = f"📰 {ticker} Analizi: Şirketin Kasası Para Dolu Ama Fiyatı Biraz Pahalı mı?"
        else:
            cash_health_tr = f"{company_name}, bilançosunda toplam {curr_sym}{net_cash_m:,.1f} milyon net borç yükü taşımaktadır. Yüksek faiz ortamında borç servis oranları ve işletme nakit akışlarının sürdürülebilirliği yakından takip edilmelidir."
            summary_tr = f"{company_name}, bilançosunda {curr_sym}{net_cash_m:,.1f} milyon net borç ile faaliyetlerini sürdürmektedir. Finansal borç yönetimi ve nakit akış performansı önümüzdeki dönemde hisse değerlemesi açısından kritik öneme sahiptir."
            bull_bear_tr = f"Boğa Senaryosu: Borç servis kapasitesinin korunması ve operasyonel nakit akışlarının artması bilançoyu rahatlatabilir.\n\nAyı Senaryosu: Yüksek borç yükü ve faiz maliyetleri kârlılık üzerinde baskı yaratabilir.\n\nKüçük Yatırımcı İçin Tavsiye: Borç yapısı nedeniyle pozisyon büyüklüğü %2,5 - %5,0 ile sınırlandırılmalı ve 50 günlük ortalama seviyesi ({curr_sym}{sma50:,.2f}) yakından izlenmelidir."
            takeaway_health_tr = f"Borç Yönetimi Kritik: Bilançodaki {curr_sym}{net_cash_m:,.1f}M net borç yükü faiz ortamında yakından izlenmeli."
            faq_ans_tr = f"Şirketin bilançosunda {curr_sym}{net_cash_m:,.1f}M net borç yükü bulunmaktadır. Bir portföy yönetiyor olsaydım riski sınırlamak adına pozisyon büyüklüğünü %2,5 - %5,0 bandında tutar ve {curr_sym}{sma50:,.2f} teknik desteğine sadık kalırdım."
            headline_tr = f"📰 {ticker} Analizi: Bilanço Borç Yapısı ve 360° Değerleme Raporu"

        if is_bank:
            blog_headline_val = f"📰 {ticker} Analizi: Bankacılık Özsermaye Kârlılığı ve Defter Değeri Dengesi"
        else:
            blog_headline_val = headline_tr

        blog_summary_val = summary_tr
        blog_cash_and_health_val = f"{cash_health_tr} Altman Z-Score değerlendirmesi: {z_score_str} ({z_zone})."
        blog_earnings_quality_val = f"Şirketin genel kârlılık karnesini incelediğimizde 9 üzerinden {pf_score} puan aldığını görüyoruz. Satışlarından elde ettiği kâr oranı %{net_margin_pct:.1f}. Şirket mali tablolarında dürüst ve şeffaf bir çizgi izliyor."
        blog_valuation_dcf_val = f"Değerleme tarafında hisse fiyatı üretilen satışların {ps_ratio:.1f} katı seviyesinden işlem görüyor (P/S: {ps_ratio:.1f}x). Piyasa geleceğe yönelik büyüme beklentilerini fiyatlamaktadır."
        blog_catalysts_val = f"Büyüme Fırsatları:\n1) Sektörel iş hacmi büyümesi ve yeni sözleşmeler.\n2) Operasyonel nakit akışlarının güçlenmesi.\n\nKritik Riskler:\n1) Yüksek faiz ve borç maliyetlerinin kârlılık üzerindeki baskısı.\n2) {curr_sym}{sma50:,.2f} seviyesindeki teknik desteğin aşağı yönlü kırılması."
        blog_bull_vs_bear_val = bull_bear_tr
        blog_takeaways_val = [
            takeaway_health_tr,
            f"Fiyat Etiketi: Satışlarına kıyasla hisse fiyatı şu an ({ps_ratio:.1f} katı) seviyesinden işlem görüyor.",
            f"Teknik Desteğe Dikkat: {curr_sym}{sma50:,.2f} seviyesindeki 50 günlük ortalama fiyat, takip edilmesi gereken ana sınır."
        ]
        blog_faqs_val = [
            {"q": f"❓ {ticker} hissesine ben olsam şu an nasıl yaklaşırdım? (Yatırımcı Perspektifi)", "a": faq_ans_tr},
            {"q": f"❓ {ticker} hissesi yeni başlayan biri için uygun mu?", "a": f"Yeni başlayan yatırımcıların borç yapısını ve dalgalanmaları dikkate alarak portföylerinin %2,5 ile %5,0'lik küçük bir kısmıyla hareket etmesi önerilir."},
            {"q": f"❓ {ticker} hissesinde en büyük risk nedir?", "a": f"En büyük risk borç yükü, faiz maliyetleri ve hareketli ortalamalar etrafındaki fiyat düzeltmeleridir."}
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
        "blog_faqs": blog_faqs_val,
        "_is_llm_generated": False,
        "_llm_model": "QUANT_FALLBACK"
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
