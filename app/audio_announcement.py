"""Store and decode operator-uploaded MP3 announcement files."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app.audio import PcmChunk
from app.config import ANNOUNCEMENT_AUDIO_DIR, AUDIO_ANNOUNCEMENT_MAX_BYTES
from app.models import Announcement, AudioAnnouncement
from app.newsline.decode import SAMPLE_RATE, ffmpeg_available, mp3_to_chunks
from app.spoken_length import apply_played_length

log = logging.getLogger("app.audio_announcement")

_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "",
        "application/octet-stream",
        "audio/mpeg",
        "audio/mp3",
        "audio/x-mpeg",
        "audio/x-mp3",
    }
)


def audio_path(announcement_id: str) -> Path:
    return ANNOUNCEMENT_AUDIO_DIR / f"{announcement_id}.mp3"


def ensure_audio_dir() -> Path:
    ANNOUNCEMENT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    return ANNOUNCEMENT_AUDIO_DIR


def delete_audio_file(announcement_id: str) -> None:
    path = audio_path(announcement_id)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        log.exception("Could not delete audio file %s", path)


def looks_like_mp3(data: bytes, *, filename: str, content_type: str | None) -> None:
    """Raise ValueError when the upload is not an acceptable MP3 candidate."""
    if not data:
        raise ValueError("File is empty")
    if len(data) > AUDIO_ANNOUNCEMENT_MAX_BYTES:
        raise ValueError(
            f"File is larger than {AUDIO_ANNOUNCEMENT_MAX_BYTES} bytes"
        )
    name = Path(filename or "").name
    if not name.lower().endswith(".mp3"):
        raise ValueError("Only MP3 files are allowed")
    ctype = (content_type or "").split(";", 1)[0].strip().lower()
    if ctype and ctype not in _ALLOWED_CONTENT_TYPES:
        raise ValueError("Only MP3 files are allowed")
    if data.startswith(b"ID3"):
        return
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return
    raise ValueError("File is not a valid MP3")


def probe_mp3(path: Path) -> float:
    """Return duration in seconds when ffprobe reports container format mp3."""
    if not ffmpeg_available():
        raise OSError("ffmpeg and ffprobe are required to use audio announcements")
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name,duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise ValueError(detail or "File is not a valid MP3")
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("File is not a valid MP3")
    format_name = lines[0].split(",")[0].strip().lower()
    if format_name != "mp3":
        raise ValueError("Only MP3 files are allowed")
    try:
        return float(lines[1])
    except ValueError as exc:
        raise ValueError("Could not read MP3 duration") from exc


def write_audio_file(announcement_id: str, data: bytes) -> Path:
    _ = ensure_audio_dir()
    path = audio_path(announcement_id)
    _ = path.write_bytes(data)
    return path


def chunks_for_audio_announcement(announcement: Announcement) -> list[PcmChunk]:
    if announcement.kind != "audio":
        raise ValueError(f"Expected audio announcement, got {announcement.kind}")
    path = audio_path(announcement.id)
    if not path.is_file():
        raise OSError(f"Audio file missing for {announcement.name}")
    return mp3_to_chunks(path, sample_rate=SAMPLE_RATE)


def measure_audio_announcement(
    announcement: AudioAnnouncement, timeout_seconds: int, *, path: Path | None = None
) -> AudioAnnouncement:
    target = path if path is not None else audio_path(announcement.id)
    duration = probe_mp3(target)
    measured = apply_played_length(announcement, duration, timeout_seconds)
    if measured.kind != "audio":
        raise TypeError("apply_played_length must preserve audio kind")
    return measured
