## What's Changed in Release v2.3.1

### ⚡ Improvements & Concurrency (Issue #33)
- **Thread-Safe SQLite Database Connections**: Added `get_db_connection(db_path, timeout=30.0)` in `1_core_builder/db_schema.py` enforcing busy timeouts and `PRAGMA journal_mode=WAL;` across `generate_report.py`, `scheduler.py`, and `main.py` to prevent database locking during concurrent web server and background cron runs.
- **Indexed Report Date Lookups**: Refactored `GET /api/dates/{ticker}` in `3_web_server/main.py` to query indexed SQLite `reports_index` table before falling back to synchronous disk globbing.
- **Dynamic Sector Peer Benchmarking**: Enhanced `fetch_peer_benchmark_data()` in `1_core_builder/fetch_yfinance.py` to select sector-relevant peer benchmark tickers (Banking, Healthcare, Energy, Consumer, Tech) for both BİST and global equity tickers.

### 🐛 Fixes & Code Quality (Issue #33)
- **Purged Import-Time Pip Execution**: Removed `auto_install_dependencies()` from `1_core_builder/fetch_yfinance.py`, eliminating runtime installer side-effects on module import.
- **Test Suite Polish**: Cleaned up duplicate test runner block in `tests/test_html_compiler.py`.

### 🧪 Automated Testing & Code Health
- **100% Test Suite Pass Rate**: Verified all 43 automated unit and integration tests cleanly in 0.09s.
