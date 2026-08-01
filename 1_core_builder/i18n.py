import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class I18nManager:
    _catalogs = {}
    _initialized = False

    @classmethod
    def _ensure_loaded(cls):
        if cls._initialized:
            return

        project_root = Path(__file__).parent.parent
        search_dirs = [
            project_root / "locales",
            project_root / "1_core_builder" / "locales",
            project_root / "3_web_server" / "locales",
        ]

        for locales_dir in search_dirs:
            if locales_dir.exists():
                for lang_file in locales_dir.glob("*.json"):
                    lang = lang_file.stem.upper()
                    if lang not in cls._catalogs:
                        cls._catalogs[lang] = {}
                    try:
                        with open(lang_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            cls._catalogs[lang].update(data)
                    except Exception as e:
                        logger.error(f"Failed to load locale file {lang_file}: {e}")

        cls._initialized = True

    @classmethod
    def t(cls, key: str, lang: str = "TR", **kwargs) -> str:
        cls._ensure_loaded()
        lang_code = (lang or "TR").upper()
        catalog = cls._catalogs.get(lang_code, cls._catalogs.get("TR", {}))

        value = catalog
        for part in key.split("."):
            if isinstance(value, dict):
                value = value.get(part, key)
            else:
                value = key
                break

        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except Exception:
                return value
        return str(value)

t = I18nManager.t

def sanitize_report_date(date_str: str) -> str:
    """
    Sanitizes a report date string by stripping language suffixes (_TR, _EN),
    file extensions (.html), and _printable markers.
    
    Example: '2026-08-01_TR' -> '2026-08-01'
    """
    if not date_str or not isinstance(date_str, str):
        return ""
    
    clean = date_str.replace(".html", "").replace("_printable", "")
    if clean.upper().endswith("_TR") or clean.upper().endswith("_EN"):
        clean = clean[:-3]
    return clean.strip()

