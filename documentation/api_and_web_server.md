# 🌐 Developer Guide: Web Server & API Architecture

This document outlines the architecture, HTTP request handlers, SQLite database schema, and security features of `3_web_server/main.py`.

---

## 🏛️ Architecture Overview

The web server is built using standard Python HTTP server modules (`http.server.HTTPServer` / `BaseHTTPRequestHandler`), eliminating heavy external dependencies while guaranteeing high performance.

- **Port**: `8000` (mapped in `docker-compose.yml`)
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
| `GET` | `/api/settings` | Yes (`X-Admin-Password`) | Retrieves system configuration settings. |
| `POST` | `/api/settings` | Yes (`X-Admin-Password`) | Updates `.env` configuration file dynamically. |
| `GET` | `/api/logs` | Yes (`X-Admin-Password`) | Streams live pipeline execution logs (`analysis.log`). |
| `POST` | `/api/verify_admin` | No | Verifies admin password credentials. |

---

## 🗄️ Database Schema (`storage/app.db`)

```sql
CREATE TABLE IF NOT EXISTS reports (
    ticker TEXT PRIMARY KEY,
    company_name TEXT,
    report_date TEXT,
    file_path TEXT,
    printable_path TEXT,
    piotroski_score INTEGER,
    altman_z_score REAL,
    wacc REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlist (
    ticker TEXT PRIMARY KEY,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔒 Security & Input Validation
1. **Path Traversal Protection**: Sanity checks reject any path parameter containing `..` or leading slashes (`/`) with HTTP 400 Bad Request.
2. **Password Masking**: The API masks `ADMIN_PASSWORD` and `LLM_API_KEY` when returning settings to non-authenticated clients.
3. **HTTP Header Auth**: Protected endpoints inspect `X-Admin-Password` header or `password` JSON field against `ADMIN_PASSWORD`.
