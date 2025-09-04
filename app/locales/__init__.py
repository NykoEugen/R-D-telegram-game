import json
from pathlib import Path
from functools import lru_cache

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LOCALE = "uk"
SUPPORTED_LOCALES = {"uk", "en"}

@lru_cache(maxsize=16)
def _load_locale(locale: str) -> dict:
    loc = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    with open(LOCALES_DIR / f"{loc}.json", "r", encoding="utf-8") as f:
        return json.load(f)

def t(key: str, locale: str | None = None, **kwargs) -> str:
    data = _load_locale(locale or DEFAULT_LOCALE)
    ref = data
    for part in key.split("."):
        ref = ref.get(part, {})
    if isinstance(ref, str):
        return ref.format(**kwargs)
    return key
