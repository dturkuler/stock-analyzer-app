# Changelog

All notable changes to the Stock Analyzer Platform project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-08-01

### ✨ New Features & M&A Readiness
- **Acquire.com Preparation**: Added root `LICENSE` (MIT License) establishing clear software IP ownership.
- **Dependency Management**: Added root `requirements.txt` manifest with pinned version limits and refactored `Dockerfile` to optimize layer caching.
- **Environment Configuration**: Added `STRICT_LLM=false` setting to `.env.example` with self-documenting usage guidance.
- **Mermaid Architecture Diagrams**: Embedded visual **System Architecture Flow** and **Database Entity Relationship Diagram (ERD)** into `README.md`.

### ⚡ Improvements & Refactoring
- **Environment Config Cleanup (Issue #30)**: Completely eliminated legacy provider-specific `NINEROUTER_URL` and `NINEROUTER_KEY` fallbacks in favor of standard `LLM_BASE_URL` / `BASE_URL` and `LLM_API_KEY` / `API_KEY`.
- **Analysis Log Formatting (Issue #32)**: Enhanced `1_core_builder/generate_report.py` to format ticker analysis runs with delimiter lines (`--------------------------------------------------`) and append explicit completion/failure banners (`✅ Analysis of {ticker} completed successfully.` / `❌ Analysis of {ticker} failed.`).

### 🐛 Fixes & Test Suite Polish (Issue #31)
- **Unit Test Mocking**: Replaced live yfinance 404 network fetches in `test_generate_report.py` with isolated `unittest.mock.patch`, resulting in an 8x execution speedup (0.09s test runner).
- **Log Purging**: Completely removed residual `INVALID_NONEXISTENT_TICKER_9999` error traces from `storage/logs/analysis.log` and `storage/logs/errors.log`.

---

## [2.2.1] - 2026-08-01

### 🐛 Fixes & Error Handling
- **Database Initialization Exception Logging (Issue #26)**: Replaced silent exception handling (`except Exception: pass`) during HTML metric regex parsing in `init_db()` with structured `log_error()` logging context in `3_web_server/main.py`.
- **Versioned & Safe SQLite Schema Migrations (Issue #27)**: Introduced `ensure_reports_index_schema(conn)` helper in `1_core_builder/db_schema.py` using `PRAGMA table_info` column inspection to safely migrate table schemas without unhandled DDL errors or silent exception swallows.
- **Shared Date Sanitization Helper (Issue #28)**: Extracted reusable `sanitize_report_date()` function in `1_core_builder/i18n.py` to strip language suffixes (`_TR`, `_EN`), `.html` extensions, and `_printable` markers consistently across report compilation and `/api/dates/{ticker}` web server endpoints.

### 🧪 Automated Testing & Code Quality
- **100% Automated Test Suite Verification**: All 43 automated unit and integration tests passed cleanly (up from 41).
- **New Test Fixtures**: Added `test_sanitize_report_date` and `test_ensure_reports_index_schema` tests in `tests/test_html_compiler.py` and `tests/test_generate_report.py`.

---

## [2.2.0] - 2026-08-01

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

---

## [2.1.0] - 2026-08-01

### ✨ New Features & LLM Transparency
- **LLM Execution Transparency & Stream Logs**: Full streaming progress, model metadata, and response section counts are now logged directly to `analysis.log` and visible in the Web Dashboard (`/api/logs`).
- **AI Provenance Badges**: HTML report headers now visually display clean badges indicating whether commentary was generated by AI (`🤖 Live AI Analysis`) or structured metrics.
- **Strict No-Fallback Mode & Fast Batch Transition**: Disabled automatic fallback commentary (`ALLOW_FALLBACK=false`). If LLM commentary fails, report generation aborts with exit code `1`, and the scheduler immediately advances to the next stock in your watchlist without retry delays.

### 🐛 Fixes & Data Integrity
- **OpenRouter SSE Reasoning Model Support**: Fixed stream parsing for OpenRouter / DeepSeek reasoning models (`opencode_combo`, `gemini_combo`) streaming tokens in `delta["reasoning"]` and sending SSE comments.
- **Dirty / Truncated JSON Auto-Repair**: Added trailing comma cleanup and unclosed brace/quote auto-repair to ensure ~10,000-byte complex financial JSON outputs parse cleanly.
- **Metric Key Alignment**: Fixed `altman_z_score["z_score"]` and `valuation_parameters["wacc"]` lookup keys in log analysis and SQLite database indexing.
- **Dynamic Net Debt Evaluation & Financial Sector Guards**: Dynamically evaluated net debt status (`net_debt < 0` vs `net_debt > 0`) in English & Turkish templates, and added bank sector guard checks to Altman Z calculations.

### 🧪 Automated Testing & Infrastructure
- **100% Test Suite Coverage**: All 31 automated unit and integration tests passing.
- **Production Container Release Stack**: Updated Docker deployment pipeline for `v2.1.0`.

---

## [2.0.0] - 2026-07-31

### 🚀 Major v2 Architectural & UI/UX Redesign
- **Top Navigation Restructuring**: Replaced mode select dropdown with top-level view buttons (`[ 📈 Single Ticker View ]`, `[ 📄 PDF View ]`, `[ 📊 All-Stocks Matrix ]`, and `[ 🖨️ Export PDF ]`).
- **Sector-Dynamic Banking Valuation Engine**: Integrated automatic banking sector detection. Financial institution reports dynamically substitute traditional DCF models with Price-to-Book vs. ROE (PB-ROE) regression and Dividend Discount Models (DDM).
- **Interactive 2D DCF Slider Sandbox**: Added real-time WACC and Growth range sliders above the DCF sensitivity matrix with instant client-side recalculations.
- **Multilingual i18n System**: Implemented full Turkish and English internationalization (`TR`/`EN`) across navigation headers, modal dialogs, analyst commentary, and iframe views.
- **Dynamic Metric-Driven AI Blog Engine**: Upgraded `llm_commentary.py` to evaluate ticker metrics dynamically to generate unique, stock-tailored investor bülten headlines and insights.

### 🐛 Bug Fixes & Stability
- **Admin Log Drawer Isolation**: Fixed HTML template container nesting in `main.py` by isolating `#adminDomainTabLogs` in its own top-level container div.
- **Console Log Overwrite Cleanup**: Removed `data-i18n="log_loading"` attribute on `#fileConsoleBox` which previously overwrote loaded log text upon language switching.
- **`jumpToLog` Controller Fix**: Updated `jumpToLog()` function in `main.py` to target the `'logs'` tab instead of `'settings'`.
- **Pre-Rendered Report Cache Regeneration**: Regenerated all stored HTML reports under `storage/reports/` to refresh pre-compiled files with dynamic headlines.
- **Multilingual Variable Scoping**: Resolved `UnboundLocalError` in `_fallback_commentary()` by properly scoping `is_bank`, `net_debt`, and `beneish_m` variables.
- **Blog Net Debt Stat Labeling**: Added dynamic sign evaluation (`net_debt < 0`) to distinguish "Net Nakit Deposu" from "Net Borç Pozisyonu" in blog cards.

---

## [1.7.2] - 2026-07-30

### 🧮 Advanced Quantitative Models & Financial Formulas
- **Altman Z'' Emerging Market & BIST Model**: Auto-detects BIST and Emerging Market tickers (`.IS`, `.NS`, `.SA`, etc.) and applies the specialized Altman Z'' 4-variable model ($6.56X_1 + 3.26X_2 + 6.72X_3 + 1.05X_4$) to accurately evaluate non-manufacturing and emerging market financial health.
- **Beneish M-Score Earnings Manipulation Detector**: Integrated 8-variable Beneish M-Score ($M \le -1.78$) into financial data sourcing (`fetch_yfinance.py`) and matrix analytics to detect accounting anomalies.
- **DuPont 5-Step ROE Decomposition**: Implemented 5-step ROE decomposition (Tax Burden, Interest Burden, Operating Margin, Asset Turnover, Financial Leverage) for deep financial performance analysis.

### 🛡️ Dashboard UI & Ticker Folder Sanitization
- **Ticker Directory Filtering**: Updated `/api/tickers` and `/api/v1/matrix` endpoints in `main.py` to sanitize directory scans and ignore folders starting with `.`, `-`, or `_`. Prevents invalid folder names (e.g. `--ticker`) from crashing the stock dashboard and sidebar.

### 🔒 Storage & File Permission Fixes
- **Cross-Environment Write Safety**: Configured explicit `os.umask(0000)` and fixed root ownership permissions across `storage/` volume to eliminate `PermissionError: [Errno 13]` when executing analysis scripts between Docker containers and host environments.

### 🧪 Automated Testing & Reliability
- **Comprehensive Unit Tests**: Updated unit test suite in `tests/test_fetch_yfinance.py` covering Developed vs. Emerging Market Altman Z models, Beneish M-Score, and DuPont decomposition (100% pass rate across all 30 tests).

---

## [1.7.1] - 2026-07-29

### ✨ Features & UI Polish
- **Dynamic App Version Badge**: Rendered dynamic app version (`v1.7.1`) in the Admin Panel Modal footer, sourced directly from `VERSION`.
- **Clean Admin Panel Labels**: Simplified all Admin Panel input labels and headings by removing redundant raw `.env` variable names (e.g. `Yönetici Şifresi (ADMIN_PASSWORD):` ➔ `Yönetici Şifresi:`), producing a sleek, professional UI aesthetic in both Turkish and English.

---

## [1.7.0] - 2026-07-29

### ✨ New Features & Admin Panel Enhancements
- **Admin Panel Autonomous Cron Scheduler Setup**: Added a dedicated **"⏰ Otomatik Analiz & Cron Zamanlayıcı Ayarları"** card inside the Admin Settings modal in the web interface.
- **SQLite Configuration Persistence (`cron_config`)**: Created a dedicated `cron_config` table in `storage/app.db` to persist schedule parameters (`schedule_time`, `timezone`, `run_days`, `misfire_grace_minutes`, `ticker_delay_seconds`, `is_enabled`) dynamically without requiring environment file edits or container restarts.
- **Misfire Grace Period & Catch-Up Protection**: Configured a **120-minute (2 hours)** misfire grace period (`misfire_grace_time=7200`). If host systems or Docker containers wake up late (e.g. PC turned on at 20:00 TSI instead of 18:30 TSI), missed daily runs execute immediately upon wake-up instead of being skipped.
- **Explicit Timezone & Schedule Frequency Controls**: Bound scheduler execution to `Europe/Istanbul` (TSI UTC+3) with presets for **Weekdays (Mon-Fri)**, **Everyday (Mon-Sun)**, or custom days.
- **On-Demand Background Trigger ("Run Cron Now")**: Added a `POST /api/cron/run-now` REST endpoint and UI button to trigger asynchronous background stock analysis on demand with an `is_running` single-execution lock guard.
- **Real-Time Status & Next Run Preview**: Live UI status badge showing 🟢 **Active** / 🟡 **Running [Ticker X/10]** / 🔴 **Paused**, plus a preview timestamp for the next scheduled run.

### 🌐 Internationalization (i18n)
- **Bilingual Admin UI Support**: Added full English (`locales/en.json`) and Turkish (`locales/tr.json`) localization strings for all scheduler controls, badges, and time pickers.

### 📖 Architecture & Documentation
- **Domain Model & ADR Documentation**: Added domain model glossary (`CONTEXT.md`) and Architectural Decision Record (`docs/adr/0001-admin-cron-scheduler-setup.md`).

---

## [1.6.0] - 2026-07-27

### 🛡️ Security & Hardening
- **CORS Hardening (VULN-001)**: Restricted CORS middleware origins from wildcard (`*`) to configurable `ALLOWED_ORIGINS` (defaults to `http://localhost:6031`).
- **Credential Masking in API (VULN-002)**: Masked sensitive values (`ADMIN_PASSWORD: "••••••••"` and `LLM_API_KEY: "••••1619"`) in `/api/settings` response, added status booleans, and protected settings update from overwriting `.env` values with masked strings.
- **Log Cleaning (VULN-003)**: Removed ephemeral admin password printing to stdout on server startup.
- **Brute-Force Rate Limiting (VULN-004)**: Added IP sliding-window rate limiting on `/api/admin/verify` (max 5 failed attempts per 60 seconds -> HTTP 429 Too Many Requests).
- **XSS Protection (VULN-005)**: Implemented frontend `escapeHtml()` utility and sanitized innerHTML template interpolations for ticker symbols, company names, and report language fields.
- **LLM Prompt Injection Mitigation (VULN-007)**: Added `_sanitize_prompt_field()` in prompt generator to strip control characters while maintaining full support for Turkish characters (`İıÖöÜüŞşÇçĞğ`).

### 🛠️ Code Health & Refactoring
- **Scripts Directory Reorganization**: Consolidated startup shell scripts into a clean `scripts/` directory with root-level proxies.
- **Module Import Fix**: Resolved BeautifulSoup4 (`bs4`) module name checking in `fetch_yfinance.py` auto-installer.
- **100% Automated Test Suite Verification**: Added security test cases for rate limiting and credential masking, achieving 28/28 passing tests.

---

## [1.5.1] - 2026-07-27

### 📖 Documentation & Operations
- **VPS Production Deployment Guide**: Created comprehensive step-by-step production deployment guide (`documentation/vps_deployment_guide.md`) covering Docker Compose host volume mounting (`./storage`), `.env` environment security, Cloudflare Tunnel (`cloudflared`) systemd setup, firewall lockdown (`ufw`), and VPS disk snapshot recovery.
- **Documentation Index Update**: Linked VPS deployment guide in `documentation/README.md` and root `README.md` Docker deployment section.

---

### ✨ Added
- **All-Stocks Valuation & Comparison Matrix**: Full-screen stock screener and side-by-side comparison table featuring 360° Weighted Composite Assessment Scores (0.0 – 10.0), color-coded Verdict Badges (`🟢 Strong Buy`, `🔵 Balanced`, `🟡 Neutral`, `🔴 High Risk`), sortable columns, live search box, and preset filter pills (`🌐 All Stocks`, `🟢 Strong Buy`, `🛡️ Safe Balance Sheet`, `🔥 High Cash Quality`, `💎 Bargain Valuation`).
- **Default Landing View**: Configured the Stock Matrix comparison view as the primary default start page upon opening the web platform (`http://localhost:8000`).
- **Header Admin Panel Icon**: Added a 34x34px Admin Panel icon button (`⚙️`) directly next to the theme toggle icon (`🌙`/`☀️`) in the top navigation header for 1-click access.

### ⚡ Improved
- **Full Light & Dark Theme Synchronization**: Implemented `[data-theme="light"]` CSS variables and smooth transitions across the main navigation header, dropdowns, inputs, modals, admin panels, stock screener matrix, and report iframe.
- **Client-Side i18n Catalog**: Expanded client-side `UI_I18N` translation dictionary for real-time localized switching (headers, filter pills, search input placeholders, currency symbols, and verdict labels).

### 🐛 Fixed & Cleaned
- **Multi-Location Matrix Scanner**: Updated matrix endpoint (`GET /api/v1/matrix`) to scan both `storage/_workspace/` and `storage/reports/{ticker}/` folders, with auto-sourcing for any unindexed stocks.
- **Report Sidebar Clean-Up**: Removed redundant bottom Admin Panel button from report dashboard sidebars to keep research navigation focused.

---

### ✨ Added
- **6-Section Deep-Dive Article Architecture for Module 13**: Expanded AI Stock Market Blog & Investor Briefing into a publication-grade equity research report incorporating all 12 quantitative models (Piotroski, Altman Z, Beneish M-Score, DuPont 5-Step, Reverse DCF, Peer Benchmarks).
- **Embedded Visual Callout Widgets**: In-article mini stat callout badges (Net Cash, Altman Z, Piotroski, Gross Margin %, P/S ratio, Reverse DCF $g$) and a 4-card Target Price Scenario Grid (`🔴 Sert Düşüş`, `🟡 Ayı`, `🔵 Baz`, `🟢 Boğa`).
- **Retail Investor Storyteller Persona**: Updated LLM system prompts and fallback commentary to translate technical financial jargon into plain language with everyday business/shopkeeper analogies.

### ⚡ Improved
- **Smart HTML Text Parser (`format_analyst_text`)**: Automatically detects inline numbers, section headers, and catalysts/risks into side-by-side 2-column visual cards (`.grid-2`).
- **Decimal-Safe Regex Parsing**: Preserves currency values (`₺390.8M`) and decimal percentage ranges (`%2,5 - %5,0`) without string fragmentation.
- **Sidebar & Header Clean-Up**: Removed hardcoded module numbers (`1.`, `2.`, `13.`) from sidebar navigation and header ticker search box for a cleaner modern UI.

### 🐛 Fixed
- **Module 13 API Response**: Updated `POST /api/v1/modules/13/generate` payload to return `blog_cash_and_health`, `blog_earnings_quality`, `blog_valuation_dcf`.

---

### ✨ Added
- Unified JSON localization catalogs (`1_core_builder/locales/{en,tr}.json` & `3_web_server/locales/{en,tr}.json`) for decoupled report compilation and Web UI rendering.
- Public `documentation/` folder with modular guides covering i18n extensions, financial metrics, new report tab creation, and Web Server REST API architecture.

### ⚡ Improved
- 100% full English HTML report compilation across all 13 core modules.
- Enriched English investor guide texts with dynamic quantitative metrics, net debt/cash figures, and technical support levels.

### 🛡️ Security
- Untracked local development notes (`docs/`) in `.gitignore`.
- Sanitized locale placeholder strings with generic public API endpoints and model names.

---

## [1.2.1] - 2026-07-26

### 🛡️ Security
- Sanitized environment configuration templates (`.env.example`) and public documentation to use generic placeholder URLs and credentials.
- Embedded strict Security & Privacy directives into release skills preventing secret leaks and shielding internal `.gitignore` files.

### 📖 Documentation
- Translated UI button labels and modal descriptions in `README.md` to English i18n (`🔒 Admin Panel`, `⚡ Analyze`, `🚀 Run All`, `🗑️ Clear Logs`).
- Added direct link to `CHANGELOG.md` in `README.md` navigation bar while keeping changelog details strictly isolated in `CHANGELOG.md`.

---

## [1.2.0] - 2026-07-26

### ✨ Added
- Centralized `VERSION` file (`v1.2.0`) integrated with Web API (`/api/settings`), HTML compiler, and Docker scripts.
- Universal `release.config.json` support for per-project release overrides.
- Consolidated 7-step `/full-release` pipeline skill with automated test gate, SemVer detection, and changelog generator.

### 🐛 Fixed
- Restored `WATCHLIST_PATH`, `BUILDER_SCRIPT`, and `SCHEDULER_SCRIPT` web server path constants.
- Added 5-attempt retry loop to Docker release container health check.
- Optimized `.gitignore` and `.dockerignore` for security and clean repository isolation.

---

## [1.0.0] - 2026-07-25

### ✨ Added
- Initial public release of Stock Analyzer Platform.
- Multi-lingual financial report generation (TR/EN).
- Password-protected Admin panel with inline stock editing and live analysis log viewing.
