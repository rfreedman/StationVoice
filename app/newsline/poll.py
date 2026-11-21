"""Hourly Newsline check inside the Thursday–Friday window, plus a manual run."""

from __future__ import annotations

import logging
import shutil
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast
from zoneinfo import ZoneInfo

from apscheduler.triggers.date import DateTrigger

if TYPE_CHECKING:
    from app.api_types import NewslineStatus

from app.config import NEWSLINE_DIR
from app.newsline.decode import ffmpeg_available
from app.newsline.download import download_file, fetch_feed, latest_report
from app.newsline.engine.progress import begin_ui_progress, end_ui_progress, set_ui_step, ui_snapshot
from app.newsline.release import parse_release_friday
from app.newsline.split_job import SplitError, split_report
from app.newsline.state import NewsState, load_state, published_on_text, save_state
from app.newsline.window import next_anchor_after, success_in_window, window_for
from app.slots import as_local, zone_for
from app.scheduler_types import SchedulerJob
from app.store import get_store

log = logging.getLogger("app.newsline")

JOB_ID = "newsline-poll"
NEWSLINE_MANUAL_CHOICE_TIMEOUT_SECONDS = 600
ManualSplitChoice = Literal["stop", "split_restart", "split_no_restart"]

_guard = threading.Lock()
_in_progress = False
_choice_lock = threading.Lock()
_choice_event = threading.Event()
_choice_result: ManualSplitChoice | None = None
_awaiting_choice = False


def check_in_progress() -> bool:
    with _guard:
        return _in_progress


def awaiting_manual_choice() -> bool:
    with _choice_lock:
        return _awaiting_choice


def log_ffmpeg_status() -> None:
    if ffmpeg_available():
        return
    log.warning("ffmpeg or ffprobe is not on PATH; Newsline download and playback cannot run")


def _begin() -> bool:
    global _in_progress
    with _guard:
        if _in_progress:
            return False
        _in_progress = True
        return True


def _end() -> None:
    global _in_progress
    with _guard:
        _in_progress = False


def _store(state: NewsState, root: Path | None = None) -> None:
    save_state(state, root)
    try:
        from app.live_notify import notify_home_data_changed

        notify_home_data_changed()
    except Exception:
        log.debug("Newsline status notify failed", exc_info=True)


def _mark_current(state: NewsState) -> None:
    state.error = None
    state.last_outcome = "current"


def _remember_published(state: NewsState, report: object) -> None:
    """Keep the feed date for this report. A missing date does not erase one already stored."""
    number = getattr(report, "report_number", None)
    published = getattr(report, "published_on", None)
    if not isinstance(number, int):
        return
    if isinstance(published, datetime):
        state.published_on = published
        return
    if isinstance(published, date):
        state.published_on = datetime(published.year, published.month, published.day)
        return
    if state.report_number != number:
        state.published_on = None


def _news_root(root: Path | None = None) -> Path:
    return root if root is not None else NEWSLINE_DIR


def _clear_report_cache(root: Path | None, number: int) -> None:
    """Remove splitter cache for one report. Playback does not use these files."""
    cache = _news_root(root) / "cache"
    prefixes = (f"Report{number}_", f"{number:04d}_")
    removed = 0
    for folder in (cache / "forced_align", cache / "slices"):
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.name.startswith(prefixes):
                path.unlink(missing_ok=True)
                removed += 1
    if removed:
        log.info("Cleared Newsline split cache for report %s", number)


def _remove_report_files(folder: Path, number: int) -> None:
    for name in (f"Report{number}.mp3", f"nsln{number}.txt"):
        path = folder / name
        if path.is_file():
            path.unlink()
    stories = folder / "stories"
    if stories.is_dir():
        shutil.rmtree(stories)


def _settings_now() -> tuple[datetime, str, str, int, ZoneInfo, int]:
    from app.config import (
        NEWS_CHECK_START,
        NEWS_CHECK_STOP,
        REPEATER_TIMEOUT_SECONDS,
        news_check_interval_minutes,
    )

    document = get_store().document()
    zone = zone_for(document.settings.timezone)
    now = as_local(datetime.now(zone), zone)
    return (
        now,
        NEWS_CHECK_START,
        NEWS_CHECK_STOP,
        REPEATER_TIMEOUT_SECONDS,
        zone,
        news_check_interval_minutes(),
    )


def submit_manual_split_choice(action: ManualSplitChoice) -> bool:
    """Record the admin's post-download choice. False when not awaiting."""
    global _choice_result
    with _choice_lock:
        if not _awaiting_choice:
            return False
        _choice_result = action
        _choice_event.set()
        return True


def _begin_await_choice() -> None:
    global _awaiting_choice, _choice_result
    with _choice_lock:
        _awaiting_choice = True
        _choice_result = None
        _choice_event.clear()


def _end_await_choice() -> None:
    global _awaiting_choice
    with _choice_lock:
        _awaiting_choice = False


def _await_manual_split_choice(*, timeout_seconds: float | None = None) -> ManualSplitChoice:
    """Block until the admin chooses, or time out as Stop."""
    wait_for = (
        NEWSLINE_MANUAL_CHOICE_TIMEOUT_SECONDS
        if timeout_seconds is None
        else timeout_seconds
    )
    _begin_await_choice()
    try:
        if not _choice_event.wait(wait_for):
            log.info(
                "Manual Newsline split choice timed out after %s seconds; stopping",
                wait_for,
            )
            return "stop"
        with _choice_lock:
            result = _choice_result
        if result is None:
            return "stop"
        log.info("Manual Newsline split choice: %s", result)
        return result
    finally:
        _end_await_choice()


def begin_manual_choice_for_tests() -> None:
    """Test helper: mark the poller as awaiting a split choice."""
    _begin_await_choice()


def reset_manual_choice_for_tests() -> None:
    """Test helper: clear any pending manual split choice wait."""
    global _choice_result, _awaiting_choice
    with _choice_lock:
        _awaiting_choice = False
        _choice_result = None
        _choice_event.set()
        _choice_event.clear()


def run_check(*, manual: bool, root: Path | None = None) -> NewsState:
    """Fetch, download, and split when a newer report is available."""
    now, start_hhmm, stop_hhmm, timeout, _zone, _interval = _settings_now()
    state = load_state(root)
    state.phase = "checking"
    state.working_report = None
    state.last_check_at = now
    _store(state, root)
    log.info("Newsline check started (manual=%s)", manual)
    begin_ui_progress("Checking the Newsline feed")
    downloaded = False
    number: int | None = None
    split_started = False
    want_restart = False
    try:
        if not ffmpeg_available():
            raise OSError("ffmpeg and ffprobe are required")
        report = latest_report(fetch_feed())
        if report is None:
            state.error = "The Newsline feed has no report"
            log.info("Newsline feed has no report")
            return state
        number = report.report_number
        window = window_for(now, start_hhmm, stop_hhmm)
        already = state.report_number == number and state.split_ok
        if already and window is not None and not manual:
            if success_in_window(
                state.completed_at,
                split_ok=True,
                start=window[0],
                stop=window[1],
            ):
                log.info("Newsline report %s was already split this window", number)
                _remember_published(state, report)
                _mark_current(state)
                return state
            if state.completed_at is not None and state.completed_at < window[0]:
                log.info(
                    "Newsline feed is still report %s from before this window; will check again",
                    number,
                )
                _remember_published(state, report)
                _mark_current(state)
                return state
        if already and manual:
            log.info("Newsline report %s is already split", number)
            _remember_published(state, report)
            _mark_current(state)
            return state
        if not manual and state.split_failed_report == number:
            log.info(
                "Newsline report %s already failed to split; not retrying until a newer report or a manual check",
                number,
            )
            return state
        if state.split_failed_report is not None and state.split_failed_report != number:
            _clear_report_cache(root, state.split_failed_report)
            state.split_failed_report = None
        folder = _news_root(root) / str(number)
        folder.mkdir(parents=True, exist_ok=True)
        audio = folder / f"Report{number}.mp3"
        transcript = folder / f"nsln{number}.txt"
        if manual and (
            state.split_failed_report == number
            or audio.is_file()
            or transcript.is_file()
            or (folder / "stories").exists()
        ):
            log.info("Manual Newsline check will re-download report %s", number)
            _remove_report_files(folder, number)
            _clear_report_cache(root, number)
            if state.split_failed_report == number:
                state.split_failed_report = None
        state.working_report = number
        state.phase = "downloading"
        _store(state, root)
        if not audio.is_file():
            set_ui_step(f"Downloading report {number} audio")
            log.info("Downloading Newsline report %s audio", number)
            download_file(report.audio_url, audio)
        else:
            log.info("Newsline audio already on disk: %s", audio)
        if not transcript.is_file():
            set_ui_step(f"Downloading report {number} script")
            log.info("Downloading Newsline report %s script", number)
            download_file(report.script_url, transcript)
        else:
            log.info("Newsline script already on disk: %s", transcript)
        downloaded = True
        if manual:
            state.phase = "awaiting_choice"
            set_ui_step("Waiting for your choice")
            _store(state, root)
            choice = _await_manual_split_choice()
            if choice == "stop":
                log.info("Manual Newsline check stopped before split (report %s)", number)
                state.error = None
                return state
            want_restart = choice == "split_restart"
        else:
            from app.config import NEWSLINE_RESTART_AFTER_PROCESS

            want_restart = NEWSLINE_RESTART_AFTER_PROCESS
        state.phase = "splitting"
        set_ui_step("Processing")
        _store(state, root)
        split_started = True
        try:
            split_report(
                audio=audio,
                transcript=transcript,
                output_dir=folder / "stories",
                cache_dir=_news_root(root) / "cache",
                repeater_timeout=timeout,
            )
        finally:
            _clear_report_cache(root, number)
        friday = (
            parse_release_friday(transcript.read_text(encoding="utf-8", errors="replace"))
            if transcript.is_file()
            else None
        )
        if friday is None:
            log.warning(
                "Newsline report %s script has no intended Friday; it will not air",
                number,
            )
        _remember_published(state, report)
        state.report_number = number
        state.release_friday = friday
        state.split_ok = True
        state.split_failed_report = None
        state.completed_at = _settings_now()[0]
        state.error = None
        state.last_outcome = "new"
        log.info("Newsline report %s is ready", number)
    except (OSError, SplitError, ValueError) as exc:
        if downloaded and number is not None:
            state.split_failed_report = number
            _clear_report_cache(root, number)
        state.error = str(exc)
        from app.notify_email import alert_admins

        alert_admins(
            "Newsline check failed",
            f"Newsline check failed: {exc}",
            exc=exc,
            key="newsline-check",
        )
    except Exception as exc:
        if downloaded and number is not None:
            state.split_failed_report = number
            _clear_report_cache(root, number)
        state.error = str(exc)
        from app.notify_email import alert_admins

        alert_admins(
            "Newsline check failed",
            "Newsline check failed with an unexpected error",
            exc=exc,
            key="newsline-check",
        )
    finally:
        end_ui_progress()
        state.phase = "idle"
        state.working_report = None
        state.last_check_at = _settings_now()[0]
        _store(state, root)
        if split_started:
            from app.process_restart import maybe_restart_after_newsline_processing

            maybe_restart_after_newsline_processing(want_restart=want_restart)
    return state


def _run_and_rearm(*, manual: bool) -> None:
    try:
        _ = run_check(manual=manual)
    finally:
        _end()
        if not manual:
            arm_next_poll(immediate=False)
        else:
            arm_next_poll(immediate=False)


def start_manual_check() -> bool:
    """Start one check on a background thread. False when one is already running."""
    if not _begin():
        log.info("Newsline check requested while one is already running")
        return False
    log.info("Manual Newsline check requested")
    state = load_state()
    state.phase = "checking"
    state.working_report = None
    _store(state)
    threading.Thread(target=_run_and_rearm, kwargs={"manual": True}, name="newsline-check", daemon=True).start()
    return True


def _scheduled_job() -> None:
    if not _begin():
        return
    _run_and_rearm(manual=False)


def arm_next_poll(*, immediate: bool) -> None:
    """Schedule the next anchor, or run now when the process woke inside the window."""
    from app.scheduler_instance import get_scheduler

    scheduler = get_scheduler()
    now, start_hhmm, stop_hhmm, _timeout, zone, interval_minutes = _settings_now()
    window = window_for(now, start_hhmm, stop_hhmm)
    if scheduler is not None:
        existing = cast(SchedulerJob | None, scheduler.get_job(JOB_ID))
        if existing is not None and (window is None or not immediate):
            scheduler.remove_job(JOB_ID)
    if window is None:
        return
    state = load_state()
    if success_in_window(state.completed_at, split_ok=state.split_ok, start=window[0], stop=window[1]):
        log.info("Newsline window already has a split report; no further checks")
        return
    if immediate and not check_in_progress():
        if _begin():
            threading.Thread(
                target=_run_and_rearm,
                kwargs={"manual": False},
                name="newsline-check",
                daemon=True,
            ).start()
        return
    nxt = next_anchor_after(
        now,
        window[0],
        window[1],
        interval_minutes=interval_minutes,
    )
    if nxt is None or scheduler is None:
        return
    _ = scheduler.add_job(
        _scheduled_job,
        DateTrigger(run_date=as_local(nxt, zone)),
        id=JOB_ID,
        replace_existing=True,
        misfire_grace_time=int(timedelta(minutes=5).total_seconds()),
    )
    log.info("Next Newsline check at %s", nxt.isoformat())


def install_news_poll() -> None:
    arm_next_poll(immediate=True)


def status_payload() -> NewslineStatus:
    state = load_state()
    stories = state.stories_dir()
    ready = False
    if stories is not None:
        from app.newsline.playlist import stories_ready

        ready = stories_ready(stories)
    from app.newsline.session import bulletin_session

    progress = ui_snapshot()
    phase = state.phase
    # Stale awaiting_choice after a crash/restart should not block the UI forever.
    if phase == "awaiting_choice" and not check_in_progress():
        phase = "idle"
    return {
        "report_number": state.report_number,
        "release_friday": state.release_friday.isoformat() if state.release_friday else None,
        "published_on": published_on_text(state.published_on),
        "split_ok": state.split_ok,
        "ready": ready,
        "phase": phase,
        "error": state.error,
        "completed_at": state.completed_at.isoformat() if state.completed_at else None,
        "last_check_at": state.last_check_at.isoformat() if state.last_check_at else None,
        "in_progress": check_in_progress(),
        "playing": bulletin_session.active,
        "working_report": state.working_report,
        "outcome": state.last_outcome,
        "step": progress["step"],
        "elapsed_seconds": progress["elapsed_seconds"],
    }
