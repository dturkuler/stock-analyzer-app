import sqlite3
from logger import log_error

def get_db_connection(db_path: str, timeout: float = 30.0) -> sqlite3.Connection:
    """
    Creates a thread-safe SQLite connection with explicit busy timeout and WAL journal mode
    to prevent database locking during concurrent operations.
    """
    conn = sqlite3.connect(db_path, timeout=timeout)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn

def ensure_reports_index_schema(conn: sqlite3.Connection):
    """
    Ensures the reports_index table and all required valuation columns exist in the SQLite database.
    Uses PRAGMA table_info inspection to avoid unhandled DDL exceptions and logs errors cleanly.
    """
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            report_date TEXT NOT NULL,
            file_path TEXT NOT NULL,
            stock_price REAL,
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
    
    cur.execute("PRAGMA table_info(reports_index);")
    existing_columns = {row[1] for row in cur.fetchall()}
    
    expected_columns = [
        ("stock_price", "REAL"),
        ("dcf_fair_value", "REAL"),
        ("graham_number", "REAL"),
        ("lynch_fair_value", "REAL")
    ]
    
    for col_name, col_type in expected_columns:
        if col_name not in existing_columns:
            try:
                cur.execute(f"ALTER TABLE reports_index ADD COLUMN {col_name} {col_type};")
            except Exception as e:
                log_error(f"Failed to add column '{col_name}' to reports_index table", exc=e)
    conn.commit()
