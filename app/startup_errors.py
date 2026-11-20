"""Startup failure type (kept separate to avoid import cycles with DRA helpers)."""

from __future__ import annotations


class StartupError(Exception):
    """Fatal startup problem; message is safe to show operators."""


class DraHardwareMissingError(RuntimeError):
    """Configured for DRA but no CM119 HID / DRA USB audio is attached.

    Soft-degraded to stub at startup; also raised from audio resolve on replug.
    """
