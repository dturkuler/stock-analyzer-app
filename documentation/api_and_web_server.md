# 🌐 Developer Guide: Web Server & API Architecture

This document outlines the architecture, HTTP request handlers, SQLite database schema, and security features of `3_web_server/main.py`.

---

## 🏛️ Architecture Overview

The web server is built using **FastAPI** and **Uvicorn**, providing asynchronous request routing, JSON validation, and high-performance HTML/REST API responses.

- **Port**: `6031` (mapped in `docker-compose.yml`)
- **Database**: SQLite database stored at `storage/app.db`
- **Config Storage**: Environment variables loaded from `.env`

---

## 📡 REST API Endpoints

| Method | Path | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | No | Serves the main SPA Dashboard UI. |
| `GET` | `/api/watchlist` | No | Returns array of tracked tickers in SQLite database. |
| `POST` | `/api/watchlist` | Yes (`X-Admin-Password`) | Adds a new ticker to watchlist and queues analysis. |
| `DELETE` | `/api/watchlist?ticker=XYZ` | Yes (`X-Admin-Password`) | Removes a ticker from watchlist and SQLite database. |
| `GET` | `/api/v1/matrix` | No | Returns all-stocks quantitative metrics matrix array. |
| `GET` | `/api/reports/{ticker}/{date}` | No | Serves compiled HTML report (`mode=dashboard` or `mode=printable`, `lang=TR/EN`). |
| `GET` | `/api/settings` | Yes (`X-Admin-Password`) | Retrieves system configuration settings. |
| `POST` | `/api/settings` | Yes (`X-Admin-Password`) | Updates `.env` configuration file dynamically. |
| `GET` | `/api/logs/files` | Yes (`X-Admin-Password`) | Reads active log file (`log_type=cron|analysis|live`). |
| `POST` | `/api/logs/clear` | Yes (`X-Admin-Password`) | Truncates target log file contents. |
| `POST` | `/api/reprocess` | Yes (`X-Admin-Password`) | Triggers report generation for a single stock or batch run. |
| `GET` | `/api/reprocess/status` | No | Returns background batch reprocessing status and progress. |
| `POST` | `/api/verify_admin` | No | Verifies admin password credentials. |

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
    status TEXT DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, report_date)
);

CREATE TABLE IF NOT EXISTS watchlist (
    ticker TEXT PRIMARY KEY,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);
```

---

## 🔒 Security & Input Validation
1. **Path Traversal Protection**: Sanity checks reject any path parameter containing `..` or leading slashes (`/`) with HTTP 400 Bad Request.
2. **Password Masking**: The API masks `ADMIN_PASSWORD` and `LLM_API_KEY` when returning settings to non-authenticated clients.
3. **HTTP Header Auth**: Protected endpoints inspect `X-Admin-Password` header or `password` JSON field against `ADMIN_PASSWORD`.
