"""Restart after Newsline processing and the manual post-download choice."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.newsline.poll import (
    ManualSplitChoice,
    begin_manual_choice_for_tests,
    reset_manual_choice_for_tests,
    run_check,
    submit_manual_split_choice,
)
from app.newsline.split_job import SplitError
from app.process_restart import (
    RestartBusyError,
    RestartUnavailableError,
    maybe_restart_after_newsline_processing,
    reset_restart_schedule_for_tests,
)
from app.store import AnnouncementStore
from tests.jsonutil import json_dict


def _write_download(_url: str, dest: Path, number: int, friday: str) -> None:
    if dest.suffix == ".txt":
        _ = dest.write_text(
            f"Amateur Radio Newsline Report {number} for Friday, {friday}\n",
            encoding="utf-8",
        )
    else:
        _ = dest.write_bytes(b"audio")


def _stub_ready_download(
    monkeypatch: pytest.MonkeyPatch,
    number: int,
    *,
    split: object | None = None,
) -> dict[str, int]:
    calls = {"download": 0, "split": 0}

    class Report:
        report_number: int = number
        audio_url: str = f"http://example.invalid/Report{number}.mp3"
        script_url: str = f"http://example.invalid/nsln{number}.txt"

    def ffmpeg_available() -> bool:
        return True

    def fetch_feed() -> None:
        return None

    def latest_report(_feed: object) -> Report:
        return Report()

    def download(_url: str, dest: Path) -> None:
        calls["download"] += 1
        _write_download(_url, dest, number, "October 30th, 2026")

    def default_split(**_kwargs: object) -> None:
        calls["split"] += 1

    monkeypatch.setattr("app.newsline.poll.ffmpeg_available", ffmpeg_available)
    monkeypatch.setattr("app.newsline.poll.fetch_feed", fetch_feed)
    monkeypatch.setattr("app.newsline.poll.latest_report", latest_report)
    monkeypatch.setattr("app.newsline.poll.download_file", download)
    monkeypatch.setattr(
        "app.newsline.poll.split_report",
        split if split is not None else default_split,
    )
    return calls


def _track_restarts(
    monkeypatch: pytest.MonkeyPatch, restarts: list[bool]
) -> None:
    def track(*, want_restart: bool) -> None:
        restarts.append(want_restart)

    monkeypatch.setattr(
        "app.process_restart.maybe_restart_after_newsline_processing",
        track,
    )


def _force_manual_choice(
    monkeypatch: pytest.MonkeyPatch, action: ManualSplitChoice
) -> None:
    def choose(*, timeout_seconds: float | None = None) -> ManualSplitChoice:
        _ = timeout_seconds
        return action

    monkeypatch.setattr("app.newsline.poll._await_manual_split_choice", choose)


def test_maybe_restart_noop_when_not_wanted(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_restart_schedule_for_tests()
    scheduled: list[bool] = []

    def schedule() -> None:
        scheduled.append(True)

    monkeypatch.setattr("app.process_restart.schedule_systemd_restart", schedule)
    maybe_restart_after_newsline_processing(want_restart=False)
    assert scheduled == []


def test_maybe_restart_schedules_when_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_restart_schedule_for_tests()
    scheduled: list[bool] = []

    def schedule() -> None:
        scheduled.append(True)

    monkeypatch.setattr("app.process_restart.transmit_blocks_restart", lambda: False)
    monkeypatch.setattr("app.process_restart.prepare_restart", lambda: None)
    monkeypatch.setattr("app.process_restart.schedule_systemd_restart", schedule)
    maybe_restart_after_newsline_processing(want_restart=True)
    assert scheduled == [True]


def test_maybe_restart_alerts_when_transmit_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_restart_schedule_for_tests()
    scheduled: list[bool] = []
    alerts: list[str] = []

    def schedule() -> None:
        scheduled.append(True)

    def alert(subject: str, _body: str, **kwargs: object) -> None:
        alerts.append(str(kwargs.get("key") or subject))

    monkeypatch.setattr("app.process_restart.transmit_blocks_restart", lambda: True)
    monkeypatch.setattr("app.process_restart.schedule_systemd_restart", schedule)
    monkeypatch.setattr("app.notify_email.alert_admins", alert)
    maybe_restart_after_newsline_processing(want_restart=True)
    assert scheduled == []
    assert alerts == ["newsline-restart-skipped"]


def test_maybe_restart_alerts_on_busy_race(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_restart_schedule_for_tests()
    alerts: list[str] = []

    def alert(_subject: str, _body: str, **kwargs: object) -> None:
        alerts.append(str(kwargs.get("key") or ""))

    def prepare() -> None:
        raise RestartBusyError("busy")

    monkeypatch.setattr("app.process_restart.transmit_blocks_restart", lambda: False)
    monkeypatch.setattr("app.process_restart.prepare_restart", prepare)
    monkeypatch.setattr("app.notify_email.alert_admins", alert)
    maybe_restart_after_newsline_processing(want_restart=True)
    assert alerts == ["newsline-restart-skipped"]


def test_maybe_restart_alerts_when_systemd_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_restart_schedule_for_tests()
    alerts: list[str] = []

    def alert(_subject: str, _body: str, **kwargs: object) -> None:
        alerts.append(str(kwargs.get("key") or ""))

    def schedule() -> None:
        raise RestartUnavailableError("no systemctl")

    monkeypatch.setattr("app.process_restart.transmit_blocks_restart", lambda: False)
    monkeypatch.setattr("app.process_restart.prepare_restart", lambda: None)
    monkeypatch.setattr("app.process_restart.schedule_systemd_restart", schedule)
    monkeypatch.setattr("app.notify_email.alert_admins", alert)
    maybe_restart_after_newsline_processing(want_restart=True)
    assert alerts == ["newsline-restart-failed"]


def test_scheduled_check_restarts_when_toggle_on(
    monkeypatch: pytest.MonkeyPatch, store: AnnouncementStore, tmp_path: Path
) -> None:
    _ = store
    restarts: list[bool] = []
    _ = _stub_ready_download(monkeypatch, 2557)
    monkeypatch.setattr("app.config.NEWSLINE_RESTART_AFTER_PROCESS", True)
    _track_restarts(monkeypatch, restarts)
    state = run_check(manual=False, root=tmp_path)
    assert state.split_ok
    assert restarts == [True]


def test_scheduled_check_does_not_restart_when_toggle_off(
    monkeypatch: pytest.MonkeyPatch, store: AnnouncementStore, tmp_path: Path
) -> None:
    _ = store
    restarts: list[bool] = []
    _ = _stub_ready_download(monkeypatch, 2557)
    monkeypatch.setattr("app.config.NEWSLINE_RESTART_AFTER_PROCESS", False)
    _track_restarts(monkeypatch, restarts)
    state = run_check(manual=False, root=tmp_path)
    assert state.split_ok
    assert restarts == [False]


def test_failed_split_still_offers_restart_when_toggle_on(
    monkeypatch: pytest.MonkeyPatch, store: AnnouncementStore, tmp_path: Path
) -> None:
    _ = store
    restarts: list[bool] = []

    def split(**_kwargs: object) -> None:
        raise SplitError("align failed")

    _ = _stub_ready_download(monkeypatch, 2557, split=split)
    monkeypatch.setattr("app.config.NEWSLINE_RESTART_AFTER_PROCESS", True)
    _track_restarts(monkeypatch, restarts)
    state = run_check(manual=False, root=tmp_path)
    assert state.split_failed_report == 2557
    assert restarts == [True]


def test_download_failure_does_not_restart(
    monkeypatch: pytest.MonkeyPatch, store: AnnouncementStore, tmp_path: Path
) -> None:
    _ = store
    restarts: list[bool] = []

    def download(_url: str, dest: Path) -> None:
        _ = dest
        raise OSError("network down")

    class Report:
        report_number: int = 2557
        audio_url: str = "http://example.invalid/Report2557.mp3"
        script_url: str = "http://example.invalid/nsln2557.txt"

    def latest_report(_feed: object) -> Report:
        return Report()

    monkeypatch.setattr("app.newsline.poll.ffmpeg_available", lambda: True)
    monkeypatch.setattr("app.newsline.poll.fetch_feed", lambda: None)
    monkeypatch.setattr("app.newsline.poll.latest_report", latest_report)
    monkeypatch.setattr("app.newsline.poll.download_file", download)
    monkeypatch.setattr("app.config.NEWSLINE_RESTART_AFTER_PROCESS", True)
    _track_restarts(monkeypatch, restarts)
    state = run_check(manual=False, root=tmp_path)
    assert state.error == "network down"
    assert restarts == []


def test_manual_stop_skips_split_and_restart(
    monkeypatch: pytest.MonkeyPatch, store: AnnouncementStore, tmp_path: Path
) -> None:
    _ = store
    restarts: list[bool] = []
    calls = _stub_ready_download(monkeypatch, 2557)
    _force_manual_choice(monkeypatch, "stop")
    _track_restarts(monkeypatch, restarts)
    state = run_check(manual=True, root=tmp_path)
    assert calls == {"download": 2, "split": 0}
    assert not state.split_ok
    assert state.report_number is None
    assert state.error is None
    assert (tmp_path / "2557" / "Report2557.mp3").is_file()
    assert restarts == []


def test_manual_split_restart_overrides_toggle_off(
    monkeypatch: pytest.MonkeyPatch, store: AnnouncementStore, tmp_path: Path
) -> None:
    _ = store
    restarts: list[bool] = []
    _ = _stub_ready_download(monkeypatch, 2557)
    monkeypatch.setattr("app.config.NEWSLINE_RESTART_AFTER_PROCESS", False)
    _force_manual_choice(monkeypatch, "split_restart")
    _track_restarts(monkeypatch, restarts)
    state = run_check(manual=True, root=tmp_path)
    assert state.split_ok
    assert restarts == [True]


def test_manual_split_no_restart_overrides_toggle_on(
    monkeypatch: pytest.MonkeyPatch, store: AnnouncementStore, tmp_path: Path
) -> None:
    _ = store
    restarts: list[bool] = []
    _ = _stub_ready_download(monkeypatch, 2557)
    monkeypatch.setattr("app.config.NEWSLINE_RESTART_AFTER_PROCESS", True)
    _force_manual_choice(monkeypatch, "split_no_restart")
    _track_restarts(monkeypatch, restarts)
    state = run_check(manual=True, root=tmp_path)
    assert state.split_ok
    assert restarts == [False]


def test_manual_choice_timeout_acts_as_stop(
    monkeypatch: pytest.MonkeyPatch, store: AnnouncementStore, tmp_path: Path
) -> None:
    _ = store
    from app.newsline import poll as newsline_poll

    restarts: list[bool] = []
    calls = _stub_ready_download(monkeypatch, 2557)
    monkeypatch.setattr(newsline_poll, "NEWSLINE_MANUAL_CHOICE_TIMEOUT_SECONDS", 0.05)
    _track_restarts(monkeypatch, restarts)
    reset_manual_choice_for_tests()
    state = run_check(manual=True, root=tmp_path)
    assert calls == {"download": 2, "split": 0}
    assert state.phase == "idle"
    assert not state.split_ok
    assert restarts == []


def test_choice_api_accepts_while_awaiting_and_409_otherwise(client: TestClient) -> None:
    reset_manual_choice_for_tests()
    rejected = client.post("/api/newsline/check/choice", json={"action": "stop"})
    assert rejected.status_code == 409

    begin_manual_choice_for_tests()
    try:
        ok = client.post(
            "/api/newsline/check/choice",
            json={"action": "split_restart"},
        )
        assert ok.status_code == 200
        assert json_dict(ok)["result"] == "split_restart"
    finally:
        reset_manual_choice_for_tests()
    again = client.post("/api/newsline/check/choice", json={"action": "stop"})
    assert again.status_code == 409
    assert submit_manual_split_choice("stop") is False


def test_admin_saves_newsline_restart_toggle(client: TestClient) -> None:
    import app.config as app_config
    from app.admin_config import ConfigState

    env_path = Path(os.environ["DOTENV_PATH"])
    _ = env_path.write_text("", encoding="utf-8")
    res = client.get("/api/admin/config")
    assert res.status_code == 200
    state = ConfigState.model_validate(json_dict(res))
    values = state.current.values.model_dump()
    values["newsline_restart_after_process"] = True
    saved = client.post(
        "/api/admin/config",
        json={"values": values, "short_description": "Restart after Newsline"},
    )
    assert saved.status_code == 200, saved.text
    body = ConfigState.model_validate(json_dict(saved))
    assert body.current.values.newsline_restart_after_process is True
    assert app_config.NEWSLINE_RESTART_AFTER_PROCESS is True
    text = env_path.read_text(encoding="utf-8")
    assert "NEWSLINE_RESTART_AFTER_PROCESS=true" in text
