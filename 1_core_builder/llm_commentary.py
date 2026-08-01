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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logger import log_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(APP_ENV_PATH)
load_dotenv()

# ═════════════════════════════════════════════════════════════════════════
# STAGE 1: INSTITUTIONAL QUANTITATIVE AUDIT MODEL (KEYS 1-18)
# ═════════════════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════════════════════════
# STAGE 1: INSTITUTIONAL QUANTITATIVE AUDIT MODEL (KEYS 1-18)
# ═════════════════════════════════════════════════════════════════════════
STAGE1_PROMPT_TR = """Sen kıdemli bir Finansal Quant ve Bilanço Denetçisisin.
Amacın, sana verilen nicel finansal metrikleri (Bilanço, Gelir Tablosu, DuPont, WACC, Piotroski, Altman Z, Beneish M-Score, RSI, SMA50/200, Peer Benchmark) kurumsal düzeyde inceleyerek aşağıdaki 18 teknik anahtar kelimeyi içeren geçerli bir JSON nesnesi döndürmektir.

YAZIM VE DERİNLİK KURALLARI (BOŞ LAF/FLUFF YOK, KESİN VERİ ODAKLI):
- TÜM ANALİZ CÜMLELERİ KESİNLİKLE %100 TÜRKÇE YAZILACAKTIR.
- KESİNLİKLE GENEL-GEÇER BOŞ LAFLAR VEYA DOLGU CÜMLELERİ (FLUFF) KULLANMA. HER CÜMLE KESİN RAKAMLAR, YÜZDELER VE BİLANÇO RASYOLARI İLE DESTEKLENECEKTİR.
- ÇOKLU PARAGRAF ZORUNLULUĞU (ÇOK ÖNEMLİ):
  * "strong_points": KESİNLİKLE EN AZ 2 DETAYLI PARAGRAF (120-200 kelime). Kasadaki net nakit miktarını, borç oranlarını ve bilanço dayanıklılığını kesin verilerle anlat.
  * "forensic_audit": KESİNLİKLE EN AZ 2 DETAYLI PARAGRAF (120-200 kelime). Beneish M-Score adli muhasebe skorunu (-2.85 eşiği), kâr manipülasyon riskini ve tahta sığlığını verilerle analiz et.
  * "weak_points": KESİNLİKLE EN AZ 2 DETAYLI PARAGRAF (120-200 kelime). Değerleme çarpanlarındaki (P/S, F/K, EV/EBITDA) prim ve balon riskini sektör ortalamalarıyla kıyasla.
  * "technical_analysis": KESİNLİKLE EN AZ 2 DETAYLI PARAGRAF (120-200 kelime). RSI, MACD, 50 günlük (SMA50) ve 200 günlük (SMA200) ortalamalar ile teknik destek seviyelerini rakamlarla açıkla.
  * "risk_discipline": KESİNLİKLE EN AZ 2 DETAYLI PARAGRAF (120-200 kelime). Kelly kriteri pozisyon büyüklüğü kısıtlamasını (%2.5-%5.0) ve stop-loss disiplinini rakamlarla analiz et.
- JSON formatına tam uy, markdown tırnakları veya kod blokları koyma.

GEREKLİ STAGE 1 JSON ANAHTARLARI:
1. "company_name": Şirket unvanı
2. "executive_summary": Yönetici özeti ve genel bilanço durumu
3. "strong_points": 2 detaylı paragraflık temel bilanço kalitesi ve nakit gücü analizi
4. "weak_points": 2 detaylı paragraflık spekülatif çarpan ısınması ve değerleme riski analizi
5. "risk_discipline": 2 detaylı paragraflık AI risk modeli ve teknik destek disiplini analizi
6. "scorecard_commentary": 360° Şirket Karnesi yorumu
7. "piotroski_commentary": Piotroski F-Score detaylı bilanço testi yorumu
8. "altman_z_commentary": Altman Z-Score iflas ve mali bünye riski yorumu
9. "moat_and_catalysts": Rekabetçi hendekler (Moat) ve önümüzdeki 12 ay katalizörleri
10. "ownership_commentary": Ortaklık yapısı, Lock-up kısıtlaması ve FX kur duyarlılığı
11. "peer_comparison": Sektör rakipleri karşılaştırması (P/S, P/E, Kâr Marjları)
12. "dupont_analysis": DuPont 5-Adım ROE ayrıştırması detaylı yorumu
13. "forward_commentary": 2026E/2027E gelecek dönem satış ve kâr tahmin yorumu
14. "dcf_valuation": WACC (% sermaye maliyeti), Ters DCF implike büyüme ve duyarlılık yorumu
15. "technical_analysis": 2 detaylı paragraflık teknik momentum ve kritik seviyeler analizi
16. "forensic_audit": 2 detaylı paragraflık Beneish M-Score adli muhasebe ve mevzuat güvenliği analizi
17. "scenario_analysis": Sert düşüş, Ayı, Baz ve Boğa senaryoları yorumu
18. "investment_verdict": DENGELİ MODEL GÖRÜŞÜ ile başlayan nihai yatırım kararı sentezi
"""

STAGE1_PROMPT_EN = """You are a Senior Financial Quant and Forensic Balance Sheet Auditor.
Analyze the provided quantitative financial metrics (Balance Sheet, Income Statement, DuPont, WACC, Piotroski, Altman Z, Beneish M-Score, RSI, SMA50/200, Peer Benchmark).
Return a valid JSON object containing the exact 18 technical keys specified below.

WRITING AND DEPTH RULES (STRICTLY DATA-DRIVEN, NO FLUFF):
- MANDATORY MULTI-PARAGRAPH DEPTH (MINIMUM 2 PARAGRAPHS / 120-200 WORDS PER SECTION):
  * "strong_points": Minimum 2 detailed paragraphs with exact cash, debt, and balance sheet figures.
  * "forensic_audit": Minimum 2 detailed paragraphs analyzing Beneish M-Score (-2.85 threshold) and liquidity safety.
  * "weak_points": Minimum 2 detailed paragraphs unpacking P/S, P/E, and valuation risk multiples.
  * "technical_analysis": Minimum 2 detailed paragraphs analyzing RSI, MACD, SMA 50, and SMA 200 price levels.
  * "risk_discipline": Minimum 2 detailed paragraphs outlining Kelly allocation limits (2.5%-5.0%) and risk rules.
- NO FLUFF MANDATE: Avoid generic filler text. Every paragraph MUST contain specific numbers, percentages, and financial metrics.

REQUIRED STAGE 1 JSON KEYS:
1. "company_name": Full legal company name
2. "executive_summary": Executive summary and overall health status
3. "strong_points": 2-paragraph detailed fundamental balance sheet quality and cash strength analysis
4. "weak_points": 2-paragraph detailed valuation multiple overheating and bubble risk analysis
5. "risk_discipline": 2-paragraph detailed risk model and execution discipline analysis
6. "scorecard_commentary": 360° Company Scorecard breakdown commentary
7. "piotroski_commentary": Piotroski F-Score detailed balance sheet audit commentary
8. "altman_z_commentary": Altman Z-Score insolvency and financial distress commentary
9. "moat_and_catalysts": Competitive moat and next 12-month catalysts
10. "ownership_commentary": Ownership structure, lock-up restrictions, and FX sensitivity
11. "peer_comparison": Industry peer comparison (P/S, P/E, Profit Margins)
12. "dupont_analysis": DuPont 5-Step ROE decomposition commentary
13. "forward_commentary": 2026E/2027E forward sales and earnings outlook
14. "dcf_valuation": WACC (% cost of capital), Reverse DCF implied growth, and sensitivity commentary
15. "technical_analysis": 2-paragraph detailed technical momentum and key price levels analysis
16. "forensic_audit": 2-paragraph detailed Beneish M-Score forensic accounting audit analysis
17. "scenario_analysis": Severe downside, Bear, Base, and Bull target scenarios commentary
18. "investment_verdict": Final investment verdict synthesis starting with 'BALANCED MODEL OUTLOOK'
"""

# ═════════════════════════════════════════════════════════════════════════
# STAGE 2: RETAIL INVESTOR BLOG BRIEFING & ARTICLE WRITER (KEYS 19-27)
# ═════════════════════════════════════════════════════════════════════════
STAGE2_PROMPT_TR = """Sen deneyimli, samimi ve sürükleyici bir Finans Analisti ve Ekonomi Yazarısın.
Amacın, sana verilen şirket metriklerini ve Kurumsal Quant Denetim Bulgularını (Stage 1) kullanarak, bireysel yatırımcılar için son derece zengin, detaylı, çok paragraflı ve akıcı bir hisse analiz makalesi (Blog Bülteni) hazırlamaktır.

YAZIM VE UZUNLUK KURALLARI (DERİN VE ZENGİN ANLATIM):
- TÜM YAZILAR KESİNLİKLE %100 TÜRKÇE OLACAKTIR.
- "Yapay Zekâ Kıdemli Analisti" veya "Quant modelimiz" gibi soğuk, robotik ifadeleri KESİNLİKLE KULLANMA. Kahve eşliğinde konuşan dost bir analist gibi samimi ve sürükleyici yaz.
- ZENGİN PARAGRAF ZORUNLULUĞU (ÇOK ÖNEMLİ):
  * "blog_summary": KESİNLİKLE EN AZ 2-3 DETAYLI PARAGRAF (150-250 kelime). Şirketin ne iş yaptığını, bilançonun genel durumunu ve hisse fiyatının ucuz/pahalı olma hikayesini detaylıca anlat.
  * "blog_cash_and_health": KESİNLİKLE EN AZ 2-3 DETAYLI PARAGRAF. Kasadaki nakit ve borç durumunu esnaf/iş yeri benzetmeleriyle açıkla. Borç doktoru (Altman Z) test sonucunu halk diliyle detaylandır.
  * "blog_earnings_quality": KESİNLİKLE EN AZ 2-3 DETAYLI PARAGRAF. Kâr marjlarını ve 9 maddelik bilanço güven puanını (Piotroski) sade dille analiz et.
  * "blog_valuation_dcf": KESİNLİKLE EN AZ 2-3 DETAYLI PARAGRAF. Hisse fiyat etiketini (P/S, F/K) ve piyasanın beklediği büyüme hızını örneklerle açıkla.
  * "blog_catalysts_and_risks": Şirket için önümüzdeki 12 ayın büyüme fırsatlarını ve risklerini "Büyüme Fırsatları:\n1)... 2)...\n\nKritik Riskler:\n1)... 2)..." formatında zengin bir dille yaz.
  * "blog_bull_vs_bear": Boğa ve Ayı senaryolarını "Boğa Senaryosu: ...\n\nAyı Senaryosu: ...\n\nKüçük Yatırımcı İçin Tavsiye: ..." formatında kıyasla.
  * "blog_key_takeaways": Google öne çıkan snippet kutusu için 3 adet net özet cümlesi dizisi (örn. ["Finansal Sağlık Mükemmel: ...", "Fiyat Etiketi Yüksek: ...", "Teknik Desteğe Dikkat: ..."]).
  * "blog_faqs": 3 adet soru-cevap nesnesi array'i. İLK SORU KESİNLİKLE: {"q": "❓ [TICKER] hissesine ben olsam şu an nasıl yaklaşırdım? (Yatırımcı Perspektifi)", "a": "Somut pozisyon büyüklüğü (%2,5-%5,0), 50 günlük ortalama koruma kalkanı ve kademeli alım tavsiyesi."}

GEREKLİ STAGE 2 JSON ANAHTARLARI:
19. "blog_headline": Şirket ve günün tarihine özel çekici bülten başlığı (örn. 📰 [TICKER] Analizi: Şirketin Kasası Para Dolu Ama Fiyatı Biraz Pahalı mı?)
20. "blog_summary": 2-3 detaylı paragraflık zengin günlük analiz özeti.
21. "blog_cash_and_health": Kasadaki nakit ve borç durumunu esnaf benzetmeleriyle anlatan 2-3 detaylı paragraflık makale bölümü.
22. "blog_earnings_quality": Şirketin kâr kalitesini ve Piotroski puanını anlatan 2-3 detaylı paragraflık bölüm.
23. "blog_valuation_dcf": Fiyat etiketini (P/S, F/K) ve piyasa beklentisini anlatan 2-3 detaylı paragraflık bölüm.
24. "blog_catalysts_and_risks": Büyüme fırsatları ve kritik riskler radarı.
25. "blog_bull_vs_bear": Boğa vs Ayı senaryoları ve küçük yatırımcı tavsiyesi.
26. "blog_key_takeaways": 3 adet özet cümle dizisi.
27. "blog_faqs": 3 adet soru-cevap nesnesi dizisi.
"""

STAGE2_PROMPT_EN = """You are an experienced, engaging Financial Columnist and Investment Writer.
Using the quantitative metrics and Stage 1 Quantitative Audit Findings provided, write a rich, multi-paragraph, engaging stock analysis blog article for retail investors.

STYLE AND LENGTH RULES:
- Minimum 2-3 detailed paragraphs (150-250 words) for "blog_summary", "blog_cash_and_health", "blog_earnings_quality", and "blog_valuation_dcf".
- Explain all ratios with accessible real-world business analogies.

REQUIRED STAGE 2 JSON KEYS:
19. "blog_headline": Catchy title (e.g. 📰 [TICKER] Analysis: Solid Cash Cushion vs. High Price Tag)
20. "blog_summary": Multi-paragraph plain-language executive summary thesis.
21. "blog_cash_and_health": Accessible breakdown of balance sheet cash reserves and Altman Z safety.
22. "blog_earnings_quality": Plain-language breakdown of gross margins and Piotroski score.
23. "blog_valuation_dcf": Clear explanation of P/S and P/E multiples vs Reverse DCF growth expectations.
24. "blog_catalysts_and_risks": Clear radar of top opportunities and risk factors.
25. "blog_bull_vs_bear": Simple Bull vs Bear comparison ending with a retail takeaway.
26. "blog_key_takeaways": JSON array of 3 plain summary bullet strings.
27. "blog_faqs": JSON array of 3 Q&A objects. FIRST QUESTION MUST BE EXACTLY: {"q": "❓ How would I personally approach this stock right now? (Investor Perspective)", "a": "..."}
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
    """Safely parse LLM JSON response with control character fixes and robust recovery."""
    def _log(msg):
        if callable(log_fn):
            log_fn(msg)
        else:
            print(msg)

    if not raw_content or not raw_content.strip():
        _log("   ⚠️ LLM returned empty raw content.")
        return None

    cleaned = raw_content.strip()

    # 1. Extract JSON block: try ```json ... ``` (with optional closing ```), or first '{' to last '}'
    json_str = ""
    codeblock_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})(?:\s*```)?', cleaned, re.IGNORECASE)
    if codeblock_match:
        candidate = codeblock_match.group(1).strip()
        # Ensure we cut at the last closing brace of the JSON object
        last_brace = candidate.rfind("}")
        if last_brace != -1:
            json_str = candidate[:last_brace + 1]
        else:
            json_str = candidate

    if not json_str:
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = cleaned[start_idx:end_idx + 1]
        elif start_idx != -1:
            json_str = cleaned[start_idx:]
        else:
            json_str = cleaned

    parsed_data = None

    # Parse Attempt 1: Standard json.loads
    try:
        parsed_data = json.loads(json_str)
    except Exception:
        pass

    # Parse Attempt 2: Relaxed json.loads with strict=False (allows unescaped control chars)
    if parsed_data is None:
        try:
            parsed_data = json.loads(json_str, strict=False)
        except Exception:
            pass

    # Parse Attempt 3: Strip trailing commas before closing braces/brackets
    if parsed_data is None:
        try:
            fixed_commas = re.sub(r',\s*([\}\]])', r'\1', json_str)
            parsed_data = json.loads(fixed_commas, strict=False)
        except Exception:
            pass

    # Parse Attempt 4: Truncated / Unclosed JSON repair
    if parsed_data is None:
        try:
            working = json_str.rstrip()
            # Remove trailing dangling comma or key colon if truncated
            working = re.sub(r',\s*$', '', working)
            working = re.sub(r':\s*$', ': ""', working)
            # Auto-close unclosed string quote if count of unescaped quotes is odd
            quote_count = len(re.findall(r'(?<!\\)"', working))
            if quote_count % 2 != 0:
                working += '"'

            # Count unclosed braces and brackets
            open_braces = working.count("{") - working.count("}")
            open_brackets = working.count("[") - working.count("]")
            working += "]" * max(0, open_brackets)
            working += "}" * max(0, open_braces)

            parsed_data = json.loads(working, strict=False)
        except Exception:
            pass

    if not isinstance(parsed_data, dict) or len(parsed_data) == 0:
        _log(f"   ❌ Could not parse LLM JSON output for {ticker}.")
        return None

    lang_upper = (lang or "TR").upper()
    res_dict = {}
    for key, val in parsed_data.items():
        if val and isinstance(val, str) and val.strip():
            clean_val = val.strip()
            if lang_upper == "TR" and _is_english_text(clean_val):
                _log(f"   ⚠️ Key '{key}' contained English output in TR mode.")
            res_dict[key] = clean_val
        elif val and isinstance(val, (list, dict)):
            res_dict[key] = val

    res_dict["_is_llm_generated"] = True
    res_dict["_llm_model"] = llm_model
    _log(f"   ✅ LLM commentary parsed successfully ({len(parsed_data)} sections) [Source: {llm_model}]")
    return res_dict


def _sanitize_prompt_field(value: str) -> str:
    """Sanitize a user-controlled string before embedding in LLM prompts.
    Allows alphanumeric, Turkish characters, common punctuation, and whitespace.
    Strips anything that could be used for prompt injection."""
    if not value or not isinstance(value, str):
        return ""
    # Allow: letters (including Turkish İıÖöÜüŞşÇçĞğ), digits, spaces, dots, hyphens, ampersands, parentheses, commas
    return re.sub(r'[^\w\s.\-&()/,;:\'\"#%+₺€$£¥]', '', value, flags=re.UNICODE).strip()


def _execute_llm_request(system_prompt: str, user_content: str, llm_base_url: str, llm_model: str, llm_api_key: str, timeout_val: int = 120) -> str:
    """Helper to execute streaming LLM API completion request."""
    url = f"{llm_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.3,
        "max_tokens": 8000,
        "stream": True
    }
    headers = {"Content-Type": "application/json"}
    if llm_api_key:
        headers["Authorization"] = f"Bearer {llm_api_key}"

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

    return "".join(chunks)


def generate_commentary(metrics: dict, lang: str = "TR", log_fn=None, strict_llm: bool = False) -> dict:
    """Generate qualitative commentary JSON using a 2-stage LLM API pipeline (Stage 1 Quant Audit, Stage 2 Retail Blog)."""
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

    ticker = _sanitize_prompt_field(metrics.get("ticker", "UNKNOWN"))

    sanitized_metrics = dict(metrics)
    if "name" in sanitized_metrics:
        sanitized_metrics["name"] = _sanitize_prompt_field(sanitized_metrics["name"])
    if "ticker" in sanitized_metrics:
        sanitized_metrics["ticker"] = _sanitize_prompt_field(sanitized_metrics["ticker"])

    lang_upper = (lang or "TR").upper()
    user_label = "Company Ticker" if lang_upper == "EN" else "Şirket Ticker"
    metrics_label = "Financial Metrics" if lang_upper == "EN" else "Finansal Metrikler"

    lang_note = ""
    if lang_upper == "TR":
        lang_note = "\nCRITICAL: KESİNLİKLE TÜM JSON DEĞERLERİ VE ANALİZ YORUMLARI %100 TÜRKÇE OLMALIDIR. TEK BİR İNGİLİZCE KELİME VEYA CÜMLE KULLANMA.\n"
    elif lang_upper == "EN":
        lang_note = "\nCRITICAL: ALL JSON VALUES, TEXT SUMMARIES, AND ANALYST COMMENTARY MUST BE 100% IN ENGLISH. DO NOT USE TURKISH WORDS OR PHRASES.\n"

    timeout_val = int(os.getenv("LLM_TIMEOUT", "120"))

    try:
        # ── STAGE 1: Institutional Quantitative Audit (Keys 1-18) ──
        stage1_prompt = STAGE1_PROMPT_EN if lang_upper == "EN" else STAGE1_PROMPT_TR
        stage1_content = f"{user_label}: {ticker}\n{metrics_label}:\n{json.dumps(sanitized_metrics, indent=2, ensure_ascii=False)}{lang_note}"
        
        _log(f"2a. [Stage 1/2] Requesting Institutional Quant Audit from {llm_base_url} ({llm_model})...")
        raw_stage1 = _execute_llm_request(stage1_prompt, stage1_content, llm_base_url, llm_model, llm_api_key, timeout_val)
        res_stage1 = _robust_parse_json(raw_stage1, ticker, metrics, lang, log_fn=log_fn, llm_model=llm_model)

        if not res_stage1 or not isinstance(res_stage1, dict):
            err_msg = f"LLM Commentary Stage 1 parsing failed for {ticker} at {llm_base_url}."
            _log(f"   ❌ {err_msg}")
            log_error(err_msg, context=ticker)
            return None

        # ── STAGE 2: Retail Investor Blog Article (Keys 19-27) ──
        stage2_prompt = STAGE2_PROMPT_EN if lang_upper == "EN" else STAGE2_PROMPT_TR
        stage2_content = f"{user_label}: {ticker}\n{metrics_label}:\n{json.dumps(sanitized_metrics, indent=2, ensure_ascii=False)}\n\nQUANT AUDIT FINDINGS (STAGE 1):\n{json.dumps(res_stage1 or {}, indent=2, ensure_ascii=False)}{lang_note}"

        _log(f"2b. [Stage 2/2] Requesting Retail Investor Blog Article from {llm_base_url} ({llm_model})...")
        raw_stage2 = _execute_llm_request(stage2_prompt, stage2_content, llm_base_url, llm_model, llm_api_key, timeout_val)
        res_stage2 = _robust_parse_json(raw_stage2, ticker, metrics, lang, log_fn=log_fn, llm_model=llm_model)

        # STAGE 2 RETRY MECHANISM: If Stage 2 JSON failed, attempt 1 retry with explicit fix instructions
        if not res_stage2 or not isinstance(res_stage2, dict) or not res_stage2.get("blog_summary"):
            _log(f"   ⚠️ Stage 2 JSON parse failed for {ticker}. Attempting 1 retry with strict JSON format directive...")
            retry_prompt = stage2_prompt + "\nCRITICAL FIX: RETURN ONLY VALID ESCAPED JSON. DO NOT INCLUDE EXTRA MARKDOWN OR UNESCAPED QUOTES.\n"
            raw_stage2_retry = _execute_llm_request(retry_prompt, stage2_content, llm_base_url, llm_model, llm_api_key, timeout_val)
            res_stage2 = _robust_parse_json(raw_stage2_retry, ticker, metrics, lang, log_fn=log_fn, llm_model=llm_model)

        if not res_stage2 or not isinstance(res_stage2, dict):
            err_msg = f"LLM Commentary Stage 2 blog generation failed after retry for {ticker}."
            _log(f"   ❌ {err_msg}")
            log_error(err_msg, context=ticker)
            return None

        # MERGE & VALIDATE ALL 27 MANDATORY KEYS
        final_res = dict(res_stage1)
        final_res.update(res_stage2)

        mandatory_keys = [
            "company_name", "executive_summary", "strong_points", "weak_points", "risk_discipline",
            "scorecard_commentary", "piotroski_commentary", "altman_z_commentary", "moat_and_catalysts",
            "ownership_commentary", "peer_comparison", "dupont_analysis", "forward_commentary",
            "dcf_valuation", "technical_analysis", "forensic_audit", "scenario_analysis", "investment_verdict",
            "blog_headline", "blog_summary", "blog_cash_and_health", "blog_earnings_quality",
            "blog_valuation_dcf", "blog_catalysts_and_risks", "blog_bull_vs_bear", "blog_key_takeaways", "blog_faqs"
        ]

        missing_keys = [k for k in mandatory_keys if not final_res.get(k)]
        if missing_keys:
            err_msg = f"LLM Commentary incomplete for {ticker}. Missing keys: {missing_keys}"
            _log(f"   ❌ {err_msg}")
            log_error(err_msg, context=ticker)
            return None

        final_res["_is_llm_generated"] = True
        final_res["_llm_model"] = llm_model
        return final_res

    except requests.exceptions.ConnectionError as ce:
        err_msg = f"LLM endpoint unreachable at {llm_base_url} ({ce})"
        _log(f"   ❌ {err_msg}")
        log_error(err_msg, exc=ce, context=ticker)
        return None
    except requests.exceptions.Timeout as te:
        err_msg = f"LLM request timeout at {llm_base_url} after {timeout_val}s ({te})"
        _log(f"   ❌ {err_msg}")
        log_error(err_msg, exc=te, context=ticker)
        return None
    except Exception as e:
        err_msg = f"LLM commentary error for {ticker}: {e}"
        _log(f"   ❌ {err_msg}")



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
