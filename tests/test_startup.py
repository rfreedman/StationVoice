from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock

import pytest

from app.radio import StubRadio, get_radio, set_radio
from app.runtime import get_runtime
from app.startup import DraHardwareMissingError, StartupError, init_radio_at_startup


def test_init_radio_at_startup_stub_registers_stub_radio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.config.radio_backend", lambda: "stub")
    set_radio(None)
    init_radio_at_startup()
    assert isinstance(get_radio(), StubRadio)
    assert get_runtime().radio_fallback_reason is None


def _fail_startup_recorder(monkeypatch: pytest.MonkeyPatch):
    seen: list[str] = []

    def fail(message: str) -> None:
        seen.append(message)
        raise SystemExit(1)

    monkeypatch.setattr("app.server.fail_startup", fail)
    return seen


def test_startup_data_file_error_exits_with_its_message(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    from app.server import complete_startup
    from app.store import DataFileError

    class BadStore:
        def document(self):
            raise DataFileError("announcements.json is not a version 2 announcements file")

    monkeypatch.setattr("app.server.get_store", lambda: BadStore())
    seen = _fail_startup_recorder(monkeypatch)
    with caplog.at_level(logging.ERROR, logger="app.server"):
        with pytest.raises(SystemExit):
            _ = asyncio.run(complete_startup(0.0, asyncio.Event()))
    assert "version 2" in seen[0]
    assert "Unexpected startup failure" not in caplog.text


def test_startup_logs_unexpected_failure_before_exit(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    from app.server import complete_startup

    class BadStore:
        def document(self):
            raise RuntimeError("scheduler boom")

    monkeypatch.setattr("app.server.get_store", lambda: BadStore())
    seen = _fail_startup_recorder(monkeypatch)
    with caplog.at_level(logging.ERROR, logger="app.server"):
        with pytest.raises(SystemExit):
            _ = asyncio.run(complete_startup(0.0, asyncio.Event()))
    assert seen == ["scheduler boom"]
    assert "Unexpected startup failure" in caplog.text
    assert "scheduler boom" in caplog.text


def test_init_radio_at_startup_wraps_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.config.radio_backend", lambda: "dra")

    def boom():
        raise RuntimeError("TTS_DRA_HID_PATH did not match any CM119 HID path.")

    monkeypatch.setattr("app.radio.create_radio_from_config", boom)
    with pytest.raises(StartupError, match="TTS_DRA_HID_PATH"):
        init_radio_at_startup()


def test_init_radio_dra_missing_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.config.radio_backend", lambda: "dra")
    alert = MagicMock()
    monkeypatch.setattr("app.notify_email.alert_admins", alert)

    def boom():
        raise DraHardwareMissingError("No CM119A HID interface found.")

    monkeypatch.setattr("app.radio.create_radio_from_config", boom)
    set_radio(None)
    init_radio_at_startup()
    assert isinstance(get_radio(), StubRadio)
    assert get_runtime().radio_fallback_reason is not None
    assert "No CM119A HID" in (get_runtime().radio_fallback_reason or "")
    alert.assert_called_once()
    assert alert.call_args.kwargs["key"] == "dra-startup-missing"
