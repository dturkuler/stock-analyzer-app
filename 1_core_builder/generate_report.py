"""
Independent Core CLI Report Builder
3-Step Pipeline:
  1. fetch_yfinance.py  → _workspace/01_quant_metrics_TICKER.json  (quantitative data)
  2. llm_commentary.py  → _workspace/02_llm_commentary_TICKER.json (LLM qualitative analysis)
  3. html_compiler.py   → storage/reports/TICKER/YYYYMMDD.html (interactive dashboard)
                        → storage/reports/TICKER/YYYYMMDD_printable.html (linear PDF/Print ready)

Usage:
  py .agents/skills/stock-analyzer-app/1_core_builder/generate_report.py ODINE.IS
  py .agents/skills/stock-analyzer-app/1_core_builder/generate_report.py KONTR.IS --lang EN
"""

import sys
import os
import json
import datetime
import subprocess

try:
    os.umask(0000)
except Exception:
    pass

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logger import log_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "storage", "logs")
ANALYSIS_LOG_FILE = os.path.join(LOGS_DIR, "analysis.log")

def log_analysis(msg: str):
    os.makedirs(LOGS_DIR, exist_ok=True)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {msg}"
    print(formatted)
    try:
        with open(ANALYSIS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception as e:
        print(f"⚠️ Analysis log write error: {e}")
        log_error(f"Analysis log write error: {e}", exc=e)


def generate_report(ticker, lang="TR", strict_llm=False):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    log_analysis(f"▶ Starting independent report generation for: {ticker} (Lang: {lang})")
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    lang_upper = (lang or "TR").upper()

    # Paths
    storage_dir = os.path.join(BASE_DIR, "storage", "reports", ticker)
    os.makedirs(storage_dir, exist_ok=True)
    report_file_lang = os.path.join(storage_dir, f"{date_str}_{lang_upper}.html")
    printable_report_file_lang = os.path.join(storage_dir, f"{date_str}_{lang_upper}_printable.html")
    report_file = os.path.join(storage_dir, f"{date_str}.html")
    printable_report_file = os.path.join(storage_dir, f"{date_str}_printable.html")

    workspace_dir = os.path.join(BASE_DIR, "storage", "_workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    metrics_path = os.path.join(workspace_dir, f"01_quant_metrics_{ticker}.json")
    commentary_path = os.path.join(workspace_dir, f"02_llm_commentary_{ticker}.json")

    for path in [report_file, report_file_lang, printable_report_file, printable_report_file_lang, metrics_path, commentary_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════
    # STEP 1: Quantitative Data Sourcing (yfinance)
    # ══════════════════════════════════════════════════════════
    log_analysis(f"1. Sourcing data & computing financial metrics for {ticker}...")
    sourcing_script = os.path.join(BASE_DIR, "1_core_builder", "fetch_yfinance.py")
    if not os.path.exists(sourcing_script):
        sourcing_script = os.path.normpath(os.path.join(BASE_DIR, "..", "stock-analyzer", "scripts", "fetch_yfinance.py"))
    python_exec = "py" if os.name == "nt" else sys.executable
    if os.path.exists(sourcing_script):
        proc = subprocess.run([python_exec, sourcing_script, ticker, "--output", metrics_path, "--language", lang_upper], capture_output=True, text=True)
        if proc.returncode != 0:
            log_analysis(f"❌ Error sourcing data for {ticker}:\n{proc.stderr}")
            log_error(f"Error sourcing data for {ticker}: {proc.stderr}", context=ticker)
            return
    else:
        log_analysis(f"⚠️ Warning: Sourcing script not found at {sourcing_script}")
        log_error(f"Sourcing script not found at {sourcing_script}", context=ticker)
        return

    # Load metrics
    if not os.path.exists(metrics_path):
        log_analysis(f"❌ Metrics file not found at: {metrics_path}")
        log_error(f"Metrics file not found at: {metrics_path}", context=ticker)
        return

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Save persistent copy in report directory for Matrix lookup
    report_metrics_path = os.path.join(storage_dir, "quant_metrics.json")
    try:
        import shutil
        shutil.copyfile(metrics_path, report_metrics_path)
    except Exception as e:
        log_analysis(f"⚠️ Warning: Failed to copy metrics to report directory: {e}")

    # Sanity check ticker
    fetched_ticker = metrics.get("ticker", "").upper()
    if fetched_ticker != ticker.upper():
        log_analysis(f"❌ Critical error: fetched metrics ticker '{fetched_ticker}' does not match target ticker '{ticker}'!")
        log_error(f"Fetched metrics ticker '{fetched_ticker}' does not match target ticker '{ticker}'", context=ticker)
        return

    # Log metrics summary
    p_score = metrics.get("piotroski_f_score", {}).get("score", "N/A")
    z_score_raw = metrics.get("altman_z_score", {}).get("z_score")
    z_score = round(z_score_raw, 2) if isinstance(z_score_raw, (int, float)) else "N/A"

    raw_wacc = metrics.get("valuation_parameters", {}).get("wacc")
    wacc_val = f"{round(raw_wacc * 100, 2)}" if isinstance(raw_wacc, (int, float)) else "N/A"
    log_analysis(f"   📊 Sourced metrics for {ticker}: Piotroski F-Score={p_score}/9, Altman Z={z_score}, WACC={wacc_val}%")

    # ══════════════════════════════════════════════════════════
    # STEP 2: LLM Commentary Generation (9Router)
    # ══════════════════════════════════════════════════════════
    from llm_commentary import generate_commentary
    commentary = generate_commentary(metrics, lang=lang, log_fn=log_analysis, strict_llm=strict_llm)

    if commentary is None or not isinstance(commentary, dict) or not commentary.get("_is_llm_generated"):
        log_analysis(f"❌ LLM Commentary Error for {ticker}. Aborting report generation (No Fallbacks Allowed).")
        log_error(f"LLM Commentary Error for {ticker}. Aborting report generation (No Fallbacks Allowed).", context=ticker)
        sys.exit(1)

    # Save commentary
    with open(commentary_path, "w", encoding="utf-8") as f:
        json.dump(commentary, f, ensure_ascii=False, indent=2)
    log_analysis(f"   💾 Commentary saved to: {commentary_path}")

    # ══════════════════════════════════════════════════════════
    # STEP 3: HTML Dashboard & Printable File Compilation
    # ══════════════════════════════════════════════════════════
    try:
        from html_compiler import compile_report, compile_printable_report
        html_content = compile_report(metrics, commentary, lang=lang)
        printable_content = compile_printable_report(metrics, commentary, lang=lang)
    except Exception as exc:
        err_msg = f"HTML compilation failed for {ticker}: {exc}"
        log_analysis(f"❌ {err_msg}")
        log_error(err_msg, exc=exc, context=ticker)
        sys.exit(1)

    with open(report_file_lang, "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(printable_report_file_lang, "w", encoding="utf-8") as f:
        f.write(printable_content)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(printable_report_file, "w", encoding="utf-8") as f:
        f.write(printable_content)

    log_analysis(f"✅ Dashboard report saved to: {report_file_lang} & {report_file}")
    log_analysis(f"📄 Printable PDF/Copy report saved to: {printable_report_file_lang} & {printable_report_file}")

    # ══════════════════════════════════════════════════════════
    # STEP 4: SQLite Database Indexing
    # ══════════════════════════════════════════════════════════
    try:
        import sqlite3
        db_path = os.path.join(BASE_DIR, "storage", "app.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
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

        piotroski = metrics.get("piotroski_f_score", {}).get("score", None)
        altman_z = metrics.get("altman_z_score", {}).get("z_score", None)
        beneish_m = metrics.get("beneish_m_score", {}).get("m_score", metrics.get("beneish_m_score", {}).get("score", None))
        raw_wacc = metrics.get("valuation_parameters", {}).get("wacc")
        wacc = round(raw_wacc * 100, 2) if isinstance(raw_wacc, (int, float)) else None

        dcf_val = (
            metrics.get("standard_dcf_model", {}).get("implied_share_price")
            or metrics.get("dcf_2stage", {}).get("intrinsic_value")
            or metrics.get("dcf_valuation", {}).get("fair_value")
        )
        graham_val = (
            metrics.get("expanded_metrics", {}).get("graham_number")
            or metrics.get("graham_number", {}).get("value")
        )
        lynch_val = (
            metrics.get("bank_valuation", {}).get("pb_roe_fair")
            or metrics.get("peter_lynch", {}).get("fair_value")
        )

        cur.execute("""
            INSERT INTO reports_index (ticker, report_date, file_path, piotroski_score, altman_z, beneish_m, wacc_pct, dcf_fair_value, graham_number, lynch_fair_value, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUCCESS')
            ON CONFLICT(ticker, report_date) DO UPDATE SET
                file_path=excluded.file_path,
                piotroski_score=excluded.piotroski_score,
                altman_z=excluded.altman_z,
                beneish_m=excluded.beneish_m,
                wacc_pct=excluded.wacc_pct,
                dcf_fair_value=excluded.dcf_fair_value,
                graham_number=excluded.graham_number,
                lynch_fair_value=excluded.lynch_fair_value,
                status='SUCCESS',
                created_at=CURRENT_TIMESTAMP;
        """, (ticker, date_str, report_file, piotroski, altman_z, beneish_m, wacc, dcf_val, graham_val, lynch_val))
        conn.commit()
        conn.close()
        log_analysis(f"🗄️ Indexed report metadata in SQLite database ({db_path})")
    except Exception as db_err:
        log_analysis(f"⚠️ SQLite DB Indexing warning: {db_err}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
        load_dotenv(override=True)
    except ImportError:
        pass

    ticker_arg = sys.argv[1] if len(sys.argv) > 1 else "ODINE.IS"
    lang_arg = None

    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        if idx + 1 < len(sys.argv):
            lang_arg = sys.argv[idx + 1].upper()

    if not lang_arg:
        try:
            import sqlite3
            db_path = os.path.join(BASE_DIR, "storage", "app.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT lang FROM watchlist WHERE ticker = ?", (ticker_arg,))
                row = cur.fetchone()
                conn.close()
                if row and row[0]:
                    lang_arg = row[0].strip().upper()
        except Exception as err:
            log_analysis(f"⚠️ Watchlist language lookup notice: {err}")

    if not lang_arg:
        lang_arg = "TR"

    generate_report(ticker_arg, lang=lang_arg)
