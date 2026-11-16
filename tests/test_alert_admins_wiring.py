"""Regression: operational failures call alert_admins."""

from __future__ import annotations

import os
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

    monkeypatch.setattr("app.notify.loader.notify_startup_failure_if_ready", alert)
    monkeypatch.setattr(os, "_exit", _exit)

    startup.fail_startup("radio missing")

    alert.assert_called_once_with("Startup failed", "radio missing")
    assert exit_calls == [1]


def test_fail_startup_skips_alert_when_notifier_never_loaded(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Plugin requirement failures must not re-enter get_notifier or dump a traceback."""
    from app import notify_email, startup

    exit_calls: list[int] = []

    def _exit(code: int) -> None:
        exit_calls.append(code)

    notify_email.reset_notifier_for_tests()
    get = MagicMock(side_effect=AssertionError("get_notifier must not be called"))
    monkeypatch.setattr("app.notify_email.get_notifier", get)
    monkeypatch.setattr(os, "_exit", _exit)

    msg = (
        "Admin notify plugin bird_email.py (BirdEmailNotifier) cannot start: "
        + "messagebird-sdk is not installed; run: uv pip install 'messagebird-sdk>=0.137.0'"
    )
    with caplog.at_level("ERROR"):
        startup.fail_startup(msg)

    get.assert_not_called()
    assert exit_calls == [1]
    assert "Could not alert admins" not in caplog.text
    assert caplog.text.count("cannot start") == 1
    assert "messagebird-sdk" in caplog.text


def test_lifespan_emails_start_and_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from app.registry import EngineRegistry
    from app.server import app

    lifecycle = MagicMock()
    monkeypatch.setattr("app.notify_email.notify_admins_lifecycle", lifecycle)
    monkeypatch.setattr("app.server.init_radio_at_startup", lambda: None)

    def _preload(_self: EngineRegistry) -> list[str]:
        return []

    monkeypatch.setattr(EngineRegistry, "preload", _preload)
    monkeypatch.setattr("app.server.warm_all", lambda: None)
    monkeypatch.setattr("app.server.start_scheduler", lambda: None)
    monkeypatch.setattr("app.server.stop_scheduler", lambda: None)

    with TestClient(app):
        pass

    subjects: list[str] = []
    for call in lifecycle.call_args_list:
        args = cast(tuple[object, ...], call.args)
        subjects.append(str(args[0]).lower())
    assert any("started" in subject for subject in subjects)
    assert any("stopped" in subject for subject in subjects)


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
