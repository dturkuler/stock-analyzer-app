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
        locales_dir = Path(__file__).parent.parent / "locales"
        if not locales_dir.exists():
            locales_dir.mkdir(parents=True, exist_ok=True)

        for lang_file in locales_dir.glob("*.json"):
            lang = lang_file.stem.upper()
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    cls._catalogs[lang] = json.load(f)
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
