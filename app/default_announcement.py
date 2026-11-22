"""Default TTS script for new announcements.

Built-in text is ``This is {STATION_CALL}`` (or blank if the call is empty).
An optional override file under the data directory replaces that built-in.
"""

from __future__ import annotations

import os
from pathlib import Path

from app import config as app_config
from app.config import DATA_DIR, enforce_text_limit


def override_path() -> Path:
    override = os.environ.get("DEFAULT_ANNOUNCEMENT_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return DATA_DIR / "default-announcement.txt"


def builtin_text() -> str:
    # Read live: admin save reassigns app.config.STATION_CALL.
    call = app_config.STATION_CALL.strip()
    if not call:
        return ""
    return f"This is {call}"


def has_override() -> bool:
    return override_path().is_file()


def effective_text() -> str:
    path = override_path()
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return builtin_text()


def save_text(text: str) -> None:
    """Persist an override, or remove it when ``text`` matches the built-in."""
    cleaned = text.strip()
    _ = enforce_text_limit(cleaned)
    path = override_path()
    if cleaned == builtin_text():
        if path.is_file():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(cleaned, encoding="utf-8")


def clear_override() -> None:
    path = override_path()
    if path.is_file():
        path.unlink()
