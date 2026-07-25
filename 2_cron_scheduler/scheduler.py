import os
import sys
import time
import json
import sqlite3
import datetime
import subprocess
from apscheduler.schedulers.blocking import BlockingScheduler

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    
    log_cron("⏰ [18:30 TSI] Cron Triggered: Running sequential stock analysis...")
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
        for attempt in range(1, 4):
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
                    success = True
                    break
                else:
                    problem = stdout_output.strip() if stdout_output else f"Exit code {proc.returncode}"
                    log_cron(f"Error ({ticker} attempt {attempt}): {problem}")
                    if attempt < 3:
                        time.sleep(120)
            except Exception as e:
                log_cron(f"Error ({ticker} attempt {attempt}): {e}")
                if attempt < 3:
                    time.sleep(120)

        log_cron(f"{ticker} ended")

        if index < len(watchlist_items):
            delay_sec = int(os.getenv("CRON_DELAY_SECONDS", "15"))
            time.sleep(delay_sec)

    total_end = datetime.datetime.now()
    total_duration = (total_end - total_start).total_seconds()
    log_cron(f"✅ Daily Cron Run Finished for all {len(watchlist_items)} tickers (Total Time: {total_duration:.1f}s).")

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        log_cron("⚡ Executing immediate cron batch run (--now)...")
        run_daily_job()
    else:
        scheduler = BlockingScheduler()
        scheduler.add_job(run_daily_job, 'cron', day_of_week='mon-fri', hour=18, minute=30)
        log_cron("🚀 APScheduler Worker Started. Waiting for 18:30 TSI trigger...")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            pass
