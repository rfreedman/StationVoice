"""Env knobs that trade Newsline split speed for cooler / quieter CPU use.

Defaults stay fast (up to 4 parallel QA/export workers; Whisper/torch use all
cores). On a small Linux host that runs hot during Thursday–Friday download,
set for example::

    ARNEWSLINE_QA_WORKERS=1
    ARNEWSLINE_EXPORT_WORKERS=1
    ARNEWSLINE_CPU_THREADS=2

That serializes slice ASR and ffmpeg, and caps per-model BLAS/OpenMP threads
so one Whisper or stable-ts run cannot peg every core.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("app.newsline")

_DEFAULT_QA_WORKERS_CAP = 4
_DEFAULT_EXPORT_WORKERS = 4


def _env_positive_int(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        log.warning("Invalid %s=%r; ignoring", name, raw)
        return None
    if value < 1:
        log.warning("Invalid %s=%r; need an integer >= 1", name, raw)
        return None
    return value


def qa_worker_count(requested: int | None = None) -> int:
    """
    How many parallel slice-QA Whisper workers to use.

    Priority: explicit ``requested`` → ``ARNEWSLINE_QA_WORKERS`` →
    ``min(4, cpu_count)`` (at least 1).
    """
    if requested is not None:
        return max(1, requested)
    env = _env_positive_int("ARNEWSLINE_QA_WORKERS")
    if env is not None:
        return env
    cpus = os.cpu_count() or 2
    return max(1, min(_DEFAULT_QA_WORKERS_CAP, cpus))


def export_worker_count(requested: int | None = None) -> int:
    """Parallel ffmpeg slice exports (``ARNEWSLINE_EXPORT_WORKERS``, default 4)."""
    if requested is not None:
        return max(1, requested)
    env = _env_positive_int("ARNEWSLINE_EXPORT_WORKERS")
    if env is not None:
        return env
    return _DEFAULT_EXPORT_WORKERS


def cpu_thread_count() -> int | None:
    """
    Cap for Whisper CTranslate2 / PyTorch / OpenMP threads.

    ``ARNEWSLINE_CPU_THREADS`` unset or empty → library defaults (often all
    cores). Set to ``1``–``N`` to keep a Newsline split from saturating the CPU.
    """
    return _env_positive_int("ARNEWSLINE_CPU_THREADS")


def apply_host_thread_caps() -> None:
    """Apply ``ARNEWSLINE_CPU_THREADS`` to torch and common BLAS env vars."""
    threads = cpu_thread_count()
    if threads is None:
        return
    os.environ["OMP_NUM_THREADS"] = str(threads)
    os.environ["MKL_NUM_THREADS"] = str(threads)
    os.environ["OPENBLAS_NUM_THREADS"] = str(threads)
    try:
        import torch

        torch.set_num_threads(threads)
        # Inter-op >1 can still fan out; keep it single for cooler splits.
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            # May only be set once per process; ignore on a second split.
            pass
    except ImportError:
        pass
    log.info("Newsline split CPU threads capped at %s (ARNEWSLINE_CPU_THREADS)", threads)
