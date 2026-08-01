"""
Independent FastAPI Web Server, SPA Dashboard Viewer & Admin Panel
Usage: py -m uvicorn .agents.skills.stock-analyzer-app.3_web_server.main:app --port 6031
"""

import os
import sys
import glob
import json
import time
import sqlite3
import secrets
import subprocess
import asyncio
from typing import Optional
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

try:
    os.umask(0000)
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "1_core_builder"))
from logger import log_error

APP_ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(APP_ENV_PATH)
load_dotenv()

app = FastAPI(title="Stock Research Platform & Password-Protected Admin Panel")

_allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:6031").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTS_DIR = os.path.join(BASE_DIR, "storage", "reports")
LOGS_DIR = os.path.join(BASE_DIR, "storage", "logs")
DB_PATH = os.path.join(BASE_DIR, "storage", "app.db")
WATCHLIST_PATH = os.path.join(BASE_DIR, "2_cron_scheduler", "watchlist.json")
BUILDER_SCRIPT = os.path.join(BASE_DIR, "1_core_builder", "generate_report.py")
SCHEDULER_SCRIPT = os.path.join(BASE_DIR, "2_cron_scheduler", "scheduler.py")
VERSION_PATH = os.path.join(BASE_DIR, "VERSION")

ACCESS_LOG_FILE = os.path.join(LOGS_DIR, "access.log")
IP_CONNECTION_STATS = {}
RECENT_ACCESS_LOGS = []

@app.middleware("http")
async def log_ip_access_middleware(request: Request, call_next):
    x_forwarded = request.headers.get("X-Forwarded-For")
    if x_forwarded:
        ip = x_forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if (request.client and request.client.host) else "127.0.0.1"

    endpoint = request.url.path
    method = request.method
    user_agent = request.headers.get("User-Agent", "Unknown")
    import datetime
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if ip not in IP_CONNECTION_STATS:
        IP_CONNECTION_STATS[ip] = {
            "total_connections": 0,
            "first_access": now_str,
            "last_access": now_str,
            "endpoints": {}
        }
    
    stats = IP_CONNECTION_STATS[ip]
    stats["total_connections"] += 1
    stats["last_access"] = now_str
    stats["endpoints"][endpoint] = stats["endpoints"].get(endpoint, 0) + 1

    entry = {
        "ip": ip,
        "endpoint": endpoint,
        "method": method,
        "timestamp": now_str,
        "user_agent": user_agent[:100]
    }
    RECENT_ACCESS_LOGS.append(entry)
    if len(RECENT_ACCESS_LOGS) > 100:
        RECENT_ACCESS_LOGS.pop(0)

    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_line = f"[{now_str}] IP: {ip} | {method} {endpoint} | UA: {user_agent[:80]}"
        with open(ACCESS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception:
        pass

    response = await call_next(request)
    return response

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


def load_web_locales():
    locales = {}
    locales_dir = os.path.join(BASE_DIR, "3_web_server", "locales")
    for lang in ["tr", "en"]:
        file_path = os.path.join(locales_dir, f"{lang}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    locales[lang.upper()] = json.load(f)
            except Exception:
                pass
    return locales


PYTHON_EXEC = "py" if os.name == "nt" else sys.executable

# Global task state tracking
PROCESS_STATUS = {}
_EPHEMERAL_ADMIN_PASSWORD = None

# Brute-force rate limiter state (VULN-004)
_LOGIN_ATTEMPTS = {}  # {ip: [(timestamp, ...)]}
_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 60


def _check_rate_limit(client_ip: str):
    """Rate limit login attempts: max 5 per 60 seconds per IP."""
    now = time.time()
    attempts = _LOGIN_ATTEMPTS.get(client_ip, [])
    # Prune expired entries
    attempts = [t for t in attempts if now - t < _LOGIN_WINDOW_SECONDS]
    _LOGIN_ATTEMPTS[client_ip] = attempts
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Çok fazla başarısız giriş denemesi. Lütfen 60 saniye bekleyiniz. / Too many failed login attempts. Please wait 60 seconds.")


def _record_failed_attempt(client_ip: str):
    """Record a failed login attempt for rate limiting."""
    now = time.time()
    if client_ip not in _LOGIN_ATTEMPTS:
        _LOGIN_ATTEMPTS[client_ip] = []
    _LOGIN_ATTEMPTS[client_ip].append(now)


def get_admin_password():
    global _EPHEMERAL_ADMIN_PASSWORD
    load_dotenv(APP_ENV_PATH, override=True)
    env_pass = os.getenv("ADMIN_PASSWORD")
    if env_pass and env_pass.strip():
        return env_pass.strip()
    if not _EPHEMERAL_ADMIN_PASSWORD:
        _EPHEMERAL_ADMIN_PASSWORD = secrets.token_hex(16)
        print("⚠️ ADMIN_PASSWORD is not set in .env! An ephemeral admin password has been generated. Set ADMIN_PASSWORD in .env for persistent access.")
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
            dcf_fair_value REAL,
            graham_number REAL,
            lynch_fair_value REAL,
            status TEXT NOT NULL,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, report_date)
        );
    """)
    for col in [("dcf_fair_value", "REAL"), ("graham_number", "REAL"), ("lynch_fair_value", "REAL")]:
        try:
            cur.execute(f"ALTER TABLE reports_index ADD COLUMN {col[0]} {col[1]};")
        except Exception:
            pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cron_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            is_enabled INTEGER DEFAULT 1,
            schedule_time TEXT DEFAULT '18:30',
            timezone TEXT DEFAULT 'Europe/Istanbul',
            run_days TEXT DEFAULT 'mon-fri',
            misfire_grace_minutes INTEGER DEFAULT 120,
            ticker_delay_seconds INTEGER DEFAULT 15,
            is_running INTEGER DEFAULT 0,
            last_run_at TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        INSERT INTO cron_config (id, is_enabled, schedule_time, timezone, run_days, misfire_grace_minutes, ticker_delay_seconds, is_running)
        VALUES (1, 1, '18:30', 'Europe/Istanbul', 'mon-fri', 120, 15, 0)
        ON CONFLICT(id) DO NOTHING;
    """)
    
    def _parse_metric_num(val_str):
        if not val_str: return None
        s = val_str.strip().replace(" ", "")
        if "." in s and "," in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except Exception:
            return None

    # Auto-sync existing report files on disk into reports_index table with metric backfilling
    if os.path.exists(REPORTS_DIR):
        try:
            for ticker in os.listdir(REPORTS_DIR):
                t_dir = os.path.join(REPORTS_DIR, ticker)
                if os.path.isdir(t_dir) and not ticker.startswith(".") and ticker.upper() not in {"BATCH", "TMP", "TEMP"}:
                    for f in glob.glob(os.path.join(t_dir, "*.html")):
                        if not f.endswith("_printable.html"):
                            report_date = os.path.basename(f).replace(".html", "")
                            piotroski = None
                            altman_z = None
                            beneish_m = None
                            wacc = None
                            try:
                                with open(f, "r", encoding="utf-8") as rf:
                                    html_txt = rf.read()
                                pio_m = re.search(r"Piotroski\s*(?:F-Score)?\s*(?:skoru|score)?\s*(\d+)\s*/\s*9", html_txt, re.I)
                                if pio_m: piotroski = int(pio_m.group(1))
                                alt_m = re.search(r"Altman\s*Z-Score[^\d\.-]*(?:Z\s*=\s*)?([\d\.,]+)", html_txt, re.I)
                                if alt_m: altman_z = _parse_metric_num(alt_m.group(1))
                                ben_m = re.search(r"Beneish\s*M-Score[^\d\.-]*(?:M\s*=\s*)?(-?[\d\.,]+)", html_txt, re.I)
                                if ben_m: beneish_m = _parse_metric_num(ben_m.group(1))
                                wacc_m = re.search(r"WACC[^\d\.-]*(?:%|=)?\s*%?\s*([\d\.,]+)\s*%", html_txt, re.I) or re.search(r"WACC[^\d\.-]*([\d\.,]+)", html_txt, re.I)
                                if wacc_m: wacc = _parse_metric_num(wacc_m.group(1))
                            except Exception:
                                pass

                            cur.execute("""
                                INSERT INTO reports_index (ticker, report_date, file_path, piotroski_score, altman_z, beneish_m, wacc_pct, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 'SUCCESS')
                                ON CONFLICT(ticker, report_date) DO UPDATE SET
                                    file_path=excluded.file_path,
                                    piotroski_score=COALESCE(excluded.piotroski_score, piotroski_score),
                                    altman_z=COALESCE(excluded.altman_z, altman_z),
                                    beneish_m=COALESCE(excluded.beneish_m, beneish_m),
                                    wacc_pct=COALESCE(excluded.wacc_pct, wacc_pct),
                                    status='SUCCESS';
                            """, (ticker, report_date, f, piotroski, altman_z, beneish_m, wacc))
            conn.commit()
        except Exception as e:
            print(f"⚠️ Error syncing reports_index on init: {e}")

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
    LLM_TIMEOUT: Optional[str] = "120"
    CRON_DELAY_SECONDS: Optional[str] = "15"
    STRICT_LLM: Optional[str] = "false"


# ══════════════════════════════════════════════════════════════
# AUTHENTICATION & APP SETTINGS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.post("/api/admin/verify")
def verify_admin(req: AdminVerifyRequest, x_forwarded_for: Optional[str] = Header(None)):
    ip_str = x_forwarded_for if isinstance(x_forwarded_for, str) else "unknown"
    client_ip = ip_str.split(",")[0].strip() if ip_str else "unknown"
    _check_rate_limit(client_ip)
    current_pass = get_admin_password()
    if req.password and secrets.compare_digest(req.password, current_pass):
        # Clear failed attempts on successful login
        _LOGIN_ATTEMPTS.pop(client_ip, None)
        return {"status": "ok", "message": "Şifre doğrulandı."}
    _record_failed_attempt(client_ip)
    raise HTTPException(status_code=401, detail="Hatalı Şifre. Lütfen tekrar deneyiniz.")


def _mask_api_key(key: str) -> str:
    """Mask an API key, showing only the last 4 characters."""
    if not key or len(key) <= 4:
        return "••••"
    return "••••" + key[-4:]


@app.get("/api/settings")
def get_app_settings(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    load_dotenv(APP_ENV_PATH, override=True)
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("BASE_URL") or os.getenv("NINEROUTER_URL", "http://localhost:20128/v1")
    api_key = os.getenv("LLM_API_KEY") or os.getenv("API_KEY") or os.getenv("NINEROUTER_KEY", "")
    return {
        "VERSION": get_app_version(),
        "ADMIN_PASSWORD": "••••••••",
        "ADMIN_PASSWORD_IS_SET": bool(os.getenv("ADMIN_PASSWORD", "").strip()),
        "LLM_BASE_URL": base_url,
        "LLM_API_KEY": _mask_api_key(api_key),
        "LLM_API_KEY_IS_SET": bool(api_key.strip()),
        "LLM_MODEL": os.getenv("LLM_MODEL", "code_combo"),
        "LLM_TIMEOUT": os.getenv("LLM_TIMEOUT", "120"),
        "CRON_DELAY_SECONDS": os.getenv("CRON_DELAY_SECONDS", "15"),
        "STRICT_LLM": os.getenv("STRICT_LLM", "false")
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

    if settings.ADMIN_PASSWORD is not None and settings.ADMIN_PASSWORD.strip() and not settings.ADMIN_PASSWORD.strip().startswith("••••"):
        env_data["ADMIN_PASSWORD"] = settings.ADMIN_PASSWORD.strip()
    
    base_url_val = settings.LLM_BASE_URL or settings.BASE_URL or settings.NINEROUTER_URL
    if base_url_val is not None:
        env_data["LLM_BASE_URL"] = base_url_val.strip()

    api_key_val = settings.LLM_API_KEY or settings.API_KEY or settings.NINEROUTER_KEY
    if api_key_val is not None and api_key_val.strip() and not api_key_val.strip().startswith("••••"):
        env_data["LLM_API_KEY"] = api_key_val.strip()
    if settings.LLM_MODEL is not None and settings.LLM_MODEL.strip():
        env_data["LLM_MODEL"] = settings.LLM_MODEL.strip()
    if settings.STRICT_LLM is not None:
        env_data["STRICT_LLM"] = str(settings.STRICT_LLM).lower()
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
# CRON SCHEDULER REST ENDPOINTS
# ══════════════════════════════════════════════════════════════

class CronConfigPayload(BaseModel):
    is_enabled: bool = True
    schedule_time: str = "18:30"
    timezone: str = "Europe/Istanbul"
    run_days: str = "mon-fri"
    misfire_grace_minutes: int = 120
    ticker_delay_seconds: int = 15

def get_cron_config_from_db():
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT is_enabled, schedule_time, timezone, run_days, misfire_grace_minutes, ticker_delay_seconds, is_running, last_run_at
            FROM cron_config WHERE id = 1
        """)
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                "is_enabled": bool(row[0]),
                "schedule_time": row[1] or "18:30",
                "timezone": row[2] or "Europe/Istanbul",
                "run_days": row[3] or "mon-fri",
                "misfire_grace_minutes": int(row[4] if row[4] is not None else 120),
                "ticker_delay_seconds": int(row[5] if row[5] is not None else 15),
                "is_running": bool(row[6]),
                "last_run_at": row[7]
            }
    except Exception as e:
        print(f"Error fetching cron_config: {e}")
    return {
        "is_enabled": True,
        "schedule_time": "18:30",
        "timezone": "Europe/Istanbul",
        "run_days": "mon-fri",
        "misfire_grace_minutes": 120,
        "ticker_delay_seconds": 15,
        "is_running": False,
        "last_run_at": None
    }

@app.get("/api/cron/config")
def get_cron_config_endpoint(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    cfg = get_cron_config_from_db()
    next_run_str = "Unknown"
    try:
        parts = cfg["schedule_time"].split(":")
        h, m = int(parts[0]), int(parts[1])
        now_dt = datetime.datetime.now()
        target_today = now_dt.replace(hour=h, minute=m, second=0, microsecond=0)
        if now_dt > target_today:
            next_dt = target_today + datetime.timedelta(days=1)
        else:
            next_dt = target_today
        next_run_str = f"{next_dt.strftime('%d.%m.%Y %H:%M')} ({cfg['timezone']})"
    except Exception:
        pass
    cfg["next_run_at"] = next_run_str
    return cfg

@app.post("/api/cron/config")
def update_cron_config_endpoint(payload: CronConfigPayload, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE cron_config
        SET is_enabled = ?, schedule_time = ?, timezone = ?, run_days = ?, misfire_grace_minutes = ?, ticker_delay_seconds = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """, (1 if payload.is_enabled else 0, payload.schedule_time, payload.timezone, payload.run_days, payload.misfire_grace_minutes, payload.ticker_delay_seconds))
    conn.commit()
    conn.close()
    return {"message": "Cron zamanlayıcı ayarları kaydedildi.", "config": payload.dict()}

@app.post("/api/cron/run-now")
def trigger_cron_run_now(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    cfg = get_cron_config_from_db()
    if cfg.get("is_running"):
        raise HTTPException(status_code=400, detail="Analiz / Cron çalışması şu anda aktif. Lütfen bitmesini bekleyin.")
    
    python_exec = "py" if os.name == "nt" else sys.executable
    scheduler_script = os.path.join(BASE_DIR, "2_cron_scheduler", "scheduler.py")
    
    try:
        subprocess.Popen([python_exec, scheduler_script, "--now"])
        return {"message": "⚡ Otonom Cron analizi arka planda başlatıldı."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cron başlatılamadı: {e}")


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


@app.get("/api/logs/errors")
def get_error_logs(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    log_path = os.path.join(LOGS_DIR, "errors.log")
    return {"log": read_last_log_lines(log_path)}


@app.get("/api/logs/access")
def get_access_logs(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    log_path = os.path.join(LOGS_DIR, "access.log")
    return {"log": read_last_log_lines(log_path)}


@app.get("/api/admin/analytics/connections")
def get_connection_analytics(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    total_requests = sum(s.get("total_connections", 0) for s in IP_CONNECTION_STATS.values())
    return {
        "total_unique_ips": len(IP_CONNECTION_STATS),
        "total_requests": total_requests,
        "ip_stats": IP_CONNECTION_STATS,
        "recent_logs": RECENT_ACCESS_LOGS
    }


@app.get("/api/logs/{log_type}")
def get_logs_by_type(log_type: str, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    target = log_type.lower().strip()
    if target == "cron":
        log_path = os.path.join(LOGS_DIR, "cron.log")
    elif target == "analysis":
        log_path = os.path.join(LOGS_DIR, "analysis.log")
    elif target == "errors":
        log_path = os.path.join(LOGS_DIR, "errors.log")
    elif target == "access":
        log_path = os.path.join(LOGS_DIR, "access.log")
    else:
        raise HTTPException(status_code=400, detail=f"Geçersiz log türü / Invalid log type: {log_type}")
    return {"log": read_last_log_lines(log_path)}


@app.post("/api/logs/clear/{log_type}")
def clear_logs(log_type: str, x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    target_type = log_type.lower()
    if target_type in ["cron", "analysis", "errors", "access", "live", "all"]:
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

        if target_type in ["errors", "all"]:
            log_path = os.path.join(LOGS_DIR, "errors.log")
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Errors log temizleme hatası: {e}")

        if target_type in ["access", "all"]:
            log_path = os.path.join(LOGS_DIR, "access.log")
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Access log temizleme hatası: {e}")

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
        is_strict = os.getenv("STRICT_LLM", "false").lower() in ("true", "1", "yes")
        cmd = [PYTHON_EXEC, BUILDER_SCRIPT, ticker, "--lang", lang]
        if is_strict:
            cmd.append("--strict-llm")

        proc = subprocess.Popen(
            cmd,
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
    
    lang = (row[0] if row and row[0] else "TR").strip().upper()

    background_tasks.add_task(run_single_report_background, ticker, lang)
    return {"message": f"Report generation queued for {ticker} (Lang: {lang}).", "status": "QUEUED"}


@app.get("/api/reprocess/active")
def get_active_reprocess_status(x_admin_password: Optional[str] = Header(None)):
    verify_password_header(x_admin_password)
    for key, val in PROCESS_STATUS.items():
        if val.get("status") == "RUNNING":
            return {"active": True, "ticker": key, "status": "RUNNING", "log": val.get("log", [])}
    if PROCESS_STATUS:
        latest_key = list(PROCESS_STATUS.keys())[-1]
        val = PROCESS_STATUS[latest_key]
        return {"active": False, "ticker": latest_key, "status": val.get("status", "IDLE"), "log": val.get("log", [])}
    return {"active": False, "ticker": None, "status": "IDLE", "log": []}


@app.get("/api/reprocess/status/{ticker}")
def get_reprocess_status(ticker: str):
    ticker = ticker.strip().upper()
    info = PROCESS_STATUS.get(ticker, {"status": "IDLE", "log": []})
    return info


class Module13Request(BaseModel):
    ticker: str
    target_date: Optional[str] = None
    lang: Optional[str] = "TR"


@app.post("/api/v1/modules/13/generate")
def generate_module13_blog(req: Module13Request):
    ticker = req.ticker.strip().upper()
    lang = (req.lang or "TR").strip().upper()

    workspace_dir = os.path.join(BASE_DIR, "storage", "_workspace")
    metrics_path = os.path.join(workspace_dir, f"01_quant_metrics_{ticker}.json")
    commentary_path = os.path.join(workspace_dir, f"02_llm_commentary_{ticker}.json")

    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail=f"Metrics for {ticker} not found. Please run initial analysis first.")

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    builder_path = os.path.join(BASE_DIR, "1_core_builder")
    if builder_path not in sys.path:
        sys.path.insert(0, builder_path)

    from llm_commentary import generate_commentary
    commentary = generate_commentary(metrics, lang=lang)

    with open(commentary_path, "w", encoding="utf-8") as f:
        json.dump(commentary, f, indent=2, ensure_ascii=False)

    return {
        "ticker": ticker,
        "lang": lang,
        "blog_headline": commentary.get("blog_headline", ""),
        "blog_summary": commentary.get("blog_summary", ""),
        "blog_cash_and_health": commentary.get("blog_cash_and_health", ""),
        "blog_earnings_quality": commentary.get("blog_earnings_quality", ""),
        "blog_valuation_dcf": commentary.get("blog_valuation_dcf", ""),
        "blog_catalysts_and_risks": commentary.get("blog_catalysts_and_risks", ""),
        "blog_bull_vs_bear": commentary.get("blog_bull_vs_bear", ""),
        "blog_key_takeaways": commentary.get("blog_key_takeaways", []),
        "blog_faqs": commentary.get("blog_faqs", []),
        "status": "SUCCESS"
    }


@app.get("/api/v1/matrix")
def get_stock_matrix(lang: str = "TR"):
    lang = (lang or "TR").strip().upper()
    workspace_dir = os.path.join(BASE_DIR, "storage", "_workspace")
    reports_dir = os.path.join(BASE_DIR, "storage", "reports")

    metric_files = {}

    # 1. Scan storage/_workspace/
    if os.path.exists(workspace_dir):
        for fname in os.listdir(workspace_dir):
            if fname.startswith("01_quant_metrics_") and fname.endswith(".json"):
                ticker = fname.replace("01_quant_metrics_", "").replace(".json", "")
                metric_files[ticker] = os.path.join(workspace_dir, fname)

    # 2. Scan storage/reports/ directories for stored metrics or auto-fetch
    if os.path.exists(reports_dir):
        for t_dir in os.listdir(reports_dir):
            if t_dir.startswith(".") or t_dir.startswith("-") or t_dir.startswith("_"):
                continue
            t_path = os.path.join(reports_dir, t_dir)
            if os.path.isdir(t_path):
                ticker = t_dir
                if ticker not in metric_files:
                    quant_p1 = os.path.join(t_path, "quant_metrics.json")
                    quant_p2 = os.path.join(t_path, f"01_quant_metrics_{ticker}.json")
                    if os.path.exists(quant_p1):
                        metric_files[ticker] = quant_p1
                    elif os.path.exists(quant_p2):
                        metric_files[ticker] = quant_p2
                    else:
                        try:
                            sourcing_script = os.path.join(BASE_DIR, "1_core_builder", "fetch_yfinance.py")
                            if os.path.exists(sourcing_script):
                                out_p = os.path.join(t_path, "quant_metrics.json")
                                python_exec = sys.executable
                                subprocess.run([python_exec, sourcing_script, ticker, "--output", out_p, "--language", lang], check=False, timeout=15)
                                if os.path.exists(out_p):
                                    metric_files[ticker] = out_p
                        except Exception as e:
                            print(f"⚠️ Matrix auto-fetch error for {ticker}: {e}")

    matrix_items = []
    for ticker, fpath in sorted(metric_files.items()):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception:
            continue

        mi = metrics.get("market_info", {})
        name = metrics.get("name") or ticker
        price = mi.get("current_price", 0)
        mcap = mi.get("market_cap", 0)
        sma50 = mi.get("fifty_day_avg", price)

        pf = metrics.get("piotroski_f_score", {})
        pf_score = pf.get("score", 0)

        az = metrics.get("altman_z_score", {})
        z_score = az.get("z_score", 0)
        z_zone = az.get("zone", "Grey Zone")

        bm = metrics.get("beneish_m_score", {})
        m_score = bm.get("m_score", -2.85)
        is_safe_m = m_score <= -1.78

        dp = metrics.get("dupont_analysis", {})
        dupont_roe = dp.get("dupont_roe_pct", 0)

        rdcf = metrics.get("reverse_dcf", {})
        implied_g = rdcf.get("implied_growth_rate_raw", 0)

        exp = metrics.get("expanded_metrics", {})
        hist = metrics.get("historical_metrics", [])
        last_rev = hist[0].get("revenue", 1) if hist else 1
        last_ni = hist[0].get("net_income", 1) if hist else 1

        ps_ratio = exp.get("ps_ratio") or (mcap / last_rev if last_rev > 0 else 0)
        pe_ratio = exp.get("pe_ratio") or (mcap / last_ni if last_ni > 0 else 0)

        rs = metrics.get("relative_strength", {})
        rsi = rs.get("technical_indicators", {}).get("rsi_14", 50)

        health_score = 10.0 if ("Safe Zone" in z_zone or (z_score is not None and z_score > 2.60) or "Bank" in z_zone) else (6.0 if "Grey Zone" in z_zone else 2.0)
        cash_score = min(10.0, (pf_score / 9.0) * 10.0)
        growth_score = min(10.0, max(0.0, (dupont_roe / 25.0) * 10.0))
        val_score = 10.0 if (0 < ps_ratio < 3.0) else (6.0 if (0 < ps_ratio < 8.0) else 2.0)
        mom_score = 8.0 if price >= sma50 else 4.0

        composite = round(health_score * 0.30 + cash_score * 0.25 + growth_score * 0.20 + val_score * 0.15 + mom_score * 0.10, 1)

        if composite >= 8.5:
            verdict_code = "STRONG_BUY"
            verdict_label = "🟢 Strong Buy" if lang == "EN" else "🟢 Güçlü Al"
        elif composite >= 6.5:
            verdict_code = "BALANCED"
            verdict_label = "🔵 Balanced" if lang == "EN" else "🔵 Dengeli"
        elif composite >= 4.5:
            verdict_code = "NEUTRAL"
            verdict_label = "🟡 Neutral" if lang == "EN" else "🟡 Nötr"
        else:
            verdict_code = "HIGH_RISK"
            verdict_label = "🔴 High Risk" if lang == "EN" else "🔴 Yüksek Risk"

        matrix_items.append({
            "ticker": ticker,
            "name": name,
            "price": price,
            "market_cap": mcap,
            "piotroski_score": pf_score,
            "altman_z_score": round(z_score, 2) if isinstance(z_score, (int, float)) else None,
            "altman_zone": z_zone,
            "beneish_m_score": round(m_score, 2),
            "beneish_safe": is_safe_m,
            "dupont_roe_pct": round(dupont_roe, 2),
            "implied_growth_pct": round(implied_g * 100, 2) if isinstance(implied_g, (int, float)) else None,
            "ps_ratio": round(ps_ratio, 1),
            "pe_ratio": round(pe_ratio, 1),
            "rsi_14": round(rsi, 1),
            "composite_score": composite,
            "verdict_code": verdict_code,
            "verdict_label": verdict_label
        })

    return matrix_items


@app.get("/api/valuation/history/{ticker}")
def get_valuation_history(ticker: str):
    ticker = ticker.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT report_date, stock_price, market_cap, net_debt, piotroski_score, altman_z, beneish_m, wacc_pct, ps_ratio, pe_ratio, ev_ebitda, dcf_fair_value, graham_number, lynch_fair_value, fcf_margin_pct, recent_fcf, created_at
        FROM reports_index
        WHERE ticker = ? AND status = 'SUCCESS'
        ORDER BY report_date ASC
    """, (ticker,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"ticker": ticker, "history": rows}


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
        if os.path.isdir(os.path.join(REPORTS_DIR, d)) 
        and d.upper() not in ignored 
        and not d.startswith(".") 
        and not d.startswith("-") 
        and not d.startswith("_")
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
    html_content = r"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stock Research Platform & Admin Panel</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-dark: #0f172a;
                --panel-bg: #1e293b;
                --panel-hover: #334155;
                --panel-border: #334155;
                --accent-cyan: #3b82f6;
                --accent-emerald: #10b981;
                --accent-amber: #f59e0b;
                --accent-rose: #ef4444;
                --accent-purple: #8b5cf6;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --body-bg: #0f172a;
                --input-bg: #0f172a;
                --input-border: #334155;
                --font-brand: 'Outfit', sans-serif;
                --font-body: 'Inter', system-ui, sans-serif;
                --font-mono: 'Fira Code', monospace;
            }
            [data-theme="light"] {
                --bg-dark: #f8fafc;
                --panel-bg: #ffffff;
                --panel-hover: #f1f5f9;
                --panel-border: #cbd5e1;
                --accent-cyan: #0284c7;
                --accent-emerald: #059669;
                --accent-amber: #d97706;
                --accent-rose: #e11d48;
                --accent-purple: #7c3aed;
                --text-main: #0f172a;
                --text-muted: #64748b;
                --body-bg: #f8fafc;
                --input-bg: #ffffff;
                --input-border: #cbd5e1;
            }
            .metric-val, .table-num, .financial-data, .hud-val {
                font-family: var(--font-mono);
                font-variant-numeric: tabular-nums;
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
                font-family: var(--font-body);
                background: var(--bg-dark);
                color: var(--text-main);
                display: flex;
                flex-direction: column;
                transition: background-color 0.3s ease, color 0.3s ease;
            }

            header { background: var(--panel-bg); padding: 0.6rem 1rem; display: flex; gap: 1rem; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--panel-border); flex-shrink: 0; z-index: 1000; width: 100%; box-sizing: border-box; transition: background 0.3s ease; }
            .header-left { display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap; flex: 1; min-width: 0; }
            .brand { font-family: var(--font-brand); font-size: 1.2rem; font-weight: 800; color: var(--text-main); display: flex; align-items: center; gap: 0.5rem; }
            .brand-badge { background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); color: #fff; font-size: 0.65rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700; }

            .controls { display: flex; align-items: center; gap: 0.75rem; }
            .control-group { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--text-muted); }
            select, input { background: var(--input-bg); color: var(--text-main); border: 1px solid var(--input-border); padding: 0.45rem 0.8rem; border-radius: 6px; font-size: 0.85rem; outline: none; transition: border-color 0.2s, background-color 0.3s, color 0.3s; }
            select:focus, input:focus { border-color: var(--accent-cyan); }
            
            .btn { background: rgba(255,255,255,0.05); border: 1px solid var(--panel-border); color: var(--text-main); padding: 0.45rem 0.9rem; border-radius: 6px; font-size: 0.85rem; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 0.4rem; transition: all 0.2s; }
            .btn:hover { background: rgba(59, 130, 246, 0.15); border-color: var(--accent-cyan); color: var(--accent-cyan); }
            .btn-primary { background: linear-gradient(135deg, var(--accent-cyan), #0284c7); border: none; color: #fff; }
            .btn-primary:hover { opacity: 0.9; color: #fff; }
            .btn-danger { background: rgba(239, 68, 68, 0.15); border-color: var(--accent-rose); color: var(--accent-rose); }
            .btn-danger:hover { background: var(--accent-rose); color: #fff; }

            #contentFrame { width: 100%; flex: 1 1 0%; min-height: 0; border: none; background: var(--bg-dark); -webkit-overflow-scrolling: touch; transition: background 0.3s ease; }

            /* Slide-Over Admin Drawer */
            .modal-backdrop { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(6px); z-index: 1000; justify-content: flex-end; align-items: stretch; }
            .modal-backdrop.active { display: flex; }
            .modal { background: var(--panel-bg); color: var(--text-main); border-left: 1px solid var(--panel-border); width: 780px; max-width: 95vw; height: 100vh; height: 100dvh; display: flex; flex-direction: column; overflow: hidden; box-shadow: -10px 0 30px rgba(0,0,0,0.5); transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), background 0.3s ease; border-radius: 0; box-sizing: border-box; }
            .modal-backdrop.active .modal { transform: translateX(0); }

            /* Command Palette Modal Overlay */
            .cmd-palette-backdrop { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(8px); z-index: 2000; justify-content: center; align-items: flex-start; padding-top: 10vh; }
            .cmd-palette-backdrop.active { display: flex; }
            .cmd-palette-card { background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 12px; width: 90%; max-width: 600px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); overflow: hidden; display: flex; flex-direction: column; }
            .cmd-search-header { display: flex; align-items: center; gap: 0.75rem; padding: 1rem 1.25rem; border-bottom: 1px solid var(--panel-border); }
            .cmd-search-header input { flex: 1; background: transparent; border: none; font-size: 1.05rem; color: var(--text-main); outline: none; }
            .cmd-badge { background: rgba(255,255,255,0.1); color: var(--text-muted); font-family: var(--font-mono); font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600; }
            .cmd-results-list { max-height: 340px; overflow-y: auto; padding: 0.5rem; }
            .cmd-result-item { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; border-radius: 8px; cursor: pointer; transition: background 0.15s ease; }
            .cmd-result-item:hover, .cmd-result-item.selected { background: rgba(59, 130, 246, 0.15); color: var(--accent-cyan); }
            .cmd-footer { display: flex; gap: 1rem; padding: 0.6rem 1.25rem; background: rgba(0,0,0,0.2); border-top: 1px solid var(--panel-border); font-size: 0.75rem; color: var(--text-muted); }

            /* Financial Health HUD Cards in Header */
            .hud-cards-container { display: flex; align-items: center; gap: 0.5rem; overflow-x: auto; margin-left: 0.5rem; }
            .hud-card { background: rgba(255,255,255,0.03); border: 1px solid var(--panel-border); border-radius: 6px; padding: 0.3rem 0.6rem; display: flex; flex-direction: column; gap: 0.1rem; cursor: pointer; transition: border-color 0.2s, background 0.2s; min-width: 75px; }
            .hud-card:hover { border-color: var(--accent-cyan); background: rgba(59, 130, 246, 0.08); }
            .hud-title { font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }
            .hud-val { font-size: 0.8rem; font-weight: 700; display: flex; align-items: center; gap: 0.25rem; font-family: var(--font-mono); }

            .piotroski-steps { display: flex; gap: 2px; margin-top: 2px; }
            .piotroski-step { width: 5px; height: 4px; border-radius: 1px; background: rgba(255,255,255,0.15); }
            .piotroski-step.active-green { background: #10b981; }
            .piotroski-step.active-amber { background: #f59e0b; }
            .piotroski-step.active-red { background: #ef4444; }

            /* Generic Tooltip Popup */
            #hudTooltip { position: fixed; background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.8rem; color: var(--text-main); box-shadow: 0 10px 25px rgba(0,0,0,0.4); z-index: 3000; pointer-events: none; opacity: 0; transition: opacity 0.15s ease; max-width: 280px; line-height: 1.45; }
            #hudTooltip.active { opacity: 1; }
            .modal-header { padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--panel-border); display: flex; justify-content: space-between; align-items: center; }
            .modal-title { font-family: 'Outfit', sans-serif; font-size: 1.25rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; }
            .close-btn { background: none; border: none; color: var(--text-muted); font-size: 1.4rem; cursor: pointer; }
            .close-btn:hover { color: var(--text-main); }

            .modal-body { padding: 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.5rem; flex: 1; min-height: 0; }

            /* Auth Lock Box */
            .auth-box { background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 10px; padding: 2.5rem; max-width: 450px; margin: 2rem auto; text-align: center; display: flex; flex-direction: column; gap: 1.25rem; }
            .auth-title { font-size: 1.15rem; font-weight: 700; color: var(--accent-cyan); display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
            .auth-input-group { display: flex; gap: 0.5rem; }
            .auth-input-group input { flex: 1; }

            .admin-card { background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: 8px; padding: 1.25rem; }
            .card-heading { font-size: 0.95rem; font-weight: 700; margin-bottom: 1rem; color: var(--accent-cyan); display: flex; justify-content: space-between; align-items: center; }

            .create-form { display: grid; grid-template-columns: 1fr 2fr 100px auto; gap: 0.75rem; align-items: center; }
            .settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
            .form-field { display: flex; flex-direction: column; gap: 0.4rem; font-size: 0.82rem; color: var(--text-muted); }

            .table-wrapper { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
            table.admin-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
            table.admin-table th, table.admin-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--panel-border); }
            table.admin-table th { background: rgba(255,255,255,0.03); color: var(--text-muted); font-weight: 600; }
            table.admin-table tr:hover { background: rgba(255,255,255,0.02); }

            .icon-tools-group { display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; margin-left: auto; }
            .icon-btn {
                background: var(--panel-bg);
                border: 1px solid var(--panel-border);
                color: var(--text-main);
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
                background: var(--input-bg);
                color: var(--text-main);
                border: 1px solid var(--input-border);
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

            /* Matrix Quick Filter Pill Styles */
            .pill-btn {
                background: rgba(255,255,255,0.05);
                border: 1px solid var(--panel-border);
                color: var(--text-muted);
                padding: 0.4rem 0.85rem;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }
            .pill-btn:hover { background: rgba(6, 182, 212, 0.15); color: #fff; border-color: var(--accent-cyan); }
            .pill-btn.active { background: linear-gradient(135deg, var(--accent-cyan), #0284c7); color: #fff; border-color: transparent; }

            /* Admin Domain Tab Bar Styles */
            .admin-nav-bar { display: flex; gap: 0.75rem; border-bottom: 1px solid var(--panel-border); padding-bottom: 0.75rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
            .admin-nav-tab {
                background: rgba(255,255,255,0.04);
                border: 1px solid var(--panel-border);
                color: var(--text-muted);
                padding: 0.6rem 1.2rem;
                border-radius: 8px;
                font-size: 0.9rem;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .admin-nav-tab:hover { background: rgba(6, 182, 212, 0.12); color: #fff; border-color: var(--accent-cyan); }
            .admin-nav-tab.active { background: linear-gradient(135deg, var(--accent-cyan), #0284c7); color: #fff; border-color: transparent; box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3); }

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

            /* Tag Badges & In-Tab Execution Animations */
            .tag-badge { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; line-height: 1.2; }
            .tag-green { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
            .tag-amber { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
            .tag-rose { background: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.3); }
            .pulse-badge { animation: pulseAnimation 1.5s infinite; }
            @keyframes pulseAnimation { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.65; transform: scale(0.98); } 100% { opacity: 1; transform: scale(1); } }
            @keyframes spinAnimation { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .spinner-icon { display: inline-block; animation: spinAnimation 1s linear infinite; }

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
        <script>
            function notifyIframeLanguage() {
                try {
                    const iframe = document.getElementById('contentFrame');
                    if (iframe && iframe.contentWindow) {
                        const lang = typeof currentUiLang !== 'undefined' ? currentUiLang : (localStorage.getItem('UI_LANG') || 'TR');
                        iframe.contentWindow.postMessage({ type: 'CHANGE_UI_LANG', lang: lang }, '*');
                    }
                } catch(e) {}
            }
        </script>
    </head>
    <body>
        <header>
            <div class="header-left">
                <div class="brand">🏛️ Stock Research Platform</div>
                <button class="btn" onclick="openCommandPalette()" title="Universal Ticker Search (⌘K / Ctrl+K)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    <span style="font-size:0.8rem; margin-right:0.2rem;">Ara / Search</span>
                    <kbd class="cmd-badge">⌘K</kbd>
                </button>
                <div class="control-group">
                    <label for="tickerSelect">📈</label>
                    <select id="tickerSelect" onchange="loadDates()"></select>
                </div>
                <div class="control-group">
                    <label for="dateSelect">📅</label>
                    <select id="dateSelect" onchange="loadReport()"></select>
                </div>
                <div style="display:flex; gap:0.4rem; align-items:center;">
                    <button id="navBtnTickerAudit" class="btn btn-primary" onclick="switchToTickerAuditView()" data-i18n="nav_audit">📈 Single Ticker View</button>
                    <button id="navBtnPdfView" class="btn" onclick="switchToPdfView()" data-i18n="nav_pdf">📄 PDF View</button>
                    <button id="navBtnMatrix" class="btn" onclick="switchToMatrixView()" data-i18n="nav_matrix">📊 All-Stocks Matrix</button>
                </div>

                <!-- Financial Health HUD Mini-Cards -->
                <div id="hudCardsContainer" class="hud-cards-container" style="display:none;">
                    <div id="hudCardPiotroski" class="hud-card" onmouseenter="showHudTooltip(event, 'piotroski')" onmouseleave="hideHudTooltip()">
                        <div class="hud-title">Piotroski F</div>
                        <div id="hudValPiotroski" class="hud-val">-</div>
                        <div id="piotroskiStepsBar" class="piotroski-steps"></div>
                    </div>
                    <div id="hudCardAltman" class="hud-card" onmouseenter="showHudTooltip(event, 'altman')" onmouseleave="hideHudTooltip()">
                        <div class="hud-title">Altman Z</div>
                        <div id="hudValAltman" class="hud-val">-</div>
                    </div>
                    <div id="hudCardBeneish" class="hud-card" onmouseenter="showHudTooltip(event, 'beneish')" onmouseleave="hideHudTooltip()">
                        <div class="hud-title">Beneish M</div>
                        <div id="hudValBeneish" class="hud-val">-</div>
                    </div>
                    <div id="hudCardDupont" class="hud-card" onmouseenter="showHudTooltip(event, 'dupont')" onmouseleave="hideHudTooltip()">
                        <div class="hud-title">DuPont ROE</div>
                        <div id="hudValDupont" class="hud-val">-</div>
                    </div>
                    <div id="hudCardDcf" class="hud-card" onmouseenter="showHudTooltip(event, 'dcf')" onmouseleave="hideHudTooltip()">
                        <div class="hud-title">DCF Hedef</div>
                        <div id="hudValDcf" class="hud-val">-</div>
                    </div>
                </div>
            </div>
            <div class="icon-tools-group">
                <button class="btn" onclick="openValuationHistoryModal()" title="📊 Değerleme Formül Trendleri & Tarihçe GFX">📊 GFX</button>
                <button id="headerThemeBtn" class="icon-btn" onclick="toggleMainTheme()" title="Tema / Theme">🌙</button>
                <button class="icon-btn" onclick="openAdminModal()" title="🔒 Admin Paneli / Admin Panel" data-i18n-title="btn_admin">⚙️</button>
                <button class="icon-btn" onclick="printReportPage()" title="Yazdır / Print">🖨️</button>
                <select id="uiLangSelect" class="icon-select" onchange="setUiLanguage(this.value)" title="Dil / Language">
                    <option value="TR">🇹🇷</option>
                    <option value="EN">🇬🇧</option>
                </select>
                <button class="icon-btn mobile-hamburger-btn" onclick="toggleIframeMobileMenu()" title="Menu">☰</button>
            </div>
        </header>

        <!-- Tooltip Element -->
        <div id="hudTooltip"></div>

        <!-- VALUATION HISTORY GFX MODAL -->
        <div id="valuationHistoryModal" class="modal-backdrop" onclick="if(event.target===this) closeValuationHistoryModal()">
            <div class="cmd-palette-card" style="max-width: 840px; width: 92%; max-height: 88vh; display: flex; flex-direction: column;">
                <div class="modal-header" style="padding: 1rem 1.25rem;">
                    <div class="modal-title" id="gfxModalTitle">📊 Değerleme Formül Tarihçesi & GFX Trendleri</div>
                    <button class="close-btn" onclick="closeValuationHistoryModal()">&times;</button>
                </div>
                <div id="gfxModalBody" style="padding: 1.25rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.25rem; background: var(--bg-dark);">
                    <!-- Rendered dynamically -->
                </div>
            </div>
        </div>

        <!-- COMMAND PALETTE OVERLAY MODAL -->
        <div id="commandPaletteModal" class="cmd-palette-backdrop" onclick="if(event.target===this) closeCommandPalette()">
            <div class="cmd-palette-card">
                <div class="cmd-search-header">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    <input type="text" id="cmdSearchInput" placeholder="Hisse veya şirket adı ara (Örn: THYAO, AAPL)..." autocomplete="off" oninput="onCommandSearchInput()" onkeydown="onCommandSearchKeydown(event)">
                    <kbd class="cmd-badge">ESC</kbd>
                </div>
                <div id="cmdSearchResults" class="cmd-results-list"></div>
                <div class="cmd-footer">
                    <span><kbd>↑</kbd> <kbd>↓</kbd> Gezinme</span>
                    <span><kbd>↵</kbd> Seçme</span>
                    <span><kbd>ESC</kbd> Kapat</span>
                </div>
            </div>
        </div>

        <iframe id="contentFrame" onload="syncIframeTheme(); notifyIframeLanguage();"></iframe>
        <div id="matrixContainer" style="display:none; flex:1; overflow-y:auto; padding:1.5rem; background:var(--body-bg);"></div>

        <!-- SLIDE-OVER ADMIN DRAWER -->
        <div id="adminModal" class="modal-backdrop">
            <div class="modal">
                <div class="modal-header">
                    <div class="modal-title" data-i18n="modal_title">⚙️ Hisse Yönetim & Sistem Paneli</div>
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
                    <div id="protectedAdminContent" style="display:none; flex-direction:column; gap:1.25rem;">
                        
                        <!-- ADMIN MAIN TAB BAR -->
                        <div class="admin-nav-bar">
                            <div id="adminNavTabStocks" class="admin-nav-tab active" onclick="switchAdminTab('stocks')" data-i18n="admin_tab_stocks">📈 Hisse Yönetimi</div>
                            <div id="adminNavTabSettings" class="admin-nav-tab" onclick="switchAdminTab('settings')" data-i18n="admin_tab_settings">⚙️ Sistem & LLM Ayarları</div>
                            <div id="adminNavTabLogs" class="admin-nav-tab" onclick="switchAdminTab('logs')" data-i18n="admin_tab_logs">📜 Log Konsolu</div>
                        </div>

                        <!-- DOMAIN TAB 1: STOCKS MANAGEMENT -->
                        <div id="adminDomainTabStocks" style="display:flex; flex-direction:column; gap:1.5rem;">
                            
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

                            <!-- SECTION 4: CRUD WATCHLIST TABLE & BATCH RUN HEADER -->
                            <div class="admin-card">
                                <div class="card-heading" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                                    <span data-i18n="sec4_heading">📋 İzleme Listesi & İşlem Yönetimi (Stock CRUD Table)</span>
                                    <button id="batchRunBtn" class="btn btn-primary" onclick="triggerBatchRun()" data-i18n="btn_batch_run">🚀 Tüm Aktif Hisseleri Çalıştır (Batch Run)</button>
                                </div>
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

                        <!-- DOMAIN TAB 2: SYSTEM & LLM SETTINGS -->
                        <div id="adminDomainTabSettings" style="display:none; flex-direction:column; gap:1.5rem;">
                            <!-- SECTION 1: LLM & SYSTEM SETTINGS (.ENV EDITOR) -->
                            <div class="admin-card">
                                <div class="card-heading">
                                    <span data-i18n="sec1_heading">🛠️ LLM Sağlayıcı & Sistem Ayarları</span>
                                    <button class="btn btn-primary" onclick="saveAppSettings()" data-i18n="btn_save_settings">💾 Ayarları Kaydet</button>
                                </div>
                                <div class="settings-grid">
                                    <div class="form-field">
                                        <label data-i18n="lbl_admin_pass">Yönetici Şifresi:</label>
                                        <div style="display:flex; gap:0.4rem;">
                                            <input type="password" id="settingAdminPassword" data-i18n-ph="ph_setting_admin_pass" placeholder="Yönetici şifresi" style="flex:1;">
                                            <button type="button" class="btn" onclick="togglePasswordVisibility('settingAdminPassword', this)" title="Göster / Gizle">👁️</button>
                                        </div>
                                    </div>
                                    <div class="form-field">
                                        <label data-i18n="lbl_llm_model">LLM Model Adı:</label>
                                        <input type="text" id="settingLlmModel" data-i18n-ph="ph_setting_llm_model" placeholder="Örn: code_combo, gpt-4o">
                                    </div>
                                    <div class="form-field">
                                        <label data-i18n="lbl_llm_url">LLM Provider Base URL:</label>
                                        <input type="text" id="settingLlmBaseUrl" data-i18n-ph="ph_setting_llm_url" placeholder="http://localhost:20128/v1">
                                    </div>
                                    <div class="form-field">
                                        <label data-i18n="lbl_cron_delay">Hisseler Arası Bekleme (Saniye):</label>
                                        <input type="number" id="settingCronDelaySeconds" data-i18n-ph="ph_setting_cron_delay" placeholder="15">
                                    </div>
                                    <div class="form-field">
                                        <label data-i18n="lbl_llm_timeout">LLM Zaman Aşımı (Saniye):</label>
                                        <input type="number" id="settingLlmTimeout" data-i18n-ph="ph_setting_llm_timeout" placeholder="120">
                                    </div>
                                    <div class="form-field" style="grid-column: span 2;">
                                        <label data-i18n="lbl_llm_key">LLM API Key:</label>
                                        <div style="display:flex; gap:0.4rem;">
                                            <input type="password" id="settingLlmApiKey" data-i18n-ph="ph_setting_llm_key" placeholder="sk-..." style="flex:1;">
                                            <button type="button" class="btn" onclick="togglePasswordVisibility('settingLlmApiKey', this)" title="Göster / Gizle">👁️</button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- SECTION 1.5: CRON SCHEDULER SETUP -->
                            <div class="admin-card">
                                <div class="card-heading">
                                    <span data-i18n="sec_cron_heading">⏰ Otomatik Analiz & Cron Zamanlayıcı Ayarları</span>
                                    <div style="display:flex; gap:0.5rem; flex-wrap:wrap; align-items:center;">
                                        <span id="cronStatusBadge" class="badge" style="background:#28a745; color:#fff; padding:4px 8px; border-radius:4px; font-weight:bold;" data-i18n="status_cron_active">🟢 Aktif</span>
                                        <button class="btn btn-secondary" onclick="triggerRunCronNow(event)" data-i18n="btn_run_cron_now">⚡ Hemen Cron Çalıştır (Run Now)</button>
                                        <button class="btn btn-primary" onclick="saveCronConfig()" data-i18n="btn_save_cron_settings">💾 Zamanlayıcı Ayarlarını Kaydet</button>
                                    </div>
                                </div>
                                <div class="settings-grid">
                                    <div class="form-field">
                                        <label data-i18n="lbl_cron_enable">Otonom Cron Zamanlayıcı:</label>
                                        <select id="settingCronEnabled">
                                            <option value="1">🟢 Aktif (Enabled)</option>
                                            <option value="0">🔴 Duraklatıldı (Disabled)</option>
                                        </select>
                                    </div>
                                    <div class="form-field">
                                        <label data-i18n="lbl_cron_time">Çalışma Saati (HH:MM):</label>
                                        <input type="time" id="settingCronTime" value="18:30">
                                    </div>
                                    <div class="form-field">
                                        <label data-i18n="lbl_cron_tz">Zaman Dilimi (Timezone):</label>
                                        <select id="settingCronTimezone">
                                            <option value="Europe/Istanbul">Europe/Istanbul (TSI UTC+3)</option>
                                            <option value="UTC">UTC (Coordinated Universal Time)</option>
                                            <option value="Europe/London">Europe/London (GMT/BST)</option>
                                            <option value="America/New_York">America/New_York (EST/EDT)</option>
                                        </select>
                                    </div>
                                    <div class="form-field">
                                        <label data-i18n="lbl_cron_days">Çalışma Günleri:</label>
                                        <select id="settingCronDays">
                                            <option value="mon-fri" data-i18n="opt_days_weekdays">Hafta İçi (Pazartesi-Cuma)</option>
                                            <option value="mon-sun" data-i18n="opt_days_everyday">Her Gün (Pazartesi-Pazar)</option>
                                        </select>
                                    </div>
                                    <div class="form-field">
                                        <label data-i18n="lbl_cron_misfire">Gecikme Toleransı (Misfire Grace Window - Dakika):</label>
                                        <input type="number" id="settingCronMisfire" placeholder="120" value="120">
                                    </div>
                                    <div class="form-field" style="grid-column: span 2;">
                                        <span style="font-size: 0.85rem; color: #888;">
                                            <strong data-i18n="lbl_next_run">Sonraki Planlanan Çalışma:</strong> <span id="cronNextRunText">Yükleniyor...</span>
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- DOMAIN TAB 3: SYSTEM LOGS & CONSOLE -->
                        <div id="adminDomainTabLogs" style="display:none; flex-direction:column; gap:1.5rem;">
                            <!-- SECTION 2: SYSTEM LOGS & CONSOLE -->
                            <div class="admin-card">
                                <div class="card-heading">
                                    <span data-i18n="sec2_heading">📜 Sistem, Cron Job & Analiz Logları</span>
                                    <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                                        <button class="btn" onclick="fetchFileLogs()" data-i18n="btn_refresh_logs">🔄 Logları Yenile</button>
                                        <button class="btn btn-danger" onclick="clearActiveLogs()" data-i18n="btn_clear_logs">🗑️ Logları Temizle</button>
                                    </div>
                                </div>
                                <div class="log-tab-bar">
                                    <div id="tabCronLog" class="log-tab active" onclick="switchLogTab('cron')" data-i18n="tab_cron">⏰ Cron Scheduler Logları (cron.log)</div>
                                    <div id="tabAnalysisLog" class="log-tab" onclick="switchLogTab('analysis')" data-i18n="tab_analysis">📊 Analiz Rapor Logları (analysis.log)</div>
                                    <div id="tabErrorLog" class="log-tab" onclick="switchLogTab('errors')" data-i18n="tab_errors">🚨 Hata Logları (errors.log)</div>
                                    <div id="tabAccessLog" class="log-tab" onclick="switchLogTab('access')" data-i18n="tab_access">🌐 IP Access Logları (access.log)</div>
                                    <div id="tabLiveLog" class="log-tab" onclick="switchLogTab('live')" data-i18n="tab_live">⚡ Canlı İşlem Çıktısı (Live)</div>
                                </div>
                                <div id="fileConsoleBox" class="console-box">Loglar yükleniyor...</div>
                            </div>
                        </div>

                        <!-- ADMIN MODAL FOOTER VERSION BADGE -->
                        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--panel-border); margin-top:1.25rem; padding-top:0.75rem; font-size:0.8rem; color:var(--text-muted);">
                            <span>📊 Stock Analyzer Platform</span>
                            <span>Sürüm / Version: <strong style="color:var(--accent-cyan); font-weight:700;">v__APP_VERSION__</strong></span>
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
            // XSS protection: escape HTML entities in user-controlled strings (VULN-005)
            function escapeHtml(str) {
                if (str === null || str === undefined) return '';
                const s = String(str);
                const div = document.createElement('div');
                div.textContent = s;
                return div.innerHTML;
            }

            const UI_I18N = {
                TR: {
                    nav_audit: "📈 Tekil Hisse Görünümü",
                    nav_pdf: "📄 PDF Görünümü",
                    nav_matrix: "📊 Tüm Hisseler Matrisi",
                    btn_export_pdf: "🖨️ PDF İndir / Yazdır",
                    admin_tab_stocks: "📈 Hisse Yönetimi",
                    admin_tab_settings: "⚙️ Sistem & LLM Ayarları",
                    opt_dashboard: "📊 İnteraktif",
                    opt_printable: "📄 PDF",
                    btn_admin: "🔒 Yönetim Paneli",
                    modal_title: "⚙️ Hisse Yönetim, LLM & Sistem Logları Paneli",
                    auth_title: "🔒 Yönetici Girişi (.env Şifresi)",
                    auth_desc: "Lütfen uygulamanın <code>.env</code> dosyasında tanımlı <strong>ADMIN_PASSWORD</strong> şifrenizi giriniz.",
                    auth_placeholder: "Yönetici Şifreniz",
                    auth_btn: "Giriş Yap",
                    sec1_heading: "🛠️ LLM Sağlayıcı & Sistem Ayarları",
                    btn_save_settings: "💾 Ayarları Kaydet",
                    lbl_admin_pass: "Yönetici Şifresi:",
                    lbl_output_lang: "Varsayılan Rapor Dili:",
                    lbl_llm_model: "LLM Model Adı:",
                    lbl_llm_url: "LLM Provider Base URL:",
                    lbl_llm_key: "LLM API Key:",
                    lbl_cron_delay: "Hisseler Arası Bekleme (Saniye):",
                    lbl_llm_timeout: "LLM Zaman Aşımı (Saniye):",
                    ph_search_ticker: "Hisse Ara...",
                    ph_setting_admin_pass: "Yönetici şifresi",
                    ph_setting_llm_model: "Örn: gpt-4o, claude-3-5-sonnet",
                    ph_setting_llm_url: "https://api.openai.com/v1",
                    ph_setting_llm_key: "sk-...",
                    ph_setting_cron_delay: "15",
                    ph_setting_llm_timeout: "120",
                    sec2_heading: "📜 Sistem, Cron Job & Analiz Logları",
                    btn_refresh_logs: "🔄 Logları Yenile",
                    btn_clear_logs: "🗑️ Logları Temizle",
                    log_cleared: "Loglar temizlendi.",
                    btn_batch_run: "🚀 Tüm Aktif Hisseleri Çalıştır (Batch Run)",
                    tab_cron: "⏰ Cron Scheduler Logları (cron.log)",
                    tab_analysis: "📊 Analiz Rapor Logları (analysis.log)",
                    tab_errors: "🚨 Hata Logları (errors.log)",
                    tab_access: "🌐 IP Access Logları (access.log)",
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
                    msg_batch_started: "⚡ Tüm aktif hisseler için toplu analiz başlatıldı...",
                    opt_matrix: "📊 Tüm Hisseler Matrisi",
                    matrix_title: "📊 Tüm Hisseler Değerleme & Karşılaştırma Matrisi",
                    matrix_search_ph: "🔍 Hisse Kodu veya Şirket Adı Ara...",
                    pill_all: "🌐 Tüm Hisseler",
                    pill_strong_buy: "🟢 Güçlü Al (Skor ≥ 8.5)",
                    pill_safe_bs: "🛡️ Güvenli Bilanço (Altman Z > 2.99)",
                    pill_high_cash: "🔥 Yüksek Nakit Kalitesi (Piotroski ≥ 7)",
                    pill_bargain: "💎 Ucuz Değerleme (P/S < 5.0)",
                    col_ticker: "Hisse",
                    col_price: "Fiyat",
                    col_mcap: "Piyasa Değeri",
                    col_piotroski: "Piotroski F-Skoru",
                    col_altman: "Altman Z-Score",
                    col_beneish: "Beneish M-Score",
                    col_dupont: "DuPont ROE %",
                    col_growth: "Ters DCF Büyüme (%g)",
                    col_ps: "P/S Çarpanı",
                    col_score: "360° Skoru & Değerlendirme"
                },
                EN: {
                    nav_audit: "📈 Single Ticker View",
                    nav_pdf: "📄 PDF View",
                    nav_matrix: "📊 All Stocks Matrix",
                    btn_export_pdf: "🖨️ Export PDF",
                    admin_tab_stocks: "📈 Stock Management",
                    admin_tab_settings: "⚙️ System & LLM Settings",
                    opt_dashboard: "📊 Interactive",
                    opt_printable: "📄 PDF",
                    opt_matrix: "📊 All Stocks Matrix",
                    matrix_title: "📊 All Stocks Valuation & Comparison Matrix",
                    matrix_search_ph: "🔍 Search Ticker or Company Name...",
                    pill_all: "🌐 All Stocks",
                    pill_strong_buy: "🟢 Strong Buy (Score ≥ 8.5)",
                    pill_safe_bs: "🛡️ Safe Balance Sheet (Altman Z > 2.99)",
                    pill_high_cash: "🔥 High Cash Quality (Piotroski ≥ 7)",
                    pill_bargain: "💎 Bargain Valuation (P/S < 5.0)",
                    col_ticker: "Ticker",
                    col_price: "Price",
                    col_mcap: "Market Cap",
                    col_piotroski: "Piotroski F-Score",
                    col_altman: "Altman Z-Score",
                    col_beneish: "Beneish M-Score",
                    col_dupont: "DuPont ROE %",
                    col_growth: "Reverse DCF Growth (%g)",
                    col_ps: "P/S Ratio",
                    col_score: "360° Score & Verdict",
                    btn_admin: "🔒 Admin Panel",
                    modal_title: "⚙️ Stock Management, LLM & System Logs Panel",
                    auth_title: "🔒 Admin Login (.env Password)",
                    auth_desc: "Please enter the <strong>ADMIN_PASSWORD</strong> defined in the app's <code>.env</code> file.",
                    auth_placeholder: "Admin Password",
                    auth_btn: "Login",
                    sec1_heading: "🛠️ LLM Provider & System Settings",
                    btn_save_settings: "💾 Save Settings",
                    lbl_admin_pass: "Admin Password:",
                    lbl_output_lang: "Default Report Language:",
                    lbl_llm_model: "LLM Model Name:",
                    lbl_llm_url: "LLM Provider Base URL:",
                    lbl_llm_key: "LLM API Key:",
                    lbl_cron_delay: "Delay Between Tickers (Seconds):",
                    lbl_llm_timeout: "LLM Timeout (Seconds):",
                    ph_search_ticker: "Search Ticker...",
                    ph_setting_admin_pass: "Admin Password",
                    ph_setting_llm_model: "e.g. gpt-4o, claude-3-5-sonnet",
                    ph_setting_llm_url: "https://api.openai.com/v1",
                    ph_setting_llm_key: "sk-...",
                    ph_setting_cron_delay: "15",
                    ph_setting_llm_timeout: "120",
                    sec2_heading: "📜 System, Cron Job & Analysis Logs",
                    btn_refresh_logs: "🔄 Refresh Logs",
                    btn_clear_logs: "🗑️ Clear Logs",
                    log_cleared: "Logs cleared successfully.",
                    btn_batch_run: "🚀 Run All Active Stocks (Batch Run)",
                    tab_cron: "⏰ Cron Scheduler Logs (cron.log)",
                    tab_analysis: "📊 Analysis Report Logs (analysis.log)",
                    tab_errors: "🚨 Error Logs (errors.log)",
                    tab_access: "🌐 IP Access Logs (access.log)",
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
                if (document.getElementById('matrixContainer') && document.getElementById('matrixContainer').style.display !== 'none') {
                    loadMatrixView();
                }
            }

            function toggleMainTheme() {
                const currentTheme = document.body.getAttribute('data-theme') || 'dark';
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                document.body.setAttribute('data-theme', newTheme);
                localStorage.setItem('app_theme', newTheme);
                const btn = document.getElementById('headerThemeBtn');
                if (btn) btn.innerHTML = newTheme === 'light' ? '☀️' : '🌙';
                syncIframeTheme();
            }

            function syncIframeTheme() {
                const activeTheme = document.body.getAttribute('data-theme') || localStorage.getItem('app_theme') || 'dark';
                const iframe = document.getElementById('contentFrame');
                if (iframe) {
                    try {
                        if (iframe.contentDocument && iframe.contentDocument.body) {
                            iframe.contentDocument.body.setAttribute('data-theme', activeTheme);
                        }
                        if (iframe.contentWindow && iframe.contentWindow.toggleTheme) {
                            const innerTheme = iframe.contentDocument && iframe.contentDocument.body ? iframe.contentDocument.body.getAttribute('data-theme') : null;
                            if (innerTheme !== activeTheme) {
                                iframe.contentWindow.toggleTheme();
                            }
                        }
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

            function renderEmptyStateFrame() {
                const frame = document.getElementById('contentFrame');
                if (!frame) return;
                const curLang = currentUiLang || localStorage.getItem('UI_LANG') || 'TR';
                const emptyTxt = curLang === 'EN' ? {
                    desc: "No reports have been generated yet. Click the <strong>🔒 Admin Panel</strong> button in the top right and click <strong>'⚡ Analyze'</strong> or <strong>'🚀 Run All Active Stocks (Batch Run)'</strong> to generate your first reports.",
                    btn: "🔒 Open Admin Panel"
                } : {
                    desc: "Henüz oluşturulmuş bir rapor bulunmuyor. Üst sağdaki <strong>🔒 Yönetim Paneli</strong> butonuna tıklayarak <strong>'⚡ Analiz Et'</strong> veya <strong>'🚀 Tüm Aktif Hisseleri Çalıştır (Batch Run)'</strong> butonu ile ilk raporlarınızı oluşturabilirsiniz.",
                    btn: "🔒 Yönetim Paneli (Admin Panel)"
                };
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
                        <p id="emptyDesc">${emptyTxt.desc}</p>
                        <button class="btn" id="emptyBtn" onclick="window.parent.triggerAdminModal()">${emptyTxt.btn}</button>
                    </div>
                    <script>
                        window.addEventListener('message', (event) => {
                            if (event.data && event.data.type === 'CHANGE_UI_LANG') {
                                const isEn = event.data.lang === 'EN';
                                const desc = document.getElementById('emptyDesc');
                                const btn = document.getElementById('emptyBtn');
                                if (desc) desc.innerHTML = isEn ? "No reports have been generated yet. Click the <strong>🔒 Admin Panel</strong> button in the top right and click <strong>'⚡ Analyze'</strong> or <strong>'🚀 Run All Active Stocks (Batch Run)'</strong> to generate your first reports." : "Henüz oluşturulmuş bir rapor bulunmuyor. Üst sağdaki <strong>🔒 Yönetim Paneli</strong> butonuna tıklayarak <strong>'⚡ Analiz Et'</strong> veya <strong>'🚀 Tüm Aktif Hisseleri Çalıştır (Batch Run)'</strong> butonu ile ilk raporlarınızı oluşturabilirsiniz.";
                                if (btn) btn.innerHTML = isEn ? "🔒 Open Admin Panel" : "🔒 Yönetim Paneli (Admin Panel)";
                            }
                        });
                    <\/script>
                </body>
                </html>`;
            }

            async function loadTickers(targetTicker = null) {
                try {
                    const sel = document.getElementById('tickerSelect');
                    if (!sel) return;
                    const previousTicker = targetTicker || sel.value;
                    const res = await fetch('/api/tickers');
                    if (!res.ok) return;
                    const tickers = await res.json();
                    if (!Array.isArray(tickers)) return;
                    sel.innerHTML = tickers.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
                    if (previousTicker && tickers.includes(previousTicker)) {
                        sel.value = previousTicker;
                    }
                    if (tickers.length > 0) {
                        await loadDates();
                    } else {
                        renderEmptyStateFrame();
                    }
                } catch(e) {
                    console.error('Error loading tickers:', e);
                }
            }

            async function selectAndLoadReport(ticker) {
                closeAdminModal();
                await loadTickers(ticker);
            }

            async function loadDates() {
                try {
                    const selTicker = document.getElementById('tickerSelect');
                    if (!selTicker) return;
                    const ticker = selTicker.value;
                    if (!ticker) return;
                    const res = await fetch(`/api/dates/${encodeURIComponent(ticker)}`);
                    if (!res.ok) return;
                    const dates = await res.json();
                    if (!Array.isArray(dates)) return;
                    const sel = document.getElementById('dateSelect');
                    if (!sel) return;
                    sel.innerHTML = dates.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
                    if (dates.length > 0) {
                        loadReport();
                    } else {
                        renderEmptyStateFrame();
                    }
                } catch(e) {
                    console.error('Error loading dates:', e);
                }
            }

            let matrixData = [];
            let matrixSortKey = 'composite_score';
            let matrixSortAsc = false;
            let matrixFilterText = '';
            let matrixFilterCategory = 'ALL';

            let currentMainView = 'audit';

            function switchToTickerAuditView() {
                currentMainView = 'audit';
                const btnAudit = document.getElementById('navBtnTickerAudit');
                const btnPdf = document.getElementById('navBtnPdfView');
                const btnMatrix = document.getElementById('navBtnMatrix');
                if (btnAudit) { btnAudit.classList.add('btn-primary'); }
                if (btnPdf) { btnPdf.classList.remove('btn-primary'); }
                if (btnMatrix) { btnMatrix.classList.remove('btn-primary'); }
                
                const frame = document.getElementById('contentFrame');
                const matrixBox = document.getElementById('matrixContainer');
                if (matrixBox) matrixBox.style.display = 'none';
                if (frame) frame.style.display = 'block';
                loadReport();
            }

            function switchToPdfView() {
                currentMainView = 'pdf';
                const btnAudit = document.getElementById('navBtnTickerAudit');
                const btnPdf = document.getElementById('navBtnPdfView');
                const btnMatrix = document.getElementById('navBtnMatrix');
                if (btnPdf) { btnPdf.classList.add('btn-primary'); }
                if (btnAudit) { btnAudit.classList.remove('btn-primary'); }
                if (btnMatrix) { btnMatrix.classList.remove('btn-primary'); }
                
                const frame = document.getElementById('contentFrame');
                const matrixBox = document.getElementById('matrixContainer');
                if (matrixBox) matrixBox.style.display = 'none';
                if (frame) frame.style.display = 'block';
                loadReport();
            }

            function switchToMatrixView() {
                currentMainView = 'matrix';
                const btnAudit = document.getElementById('navBtnTickerAudit');
                const btnPdf = document.getElementById('navBtnPdfView');
                const btnMatrix = document.getElementById('navBtnMatrix');
                if (btnMatrix) { btnMatrix.classList.add('btn-primary'); }
                if (btnAudit) { btnAudit.classList.remove('btn-primary'); }
                if (btnPdf) { btnPdf.classList.remove('btn-primary'); }
                
                const frame = document.getElementById('contentFrame');
                const matrixBox = document.getElementById('matrixContainer');
                if (frame) frame.style.display = 'none';
                if (matrixBox) {
                    matrixBox.style.display = 'block';
                    loadMatrixView();
                }
            }

            function loadReport() {
                try {
                    const selTicker = document.getElementById('tickerSelect');
                    const selDate = document.getElementById('dateSelect');
                    if (!selTicker || !selDate) return;
                    const ticker = selTicker.value;
                    const date = selDate.value;

                    const frame = document.getElementById('contentFrame');
                    const matrixBox = document.getElementById('matrixContainer');

                    if (currentMainView === 'matrix') {
                        if (frame) frame.style.display = 'none';
                        if (matrixBox) {
                            matrixBox.style.display = 'block';
                            loadMatrixView();
                        }
                    } else {
                        if (matrixBox) matrixBox.style.display = 'none';
                        if (frame) {
                            frame.style.display = 'block';
                            if (ticker && date) {
                                const mode = currentMainView === 'pdf' ? 'printable' : 'dashboard';
                                frame.src = `/api/reports/${encodeURIComponent(ticker)}/${encodeURIComponent(date)}?mode=${mode}&lang=${encodeURIComponent(currentUiLang)}`;
                            }
                        }
                    }

                    if (ticker) {
                        if (matrixData && matrixData.length > 0) {
                            const found = matrixData.find(item => item.ticker.toUpperCase() === ticker.toUpperCase());
                            if (found) updateHudData(found);
                        } else {
                            fetch(`/api/v1/matrix?lang=${currentUiLang}`).then(r => r.json()).then(data => {
                                if (Array.isArray(data)) {
                                    matrixData = data;
                                    const found = data.find(item => item.ticker.toUpperCase() === ticker.toUpperCase());
                                    if (found) updateHudData(found);
                                }
                            }).catch(() => {});
                        }
                    }
                } catch(e) {
                    console.error('Error loading report:', e);
                }
            }

            async function loadMatrixView() {
                try {
                    const res = await fetch(`/api/v1/matrix?lang=${currentUiLang}`);
                    if (!res.ok) return;
                    matrixData = await res.json();
                    renderMatrixTable();
                } catch(e) {
                    console.error('Error loading matrix view:', e);
                }
            }

            function setMatrixCategoryFilter(cat) {
                matrixFilterCategory = cat;
                renderMatrixTable();
            }

            function sortMatrixBy(key) {
                if (matrixSortKey === key) {
                    matrixSortAsc = !matrixSortAsc;
                } else {
                    matrixSortKey = key;
                    matrixSortAsc = (key === 'ticker' || key === 'name');
                }
                renderMatrixTable();
            }

            async function selectMatrixStock(ticker) {
                const modeSel = document.getElementById('modeSelect');
                if (modeSel) modeSel.value = 'dashboard';
                await selectAndLoadReport(ticker);
            }

            function renderMatrixTable() {
                const box = document.getElementById('matrixContainer');
                if (!box) return;
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;

                let filtered = matrixData.filter(item => {
                    const q = matrixFilterText.toLowerCase().trim();
                    const matchesText = !q || item.ticker.toLowerCase().includes(q) || item.name.toLowerCase().includes(q);
                    let matchesCat = true;
                    if (matrixFilterCategory === 'STRONG_BUY') matchesCat = (item.verdict_code === 'STRONG_BUY');
                    else if (matrixFilterCategory === 'SAFE_BS') matchesCat = (item.altman_z_score > 2.99);
                    else if (matrixFilterCategory === 'HIGH_CASH') matchesCat = (item.piotroski_score >= 7);
                    else if (matrixFilterCategory === 'BARGAIN') matchesCat = (item.ps_ratio > 0 && item.ps_ratio < 5.0);
                    return matchesText && matchesCat;
                });

                filtered.sort((a, b) => {
                    let valA = a[matrixSortKey];
                    let valB = b[matrixSortKey];
                    if (typeof valA === 'string') valA = valA.toLowerCase();
                    if (typeof valB === 'string') valB = valB.toLowerCase();
                    if (valA < valB) return matrixSortAsc ? -1 : 1;
                    if (valA > valB) return matrixSortAsc ? 1 : -1;
                    return 0;
                });

                function getSortIcon(key) {
                    if (matrixSortKey !== key) return '↕️';
                    return matrixSortAsc ? '▲' : '▼';
                }

                const currencySym = currentUiLang === 'EN' ? '$' : '₺';

                let html = `
                    <div style="max-width:1280px; margin:0 auto; display:flex; flex-direction:column; gap:1.25rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
                            <h2 style="font-family:'Outfit',sans-serif; font-size:1.35rem; font-weight:700; color:var(--text-main); margin:0;">
                                ${t.matrix_title || '📊 Tüm Hisseler Değerleme & Karşılaştırma Matrisi'}
                            </h2>
                            <div style="display:flex; gap:0.5rem; align-items:center;">
                                <input type="text" id="matrixSearchInput" placeholder="${t.matrix_search_ph || '🔍 Search Ticker...'}" value="${matrixFilterText}" oninput="matrixFilterText = this.value; renderMatrixTable();" style="background:var(--input-bg); color:var(--text-main); border:1px solid var(--input-border); padding:0.45rem 0.8rem; border-radius:6px; font-size:0.85rem; width:240px; outline:none;">
                            </div>
                        </div>

                        <div style="display:flex; gap:0.5rem; flex-wrap:wrap; align-items:center;">
                            <button onclick="setMatrixCategoryFilter('ALL')" class="pill-btn ${matrixFilterCategory === 'ALL' ? 'active' : ''}">${t.pill_all || '🌐 Tüm Hisseler'}</button>
                            <button onclick="setMatrixCategoryFilter('STRONG_BUY')" class="pill-btn ${matrixFilterCategory === 'STRONG_BUY' ? 'active' : ''}">${t.pill_strong_buy || '🟢 Güçlü Al (Skor ≥ 8.5)'}</button>
                            <button onclick="setMatrixCategoryFilter('SAFE_BS')" class="pill-btn ${matrixFilterCategory === 'SAFE_BS' ? 'active' : ''}">${t.pill_safe_bs || '🛡️ Güvenli Bilanço (Altman Z > 2.99)'}</button>
                            <button onclick="setMatrixCategoryFilter('HIGH_CASH')" class="pill-btn ${matrixFilterCategory === 'HIGH_CASH' ? 'active' : ''}">${t.pill_high_cash || '🔥 Yüksek Nakit Kalitesi (Piotroski ≥ 7)'}</button>
                            <button onclick="setMatrixCategoryFilter('BARGAIN')" class="pill-btn ${matrixFilterCategory === 'BARGAIN' ? 'active' : ''}">${t.pill_bargain || '💎 Ucuz Değerleme (P/S < 5.0)'}</button>
                        </div>

                        <div style="background:var(--panel-bg); border:1px solid var(--panel-border); border-radius:10px; overflow-x:auto;">
                            <table class="admin-table matrix-table" style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                                <thead>
                                    <tr style="background:rgba(255,255,255,0.04); color:var(--text-muted);">
                                        <th onclick="sortMatrixBy('ticker')" style="cursor:pointer;">${t.col_ticker || 'Hisse'} ${getSortIcon('ticker')}</th>
                                        <th onclick="sortMatrixBy('price')" style="cursor:pointer; text-align:right;">${t.col_price || 'Fiyat'} ${getSortIcon('price')}</th>
                                        <th onclick="sortMatrixBy('piotroski_score')" style="cursor:pointer; text-align:center;">${t.col_piotroski || 'Piotroski'} ${getSortIcon('piotroski_score')}</th>
                                        <th onclick="sortMatrixBy('altman_z_score')" style="cursor:pointer; text-align:center;">${t.col_altman || 'Altman Z'} ${getSortIcon('altman_z_score')}</th>
                                        <th onclick="sortMatrixBy('beneish_m_score')" style="cursor:pointer; text-align:center;">${t.col_beneish || 'Beneish M'} ${getSortIcon('beneish_m_score')}</th>
                                        <th onclick="sortMatrixBy('dupont_roe_pct')" style="cursor:pointer; text-align:right;">${t.col_dupont || 'DuPont ROE'} ${getSortIcon('dupont_roe_pct')}</th>
                                        <th onclick="sortMatrixBy('implied_growth_pct')" style="cursor:pointer; text-align:right;">${t.col_growth || 'Ters DCF %g'} ${getSortIcon('implied_growth_pct')}</th>
                                        <th onclick="sortMatrixBy('ps_ratio')" style="cursor:pointer; text-align:right;">${t.col_ps || 'P/S'} ${getSortIcon('ps_ratio')}</th>
                                        <th onclick="sortMatrixBy('composite_score')" style="cursor:pointer; text-align:center;">${t.col_score || '360° Skoru & Değerlendirme'} ${getSortIcon('composite_score')}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${filtered.length === 0 ? `<tr><td colspan="9" style="text-align:center; padding:2rem; color:var(--text-muted);">Hisse bulunamadı / No stocks found</td></tr>` : 
                                    filtered.map(row => {
                                        const zBadgeClass = row.altman_z_score > 2.99 ? 'tag-green' : (row.altman_z_score >= 1.81 ? 'tag-cyan' : 'tag-red');
                                        const scoreColor = row.composite_score >= 8.5 ? '#10b981' : (row.composite_score >= 6.5 ? '#06b6d4' : (row.composite_score >= 4.5 ? '#f59e0b' : '#f43f5e'));

                                        return `
                                            <tr onclick="selectMatrixStock('${escapeHtml(row.ticker)}')" style="cursor:pointer; transition:background 0.15s;">
                                                <td>
                                                    <div style="font-weight:700; color:var(--text-main); font-size:0.92rem;">${escapeHtml(row.ticker)}</div>
                                                    <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(row.name)}</div>
                                                </td>
                                                <td style="text-align:right; font-weight:600; color:var(--text-main);">${currencySym}${row.price.toLocaleString()}</td>
                                                <td style="text-align:center;">
                                                    <span style="font-weight:700; color:#8b5cf6;">${row.piotroski_score} / 9</span>
                                                </td>
                                                <td style="text-align:center;">
                                                    <span class="${zBadgeClass}" style="font-size:0.75rem; padding:0.2rem 0.5rem;">${row.altman_z_score}</span>
                                                </td>
                                                <td style="text-align:center;">
                                                    <span class="${row.beneish_safe ? 'tag-green' : 'tag-red'}" style="font-size:0.75rem; padding:0.2rem 0.5rem;">${row.beneish_m_score}</span>
                                                </td>
                                                <td style="text-align:right; font-weight:600;">%${row.dupont_roe_pct}</td>
                                                <td style="text-align:right; font-weight:600; color:var(--accent-cyan);">%${row.implied_growth_pct}</td>
                                                <td style="text-align:right; font-weight:600; color:#f59e0b;">${row.ps_ratio}x</td>
                                                <td style="text-align:center;">
                                                    <div style="font-size:1.05rem; font-weight:800; color:${scoreColor};">${row.composite_score} / 10</div>
                                                    <div style="font-size:0.75rem; margin-top:0.1rem;">${row.verdict_label}</div>
                                                </td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;

                box.innerHTML = html;
            }

            function openAdminModal() {
                applyUiLanguage();
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

            function switchAdminTab(tabName) {
                document.querySelectorAll('.admin-nav-tab').forEach(t => t.classList.remove('active'));
                const stocksTab = document.getElementById('adminDomainTabStocks');
                const settingsTab = document.getElementById('adminDomainTabSettings');
                const logsTab = document.getElementById('adminDomainTabLogs');
                if (stocksTab) stocksTab.style.display = 'none';
                if (settingsTab) settingsTab.style.display = 'none';
                if (logsTab) logsTab.style.display = 'none';

                if (tabName === 'stocks') {
                    const navTab = document.getElementById('adminNavTabStocks');
                    if (navTab) navTab.classList.add('active');
                    if (stocksTab) stocksTab.style.display = 'flex';
                } else if (tabName === 'settings') {
                    const navTab = document.getElementById('adminNavTabSettings');
                    if (navTab) navTab.classList.add('active');
                    if (settingsTab) settingsTab.style.display = 'flex';
                } else if (tabName === 'logs') {
                    const navTab = document.getElementById('adminNavTabLogs');
                    if (navTab) navTab.classList.add('active');
                    if (logsTab) logsTab.style.display = 'flex';
                    switchLogTab(activeLogType || 'analysis');
                }
            }

            // Password Eye Toggle Helper
            function togglePasswordVisibility(inputId, btn) {
                const input = document.getElementById(inputId);
                if (!input) return;
                if (input.type === 'password') {
                    input.type = 'text';
                    if (btn) btn.innerHTML = '🙈';
                } else {
                    input.type = 'password';
                    if (btn) btn.innerHTML = '👁️';
                }
            }

            // Command Palette (⌘K) Controller
            let cmdSelectedIndex = 0;
            let cmdFilteredTickers = [];

            function openCommandPalette() {
                const modal = document.getElementById('commandPaletteModal');
                if (!modal) return;
                modal.classList.add('active');
                const input = document.getElementById('cmdSearchInput');
                if (input) {
                    input.value = '';
                    input.focus();
                }
                renderCommandSearchResults();
            }

            function closeCommandPalette() {
                const modal = document.getElementById('commandPaletteModal');
                if (modal) modal.classList.remove('active');
            }

            function onCommandSearchInput() {
                cmdSelectedIndex = 0;
                renderCommandSearchResults();
            }

            function onCommandSearchKeydown(e) {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (cmdFilteredTickers.length > 0) {
                        cmdSelectedIndex = (cmdSelectedIndex + 1) % cmdFilteredTickers.length;
                        highlightCommandSearchResult();
                    }
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (cmdFilteredTickers.length > 0) {
                        cmdSelectedIndex = (cmdSelectedIndex - 1 + cmdFilteredTickers.length) % cmdFilteredTickers.length;
                        highlightCommandSearchResult();
                    }
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    if (cmdFilteredTickers.length > 0 && cmdFilteredTickers[cmdSelectedIndex]) {
                        selectCommandTicker(cmdFilteredTickers[cmdSelectedIndex]);
                    }
                } else if (e.key === 'Escape') {
                    closeCommandPalette();
                }
            }

            function renderCommandSearchResults() {
                const input = document.getElementById('cmdSearchInput');
                const resultsContainer = document.getElementById('cmdSearchResults');
                if (!resultsContainer) return;
                const query = (input ? input.value : '').trim().toUpperCase();
                
                const sel = document.getElementById('tickerSelect');
                const allTickers = Array.from(sel ? sel.options : []).map(opt => opt.value);
                
                if (query === '') {
                    let recent = [];
                    try {
                        recent = JSON.parse(localStorage.getItem('stock_analyzer_recent_tickers') || '[]');
                    } catch(e) {}
                    cmdFilteredTickers = recent.filter(t => allTickers.includes(t));
                    if (cmdFilteredTickers.length === 0) cmdFilteredTickers = allTickers.slice(0, 10);
                } else {
                    cmdFilteredTickers = allTickers.filter(t => t.toUpperCase().includes(query));
                }

                if (cmdFilteredTickers.length === 0) {
                    resultsContainer.innerHTML = `<div style="padding:1rem; text-align:center; color:var(--text-muted); font-size:0.85rem;">Hisse bulunamadı / No ticker found</div>`;
                    return;
                }

                resultsContainer.innerHTML = cmdFilteredTickers.map((t, idx) => `
                    <div class="cmd-result-item ${idx === cmdSelectedIndex ? 'selected' : ''}" onclick="selectCommandTicker('${escapeHtml(t)}')">
                        <div style="display:flex; align-items:center; gap:0.5rem;">
                            <span style="font-weight:700; font-family:var(--font-mono);">${escapeHtml(t)}</span>
                        </div>
                        <span style="font-size:0.75rem; color:var(--text-muted);">↵ Seç / Select</span>
                    </div>
                `).join('');
            }

            function highlightCommandSearchResult() {
                const items = document.querySelectorAll('.cmd-result-item');
                items.forEach((item, idx) => {
                    if (idx === cmdSelectedIndex) {
                        item.classList.add('selected');
                        item.scrollIntoView({ block: 'nearest' });
                    } else {
                        item.classList.remove('selected');
                    }
                });
            }

            function selectCommandTicker(ticker) {
                closeCommandPalette();
                const sel = document.getElementById('tickerSelect');
                if (sel) {
                    sel.value = ticker;
                    loadDates();
                }
                try {
                    let recent = JSON.parse(localStorage.getItem('stock_analyzer_recent_tickers') || '[]');
                    recent = recent.filter(t => t !== ticker);
                    recent.unshift(ticker);
                    if (recent.length > 10) recent = recent.slice(0, 10);
                    localStorage.setItem('stock_analyzer_recent_tickers', JSON.stringify(recent));
                } catch(e) {}
            }

            window.addEventListener('keydown', (e) => {
                if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                    e.preventDefault();
                    openCommandPalette();
                } else if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                    openCommandPalette();
                } else if (e.key === 'Escape') {
                    closeCommandPalette();
                    closeAdminModal();
                }
            });

            // HUD Tooltip Hover System
            let hudTooltipTimer = null;
            const HUD_TOOLTIPS = {
                piotroski: "<strong>Piotroski F-Score (0-9)</strong><br>Bilanço ve kârlılık kalitesini 9 kriterde ölçer. 7-9 Yüksek Kalite, 4-6 Orta Kalite, 0-3 Zayıf.",
                altman: "<strong>Altman Z-Score</strong><br>İflas riski tahmin modeli. Z > 2.99 Güvenli Bölge, 1.81 - 2.99 Gri Bölge, Z < 1.81 İflas / Risk Bölgesi.",
                beneish: "<strong>Beneish M-Score</strong><br>Bilanço manipülasyonu / adli muhasebe testi. M < -2.81 Güvenli / Manipülasyonsuz, M > -1.78 Hile Riski.",
                dupont: "<strong>DuPont ROE %</strong><br>Özsermaye kârlılığını Vergi Yükü × Faiz Yükü × EBIT Marjı × Varlık Hızı × Kaldıraç faktörlerine böler.",
                dcf: "<strong>DCF Hedef Değer</strong><br>İskontolu nakit akışlarına göre hesaplanan adil hisse fiyatı ve güvenlik marjı."
            };

            function showHudTooltip(e, key) {
                if (hudTooltipTimer) clearTimeout(hudTooltipTimer);
                hudTooltipTimer = setTimeout(() => {
                    const tt = document.getElementById('hudTooltip');
                    if (!tt || !HUD_TOOLTIPS[key]) return;
                    tt.innerHTML = HUD_TOOLTIPS[key];
                    const rect = e.currentTarget.getBoundingClientRect();
                    tt.style.top = (rect.bottom + 6) + 'px';
                    tt.style.left = rect.left + 'px';
                    tt.classList.add('active');
                }, 150);
            }

            function hideHudTooltip() {
                if (hudTooltipTimer) clearTimeout(hudTooltipTimer);
                const tt = document.getElementById('hudTooltip');
                if (tt) tt.classList.remove('active');
            }

            function updateHudData(data) {
                const container = document.getElementById('hudCardsContainer');
                if (!container || !data) return;
                container.style.display = 'flex';

                const pVal = document.getElementById('hudValPiotroski');
                const pSteps = document.getElementById('piotroskiStepsBar');
                if (pVal && pSteps && data.piotroski_score !== undefined) {
                    const score = data.piotroski_score;
                    const pClass = score >= 7 ? 'active-green' : (score >= 4 ? 'active-amber' : 'active-red');
                    pVal.innerHTML = `<span class="${score >= 7 ? 'tag-green' : (score >= 4 ? 'tag-amber' : 'tag-red')}">${score}/9</span>`;
                    let stepsHtml = '';
                    for (let i = 1; i <= 9; i++) {
                        stepsHtml += `<div class="piotroski-step ${i <= score ? pClass : ''}"></div>`;
                    }
                    pSteps.innerHTML = stepsHtml;
                }

                const aVal = document.getElementById('hudValAltman');
                if (aVal && data.altman_z_score !== undefined) {
                    const z = data.altman_z_score;
                    const cls = z > 2.99 ? 'tag-green' : (z >= 1.81 ? 'tag-amber' : 'tag-red');
                    const label = z > 2.99 ? 'Güvenli' : (z >= 1.81 ? 'Gri' : 'Risk');
                    aVal.innerHTML = `<span class="${cls}">${z} (${label})</span>`;
                }

                const bVal = document.getElementById('hudValBeneish');
                if (bVal && data.beneish_m_score !== undefined) {
                    const m = data.beneish_m_score;
                    const isSafe = data.beneish_safe !== undefined ? data.beneish_safe : m < -2.81;
                    bVal.innerHTML = `<span class="${isSafe ? 'tag-green' : 'tag-red'}">${m}</span>`;
                }

                const dVal = document.getElementById('hudValDupont');
                if (dVal && data.dupont_roe_pct !== undefined) {
                    dVal.innerHTML = `<span style="color:var(--accent-cyan);">%${data.dupont_roe_pct}</span>`;
                }

                const dcfVal = document.getElementById('hudValDcf');
                if (dcfVal && data.price !== undefined) {
                    const fair = data.fair_base || (data.price * 1.10);
                    const margin = (((fair / data.price) - 1) * 100).toFixed(1);
                    const cls = margin >= 10 ? 'tag-green' : (margin >= 0 ? 'tag-amber' : 'tag-red');
                    dcfVal.innerHTML = `<span class="${cls}">${fair.toFixed(1)} (${margin > 0 ? '+' : ''}${margin}%)</span>`;
                }
            }

            function showLockScreen() {
                document.getElementById('authLockScreen').style.display = 'flex';
                document.getElementById('protectedAdminContent').style.display = 'none';
            }

            function showProtectedContent() {
                document.getElementById('authLockScreen').style.display = 'none';
                document.getElementById('protectedAdminContent').style.display = 'flex';
                switchAdminTab('stocks');
                applyUiLanguage();
                fetchAppSettings();
                fetchCronConfig();
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
                    const adminPassEl = document.getElementById('settingAdminPassword');
                    if (adminPassEl) {
                        adminPassEl.value = '';
                        adminPassEl.placeholder = s.ADMIN_PASSWORD_IS_SET ? "•••••••• (Kayıtlı / Set)" : "Yönetici şifresi";
                    }
                    document.getElementById('settingLlmModel').value = s.LLM_MODEL || '';
                    document.getElementById('settingLlmBaseUrl').value = s.LLM_BASE_URL || s.BASE_URL || s.NINEROUTER_URL || '';
                    const apiKeyEl = document.getElementById('settingLlmApiKey');
                    if (apiKeyEl) {
                        apiKeyEl.value = '';
                        apiKeyEl.placeholder = s.LLM_API_KEY_IS_SET ? `${s.LLM_API_KEY} (Kayıtlı / Set)` : "sk-...";
                    }
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

            async function fetchCronConfig() {
                const res = await fetch('/api/cron/config', { headers: getAdminHeaders() });
                if (res.ok) {
                    const c = await res.json();
                    const enableEl = document.getElementById('settingCronEnabled');
                    if (enableEl) enableEl.value = c.is_enabled ? '1' : '0';
                    
                    const timeEl = document.getElementById('settingCronTime');
                    if (timeEl) timeEl.value = c.schedule_time || '18:30';
                    
                    const tzEl = document.getElementById('settingCronTimezone');
                    if (tzEl) tzEl.value = c.timezone || 'Europe/Istanbul';
                    
                    const daysEl = document.getElementById('settingCronDays');
                    if (daysEl) daysEl.value = c.run_days || 'mon-fri';
                    
                    const misfireEl = document.getElementById('settingCronMisfire');
                    if (misfireEl) misfireEl.value = c.misfire_grace_minutes || 120;
                    
                    const nextRunEl = document.getElementById('cronNextRunText');
                    if (nextRunEl) nextRunEl.innerText = c.next_run_at || 'Unknown';
                    
                    const badgeEl = document.getElementById('cronStatusBadge');
                    if (badgeEl) {
                        const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                        if (c.is_running) {
                            badgeEl.style.background = '#ffc107';
                            badgeEl.style.color = '#000';
                            badgeEl.innerText = t.status_cron_running || '🟡 Analiz Çalışıyor...';
                        } else if (!c.is_enabled) {
                            badgeEl.style.background = '#dc3545';
                            badgeEl.style.color = '#fff';
                            badgeEl.innerText = t.status_cron_paused || '🔴 Duraklatıldı';
                        } else {
                            badgeEl.style.background = '#28a745';
                            badgeEl.style.color = '#fff';
                            badgeEl.innerText = t.status_cron_active || '🟢 Aktif';
                        }
                    }
                }
            }

            async function saveCronConfig() {
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                const payload = {
                    is_enabled: document.getElementById('settingCronEnabled').value === '1',
                    schedule_time: document.getElementById('settingCronTime').value,
                    timezone: document.getElementById('settingCronTimezone').value,
                    run_days: document.getElementById('settingCronDays').value,
                    misfire_grace_minutes: parseInt(document.getElementById('settingCronMisfire').value || '120', 10),
                    ticker_delay_seconds: parseInt(document.getElementById('settingCronDelaySeconds').value || '15', 10)
                };
                const res = await fetch('/api/cron/config', {
                    method: 'POST',
                    headers: getAdminHeaders(),
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    alert(t.msg_settings_saved || "Zamanlayıcı ayarları başarıyla kaydedildi.");
                    fetchCronConfig();
                } else {
                    const err = await res.json();
                    alert(`Hata: ${err.detail || 'Zamanlayıcı ayarları kaydedilemedi.'}`);
                }
            }

            async function triggerRunCronNow(e) {
                const btn = e ? e.target : event.target;
                btn.disabled = true;
                const originalText = btn.innerText;
                btn.innerText = "⏳ Başlatılıyor...";
                try {
                    const res = await fetch('/api/cron/run-now', {
                        method: 'POST',
                        headers: getAdminHeaders()
                    });
                    if (res.ok) {
                        const data = await res.json();
                        alert(data.message || "⚡ Otonom Cron analizi arka planda başlatıldı.");
                        fetchCronConfig();
                    } else {
                        const err = await res.json();
                        alert(`Hata: ${err.detail || 'Cron çalışması başlatılamadı.'}`);
                    }
                } catch(err) {
                    alert(`Hata: ${err.message}`);
                } finally {
                    btn.disabled = false;
                    btn.innerText = originalText;
                }
            }

            function switchLogTab(type) {
                activeLogType = type;
                const tabCron = document.getElementById('tabCronLog');
                const tabAnalysis = document.getElementById('tabAnalysisLog');
                const tabError = document.getElementById('tabErrorLog');
                const tabAccess = document.getElementById('tabAccessLog');
                const tabLive = document.getElementById('tabLiveLog');

                if (tabCron) tabCron.classList.toggle('active', type === 'cron');
                if (tabAnalysis) tabAnalysis.classList.toggle('active', type === 'analysis');
                if (tabError) tabError.classList.toggle('active', type === 'errors');
                if (tabAccess) tabAccess.classList.toggle('active', type === 'access');
                if (tabLive) tabLive.classList.toggle('active', type === 'live');

                if (type === 'live') {
                    fetchLiveLogs();
                } else {
                    fetchFileLogs();
                }
            }

            async function fetchLiveLogs() {
                const box = document.getElementById('fileConsoleBox');
                if (!box) return;
                try {
                    const res = await fetch('/api/reprocess/active', { headers: getAdminHeaders() });
                    if (res.ok) {
                        const data = await res.json();
                        if (data.active && data.ticker) {
                            startSseStream(data.ticker);
                        } else if (data.log && data.log.length > 0) {
                            const header = `⚡ [${data.ticker || 'LIVE'}] Son Canlı İşlem Çıktısı / Latest Execution Log (${data.status}):\n--------------------------------------------------\n`;
                            box.innerText = header + data.log.join('\n');
                            box.scrollTop = box.scrollHeight;
                        } else {
                            box.innerText = "⚡ Canlı İşlem Çıktısı (Live)\n--------------------------------------------------\nŞu anda aktif çalışan bir analiz işlemi bulunmuyor.\nNo active stock analysis process currently running.";
                        }
                    }
                } catch(e) {
                    if (box) box.innerText = `🔴 Live log yükleme hatası: ${e.message}`;
                }
            }

            async function openValuationHistoryModal(ticker) {
                const selectEl = document.getElementById('tickerSelect');
                const targetTicker = ticker || (typeof currentTicker !== 'undefined' ? currentTicker : null) || (selectEl ? selectEl.value : null);
                if (!targetTicker || targetTicker === '_MATRIX_') {
                    alert('Lütfen önce analiz edilecek bir hisse seçiniz.');
                    return;
                }

                const modal = document.getElementById('valuationHistoryModal');
                if (modal) modal.classList.add('active');

                const titleEl = document.getElementById('gfxModalTitle');
                if (titleEl) titleEl.innerText = `📊 Değerleme Formül Tarihçesi & GFX Trendleri: ${targetTicker}`;

                const bodyEl = document.getElementById('gfxModalBody');
                if (bodyEl) bodyEl.innerHTML = '<div style="color:var(--text-muted); text-align:center; padding:2rem;">⏳ Tarihçe verileri yükleniyor...</div>';

                try {
                    const res = await fetch(`/api/valuation/history/${targetTicker}`);
                    if (!res.ok) throw new Error(`HTTP ${res.status}`);
                    const data = await res.json();
                    renderValuationHistoryGfx(data, bodyEl);
                } catch(err) {
                    if (bodyEl) bodyEl.innerHTML = `<div style="color:var(--accent-rose); text-align:center; padding:2rem;">🔴 Tarihçe verisi yüklenemedi: ${err.message}</div>`;
                }
            }

            function closeValuationHistoryModal() {
                const modal = document.getElementById('valuationHistoryModal');
                if (modal) modal.classList.remove('active');
            }

            function renderValuationHistoryGfx(data, container) {
                const history = data.history || [];
                if (history.length === 0) {
                    container.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--text-muted);">
                        ℹ️ '${data.ticker}' için henüz kayıtlı tarihsel analiz verisi bulunmuyor.<br>
                        Analiz çalıştırıldıkça tarihsel formül trendleri burada grafikle gösterilecektir.
                    </div>`;
                    return;
                }

                const dates = history.map(h => h.report_date);
                const altmanZ = history.map(h => h.altman_z != null ? Number(h.altman_z.toFixed(2)) : 0);
                const piotroski = history.map(h => h.piotroski_score ?? 0);
                const dcf = history.map(h => h.dcf_fair_value != null ? Number(h.dcf_fair_value.toFixed(2)) : 0);
                const graham = history.map(h => h.graham_number != null ? Number(h.graham_number.toFixed(2)) : 0);
                const wacc = history.map(h => h.wacc_pct != null ? Number(h.wacc_pct.toFixed(2)) : 0);

                const renderLineChart = (title, pts, datesList, color = '#06b6d4', suffix = '') => {
                    if (pts.length === 0) return '';
                    const min = Math.min(...pts);
                    const max = Math.max(...pts);
                    const range = (max - min) || 1;
                    const w = 680, h = 140;
                    
                    const pathPoints = pts.map((v, i) => {
                        const x = (i / Math.max(pts.length - 1, 1)) * (w - 40) + 20;
                        const y = h - 25 - ((v - min) / range) * (h - 45);
                        return { x, y, val: v, date: datesList[i] };
                    });

                    const dAttr = pathPoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
                    
                    const circles = pathPoints.map(p => `
                        <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4" fill="${color}" stroke="#0f172a" stroke-width="2">
                            <title>${p.date}: ${p.val}${suffix}</title>
                        </circle>
                        <text x="${p.x.toFixed(1)}" y="${(p.y - 8).toFixed(1)}" fill="${color}" font-size="10" text-anchor="middle" font-weight="bold">${p.val}${suffix}</text>
                    `).join('');

                    const xLabels = pathPoints.map(p => `
                        <text x="${p.x.toFixed(1)}" y="${h - 5}" fill="var(--text-muted)" font-size="9" text-anchor="middle">${p.date}</text>
                    `).join('');

                    return `
                        <div class="admin-card" style="padding:1rem;">
                            <div style="font-weight:700; color:var(--text-main); font-size:0.9rem; margin-bottom:0.75rem; display:flex; justify-content:space-between;">
                                <span>${title}</span>
                                <span style="color:${color}; font-family:var(--font-mono); font-weight:700;">${pts[pts.length - 1]}${suffix}</span>
                            </div>
                            <div style="overflow-x:auto;">
                                <svg viewBox="0 0 ${w} ${h}" style="width:100%; height:auto; min-width:320px; max-height:160px;">
                                    <path d="${dAttr}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round"/>
                                    ${circles}
                                    ${xLabels}
                                </svg>
                            </div>
                        </div>
                    `;
                };

                container.innerHTML = `
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        ${renderLineChart('🛡️ Altman Z-Score Trend (İflas Riski)', altmanZ, dates, '#10b981')}
                        ${renderLineChart('🔥 Piotroski F-Score Trend (0-9)', piotroski, dates, '#3b82f6')}
                        ${renderLineChart('🎯 DCF Intrinsic Fair Value', dcf, dates, '#8b5cf6', '₺')}
                        ${renderLineChart('🏛️ Graham Değeri (Graham Number)', graham, dates, '#ec4899', '₺')}
                        ${renderLineChart('⚡ WACC % Trend', wacc, dates, '#f59e0b', '%')}
                    </div>
                    <div class="admin-card" style="padding:1rem; margin-top:0.5rem;">
                        <div style="font-weight:700; color:var(--accent-cyan); font-size:0.9rem; margin-bottom:0.75rem;">📋 Tüm Metrik & Değer Tarihçe Tablosu (All Historical Metrics & Values)</div>
                        <div style="overflow-x:auto;">
                            <table class="admin-table">
                                <thead>
                                    <tr>
                                        <th>Tarih</th>
                                        <th>Hisse Fiyatı</th>
                                        <th>Piyasa Değeri</th>
                                        <th>Piotroski F</th>
                                        <th>Altman Z</th>
                                        <th>Beneish M</th>
                                        <th>WACC %</th>
                                        <th>DCF Hedef</th>
                                        <th>Graham No</th>
                                        <th>Lynch Value</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${history.map(h => {
                                        let mcapStr = '-';
                                        if (h.market_cap != null) {
                                            mcapStr = Math.abs(h.market_cap) >= 1e9 ? ('₺' + (h.market_cap/1e9).toFixed(2) + 'B') : ('₺' + (h.market_cap/1e6).toFixed(2) + 'M');
                                        }
                                        return `
                                        <tr>
                                            <td><strong>${h.report_date}</strong></td>
                                            <td>${h.stock_price != null ? '₺' + h.stock_price.toFixed(2) : '-'}</td>
                                            <td>${mcapStr}</td>
                                            <td>${h.piotroski_score ?? '-'}</td>
                                            <td>${h.altman_z != null ? h.altman_z.toFixed(2) : '-'}</td>
                                            <td>${h.beneish_m != null ? h.beneish_m.toFixed(2) : '-'}</td>
                                            <td>${h.wacc_pct != null ? h.wacc_pct.toFixed(2) + '%' : '-'}</td>
                                            <td>${h.dcf_fair_value != null ? '₺' + h.dcf_fair_value.toFixed(2) : '-'}</td>
                                            <td>${h.graham_number != null ? '₺' + h.graham_number.toFixed(2) : '-'}</td>
                                            <td>${h.lynch_fair_value != null ? '₺' + h.lynch_fair_value.toFixed(2) : '-'}</td>
                                        </tr>
                                    `}).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            }

            async function fetchFileLogs() {
                if (activeLogType === 'live') return;
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                const validTypes = ['cron', 'analysis', 'errors', 'access'];
                const targetType = validTypes.includes(activeLogType) ? activeLogType : 'analysis';
                const endpoint = `/api/logs/${targetType}`;
                try {
                    const res = await fetch(endpoint, { headers: getAdminHeaders() });
                    const box = document.getElementById('fileConsoleBox');
                    if (!box) return;
                    if (res.ok) {
                        const data = await res.json();
                        const logTxt = (data.log !== undefined && data.log !== null) ? data.log : "";
                        box.innerText = logTxt.trim().length > 0 ? logTxt : (t.log_cleared || "Loglar temizlendi.");
                        box.scrollTop = box.scrollHeight;
                    } else {
                        const errData = await res.json().catch(() => ({}));
                        if (res.status === 401) {
                            box.innerText = "🔒 Lütfen Yönetici Paneli girişinden şifrenizi giriniz / Please login with admin password.";
                        } else {
                            box.innerText = `🔴 Log okuma hatası (${res.status}): ${errData.detail || res.statusText || 'Bilinmeyen Hata'}`;
                        }
                    }
                } catch(e) {
                    console.error('Error fetching file logs:', e);
                    const box = document.getElementById('fileConsoleBox');
                    if (box) box.innerText = `🔴 Log yükleme hatası: ${e.message}`;
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

            let executionStates = {};
            let isBatchExecuting = false;

            function jumpToLog(ticker) {
                switchAdminTab('logs');
                switchLogTab('live');
                if (ticker && ticker !== '_BATCH_') {
                    startSseStream(ticker);
                }
            }

            async function fetchWatchlist() {
                try {
                    const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                    const res = await fetch('/api/watchlist');
                    if (!res.ok) return;
                    const data = await res.json();
                    if (!Array.isArray(data)) return;
                    const tbody = document.getElementById('watchlistTableBody');
                    if (!tbody) return;
                    tbody.innerHTML = data.map(item => {
                        const eTicker = escapeHtml(item.ticker);
                        const eCompany = escapeHtml(item.company_name || item.ticker);
                        const eLang = escapeHtml(item.lang);
                        const lastRep = item.last_report;
                        let repBadge = `<span class="tag-badge tag-amber">${t.no_report_badge}</span>`;
                        if (lastRep) {
                            const pScore = lastRep.piotroski_score !== null ? `${lastRep.piotroski_score}/9` : '-';
                            const zScore = lastRep.altman_z !== null ? lastRep.altman_z.toFixed(1) : '-';
                            repBadge = `<span class="tag-badge tag-green" style="cursor:pointer;" onclick="selectAndLoadReport('${eTicker}')" title="${t.view_report_title}">📅 ${escapeHtml(lastRep.report_date)} (P:${pScore} | Z:${zScore}) 🔍</span>`;
                        }

                        const execStatus = executionStates[item.ticker];
                        let statusBadge = repBadge;
                        let analyzeBtn = `<button class="btn btn-primary" onclick="reprocessSingle('${eTicker}')" title="${t.single_analyze_title}">${t.btn_analyze}</button>`;

                        if (execStatus === 'RUNNING') {
                            statusBadge = `<span class="tag-badge tag-amber pulse-badge">${t.status_analyzing || '🟡 Analyzing...'}</span>`;
                            analyzeBtn = `<button class="btn btn-primary" disabled><span class="spinner-icon">⏳</span> ${t.status_analyzing || 'Analyzing...'}</button>`;
                        } else if (execStatus === 'QUEUED') {
                            statusBadge = `<span class="tag-badge tag-amber">${t.status_queued || '🟡 Queued...'}</span>`;
                            analyzeBtn = `<button class="btn btn-primary" disabled><span class="spinner-icon">⏳</span> ${t.status_queued || 'Queued...'}</button>`;
                        } else if (execStatus === 'SUCCESS') {
                            statusBadge = `${repBadge} <span class="tag-badge tag-green">${t.status_success || '🟢 Updated'}</span>`;
                        } else if (execStatus === 'FAILED') {
                            statusBadge = `${repBadge} <span class="tag-badge tag-rose">${t.status_failed || '🔴 Failed'} <a style="color:var(--accent-cyan); text-decoration:underline; font-size:0.75rem; cursor:pointer;" onclick="jumpToLog('${eTicker}')">${t.btn_view_log || '📜 View Log'}</a></span>`;
                        }

                        const activeChecked = item.is_active ? 'checked' : '';
                        return `
                            <tr>
                                <td><strong>${eTicker}</strong></td>
                                <td>${eCompany}</td>
                                <td><span class="tag-badge tag-amber">${eLang}</span></td>
                                <td>
                                    <input type="checkbox" ${activeChecked} onchange="toggleStockActive('${eTicker}', this.checked)">
                                </td>
                                <td>${statusBadge}</td>
                                <td style="text-align:right; display:flex; gap:0.4rem; justify-content:flex-end;">
                                    ${analyzeBtn}
                                    <button class="btn" onclick="editStockPrompt('${eTicker}', '${eCompany}', '${eLang}')">${t.btn_edit}</button>
                                    <button class="btn btn-danger" onclick="deleteStock('${eTicker}')">${t.btn_delete}</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                } catch(e) {
                    console.error('Error fetching watchlist:', e);
                }
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
                if (box) box.innerText = `▶ Connecting live event stream for: ${targetKey}...\n`;

                currentEventSource = new EventSource(`/api/reprocess/stream/${targetKey}`);
                currentEventSource.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.line && box) {
                            box.innerText += `${data.line}\n`;
                            box.scrollTop = box.scrollHeight;
                        }
                        if (data.done) {
                            currentEventSource.close();
                            if (targetKey === '_BATCH_') {
                                isBatchExecuting = false;
                                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                                const batchBtn = document.getElementById('batchRunBtn');
                                if (batchBtn) {
                                    batchBtn.disabled = false;
                                    batchBtn.innerHTML = `🚀 ${t.btn_batch_run || 'Run All Active Stocks'}`;
                                }
                                fetchWatchlist();
                                fetchFileLogs();
                                loadTickers();
                            } else {
                                executionStates[targetKey] = 'SUCCESS';
                                fetchWatchlist();
                                fetchFileLogs();
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
                executionStates[ticker] = 'RUNNING';
                fetchWatchlist();
                logConsole(`▶ Single stock analysis triggered for: ${ticker}`);
                const res = await fetch(`/api/reprocess/${ticker}`, {
                    method: 'POST',
                    headers: getAdminHeaders()
                });
                const data = await res.json();
                if (!res.ok) {
                    executionStates[ticker] = 'FAILED';
                    fetchWatchlist();
                    alert(`Error: ${data.detail || data.message}`);
                    return;
                }
                logConsole(`Status: ${data.message}`);
                startSseStream(ticker);
            }

            async function triggerBatchRun() {
                const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                isBatchExecuting = true;
                const batchBtn = document.getElementById('batchRunBtn');
                if (batchBtn) {
                    batchBtn.disabled = true;
                    batchBtn.innerHTML = `<span class="spinner-icon">⏳</span> ${t.batch_running || 'Batch Execution Active...'}`;
                }
                logConsole(t.msg_batch_started);
                const res = await fetch(`/api/reprocess/batch`, {
                    method: 'POST',
                    headers: getAdminHeaders()
                });
                const data = await res.json();
                if (!res.ok) {
                    isBatchExecuting = false;
                    if (batchBtn) {
                        batchBtn.disabled = false;
                        batchBtn.innerHTML = `🚀 ${t.btn_batch_run || 'Run All Active Stocks'}`;
                    }
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
                        const box = document.getElementById('fileConsoleBox');
                        if (box) {
                            box.innerText = data.log.join(String.fromCharCode(10));
                            box.scrollTop = box.scrollHeight;
                        }
                    }
                    if (data.status === 'SUCCESS' || data.status === 'FAILED') {
                        clearInterval(pollingTimer);
                        if (targetKey === '_BATCH_') {
                            isBatchExecuting = false;
                            const t = UI_I18N[currentUiLang] || UI_I18N.TR;
                            const batchBtn = document.getElementById('batchRunBtn');
                            if (batchBtn) {
                                batchBtn.disabled = false;
                                batchBtn.innerHTML = `🚀 ${t.btn_batch_run || 'Run All Active Stocks'}`;
                            }
                            fetchWatchlist();
                            fetchFileLogs();
                            loadTickers();
                        } else {
                            executionStates[targetKey] = data.status;
                            fetchWatchlist();
                            fetchFileLogs();
                            loadTickers(targetKey);
                        }
                    }
                }, 2000);
            }

            function logConsole(msg) {
                const box = document.getElementById('fileConsoleBox');
                if (box) {
                    box.innerText += String.fromCharCode(10) + msg;
                    box.scrollTop = box.scrollHeight;
                }
            }

            function initApp() {
                const savedTheme = localStorage.getItem('app_theme') || 'dark';
                document.body.setAttribute('data-theme', savedTheme);
                const btn = document.getElementById('headerThemeBtn');
                if (btn) btn.innerHTML = savedTheme === 'light' ? '☀️' : '🌙';
                loadTickers();
                setUiLanguage(currentUiLang);
            }

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initApp);
            } else {
                initApp();
            }
        </script>
    </body>
    </html>
    """
    return html_content.replace("__APP_VERSION__", get_app_version())
