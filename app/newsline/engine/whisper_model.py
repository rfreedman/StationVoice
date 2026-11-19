"""Process-wide Whisper model cache (shared by handoff inspect + slice QA).

Parallel QA uses distinct ``slot`` indices so each worker owns a model
instance (faster-whisper / CTranslate2 is not safe for concurrent
``transcribe`` on one model).

Models stay loaded for the duration of one Newsline split only. Call
``clear_whisper_models`` when the pipeline finishes so the announcer process
does not keep multiple ``small.en`` / ``base.en`` instances for the rest of
the week.
"""

from __future__ import annotations

import gc
import logging
import os
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

log = logging.getLogger("app.newsline")

_whisper_model_cache: dict[tuple[str, int], WhisperModel] = {}
_cache_lock = threading.Lock()

# Cap RAM: each small.en instance is substantial. Override with env/CLI.
_DEFAULT_QA_WORKERS_CAP = 4


def qa_worker_count(requested: int | None = None) -> int:
    """
    How many parallel slice-QA Whisper workers to use.

    Priority: explicit ``requested`` → ``ARNEWSLINE_QA_WORKERS`` →
    ``min(4, cpu_count)`` (at least 1).
    """
    if requested is not None:
        return max(1, requested)
    env = os.environ.get("ARNEWSLINE_QA_WORKERS")
    if env is not None and env.strip() != "":
        return max(1, int(env))
    cpus = os.cpu_count() or 2
    return max(1, min(_DEFAULT_QA_WORKERS_CAP, cpus))


def get_whisper_model(model_name: str, *, slot: int = 0) -> WhisperModel:
    """Return a cached faster-whisper ``WhisperModel`` for ``model_name`` + slot."""
    key = (model_name, max(0, slot))
    with _cache_lock:
        if key not in _whisper_model_cache:
            from faster_whisper import WhisperModel as _WhisperModel

            _whisper_model_cache[key] = _WhisperModel(
                model_name, device="auto", compute_type="auto"
            )
        return _whisper_model_cache[key]


def warm_whisper_slots(model_name: str, workers: int) -> None:
    """Load one model per QA worker slot up front (avoids first-hit stampedes)."""
    for slot in range(max(1, workers)):
        _ = get_whisper_model(model_name, slot=slot)


def clear_whisper_models() -> int:
    """Drop cached faster-whisper models and ask the GC to reclaim them.

    Returns how many cache entries were removed. Native allocators (CTranslate2)
    may not return every byte to the OS, but this prevents holding several
    multi-hundred-MB models until process restart.
    """
    with _cache_lock:
        count = len(_whisper_model_cache)
        _whisper_model_cache.clear()
    if count:
        _ = gc.collect()
        log.info("Released %s cached Whisper model(s) after Newsline split", count)
    return count


def cached_whisper_model_count() -> int:
    """Test helper: how many Whisper instances are currently cached."""
    with _cache_lock:
        return len(_whisper_model_cache)
