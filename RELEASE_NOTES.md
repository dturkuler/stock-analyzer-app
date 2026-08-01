## What's Changed in Release v2.2.1

### 🐛 Fixes & Error Handling
- **Database Initialization Exception Logging (Issue #26)**: Replaced silent exception handling (`except Exception: pass`) during HTML metric regex parsing in `init_db()` with structured `log_error()` logging context in `3_web_server/main.py`.
- **Versioned & Safe SQLite Schema Migrations (Issue #27)**: Introduced `ensure_reports_index_schema(conn)` helper in `1_core_builder/db_schema.py` using `PRAGMA table_info` column inspection to safely migrate table schemas without unhandled DDL errors or silent exception swallows.
- **Shared Date Sanitization Helper (Issue #28)**: Extracted reusable `sanitize_report_date()` function in `1_core_builder/i18n.py` to strip language suffixes (`_TR`, `_EN`), `.html` extensions, and `_printable` markers consistently across report compilation and `/api/dates/{ticker}` web server endpoints.

### 🧪 Automated Testing & Code Quality
- **100% Automated Test Suite Verification**: All 43 automated unit and integration tests passed cleanly (up from 41).
- **New Test Fixtures**: Added `test_sanitize_report_date` and `test_ensure_reports_index_schema` tests in `tests/test_html_compiler.py` and `tests/test_generate_report.py`.
