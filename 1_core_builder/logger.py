import os
import sys
import datetime
import traceback

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "storage", "logs")
ERRORS_LOG_FILE = os.path.join(LOGS_DIR, "errors.log")

def log_error(msg: str, exc: Exception = None, context: str = None):
    """
    Logs structured error details to storage/logs/errors.log and stdout.
    
    :param msg: Description of the error / failure.
    :param exc: Optional Exception object to format traceback from.
    :param context: Optional context string (e.g. Ticker symbol, endpoint, or task name).
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    ctx_str = f" [{context}]" if context else ""
    header = f"[{now_str}]{ctx_str} ❌ ERROR: {msg}"
    
    lines = [header]
    if exc is not None:
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        lines.append(f"   Traceback:\n{tb_str.strip()}")
    elif sys.exc_info()[0] is not None:
        tb_str = traceback.format_exc()
        lines.append(f"   Traceback:\n{tb_str.strip()}")
        
    formatted = "\n".join(lines)
    print(formatted, flush=True)
    try:
        with open(ERRORS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n\n")
    except Exception as e:
        print(f"⚠️ Errors log write error: {e}", flush=True)
