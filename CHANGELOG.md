# Changelog

All notable changes to the Stock Analyzer Platform project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
