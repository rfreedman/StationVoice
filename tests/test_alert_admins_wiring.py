"""Regression: operational failures call alert_admins."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock
from typing import cast

import pytest
from fastapi import HTTPException

from app.fire_types import FireOutcome
from app.routes.speak import raise_engine_http
from app.scheduler_jobs import add_defer_job
from app.scheduler_types import ManualDeferFn, ManualDeferJobKwargs
from app.tts.base import VoiceError


def test_raise_engine_http_400_does_not_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    alert = MagicMock()
    monkeypatch.setattr("app.notify_email.alert_admins", alert)

    with pytest.raises(HTTPException) as caught:
        raise_engine_http(VoiceError("bad voice"), where="speak")

    assert caught.value.status_code == 400
    alert.assert_not_called()


def test_raise_engine_http_502_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    alert = MagicMock()
    monkeypatch.setattr("app.notify_email.alert_admins", alert)

    with pytest.raises(HTTPException) as caught:
        raise_engine_http(OSError("disk full"), where="prepare")

    assert caught.value.status_code == 502
    alert.assert_called_once()
    assert alert.call_args.kwargs["key"] == "engine-io-prepare"


def test_raise_engine_http_500_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    alert = MagicMock()
    monkeypatch.setattr("app.notify_email.alert_admins", alert)

    with pytest.raises(HTTPException) as caught:
        raise_engine_http(RuntimeError("boom"), where="speak")

    assert caught.value.status_code == 500
    alert.assert_called_once()
    assert alert.call_args.kwargs["key"] == "engine-500-speak"


def test_fail_startup_alerts_before_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import startup

    alert = MagicMock()
    exit_calls: list[int] = []

    def _exit(code: int) -> None:
        exit_calls.append(code)

    def _write(_s: str) -> int:
        return 1

    def _flush() -> None:
        return None

    monkeypatch.setattr("app.notify_email.alert_admins", alert)
    monkeypatch.setattr(os, "_exit", _exit)
    monkeypatch.setattr(sys.stderr, "write", _write)
    monkeypatch.setattr(sys.stderr, "flush", _flush)

    startup.fail_startup("radio missing")

    alert.assert_called_once()
    assert alert.call_args.args[0] == "Startup failed"
    assert alert.call_args.kwargs["key"] == "startup"
    assert exit_calls == [1]


def test_add_defer_job_alerts_when_scheduler_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alert = MagicMock()
    monkeypatch.setattr("app.notify_email.alert_admins", alert)
    monkeypatch.setattr("app.scheduler_jobs.get_scheduler", lambda: None)

    def _noop(
        schedule_id: str,
        *,
        fired_at_iso: str | None = None,
        deadline_iso: str | None = None,
        defer_kind: str | None = None,
    ) -> FireOutcome:
        _ = (schedule_id, fired_at_iso, deadline_iso, defer_kind)
        return FireOutcome.DEFERRED

    kwargs: ManualDeferJobKwargs = {
        "schedule_id": "sched-1",
        "fired_at_iso": "2026-01-01T00:00:00+00:00",
        "deadline_iso": "2026-01-01T00:01:00+00:00",
    }
    ok = add_defer_job(
        cast(ManualDeferFn, _noop),
        "manual:sched-1",
        datetime.now(timezone.utc),
        kwargs,
    )

    assert ok is False
    alert.assert_called_once()
    assert alert.call_args.kwargs["key"] == "scheduler-defer"
