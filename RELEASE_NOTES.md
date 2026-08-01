## What's Changed in Release v2.3.0

### ✨ New Features & M&A Readiness
- **Acquire.com Preparation**: Added root `LICENSE` (MIT License) establishing clear software IP ownership.
- **Dependency Management**: Added root `requirements.txt` manifest with pinned version limits and refactored `Dockerfile` to optimize layer caching.
- **Environment Configuration**: Added `STRICT_LLM=false` setting to `.env.example` with self-documenting usage guidance.
- **Mermaid Architecture Diagrams**: Embedded visual **System Architecture Flow** and **Database Entity Relationship Diagram (ERD)** into `README.md`.

### ⚡ Improvements & Refactoring
- **Environment Config Cleanup**: Completely eliminated legacy provider-specific `NINEROUTER_URL` and `NINEROUTER_KEY` fallbacks in favor of standard `LLM_BASE_URL` / `BASE_URL` and `LLM_API_KEY` / `API_KEY`.
- **Analysis Log Formatting**: Enhanced `1_core_builder/generate_report.py` to format ticker analysis runs with delimiter lines (`--------------------------------------------------`) and append explicit completion/failure banners (`✅ Analysis of {ticker} completed successfully.` / `❌ Analysis of {ticker} failed.`).

### 🐛 Fixes & Test Suite Polish
- **Unit Test Mocking**: Replaced live yfinance 404 network fetches in `test_generate_report.py` with isolated `unittest.mock.patch`, resulting in an 8x execution speedup (0.09s test runner).
- **Log Purging**: Completely removed residual `INVALID_NONEXISTENT_TICKER_9999` error traces from `storage/logs/analysis.log` and `storage/logs/errors.log`.
