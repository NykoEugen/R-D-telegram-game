"""Loads scene texts from YAML. Singleton — file read once."""

from pathlib import Path
from typing import Dict, Optional

import yaml

_TEXTS: Optional[Dict] = None
_YAML_PATH = Path(__file__).parent.parent / "game" / "scene_texts.yaml"


def _load() -> Dict:
    global _TEXTS
    if _TEXTS is not None:
        return _TEXTS
    with open(_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _TEXTS = data.get("scenes", {})
    return _TEXTS


def get_scene_text(scene_id: str, locale: str = "en") -> str:
    texts = _load()
    scene = texts.get(scene_id, {})
    return scene.get(locale) or scene.get("en") or f"📍 {scene_id.replace('_', ' ').title()}"
