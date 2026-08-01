# 🌐 Developer Guide: Web Server & API Architecture (v2.3.0)

This document outlines the architecture, HTTP request handlers, SQLite database schema, and security features of `3_web_server/main.py`.

---

## 🏛️ Architecture Overview

The web server is built using **FastAPI** and **Uvicorn**, providing asynchronous request routing, JSON validation, and high-performance HTML/REST API responses.

- **Port**: `6031` (mapped in `docker-compose.yml`)
- **Database**: SQLite database stored at `storage/app.db` managed via `1_core_builder/db_schema.py`
- **Config Storage**: Environment variables loaded from `.env`
- **Session Access Logging**: Logs client IP and timestamp on initial/new session start (`[YYYY-MM-DD HH:MM:SS] IP: x.x.x.x`)

---

## 📡 REST API Endpoints

| Method | Path | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | No | Serves the main SPA Dashboard UI. |
| `GET` | `/api/tickers` | No | Returns array of tracked stock tickers in SQLite database. |
| `GET` | `/api/reports/index` | No | Returns summary array of indexed report metadata. |
| `GET` | `/api/reports/{ticker}/latest` | No | Returns latest compiled HTML report for ticker. |
| `GET` | `/api/reports/{ticker}/{date}` | No | Serves compiled HTML report (`mode=dashboard` or `mode=printable`). Sanitizes date suffixes. |
| `GET` | `/api/v1/matrix` | No | Returns all-stocks quantitative metrics matrix array. |
| `GET` | `/api/valuation-history` | No | Returns historical valuation metrics for GFX charts. |
| `GET` | `/api/watchlist` | No | Returns active/inactive watchlist items. |
| `POST` | `/api/watchlist` | Yes (`X-Admin-Password`) | Adds a new ticker to watchlist (`ticker`, `company_name`, `lang`). |
| `PUT` | `/api/watchlist/{id}` | Yes (`X-Admin-Password`) | Updates watchlist item active status or preferred language. |
| `DELETE` | `/api/watchlist/{id}` | Yes (`X-Admin-Password`) | Removes stock from watchlist. |
| `GET` | `/api/settings` | Yes (`X-Admin-Password`) | Retrieves system configuration settings (passwords masked). |
| `POST` | `/api/settings` | Yes (`X-Admin-Password`) | Updates `.env` configuration file dynamically. |
| `GET` | `/api/logs/files` / `GET /api/logs/{type}` | Yes (`X-Admin-Password`) | Reads active log file (`cron`, `analysis`, `errors`, `live`). |
| `POST` | `/api/logs/clear/{log_type}` | Yes (`X-Admin-Password`) | Truncates target log file contents (`cron`, `analysis`, `errors`, `live`, `all`). |
| `POST` | `/api/reprocess/{ticker}` | Yes (`X-Admin-Password`) | Triggers report generation for a single stock. |
| `POST` | `/api/reprocess/batch` | Yes (`X-Admin-Password`) | Triggers batch report generation for all active stocks. |
| `GET` | `/api/reprocess/status/{ticker}` | No | Returns background reprocessing status and log stream. |
| `POST` | `/api/admin/verify` | No | Verifies admin password credentials against `ADMIN_PASSWORD`. |

---

## 🗄️ Database Schema (`storage/app.db`)

```sql
CREATE TABLE IF NOT EXISTS reports_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    report_date TEXT NOT NULL,
    file_path TEXT NOT NULL,
    printable_path TEXT,
    piotroski_score INTEGER,
    altman_z REAL,
    beneish_m REAL,
    wacc_pct REAL,
    status TEXT DEFAULT 'SUCCESS',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, report_date)
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE NOT NULL,
    company_name TEXT,
    is_active INTEGER DEFAULT 1,
    lang TEXT DEFAULT 'TR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔒 Security & Input Validation
1. **Path Traversal Protection**: Sanity checks reject any path parameter containing `..` or leading slashes (`/`) with HTTP 400 Bad Request.
2. **Password Masking**: The API masks `ADMIN_PASSWORD` and `LLM_API_KEY` when returning settings to non-authenticated clients.
3. **HTTP Header & JSON Auth**: Protected endpoints inspect `X-Admin-Password` header or `password` JSON field against `ADMIN_PASSWORD`.
