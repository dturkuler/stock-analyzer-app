# 🌐 Developer Guide: Adding a New Language (i18n) (v2.3.0)

This guide provides step-by-step instructions for adding internationalization (i18n) support for a new language (e.g., German `DE`, French `FR`, Spanish `ES`).

---

## 🛠️ Step-by-Step Procedure

### 1. Create Core Report Catalog
Create a new JSON catalog file in `1_core_builder/locales/` named `<lang_code>.json` (lowercase):
- **Path**: `1_core_builder/locales/de.json`
- Copy keys from `1_core_builder/locales/en.json` and translate values:

```json
{
  "lang": "DE",
  "menu_title": "Module",
  "theme_dark": "Dunkles Thema",
  "theme_light": "Helles Thema",
  "btn_print": "Drucken / PDF herunterladen",
  "btn_admin": "🔒 Admin-Panel",
  "tab_exec": "🏛️ Zusammenfassung",
  "tab_scorecard": "⭐ 1. 360° Unternehmensbewertung"
}
```

### 2. Create Web UI Catalog
Create a matching JSON catalog file in `3_web_server/locales/`:
- **Path**: `3_web_server/locales/de.json`
- Copy keys from `3_web_server/locales/en.json` and translate values:

```json
{
  "app_title": "📊 Stock Analyzer — Aktienanalyse Platform",
  "menu_overview": "📈 Aktienübersicht",
  "menu_watchlist": "⭐ Beobachtungsliste",
  "menu_reprocess": "🔄 Aktie Analysieren",
  "menu_settings": "⚙️ System-Einstellungen"
}
```

### 3. Register LLM Commentary Language Enforcer
In `1_core_builder/llm_commentary.py`, ensure the target language prompt instruction is defined for the 2-Stage LLM commentary pipeline (Stage 1 Quant Audit & Stage 2 Retail Blog Briefing):

```python
lang_instruction = "Respond ENTIRELY in German." if lang == "DE" else ("Respond ENTIRELY in Turkish." if lang == "TR" else "Respond ENTIRELY in English.")
```

### 4. Update Format Helpers (Optional)
If the new language requires specific currency symbols (e.g. `€`) or decimal formatting:
- Inspect `_fmt_try`, `_fmt_num`, and `_fmt_pct` in `1_core_builder/html_compiler.py`.
- Pass `is_en=(lang.upper() in ["EN", "DE", "FR"])` or configure locale-specific currency rules.

### 5. Run & Test
Test report compilation with the new language code:

```bash
# Generate report for Apple (AAPL) in German
python3 1_core_builder/generate_report.py AAPL --lang DE

# Execute test suite runner
python3 tests/run_tests.py
```
