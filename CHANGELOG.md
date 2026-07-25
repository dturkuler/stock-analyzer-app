# Changelog

All notable changes to the Stock Analyzer Platform project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
