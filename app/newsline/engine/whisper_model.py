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
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

from app.newsline.engine.runtime_limits import cpu_thread_count, qa_worker_count

log = logging.getLogger("app.newsline")

_whisper_model_cache: dict[tuple[str, int], WhisperModel] = {}
_cache_lock = threading.Lock()

# Re-export for callers that imported qa_worker_count from this module.
__all__ = [
    "cached_whisper_model_count",
    "clear_whisper_models",
    "get_whisper_model",
    "qa_worker_count",
    "warm_whisper_slots",
]


def get_whisper_model(model_name: str, *, slot: int = 0) -> WhisperModel:
    """Return a cached faster-whisper ``WhisperModel`` for ``model_name`` + slot."""
    key = (model_name, max(0, slot))
    with _cache_lock:
        if key not in _whisper_model_cache:
            from faster_whisper import WhisperModel as _WhisperModel

            threads = cpu_thread_count()
            if threads is None:
                model = _WhisperModel(model_name, device="auto", compute_type="auto")
            else:
                model = _WhisperModel(
                    model_name,
                    device="auto",
                    compute_type="auto",
                    cpu_threads=threads,
                )
            _whisper_model_cache[key] = model
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
