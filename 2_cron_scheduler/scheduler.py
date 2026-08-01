import os
import sys
import time
import json
import sqlite3
import datetime
import subprocess
from apscheduler.schedulers.blocking import BlockingScheduler

from dotenv import load_dotenv

try:
    os.umask(0000)
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "1_core_builder"))
from logger import log_error

LOGS_DIR = os.path.join(BASE_DIR, "storage", "logs")
CRON_LOG_FILE = os.path.join(LOGS_DIR, "cron.log")
APP_ENV_PATH = os.path.join(BASE_DIR, ".env")
DB_PATH = os.path.join(BASE_DIR, "storage", "app.db")
WATCHLIST_PATH = os.path.join(BASE_DIR, "2_cron_scheduler", "watchlist.json")

def log_cron(msg: str):
    os.makedirs(LOGS_DIR, exist_ok=True)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {msg}"
    print(formatted, flush=True)
    try:
        with open(CRON_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception as e:
        print(f"⚠️ Log write error: {e}", flush=True)

def init_cron_config_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    cur = conn.cursor()
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
    conn.commit()
    conn.close()

def get_cron_config():
    init_cron_config_db()
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
        print(f"⚠️ Warning loading cron_config: {e}")
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

def set_cron_running(is_running: bool):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if is_running:
            cur.execute("UPDATE cron_config SET is_running = 1, updated_at = CURRENT_TIMESTAMP WHERE id = 1")
        else:
            cur.execute("UPDATE cron_config SET is_running = 0, last_run_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (now_str,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Warning updating is_running in DB: {e}")

def get_watchlist_items():
    """Retrieve active watchlist items with assigned report languages."""
    items = []
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT ticker, lang FROM watchlist WHERE is_active = 1 ORDER BY ticker ASC")
            rows = cur.fetchall()
            conn.close()
            if rows:
                return [{"ticker": r[0], "lang": r[1] or "TR"} for r in rows]
        except Exception:
            pass

    if os.path.exists(WATCHLIST_PATH):
        try:
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                tickers = json.load(f)
                return [{"ticker": t, "lang": "TR"} for t in tickers]
        except Exception:
            pass

    return items

def run_daily_job():
    load_dotenv(APP_ENV_PATH, override=True)
    load_dotenv(override=True)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    config = get_cron_config()
    is_now_trigger = len(sys.argv) > 1 and sys.argv[1] == "--now"
    
    if not is_now_trigger and not config["is_enabled"]:
        log_cron("⏸️ Cron execution skipped (Disabled in Admin Panel).")
        return

    set_cron_running(True)
    try:
        log_cron(f"⏰ [{config['schedule_time']} {config['timezone']}] Cron Triggered: Running sequential stock analysis...")
        builder_script = os.path.join(BASE_DIR, "1_core_builder", "generate_report.py")

        watchlist_items = get_watchlist_items()
        if not watchlist_items:
            log_cron("🔴 ERROR: No active tickers found in watchlist.")
            return

        ticker_names = [item["ticker"] for item in watchlist_items]
        log_cron(f"📋 Queued active watchlist ({len(watchlist_items)} tickers): {', '.join(ticker_names)}")
        python_exec = "py" if os.name == "nt" else sys.executable

        total_start = datetime.datetime.now()

        for index, item in enumerate(watchlist_items, 1):
            ticker = item["ticker"]
            lang = item.get("lang", "TR")
            
            log_cron(f"{ticker} started")

            success = False
            try:
                proc = subprocess.Popen(
                    [python_exec, builder_script, ticker, "--lang", lang],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                stdout_output, _ = proc.communicate()

                if proc.returncode == 0:
                    log_cron(f"✅ {ticker} report generated successfully.")
                else:
                    problem = stdout_output.strip() if stdout_output else f"Exit code {proc.returncode}"
                    log_cron(f"❌ Error ({ticker}): {problem} - Moving to next ticker.")
                    log_error(f"Cron batch failed for {ticker}: {problem}", context=f"cron:{ticker}")
            except Exception as e:
                log_cron(f"❌ Error ({ticker}): {e} - Moving to next ticker.")
                log_error(f"Cron batch exception for {ticker}: {e}", exc=e, context=f"cron:{ticker}")

            log_cron(f"{ticker} ended")

            if index < len(watchlist_items):
                delay_sec = int(config.get("ticker_delay_seconds") or os.getenv("CRON_DELAY_SECONDS", "15"))
                time.sleep(delay_sec)

        total_end = datetime.datetime.now()
        total_duration = (total_end - total_start).total_seconds()
        log_cron(f"✅ Daily Cron Run Finished for all {len(watchlist_items)} tickers (Total Time: {total_duration:.1f}s).")
    finally:
        set_cron_running(False)

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        log_cron("⚡ Executing immediate cron batch run (--now)...")
        run_daily_job()
    else:
        config = get_cron_config()
        tz_str = config.get("timezone", "Europe/Istanbul")
        sched_time = config.get("schedule_time", "18:30")
        run_days = config.get("run_days", "mon-fri")
        misfire_mins = config.get("misfire_grace_minutes", 120)

        tz = None
        if tz_str:
            try:
                import pytz
                tz = pytz.timezone(tz_str)
            except Exception:
                tz = None

        try:
            parts = sched_time.split(":")
            hour, minute = int(parts[0]), int(parts[1])
        except Exception:
            hour, minute = 18, 30

        scheduler = BlockingScheduler(timezone=tz)
        scheduler.add_job(
            run_daily_job,
            'cron',
            day_of_week=run_days,
            hour=hour,
            minute=minute,
            misfire_grace_time=misfire_mins * 60
        )
        log_cron(f"🚀 APScheduler Worker Started ({sched_time} {tz_str}, Days: {run_days}, Misfire Grace: {misfire_mins}m).")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            pass
