## What's Changed in Release v2.2.0

### ✨ New Features & Organic AI Commentary
- **Decoupled AI Model Verdict & Rating (`verdict_rating`)**: Separated short rating badges (`🟢 GÜÇLÜ MODEL ALIM`, `🟡 TEMKİNLİ NÖTR GÖRÜŞ`, `🔴 YÜKSEK İFLAS VE PAHALILIK RİSKİ`) from the multi-paragraph model assessment review.
- **Organic 2-Paragraph Equity Research Review (`investment_verdict`)**: Upgraded `llm_commentary.py` prompts to generate rich, multi-paragraph organic equity research syntheses detailing balance sheet health, ROE efficiency, valuation upside, WACC cost of capital, and technical support levels without rigid template phrases.
- **Enhanced Stage 1 Retry Mechanism**: Added automatic retry with strict formatting instructions if Stage 1 encounters a stream timeout or partial network drop.

### 🐛 Fixes & Data Integrity
- **GFX Financial Time Series Date Sanitization**: Stripped trailing language suffixes (`_TR`, `_EN`) from GFX time series chart points, tooltips, data tables, and date dropdown options in `main.py` and `html_compiler.py`.
- **Pipeline Exit Code Propagation**: Resolved issue where failed pipeline executions suppressed exit code `1` (#24, #25).
- **SQLite `reports_index` Database Scrub**: Automatically scrubbed legacy dirty date records and duplicate rows from `storage/app.db`.

### 🧪 Automated Testing & Code Health
- **100% Automated Test Suite Verification**: Passed all 41 unit and integration tests cleanly.
- **Test Directory Cleanup Guard**: Added automatic cleanup to test fixtures (`test_generate_report.py`) to keep local workspace free of test artifacts.
