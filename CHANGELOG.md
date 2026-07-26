# Changelog

All notable changes to the Stock Analyzer Platform project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-07-27

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
