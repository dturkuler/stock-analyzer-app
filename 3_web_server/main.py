"""
Independent FastAPI Web Server, SPA Dashboard Viewer & Admin Panel
Usage: py -m uvicorn .agents.skills.stock-analyzer-app.3_web_server.main:app --port 6031
"""

import os
import sys
import glob
import json
import sqlite3
import secrets
import subprocess
import asyncio
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(APP_ENV_PATH)
load_dotenv()

app = FastAPI(title="Stock Research Platform & Password-Protected Admin Panel")

REPORTS_DIR = os.path.join(BASE_DIR, "storage", "reports")
LOGS_DIR = os.path.join(BASE_DIR, "storage", "logs")
DB_PATH = os.path.join(BASE_DIR, "storage", "app.db")
WATCHLIST_PATH = os.path.join(BASE_DIR, "2_cron_scheduler", "watchlist.json")
BUILDER_SCRIPT = os.path.join(BASE_DIR, "1_core_builder", "generate_report.py")
SCHEDULER_SCRIPT = os.path.join(BASE_DIR, "2_cron_scheduler", "scheduler.py")
VERSION_PATH = os.path.join(BASE_DIR, "VERSION")

def get_app_version():
    if os.path.exists(VERSION_PATH):
        try:
            with open(VERSION_PATH, "r", encoding="utf-8") as f:
                ver = f.read().strip()
                if ver:
                    return ver
        except Exception:
            pass
    return "1.1.0"


PYTHON_EXEC = "py" if os.name == "nt" else sys.executable

# Global task state tracking
PROCESS_STATUS = {}
_EPHEMERAL_ADMIN_PASSWORD = None


def get_admin_password():
    global _EPHEMERAL_ADMIN_PASSWORD
    load_dotenv(APP_ENV_PATH, override=True)
    env_pass = os.getenv("ADMIN_PASSWORD")
    if env_pass and env_pass.strip():
        return env_pass.strip()
    if not _EPHEMERAL_ADMIN_PASSWORD:
        _EPHEMERAL_ADMIN_PASSWORD = secrets.token_hex(16)
        print(f"⚠️ ADMIN_PASSWORD is not set in .env! Generated ephemeral admin password: {_EPHEMERAL_ADMIN_PASSWORD}")
    return _EPHEMERAL_ADMIN_PASSWORD


def verify_password_header(x_admin_password: Optional[str] = Header(None)):
    current_pass = get_admin_password()
    if not x_admin_password or not secrets.compare_digest(x_admin_password, current_pass):
        raise HTTPException(status_code=401, detail="Geçersiz Yönetici Şifresi. Lütfen .env şifrenizi giriniz.")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE NOT NULL,
            company_name TEXT,
            is_active INTEGER DEFAULT 1,
            lang TEXT DEFAULT 'TR',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            report_date TEXT NOT NULL,
            file_path TEXT NOT NULL,
            piotroski_score INTEGER,
            altman_z REAL,
            beneish_m REAL,
            wacc_pct REAL,
            status TEXT NOT NULL,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, report_date)
        );
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM watchlist")
    if cur.fetchone()[0] == 0 and os.path.exists(WATCHLIST_PATH):
        try:
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                tickers = json.load(f)
            for t in tickers:
                cur.execute("INSERT OR IGNORE INTO watchlist (ticker, company_name, is_active) VALUES (?, ?, 1)", (t, t))
            conn.commit()
        except Exception as e:
            print(f"⚠️ Error seeding DB from watchlist.json: {e}")
    conn.close()

init_db()


def sync_watchlist_json():
    """Sync active tickers from DB to watchlist.json for the cron scheduler."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT ticker FROM watchlist WHERE is_active = 1 ORDER BY ticker ASC")
    active_tickers = [row[0] for row in cur.fetchall()]
    conn.close()

    os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(active_tickers, f, indent=2, ensure_ascii=False)


# Pydantic Request Schemas
class WatchlistCreate(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    lang: Optional[str] = "TR"

class WatchlistUpdate(BaseModel):
    company_name: Optional[str] = None
    is_active: Optional[int] = 1
    lang: Optional[str] = "TR"

class AdminVerifyRequest(BaseModel):
    password: str

class SettingsUpdate(BaseModel):
    ADMIN_PASSWORD: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    BASE_URL: Optional[str] = None
    API_KEY: Optional[str] = None
    NINEROUTER_URL: Optional[str] = None
    NINEROUTER_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None
    OUTPUT_LANGUAGE: Optional[str] = "TR"
    LLM_TIMEOUT: Optional[str] = "120"
    CRON_DELAY_SECONDS: Optional[str] = "15"


# ══════════════════════════════════════════════════════════════
# AUTHENTICATION & APP SETTINGS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.post("/api/admin/verify")
def verify_admin(req: AdminVerifyRequest):
    current_pass = get_admin_password()
    if req.password and secrets.compare_digest(req.password, current_pass):
        return {"status": "ok", "message": "Şifre doğrulandı."}
    raise HTTPException(status_code=401, detail="Hatalı Şifre. Lütfen tekrar deneyiniz.")


@app.get("/api/settings")
def get_app_settings(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    load_dotenv(APP_ENV_PATH, override=True)
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("BASE_URL") or os.getenv("NINEROUTER_URL", "http://localhost:20128/v1")
    api_key = os.getenv("LLM_API_KEY") or os.getenv("API_KEY") or os.getenv("NINEROUTER_KEY", "")
    return {
        "ADMIN_PASSWORD": get_admin_password(),
        "LLM_BASE_URL": base_url,
        "LLM_API_KEY": api_key,
        "LLM_MODEL": os.getenv("LLM_MODEL", "code_combo"),
        "OUTPUT_LANGUAGE": os.getenv("OUTPUT_LANGUAGE", "TR"),
        "LLM_TIMEOUT": os.getenv("LLM_TIMEOUT", "120"),
        "CRON_DELAY_SECONDS": os.getenv("CRON_DELAY_SECONDS", "15")
    }


@app.put("/api/settings")
def update_app_settings(settings: SettingsUpdate, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)

    env_data = {}
    if os.path.exists(APP_ENV_PATH):
        with open(APP_ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str and not line_str.startswith("#") and "=" in line_str:
                    key, val = line_str.split("=", 1)
                    env_data[key.strip()] = val.strip()

    if settings.ADMIN_PASSWORD is not None and settings.ADMIN_PASSWORD.strip():
        env_data["ADMIN_PASSWORD"] = settings.ADMIN_PASSWORD.strip()
    
    base_url_val = settings.LLM_BASE_URL or settings.BASE_URL or settings.NINEROUTER_URL
    if base_url_val is not None:
        env_data["LLM_BASE_URL"] = base_url_val.strip()

    api_key_val = settings.LLM_API_KEY or settings.API_KEY or settings.NINEROUTER_KEY
    if api_key_val is not None:
        env_data["LLM_API_KEY"] = api_key_val.strip()
    if settings.LLM_MODEL is not None and settings.LLM_MODEL.strip():
        env_data["LLM_MODEL"] = settings.LLM_MODEL.strip()
    if settings.OUTPUT_LANGUAGE is not None and settings.OUTPUT_LANGUAGE.strip():
        env_data["OUTPUT_LANGUAGE"] = settings.OUTPUT_LANGUAGE.strip().upper()
    if settings.LLM_TIMEOUT is not None and settings.LLM_TIMEOUT.strip():
        env_data["LLM_TIMEOUT"] = settings.LLM_TIMEOUT.strip()
    if settings.CRON_DELAY_SECONDS is not None and settings.CRON_DELAY_SECONDS.strip():
        env_data["CRON_DELAY_SECONDS"] = settings.CRON_DELAY_SECONDS.strip()

    with open(APP_ENV_PATH, "w", encoding="utf-8") as f:
        f.write("# Stock Analyzer App Local Environment Configuration\n")
        for k, v in env_data.items():
            f.write(f"{k}={v}\n")

    load_dotenv(APP_ENV_PATH, override=True)
    for k, v in env_data.items():
        os.environ[k] = v

    return {"message": "Ayarlar .env dosyasına başarıyla kaydedildi.", "settings": env_data}


# ══════════════════════════════════════════════════════════════
# FILE LOGS REST ENDPOINTS
# ══════════════════════════════════════════════════════════════

def read_last_log_lines(file_path: str, max_lines: int = 200) -> str:
    if not os.path.exists(file_path):
        return f"⚠️ Log dosyası henüz oluşturulmadı: {os.path.basename(file_path)}"
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-max_lines:])
    except Exception as e:
        return f"🔴 Log okuma hatası: {e}"


@app.get("/api/logs/cron")
def get_cron_logs(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    log_path = os.path.join(LOGS_DIR, "cron.log")
    return {"log": read_last_log_lines(log_path)}


@app.get("/api/logs/analysis")
def get_analysis_logs(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    log_path = os.path.join(LOGS_DIR, "analysis.log")
    return {"log": read_last_log_lines(log_path)}


@app.post("/api/logs/clear/{log_type}")
def clear_logs(log_type: str, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    target_type = log_type.lower()
    if target_type in ["cron", "analysis", "live", "all"]:
        if target_type in ["cron", "all"]:
            log_path = os.path.join(LOGS_DIR, "cron.log")
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Cron log temizleme hatası: {e}")

        if target_type in ["analysis", "all"]:
            log_path = os.path.join(LOGS_DIR, "analysis.log")
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Analysis log temizleme hatası: {e}")
            PROCESS_STATUS.clear()

        if target_type == "live":
            PROCESS_STATUS.clear()

        return {"status": "ok", "message": f"{target_type} logları başarıyla temizlendi."}
    return {"status": "ok", "message": "Log temizlendi."}


# ══════════════════════════════════════════════════════════════
# WATCHLIST CRUD API ENDPOINTS (PASSWORD PROTECTED)
# ══════════════════════════════════════════════════════════════

@app.get("/api/watchlist")
def get_watchlist():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, ticker, company_name, is_active, lang, created_at FROM watchlist ORDER BY ticker ASC")
    rows = [dict(row) for row in cur.fetchall()]

    for row in rows:
        t = row["ticker"]
        cur.execute("SELECT report_date, piotroski_score, altman_z, status FROM reports_index WHERE ticker = ? ORDER BY report_date DESC LIMIT 1", (t,))
        r = cur.fetchone()
        row["last_report"] = dict(r) if r else None

    conn.close()
    return rows


@app.post("/api/watchlist")
def create_watchlist_item(item: WatchlistCreate, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)

    ticker = item.ticker.strip().upper()
    company_name = item.company_name.strip() if item.company_name else ticker

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO watchlist (ticker, company_name, is_active, lang) VALUES (?, ?, 1, ?)", (ticker, company_name, item.lang or "TR"))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Ticker {ticker} already exists in watchlist.")
    conn.close()

    sync_watchlist_json()
    return {"message": f"Ticker {ticker} added successfully.", "ticker": ticker}


@app.put("/api/watchlist/{ticker}")
def update_watchlist_item(ticker: str, item: WatchlistUpdate, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)

    ticker = ticker.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id FROM watchlist WHERE ticker = ?", (ticker,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found.")

    if item.company_name is not None:
        cur.execute("UPDATE watchlist SET company_name = ? WHERE ticker = ?", (item.company_name, ticker))
    if item.is_active is not None:
        cur.execute("UPDATE watchlist SET is_active = ? WHERE ticker = ?", (item.is_active, ticker))
    if item.lang is not None:
        cur.execute("UPDATE watchlist SET lang = ? WHERE ticker = ?", (item.lang, ticker))

    conn.commit()
    conn.close()

    sync_watchlist_json()
    return {"message": f"Ticker {ticker} updated successfully."}


@app.delete("/api/watchlist/{ticker}")
def delete_watchlist_item(ticker: str, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)

    ticker = ticker.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()

    sync_watchlist_json()
    return {"message": f"Ticker {ticker} removed from watchlist."}


# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
# REPROCESSING & BATCH EXECUTION ENDPOINTS
# ══════════════════════════════════════════════════════════════

def run_single_report_background(ticker: str, lang: str = "TR"):
    PROCESS_STATUS[ticker] = {"status": "RUNNING", "log": [f"▶ Starting analysis for {ticker}..."]}
    try:
        proc = subprocess.Popen(
            [PYTHON_EXEC, BUILDER_SCRIPT, ticker, "--lang", lang],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        for line in proc.stdout:
            line_str = line.strip()
            if line_str:
                PROCESS_STATUS[ticker]["log"].append(line_str)
        proc.wait()
        if proc.returncode == 0:
            PROCESS_STATUS[ticker]["status"] = "SUCCESS"
            PROCESS_STATUS[ticker]["log"].append(f"✅ Report generation completed for {ticker}")
        else:
            PROCESS_STATUS[ticker]["status"] = "FAILED"
            PROCESS_STATUS[ticker]["log"].append(f"🔴 Report generation failed with exit code {proc.returncode}")
    except Exception as e:
        PROCESS_STATUS[ticker]["status"] = "FAILED"
        PROCESS_STATUS[ticker]["log"].append(f"🔴 Error executing process: {e}")


def run_batch_reports_background():
    PROCESS_STATUS["_BATCH_"] = {"status": "RUNNING", "log": ["⚡ Starting batch run for all active watchlist stocks..."]}
    try:
        proc = subprocess.Popen(
            [PYTHON_EXEC, SCHEDULER_SCRIPT, "--now"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        for line in proc.stdout:
            line_str = line.strip()
            if line_str:
                PROCESS_STATUS["_BATCH_"]["log"].append(line_str)
        proc.wait()
        if proc.returncode == 0:
            PROCESS_STATUS["_BATCH_"]["status"] = "SUCCESS"
            PROCESS_STATUS["_BATCH_"]["log"].append("✅ Batch run completed successfully.")
        else:
            PROCESS_STATUS["_BATCH_"]["status"] = "FAILED"
            PROCESS_STATUS["_BATCH_"]["log"].append(f"🔴 Batch run failed with exit code {proc.returncode}")
    except Exception as e:
        PROCESS_STATUS["_BATCH_"]["status"] = "FAILED"
        PROCESS_STATUS["_BATCH_"]["log"].append(f"🔴 Error executing batch run: {e}")


@app.post("/api/reprocess/batch")
def reprocess_batch(background_tasks: BackgroundTasks, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)

    if PROCESS_STATUS.get("_BATCH_", {}).get("status") == "RUNNING":
        return {"message": "Batch processing is already in progress.", "status": "RUNNING"}

    background_tasks.add_task(run_batch_reports_background)
    return {"message": "Batch processing queued for all active stocks.", "status": "QUEUED"}


@app.post("/api/reprocess/{ticker}")
def reprocess_single_stock(ticker: str, background_tasks: BackgroundTasks, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)

    ticker = ticker.strip().upper()
    if PROCESS_STATUS.get(ticker, {}).get("status") == "RUNNING":
        return {"message": f"Processing for {ticker} is already in progress.", "status": "RUNNING"}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT lang FROM watchlist WHERE ticker = ?", (ticker,))
    row = cur.fetchone()
    conn.close()
    
    default_env_lang = os.getenv("OUTPUT_LANGUAGE", "TR")
    lang = row[0] if row and row[0] else default_env_lang

    background_tasks.add_task(run_single_report_background, ticker, lang)
    return {"message": f"Report generation queued for {ticker} (Lang: {lang}).", "status": "QUEUED"}


@app.get("/api/reprocess/status/{ticker}")
def get_reprocess_status(ticker: str):
    ticker = ticker.strip().upper()
    info = PROCESS_STATUS.get(ticker, {"status": "IDLE", "log": []})
    return info


@app.get("/api/reprocess/stream/{ticker}")
async def stream_reprocess_logs(ticker: str):
    ticker = ticker.strip().upper()

    async def log_generator():
        last_idx = 0
        while True:
            info = PROCESS_STATUS.get(ticker, {})
            logs = info.get("log", [])
            status = info.get("status", "IDLE")

            while last_idx < len(logs):
                line = logs[last_idx]
                last_idx += 1
                yield f"data: {json.dumps({'line': line, 'status': status, 'done': False})}\n\n"

            if status in ["SUCCESS", "FAILED"] and last_idx >= len(logs):
                yield f"data: {json.dumps({'line': f'✅ Execution finished with status: {status}', 'status': status, 'done': True})}\n\n"
                break

            if status == "IDLE" and last_idx >= len(logs):
                yield f"data: {json.dumps({'line': 'ℹ️ No active process running.', 'status': 'IDLE', 'done': True})}\n\n"
                break

            await asyncio.sleep(0.4)

    return StreamingResponse(log_generator(), media_type="text/event-stream")


# ══════════════════════════════════════════════════════════════
# VIEWER & STATIC ASSET ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.get("/api/tickers")
def get_tickers():
    if not os.path.exists(REPORTS_DIR):
        return []
    ignored = {"BATCH", "TMP", "TEMP"}
    tickers = [
        d for d in os.listdir(REPORTS_DIR) 
        if os.path.isdir(os.path.join(REPORTS_DIR, d)) and d.upper() not in ignored and not d.startswith(".")
    ]
    return sorted(tickers)


@app.get("/api/dates/{ticker}")
def get_dates(ticker: str):
    safe_ticker = os.path.basename(ticker)
    ticker_dir = os.path.abspath(os.path.join(REPORTS_DIR, safe_ticker))
    reports_dir_abs = os.path.abspath(REPORTS_DIR) + os.sep
    if not (ticker_dir + os.sep).startswith(reports_dir_abs) or not os.path.exists(ticker_dir):
        return []
    files = glob.glob(os.path.join(ticker_dir, "*.html"))
    dates = [os.path.basename(f).replace(".html", "").replace("_printable", "") for f in files]
    unique_dates = sorted(list(set(dates)), reverse=True)
    return unique_dates


@app.get("/api/index")
def get_index():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, ticker, report_date, piotroski_score, altman_z, beneish_m, wacc_pct, status, created_at FROM reports_index ORDER BY id DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/reports/{ticker}/{date}", response_class=HTMLResponse)
def get_report(ticker: str, date: str, mode: str = "dashboard"):
    if ".." in ticker or ".." in date or "/" in ticker or "\\" in ticker or "/" in date or "\\" in date:
        raise HTTPException(status_code=400, detail="Invalid path parameter.")
    safe_ticker = os.path.basename(ticker)
    safe_date = os.path.basename(date)
    filename = f"{safe_date}_printable.html" if mode == "printable" else f"{safe_date}.html"
    file_path = os.path.abspath(os.path.join(REPORTS_DIR, safe_ticker, filename))
    reports_dir_abs = os.path.abspath(REPORTS_DIR) + os.sep

    if not file_path.startswith(reports_dir_abs):
        raise HTTPException(status_code=400, detail="Invalid path parameter.")

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse(content="<div style='color:#fff; padding:2rem;'><h1>⚠️ Report Not Found</h1><p>No report exists for this ticker/date combination.</p></div>", status_code=404)


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stock Research Platform & Admin Panel</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-dark: #0b0f19;
                --panel-bg: #141b2d;
                --panel-border: rgba(255, 255, 255, 0.1);
                --accent-cyan: #06b6d4;
                --accent-emerald: #10b981;
                --accent-amber: #f59e0b;
                --accent-rose: #f43f5e;
                --accent-purple: #8b5cf6;
                --text-main: #f3f4f6;
                --text-muted: #9ca3af;
            }
            html, body {
                margin: 0;
                padding: 0;
                width: 100vw;
                height: 100vh;
                height: 100dvh;
                overflow: hidden;
                position: fixed;
                top: 0;
                left: 0;
                font-family: 'Inter', sans-serif;
                background: var(--bg-dark);
                color: var(--text-main);
                display: flex;
                flex-direction: column;
            }

            header { background: var(--panel-bg); padding: 0.6rem 1rem; display: flex; gap: 1rem; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--panel-border); flex-shrink: 0; z-index: 1000; width: 100%; box-sizing: border-box; }
            .header-left { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; flex: 1; min-width: 0; }
            .brand { font-family: 'Outfit', sans-serif; font-size: 1.2rem; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 0.5rem; }
            .brand-badge { background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); color: #fff; font-size: 0.65rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700; }

            .controls { display: flex; align-items: center; gap: 1rem; }
            .control-group { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--text-muted); }
            select, input { background: #1a202c; color: #fff; border: 1px solid #374151; padding: 0.45rem 0.8rem; border-radius: 6px; font-size: 0.85rem; outline: none; transition: border-color 0.2s; }
            select:focus, input:focus { border-color: var(--accent-cyan); }
            
            .btn { background: rgba(255,255,255,0.05); border: 1px solid var(--panel-border); color: #fff; padding: 0.45rem 0.9rem; border-radius: 6px; font-size: 0.85rem; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 0.4rem; transition: all 0.2s; }
            .btn:hover { background: rgba(6, 182, 212, 0.15); border-color: var(--accent-cyan); color: var(--accent-cyan); }
            .btn-primary { background: linear-gradient(135deg, var(--accent-cyan), #0284c7); border: none; color: #fff; }
            .btn-primary:hover { opacity: 0.9; color: #fff; }
            .btn-danger { background: rgba(244, 63, 94, 0.15); border-color: var(--accent-rose); color: var(--accent-rose); }
            .btn-danger:hover { background: var(--accent-rose); color: #fff; }

            #contentFrame { width: 100%; flex: 1 1 0%; min-height: 0; border: none; background: var(--bg-dark); -webkit-overflow-scrolling: touch; }

            /* Modal Overlay */
            .modal-backdrop { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.75); backdrop-filter: blur(6px); z-index: 1000; justify-content: center; align-items: center; }
            .modal-backdrop.active { display: flex; }
            .modal { background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 12px; width: 90%; max-width: 1050px; max-height: 88vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
            .modal-header { padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--panel-border); display: flex; justify-content: space-between; align-items: center; }
            .modal-title { font-family: 'Outfit', sans-serif; font-size: 1.25rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; }
            .close-btn { background: none; border: none; color: var(--text-muted); font-size: 1.4rem; cursor: pointer; }
            .close-btn:hover { color: #fff; }

            .modal-body { padding: 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.5rem; }

            /* Auth Lock Box */
            .auth-box { background: rgba(11, 15, 25, 0.8); border: 1px solid var(--panel-border); border-radius: 10px; padding: 2.5rem; max-width: 450px; margin: 2rem auto; text-align: center; display: flex; flex-direction: column; gap: 1.25rem; }
            .auth-title { font-size: 1.15rem; font-weight: 700; color: var(--accent-cyan); display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
            .auth-input-group { display: flex; gap: 0.5rem; }
            .auth-input-group input { flex: 1; }

            .admin-card { background: rgba(11, 15, 25, 0.6); border: 1px solid var(--panel-border); border-radius: 8px; padding: 1.25rem; }
            .card-heading { font-size: 0.95rem; font-weight: 700; margin-bottom: 1rem; color: var(--accent-cyan); display: flex; justify-content: space-between; align-items: center; }

            .create-form { display: grid; grid-template-columns: 1fr 2fr 120px auto; gap: 0.75rem; align-items: center; }
            .settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
            .form-field { display: flex; flex-direction: column; gap: 0.4rem; font-size: 0.82rem; color: var(--text-muted); }

            table.admin-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
            table.admin-table th, table.admin-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--panel-border); }
            table.admin-table th { background: rgba(255,255,255,0.03); color: var(--text-muted); font-weight: 600; }
            table.admin-table tr:hover { background: rgba(255,255,255,0.02); }

            .icon-tools-group { display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; margin-left: auto; }
            .icon-btn {
                background: rgba(255,255,255,0.06);
                border: 1px solid var(--panel-border);
                color: #fff;
                width: 34px;
                height: 34px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 0.95rem;
                transition: all 0.2s;
            }
            .icon-btn:hover { background: rgba(6, 182, 212, 0.2); border-color: var(--accent-cyan); }
            
            .icon-select {
                background: #1a202c;
                color: #fff;
                border: 1px solid #374151;
                padding: 0.35rem 0.4rem;
                border-radius: 6px;
                font-size: 0.95rem;
                outline: none;
                cursor: pointer;
            }

            .mobile-hamburger-btn {
                display: none;
            }

            /* Log Section Styles */
            .log-tab-bar { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
            .log-tab {
                background: rgba(255,255,255,0.05);
                border: 1px solid var(--panel-border);
                color: var(--text-muted);
                padding: 0.45rem 0.85rem;
                border-radius: 6px;
                font-size: 0.82rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 0.4rem;
            }
            .log-tab:hover { background: rgba(6, 182, 212, 0.15); color: #fff; border-color: var(--accent-cyan); }
            .log-tab.active { background: linear-gradient(135deg, var(--accent-cyan), #0284c7); color: #fff; border-color: transparent; }

            .console-box {
                background: #070a12;
                color: #10b981;
                font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
                font-size: 0.82rem;
                line-height: 1.5;
                height: 320px;
                max-height: 320px;
                overflow-y: auto;
                overflow-x: auto;
                padding: 1rem;
                border-radius: 8px;
                border: 1px solid var(--panel-border);
                white-space: pre-wrap;
                word-break: break-all;
                box-shadow: inset 0 2px 6px rgba(0,0,0,0.5);
            }
            .console-box::-webkit-scrollbar { width: 8px; height: 8px; }
            .console-box::-webkit-scrollbar-track { background: rgba(0,0,0,0.3); border-radius: 4px; }
            .console-box::-webkit-scrollbar-thumb { background: rgba(6, 182, 212, 0.4); border-radius: 4px; }
            .console-box::-webkit-scrollbar-thumb:hover { background: var(--accent-cyan); }

            /* Responsive Mobile Layout */
            @media (max-width: 900px) {
                html, body { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; height: 100dvh; overflow: hidden; }
                .mobile-hamburger-btn { display: flex; }
                header { flex-shrink: 0; display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 0.5rem 0.75rem; padding: 0.5rem 0.75rem; }
                .header-left { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; grid-column: 1; }
                .icon-tools-group { grid-column: 2; margin-left: auto; flex-shrink: 0; }
                .control-group { font-size: 0.8rem; }
                select, input { padding: 0.4rem 0.6rem; font-size: 0.8rem; }
                .brand { font-size: 1.05rem; }
                .modal { width: 95%; max-height: 94vh; border-radius: 8px; }
                .modal-header { padding: 0.9rem 1rem; }
                .modal-body { padding: 1rem; gap: 1rem; }
                .create-form { grid-template-columns: 1fr; gap: 0.5rem; }
                .settings-grid { grid-template-columns: 1fr; gap: 0.75rem; }
                .form-field[style*="span 2"] { grid-column: span 1 !important; }
                .log-tab-bar { flex-wrap: wrap; }
                .card-heading { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
                .card-heading > div { width: 100%; flex-wrap: wrap; }
                .table-wrapper { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
                table.admin-table { white-space: nowrap; min-width: 600px; }
            }
        </style>
    </head>
    <body>
        <header>
            <div class="header-left">
                <div class="brand">🏛️ Stock Research Platform</div>
                <div class="control-group">
                    <label for="tickerFilter">🔍</label>
                    <input type="text" id="tickerFilter" placeholder="Hisse Ara..." oninput="filterTickers(this.value)" style="width:110px; padding:0.35rem 0.5rem; font-size:0.8rem;">
                </div>
                <div class="control-group">
                    <label for="tickerSelect">📈</label>
                    <select id="tickerSelect" onchange="loadDates()"></select>
                </div>
                <div class="control-group">
                    <label for="dateSelect">📅</label>
                    <select id="dateSelect" onchange="loadReport()"></select>
                </div>
                <div class="control-group">
                    <label for="modeSelect">👁️</label>
                    <select id="modeSelect" onchange="loadReport()">
                        <option value="dashboard" data-i18n="opt_dashboard">📊 İnteraktif</option>
                        <option value="printable" data-i18n="opt_printable">📄 PDF</option>
                    </select>
                </div>
            </div>
            <div class="icon-tools-group">
                <button id="headerThemeBtn" class="icon-btn" onclick="toggleMainTheme()" title="Tema / Theme">🌙</button>
                <button class="icon-btn" onclick="printReportPage()" title="Yazdır / Print">🖨️</button>
                <select id="uiLangSelect" class="icon-select" onchange="setUiLanguage(this.value)" title="Dil / Language">
                    <option value="TR">🇹🇷</option>
                    <option value="EN">🇬🇧</option>
                </select>
                <button class="icon-btn mobile-hamburger-btn" onclick="toggleIframeMobileMenu()" title="Menu">☰</button>
            </div>
        </header>

        <iframe id="contentFrame" onload="notifyIframeLanguage()"></iframe>

        <!-- ADMIN MODAL -->
        <div id="adminModal" class="modal-backdrop">
            <div class="modal">
                <div class="modal-header">
                    <div class="modal-title" data-i18n="modal_title">⚙️ Hisse Yönetim, LLM & Sistem Logları Paneli</div>
                    <button class="close-btn" onclick="closeAdminModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- PASSWORD LOCK SCREEN -->
                    <div id="authLockScreen" class="auth-box">
                        <div class="auth-title" data-i18n="auth_title">🔒 Yönetici Girişi (.env Şifresi)</div>
                        <p style="font-size:0.85rem; color:var(--text-muted);" data-i18n="auth_desc">Lütfen uygulamanın <code>.env</code> dosyasında tanımlı <strong>ADMIN_PASSWORD</strong> şifrenizi giriniz.</p>
                        <div class="auth-input-group">
                            <input type="password" id="adminPasswordInput" data-i18n-ph="auth_placeholder" placeholder="Yönetici Şifreniz" onkeypress="if(event.key==='Enter') submitAdminPassword()">
                            <button class="btn btn-primary" onclick="submitAdminPassword()" data-i18n="auth_btn">Giriş Yap</button>
                        </div>
                        <div id="authErrorMsg" style="font-size:0.8rem; color:var(--accent-rose); display:none;"></div>
                    </div>

                    <!-- PROTECTED ADMIN CONTENT CONTAINER -->
                    <div id="protectedAdminContent" style="display:none; flex-direction:column; gap:1.5rem;">
                        
                        <!-- SECTION 1: LLM & SYSTEM SETTINGS (.ENV EDITOR) -->
                        <div class="admin-card">
                            <div class="card-heading">
                                <span data-i18n="sec1_heading">🛠️ LLM Sağlayıcı & Sistem Ayarları (.env Düzenleyici)</span>
                                <button class="btn btn-primary" onclick="saveAppSettings()" data-i18n="btn_save_settings">💾 Ayarları Kaydet (.env)</button>
                            </div>
                            <div class="settings-grid">
                                <div class="form-field">
                                    <label data-i18n="lbl_admin_pass">Yönetici Şifresi (ADMIN_PASSWORD):</label>
                                    <input type="password" id="settingAdminPassword" placeholder="Yönetici şifresi">
                                </div>
                                <div class="form-field">
                                    <label data-i18n="lbl_output_lang">Varsayılan Rapor Dili (OUTPUT_LANGUAGE):</label>
                                    <select id="settingOutputLanguage">
                                        <option value="TR">TR (Türkçe)</option>
                                        <option value="EN">EN (English)</option>
                                    </select>
                                </div>
                                <div class="form-field">
                                    <label data-i18n="lbl_llm_model">LLM Model Adı (LLM_MODEL):</label>
                                    <input type="text" id="settingLlmModel" placeholder="Örn: code_combo, gpt-4o">
                                </div>
                                <div class="form-field">
                                    <label data-i18n="lbl_llm_url">LLM Provider Base URL (LLM_BASE_URL):</label>
                                    <input type="text" id="settingLlmBaseUrl" placeholder="http://localhost:20128/v1">
                                </div>
                                <div class="form-field">
                                    <label data-i18n="lbl_cron_delay">Cron Hisseler Arası Bekleme (Saniye) (CRON_DELAY_SECONDS):</label>
                                    <input type="number" id="settingCronDelaySeconds" placeholder="15">
                                </div>
                                <div class="form-field">
                                    <label data-i18n="lbl_llm_timeout">LLM Zaman Aşımı (Saniye) (LLM_TIMEOUT):</label>
                                    <input type="number" id="settingLlmTimeout" placeholder="120">
                                </div>
                                <div class="form-field" style="grid-column: span 2;">
                                    <label data-i18n="lbl_llm_key">LLM API Key (LLM_API_KEY):</label>
                                    <input type="password" id="settingLlmApiKey" placeholder="sk-...">
                                </div>
                            </div>
                        </div>

                        <!-- SECTION 2: SYSTEM LOGS & CONSOLE -->
                        <div class="admin-card">
                            <div class="card-heading">
                                <span data-i18n="sec2_heading">📜 Sistem, Cron Job & Analiz Logları</span>
                                <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                                    <button class="btn" onclick="fetchFileLogs()" data-i18n="btn_refresh_logs">🔄 Logları Yenile</button>
                                    <button class="btn btn-danger" onclick="clearActiveLogs()" data-i18n="btn_clear_logs">🗑️ Logları Temizle</button>
                                    <button class="btn btn-primary" onclick="triggerBatchRun()" data-i18n="btn_batch_run">🚀 Tüm Aktif Hisseleri Çalıştır (Batch Run)</button>
                                </div>
                            </div>
                            <div class="log-tab-bar">
                                <div id="tabCronLog" class="log-tab active" onclick="switchLogTab('cron')" data-i18n="tab_cron">⏰ Cron Scheduler Logları (cron.log)</div>
                                <div id="tabAnalysisLog" class="log-tab" onclick="switchLogTab('analysis')" data-i18n="tab_analysis">📊 Analiz Rapor Logları (analysis.log)</div>
                                <div id="tabLiveLog" class="log-tab" onclick="switchLogTab('live')" data-i18n="tab_live">⚡ Canlı İşlem Çıktısı (Live)</div>
                            </div>
                            <div id="fileConsoleBox" class="console-box" data-i18n="log_loading">Loglar yükleniyor...</div>
                        </div>

                        <!-- SECTION 3: ADD NEW STOCK -->
                        <div class="admin-card">
                            <div class="card-heading" data-i18n="sec3_heading">➕ Yeni Hisse Ekle (Create Stock)</div>
                            <div class="create-form">
                                <input type="text" id="newTicker" data-i18n-ph="ph_ticker" placeholder="Hisse Sembolü (Örn: AAPL, THYAO.IS)" style="text-transform:uppercase;">
                                <input type="text" id="newCompanyName" data-i18n-ph="ph_company" placeholder="Şirket Unvanı (Örn: Türk Hava Yolları)">
                                <select id="newLang">
                                    <option value="TR">TR (Türkçe)</option>
                                    <option value="EN">EN (English)</option>
                                </select>
                                <button class="btn btn-primary" onclick="createStock()" data-i18n="btn_add">➕ Ekle</button>
                            </div>
                        </div>

                        <!-- SECTION 4: CRUD WATCHLIST TABLE -->
                        <div class="admin-card">
                            <div class="card-heading" data-i18n="sec4_heading">📋 İzleme Listesi & İşlem Yönetimi (Stock CRUD Table)</div>
                            <div class="table-wrapper">
                                <table class="admin-table">
                                    <thead>
                                        <tr>
                                            <th data-i18n="th_ticker">Sembol</th>
                                            <th data-i18n="th_company">Şirket Unvanı</th>
                                            <th data-i18n="th_lang">Dil</th>
                                            <th data-i18n="th_active">Aktif</th>
                                            <th data-i18n="th_last_report">Son Rapor / Skorlar</th>
                                            <th style="text-align:right;" data-i18n="th_actions">İşlemler (Actions)</th>
                                        </tr>
                                    </thead>
                                    <tbody id="watchlistTableBody">
                                        <!-- Populated via JavaScript -->
                                    </tbody>
                                </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- EDIT STOCK MODAL -->
        <div id="editStockModal" class="modal-backdrop">
            <div class="modal" style="max-width:480px;">
                <div class="modal-header">
                    <div class="modal-title" id="editStockModalTitle" data-i18n="edit_modal_title">✏️ Hisse Düzenle</div>
                    <button class="close-btn" onclick="closeEditStockModal()">&times;</button>
                </div>
                <div class="modal-body" style="gap:1rem;">
                    <input type="hidden" id="editStockTicker">
                    <div class="form-field">
                        <label data-i18n="edit_lbl_ticker">Hisse Sembolü (Ticker):</label>
                        <input type="text" id="editStockTickerDisplay" disabled style="opacity:0.75; font-weight:700;">
                    </div>
                    <div class="form-field">
                        <label data-i18n="edit_lbl_company">Şirket Unvanı (Company Name):</label>
                        <input type="text" id="editStockCompanyName" data-i18n-ph="edit_ph_company" placeholder="Şirket unvanı giriniz">
                    </div>
                    <div class="form-field">
                        <label data-i18n="edit_lbl_lang">Rapor Dili (Language):</label>
                        <select id="editStockLang">
                            <option value="TR">TR (Türkçe)</option>
                            <option value="EN">EN (English)</option>
                        </select>
                    </div>
                    <div style="display:flex; justify-content:flex-end; gap:0.5rem; margin-top:0.75rem;">
                        <button class="btn" onclick="closeEditStockModal()" data-i18n="btn_cancel">İptal</button>
                        <button class="btn btn-primary" onclick="submitEditStock()" data-i18n="btn_save">💾 Kaydet</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const UI_I18N = {
                TR: {
                    opt_dashboard: "📊 İnteraktif",
                    opt_printable: "📄 PDF",
                    btn_admin: "🔒 Yönetim Paneli",
                    modal_title: "⚙️ Hisse Yönetim, LLM & Sistem Logları Paneli",
                    auth_title: "🔒 Yönetici Girişi (.env Şifresi)",
                    auth_desc: "Lütfen uygulamanın <code>.env</code> dosyasında tanımlı <strong>ADMIN_PASSWORD</strong> şifrenizi giriniz.",
                    auth_placeholder: "Yönetici Şifreniz",
                    auth_btn: "Giriş Yap",
                    sec1_heading: "🛠️ LLM Sağlayıcı & Sistem Ayarları (.env Düzenleyici)",
                    btn_save_settings: "💾 Ayarları Kaydet (.env)",
                    lbl_admin_pass: "Yönetici Şifresi (ADMIN_PASSWORD):",
                    lbl_output_lang: "Varsayılan Rapor Dili (OUTPUT_LANGUAGE):",
                    lbl_llm_model: "LLM Model Adı (LLM_MODEL):",
                    lbl_llm_url: "LLM Provider Base URL (LLM_BASE_URL):",
                    lbl_llm_key: "LLM API Key (LLM_API_KEY):",
                    sec2_heading: "📜 Sistem, Cron Job & Analiz Logları",
                    btn_refresh_logs: "🔄 Logları Yenile",
                    btn_clear_logs: "🗑️ Logları Temizle",
                    log_cleared: "Loglar temizlendi.",
                    btn_batch_run: "🚀 Tüm Aktif Hisseleri Çalıştır (Batch Run)",
                    tab_cron: "⏰ Cron Scheduler Logları (cron.log)",
                    tab_analysis: "📊 Analiz Rapor Logları (analysis.log)",
                    tab_live: "⚡ Canlı İşlem Çıktısı (Live)",
                    log_loading: "Loglar yükleniyor...",
                    sec3_heading: "➕ Yeni Hisse Ekle (Create Stock)",
                    ph_ticker: "Hisse Sembolü (Örn: AAPL, THYAO.IS)",
                    ph_company: "Şirket Unvanı (Örn: Türk Hava Yolları)",
                    btn_add: "➕ Ekle",
                    sec4_heading: "📋 İzleme Listesi & İşlem Yönetimi (Stock CRUD Table)",
                    th_ticker: "Sembol",
                    th_company: "Şirket Unvanı",
                    th_lang: "Dil",
                    th_active: "Aktif",
                    th_last_report: "Son Rapor / Skorlar",
                    th_actions: "İşlemler (Actions)",
                    no_report_badge: "Henüz Rapor Yok",
                    btn_analyze: "⚡ Analiz Et",
                    btn_edit: "✏️ Düzenle",
                    btn_delete: "🗑️ Sil",
                    edit_modal_title: "✏️ Hisse Düzenle",
                    edit_lbl_ticker: "Hisse Sembolü (Ticker):",
                    edit_lbl_company: "Şirket Unvanı (Company Name):",
                    edit_ph_company: "Şirket unvanı giriniz",
                    edit_lbl_lang: "Rapor Dili (Language):",
                    btn_cancel: "İptal",
                    btn_save: "💾 Kaydet",
                    view_report_title: "Raporu Görüntüle",
                    single_analyze_title: "Yalnızca bu seçili hisseyi analiz et",
                    prompt_company_name: "Yeni şirket unvanını giriniz:",
                    confirm_delete: "izleme listesinden çıkarılsın mı?",
                    msg_settings_saved: "✅ Ayarlar ve Rapor Dili .env dosyasına başarıyla kaydedildi.",
                    msg_enter_ticker: "Lütfen hisse sembolü giriniz.",
                    msg_batch_started: "⚡ Tüm aktif hisseler için toplu analiz başlatıldı..."
                },
                EN: {
                    opt_dashboard: "📊 Interactive",
                    opt_printable: "📄 PDF",
                    btn_admin: "🔒 Admin Panel",
                    modal_title: "⚙️ Stock Management, LLM & System Logs Panel",
                    auth_title: "🔒 Admin Login (.env Password)",
                    auth_desc: "Please enter the <strong>ADMIN_PASSWORD</strong> defined in the app's <code>.env</code> file.",
                    auth_placeholder: "Admin Password",
                    auth_btn: "Login",
                    sec1_heading: "🛠️ LLM Provider & System Settings (.env Editor)",
                    btn_save_settings: "💾 Save Settings (.env)",
                    lbl_admin_pass: "Admin Password (ADMIN_PASSWORD):",
                    lbl_output_lang: "Default Report Language (OUTPUT_LANGUAGE):",
                    lbl_llm_model: "LLM Model Name (LLM_MODEL):",
                    lbl_llm_url: "LLM Provider Base URL (LLM_BASE_URL):",
                    lbl_llm_key: "LLM API Key (LLM_API_KEY):",
                    sec2_heading: "📜 System, Cron Job & Analysis Logs",
                    btn_refresh_logs: "🔄 Refresh Logs",
                    btn_clear_logs: "🗑️ Clear Logs",
                    log_cleared: "Logs cleared successfully.",
                    btn_batch_run: "🚀 Run All Active Stocks (Batch Run)",
                    tab_cron: "⏰ Cron Scheduler Logs (cron.log)",
                    tab_analysis: "📊 Analysis Report Logs (analysis.log)",
                    tab_live: "⚡ Live Execution Output (Live)",
                    log_loading: "Loading logs...",
                    sec3_heading: "➕ Add New Stock (Create Stock)",
                    ph_ticker: "Ticker Symbol (e.g. AAPL, THYAO.IS)",
                    ph_company: "Company Name (e.g. Apple Inc.)",
                    btn_add: "➕ Add",
                    sec4_heading: "📋 Watchlist & Stock Operations (CRUD Table)",
                    th_ticker: "Symbol",
                    th_company: "Company Name",
                    th_lang: "Language",
                    th_active: "Active",
                    th_last_report: "Last Report / Scores",
                    th_actions: "Actions",
                    no_report_badge: "No Report Yet",
                    btn_analyze: "⚡ Analyze",
                    btn_edit: "✏️ Edit",
                    btn_delete: "🗑️ Delete",
                    edit_modal_title: "✏️ Edit Stock Settings",
                    edit_lbl_ticker: "Ticker Symbol:",
                    edit_lbl_company: "Company Name:",
                    edit_ph_company: "Enter company name",
                    edit_lbl_lang: "Report Language:",
                    btn_cancel: "Cancel",
                    btn_save: "💾 Save",
                    view_report_title: "View Report",
                    single_analyze_title: "Analyze only this selected stock",
                    prompt_company_name: "Enter new company name for",
                    confirm_delete: "Remove from watchlist?",
                    msg_settings_saved: "✅ Settings and Report Language saved to .env file successfully.",
                    msg_enter_ticker: "Please enter a stock ticker symbol.",
                    msg_batch_started: "⚡ Batch analysis triggered for all active stocks..."
                }
            };

            let currentUiLang = localStorage.getItem('UI_LANG') || 'TR';
            let pollingTimer = null;
            let activeLogType = 'cron';
            let adminAuthPassword = sessionStorage.getItem('ADMIN_AUTH_PASS') || '';

            function setUiLanguage(lang) {
                currentUiLang = lang;
                localStorage.setItem('UI_LANG', lang);
                const sel = document.getElementById('uiLangSelect');
                if (sel) sel.value = lang;
                applyUiLanguage();
                fetchWatchlist();
                notifyIframeLanguage();
            }

            function toggleMainTheme() {
                const currentTheme = document.body.getAttribute('data-theme') || 'dark';
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                document.body.setAttribute('data-theme', newTheme);
                const btn = document.getElementById('headerThemeBtn');
                if (btn) btn.innerHTML = newTheme === 'light' ? '☀️' : '🌙';
                const iframe = document.getElementById('contentFrame');
                if (iframe && iframe.contentWindow && iframe.contentWindow.toggleTheme) {
                    try {
                        iframe.contentWindow.toggleTheme();
                    } catch(e) {}
                }
            }

            function printReportPage() {
                const iframe = document.getElementById('contentFrame');
                if (iframe && iframe.contentWindow) {
                    try {
                        iframe.contentWindow.print();
                    } catch(e) { window.print(); }
                } else {
                    window.print();
                }
            }

            function toggleIframeMobileMenu() {
                const iframe = document.getElementById('contentFrame');
                if (iframe && iframe.contentWindow) {
                    try {
                        iframe.contentWindow.postMessage({ type: 'TOGGLE_MOBILE_MENU' }, '*');
                    } catch(e) {}
                }
            }

            function notifyIframeLanguage() {
                const iframe = document.getElementById('contentFrame');
                if (iframe && iframe.contentWindow) {
                    try {
                        iframe.contentWindow.postMessage({ type: 'CHANGE_UI_LANG', lang: currentUiLang }, '*');
                    } catch(e) {}
                }
            }

            function applyUiLanguage() {
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                document.querySelectorAll('[data-i18n]').forEach(el => {
                    const key = el.getAttribute('data-i18n');
                    if (t[key]) {
                        if (el.tagName === 'INPUT' && (el.type === 'text' || el.type === 'password')) {
                            el.placeholder = t[key];
                        } else {
                            el.innerHTML = t[key];
                        }
                    }
                });
                document.querySelectorAll('[data-i18n-ph]').forEach(el => {
                    const key = el.getAttribute('data-i18n-ph');
                    if (t[key]) el.placeholder = t[key];
                });
            }

            async function loadTickers(targetTicker = null) {
                const sel = document.getElementById('tickerSelect');
                const previousTicker = targetTicker || (sel ? sel.value : null);
                const res = await fetch('/api/tickers');
                const tickers = await res.json();
                sel.innerHTML = tickers.map(t => `<option value="${t}">${t}</option>`).join('');
                if (previousTicker && tickers.includes(previousTicker)) {
                    sel.value = previousTicker;
                }
                if (tickers.length > 0) {
                    loadDates();
                } else {
                    document.getElementById('dateSelect').innerHTML = '';
                    const frame = document.getElementById('contentFrame');
                    frame.src = 'about:blank';
                    frame.srcdoc = `
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <style>
                            body { background:#0b0f19; color:#f3f4f6; font-family:'Inter', system-ui, -apple-system, sans-serif; display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; margin:0; text-align:center; padding:1.5rem; box-sizing:border-box; }
                            .card { background:rgba(20,27,45,0.85); border:1px solid rgba(255,255,255,0.1); border-radius:14px; padding:3rem 2.5rem; max-width:540px; box-shadow:0 12px 35px rgba(0,0,0,0.6); backdrop-filter:blur(12px); }
                            .icon { font-size:3rem; margin-bottom:1rem; }
                            h2 { color:#06b6d4; margin-bottom:0.75rem; font-size:1.4rem; font-weight:700; }
                            p { color:#9ca3af; line-height:1.6; margin-bottom:1.75rem; font-size:0.95rem; }
                            .btn { background:linear-gradient(135deg, #06b6d4, #0284c7); color:#fff; border:none; padding:0.8rem 1.6rem; border-radius:8px; font-weight:600; cursor:pointer; font-size:0.92rem; transition:transform 0.2s, box-shadow 0.2s; }
                            .btn:hover { transform:translateY(-2px); box-shadow:0 6px 20px rgba(6,182,212,0.4); }
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <div class="icon">🏛️</div>
                            <h2>Stock Research Platform</h2>
                            <p>Henüz oluşturulmuş bir rapor bulunmuyor. Üst sağdaki <strong>🔒 Yönetim Paneli</strong> butonuna tıklayarak <strong>'⚡ Analiz Et'</strong> veya <strong>'🚀 Tüm Aktif Hisseleri Çalıştır (Batch Run)'</strong> butonu ile ilk raporlarınızı oluşturabilirsiniz.</p>
                            <button class="btn" onclick="window.parent.triggerAdminModal()">🔒 Yönetim Panelini Aç (Admin Panel)</button>
                        </div>
                    </body>
                    </html>`;
                }
            }

            async function selectAndLoadReport(ticker) {
                closeAdminModal();
                await loadTickers(ticker);
            }

            async function loadDates() {
                const ticker = document.getElementById('tickerSelect').value;
                if (!ticker) return;
                const res = await fetch(`/api/dates/${ticker}`);
                const dates = await res.json();
                const sel = document.getElementById('dateSelect');
                sel.innerHTML = dates.map(d => `<option value="${d}">${d}</option>`).join('');
                if (dates.length > 0) loadReport();
            }

            function loadReport() {
                const ticker = document.getElementById('tickerSelect').value;
                const date = document.getElementById('dateSelect').value;
                const mode = document.getElementById('modeSelect').value;
                if (ticker && date) {
                    document.getElementById('contentFrame').src = `/api/reports/${ticker}/${date}?mode=${mode}`;
                }
            }

            function openAdminModal() {
                document.getElementById('adminModal').classList.add('active');
                if (adminAuthPassword) {
                    verifyStoredPassword();
                } else {
                    showLockScreen();
                }
            }
            window.triggerAdminModal = openAdminModal;

            function closeAdminModal() {
                document.getElementById('adminModal').classList.remove('active');
                if (pollingTimer) clearInterval(pollingTimer);
                loadTickers();
            }

            function showLockScreen() {
                document.getElementById('authLockScreen').style.display = 'flex';
                document.getElementById('protectedAdminContent').style.display = 'none';
            }

            function showProtectedContent() {
                document.getElementById('authLockScreen').style.display = 'none';
                document.getElementById('protectedAdminContent').style.display = 'flex';
                fetchAppSettings();
                fetchWatchlist();
                fetchFileLogs();
            }

            async function submitAdminPassword() {
                const pass = document.getElementById('adminPasswordInput').value;
                const errDiv = document.getElementById('authErrorMsg');
                errDiv.style.display = 'none';

                const res = await fetch('/api/admin/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: pass })
                });

                if (res.ok) {
                    adminAuthPassword = pass;
                    sessionStorage.setItem('ADMIN_AUTH_PASS', pass);
                    showProtectedContent();
                } else {
                    const err = await res.json();
                    errDiv.innerText = err.detail || 'Geçersiz Şifre.';
                    errDiv.style.display = 'block';
                }
            }

            async function verifyStoredPassword() {
                const res = await fetch('/api/admin/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: adminAuthPassword })
                });
                if (res.ok) {
                    showProtectedContent();
                } else {
                    sessionStorage.removeItem('ADMIN_AUTH_PASS');
                    adminAuthPassword = '';
                    showLockScreen();
                }
            }

            function getAdminHeaders() {
                return {
                    'Content-Type': 'application/json',
                    'X-Admin-Password': adminAuthPassword
                };
            }

            async function fetchAppSettings() {
                const res = await fetch('/api/settings', { headers: getAdminHeaders() });
                if (res.ok) {
                    const s = await res.json();
                    document.getElementById('settingAdminPassword').value = s.ADMIN_PASSWORD || '';
                    document.getElementById('settingLlmModel').value = s.LLM_MODEL || '';
                    document.getElementById('settingLlmBaseUrl').value = s.LLM_BASE_URL || s.BASE_URL || s.NINEROUTER_URL || '';
                    document.getElementById('settingLlmApiKey').value = s.LLM_API_KEY || s.API_KEY || s.NINEROUTER_KEY || '';
                    document.getElementById('settingOutputLanguage').value = s.OUTPUT_LANGUAGE || 'TR';
                    document.getElementById('settingCronDelaySeconds').value = s.CRON_DELAY_SECONDS || '15';
                    document.getElementById('settingLlmTimeout').value = s.LLM_TIMEOUT || '120';
                }
            }

            async function saveAppSettings() {
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                const updated = {
                    ADMIN_PASSWORD: document.getElementById('settingAdminPassword').value.trim(),
                    LLM_MODEL: document.getElementById('settingLlmModel').value.trim(),
                    LLM_BASE_URL: document.getElementById('settingLlmBaseUrl').value.trim(),
                    LLM_API_KEY: document.getElementById('settingLlmApiKey').value.trim(),
                    OUTPUT_LANGUAGE: document.getElementById('settingOutputLanguage').value,
                    CRON_DELAY_SECONDS: document.getElementById('settingCronDelaySeconds').value.trim(),
                    LLM_TIMEOUT: document.getElementById('settingLlmTimeout').value.trim()
                };
                const res = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: getAdminHeaders(),
                    body: JSON.stringify(updated)
                });
                if (res.ok) {
                    if (updated.ADMIN_PASSWORD) {
                        adminAuthPassword = updated.ADMIN_PASSWORD;
                        sessionStorage.setItem('ADMIN_AUTH_PASS', updated.ADMIN_PASSWORD);
                    }
                    alert(t.msg_settings_saved);
                } else {
                    const err = await res.json();
                    alert(`Error: ${err.detail || 'Failed to save settings.'}`);
                }
            }

            function switchLogTab(type) {
                activeLogType = type;
                document.getElementById('tabCronLog').classList.toggle('active', type === 'cron');
                document.getElementById('tabAnalysisLog').classList.toggle('active', type === 'analysis');
                document.getElementById('tabLiveLog').classList.toggle('active', type === 'live');
                if (type !== 'live') {
                    fetchFileLogs();
                }
            }

            async function fetchFileLogs() {
                if (activeLogType === 'live') return;
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                const endpoint = activeLogType === 'cron' ? '/api/logs/cron' : '/api/logs/analysis';
                const res = await fetch(endpoint, { headers: getAdminHeaders() });
                if (res.ok) {
                    const data = await res.json();
                    const box = document.getElementById('fileConsoleBox');
                    const logTxt = (data.log !== undefined && data.log !== null) ? data.log : "";
                    box.innerText = logTxt.trim().length > 0 ? logTxt : (t.log_cleared || "Loglar temizlendi.");
                    box.scrollTop = box.scrollHeight;
                }
            }

            async function clearActiveLogs() {
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                const res = await fetch(`/api/logs/clear/${activeLogType}`, {
                    method: 'POST',
                    headers: getAdminHeaders()
                });
                if (res.ok) {
                    document.getElementById('fileConsoleBox').innerText = t.log_cleared || "Loglar temizlendi.";
                } else {
                    const err = await res.json();
                    alert(`Error: ${err.detail || err.message}`);
                }
            }

            async function fetchWatchlist() {
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                const res = await fetch('/api/watchlist');
                const data = await res.json();
                const tbody = document.getElementById('watchlistTableBody');
                if (!tbody) return;
                tbody.innerHTML = data.map(item => {
                    const lastRep = item.last_report;
                    let repBadge = `<span class="tag-badge tag-amber">${t.no_report_badge}</span>`;
                    if (lastRep) {
                        const pScore = lastRep.piotroski_score !== null ? `${lastRep.piotroski_score}/9` : '-';
                        const zScore = lastRep.altman_z !== null ? lastRep.altman_z.toFixed(1) : '-';
                        repBadge = `<span class="tag-badge tag-green" style="cursor:pointer;" onclick="selectAndLoadReport('${item.ticker}')" title="${t.view_report_title}">📅 ${lastRep.report_date} (P:${pScore} | Z:${zScore}) 🔍</span>`;
                    }
                    const activeChecked = item.is_active ? 'checked' : '';
                    return `
                        <tr>
                            <td><strong>${item.ticker}</strong></td>
                            <td>${item.company_name || item.ticker}</td>
                            <td><span class="tag-badge tag-amber">${item.lang}</span></td>
                            <td>
                                <input type="checkbox" ${activeChecked} onchange="toggleStockActive('${item.ticker}', this.checked)">
                            </td>
                            <td>${repBadge}</td>
                            <td style="text-align:right; display:flex; gap:0.4rem; justify-content:flex-end;">
                                <button class="btn btn-primary" onclick="reprocessSingle('${item.ticker}')" title="${t.single_analyze_title}">${t.btn_analyze}</button>
                                <button class="btn" onclick="editStockPrompt('${item.ticker}', '${item.company_name || ''}', '${item.lang}')">${t.btn_edit}</button>
                                <button class="btn btn-danger" onclick="deleteStock('${item.ticker}')">${t.btn_delete}</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            async function createStock() {
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                const tickerInput = document.getElementById('newTicker');
                const companyInput = document.getElementById('newCompanyName');
                const langInput = document.getElementById('newLang');
                const ticker = tickerInput.value.trim();
                if (!ticker) return alert(t.msg_enter_ticker);

                const res = await fetch('/api/watchlist', {
                    method: 'POST',
                    headers: getAdminHeaders(),
                    body: JSON.stringify({
                        ticker: ticker,
                        company_name: companyInput.value.trim(),
                        lang: langInput.value
                    })
                });
                if (res.ok) {
                    tickerInput.value = '';
                    companyInput.value = '';
                    fetchWatchlist();
                    loadTickers(ticker);
                } else {
                    const err = await res.json();
                    alert(`Error: ${err.detail}`);
                }
            }

            async function toggleStockActive(ticker, isActive) {
                await fetch(`/api/watchlist/${ticker}`, {
                    method: 'PUT',
                    headers: getAdminHeaders(),
                    body: JSON.stringify({ is_active: isActive ? 1 : 0 })
                });
                fetchWatchlist();
            }

            function editStockPrompt(ticker, currentName, currentLang) {
                document.getElementById('editStockTicker').value = ticker;
                document.getElementById('editStockTickerDisplay').value = ticker;
                document.getElementById('editStockCompanyName').value = currentName || ticker;
                document.getElementById('editStockLang').value = currentLang || 'TR';
                document.getElementById('editStockModalTitle').innerText = `✏️ Hisse Düzenle: ${ticker}`;
                document.getElementById('editStockModal').classList.add('active');
            }

            function closeEditStockModal() {
                document.getElementById('editStockModal').classList.remove('active');
            }

            async function submitEditStock() {
                const ticker = document.getElementById('editStockTicker').value;
                const companyName = document.getElementById('editStockCompanyName').value.trim();
                const lang = document.getElementById('editStockLang').value;
                if (!ticker) return;

                const res = await fetch(`/api/watchlist/${ticker}`, {
                    method: 'PUT',
                    headers: getAdminHeaders(),
                    body: JSON.stringify({ company_name: companyName, lang: lang })
                });
                if (res.ok) {
                    closeEditStockModal();
                    fetchWatchlist();
                } else {
                    const err = await res.json();
                    alert(`Error: ${err.detail || err.message}`);
                }
            }

            async function deleteStock(ticker) {
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                if (!confirm(`'${ticker}' ${t.confirm_delete}`)) return;
                await fetch(`/api/watchlist/${ticker}`, {
                    method: 'DELETE',
                    headers: getAdminHeaders()
                });
                fetchWatchlist();
                loadTickers();
            }

            function filterTickers(query) {
                const select = document.getElementById("tickerSelect");
                const q = query.toLowerCase().trim();
                for (let i = 0; i < select.options.length; i++) {
                    const opt = select.options[i];
                    const match = opt.text.toLowerCase().includes(q) || opt.value.toLowerCase().includes(q);
                    opt.style.display = match ? "" : "none";
                }
            }

            let currentEventSource = null;

            function startSseStream(targetKey) {
                if (currentEventSource) {
                    currentEventSource.close();
                }
                const box = document.getElementById('fileConsoleBox');
                box.innerText = `▶ Connecting live event stream for: ${targetKey}...\n`;

                currentEventSource = new EventSource(`/api/reprocess/stream/${targetKey}`);
                currentEventSource.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.line) {
                            box.innerText += `${data.line}\n`;
                            box.scrollTop = box.scrollHeight;
                        }
                        if (data.done) {
                            currentEventSource.close();
                            fetchWatchlist();
                            fetchFileLogs();
                            if (targetKey !== '_BATCH_') {
                                loadTickers(targetKey);
                            }
                        }
                    } catch(e) {}
                };
                currentEventSource.onerror = function() {
                    currentEventSource.close();
                    startStatusPolling(targetKey);
                };
            }

            async function reprocessSingle(ticker) {
                switchLogTab('live');
                logConsole(`▶ Single stock analysis triggered for: ${ticker}`);
                const res = await fetch(`/api/reprocess/${ticker}`, {
                    method: 'POST',
                    headers: getAdminHeaders()
                });
                const data = await res.json();
                if (!res.ok) {
                    alert(`Error: ${data.detail || data.message}`);
                    return;
                }
                logConsole(`Status: ${data.message}`);
                startSseStream(ticker);
            }

            async function triggerBatchRun() {
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                switchLogTab('live');
                logConsole(t.msg_batch_started);
                const res = await fetch(`/api/reprocess/batch`, {
                    method: 'POST',
                    headers: getAdminHeaders()
                });
                const data = await res.json();
                if (!res.ok) {
                    alert(`Error: ${data.detail || data.message}`);
                    return;
                }
                logConsole(`Status: ${data.message}`);
                startSseStream('_BATCH_');
            }

            function startStatusPolling(targetKey) {
                if (pollingTimer) clearInterval(pollingTimer);
                pollingTimer = setInterval(async () => {
                    const res = await fetch(`/api/reprocess/status/${targetKey}`);
                    const data = await res.json();
                    if (data.log && data.log.length > 0) {
                        document.getElementById('fileConsoleBox').innerText = data.log.join('\n');
                        const box = document.getElementById('fileConsoleBox');
                        box.scrollTop = box.scrollHeight;
                    }
                    if (data.status === 'SUCCESS' || data.status === 'FAILED') {
                        clearInterval(pollingTimer);
                        fetchWatchlist();
                        fetchFileLogs();
                        if (targetKey !== '_BATCH_') {
                            loadTickers(targetKey);
                        }
                    }
                }, 2000);
            }

            function logConsole(msg) {
                const box = document.getElementById('fileConsoleBox');
                box.innerText += `\n${msg}`;
                box.scrollTop = box.scrollHeight;
            }

            window.onload = function() {
                setUiLanguage(currentUiLang);
                loadTickers();
            };
        </script>
    </body>
    </html>
    """
