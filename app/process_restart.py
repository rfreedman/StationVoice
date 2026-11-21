"""Admin-requested process restart via systemd (Linux host)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time

from app.config import systemd_unit_name
from app.radio import as_cos_polling, get_radio

log = logging.getLogger(__name__)

_RESTART_DELAY_SECONDS = 1.0
_restart_lock = threading.Lock()
_restart_scheduled = False


class RestartBusyError(Exception):
    """Transmit is in progress; refuse to restart."""


class RestartUnavailableError(Exception):
    """systemctl / sudo cannot restart the unit on this host."""


def transmit_blocks_restart() -> bool:
    """True when PTT or a DRA USB transmit session is active."""
    radio = get_radio()
    poller = as_cos_polling(radio)
    if poller is not None and poller.ptt_keyed:
        return True
    from app.dra_radio import DraRadio

    if isinstance(radio, DraRadio) and radio.transmit_session_active():
        return True
    return False


def prepare_restart() -> None:
    """Raise if restart is unsafe; otherwise best-effort unkey."""
    if transmit_blocks_restart():
        raise RestartBusyError(
            "A transmission is in progress. Wait until it finishes, then try again."
        )
    radio = get_radio()
    try:
        radio.set_ptt(False)
    except Exception:
        log.debug("Best-effort PTT unkey before restart failed", exc_info=True)


def ensure_restart_possible(*, unit: str | None = None) -> str:
    """Validate unit name and ``systemctl`` presence. Returns the bare unit name."""
    name = (unit or systemd_unit_name()).strip()
    if not name or name.endswith(".service"):
        raise RestartUnavailableError(
            "TTS_SYSTEMD_UNIT must be the bare unit name (e.g. dvra-announcements), "
            + "without a .service suffix."
        )
    if shutil.which("systemctl") is None:
        raise RestartUnavailableError(
            "systemctl is not available on this host. Restart the process from the shell."
        )
    return name


def schedule_systemd_restart() -> None:
    """Queue a delayed ``sudo -n systemctl restart`` (idempotent per process)."""
    global _restart_scheduled
    _ = ensure_restart_possible()
    with _restart_lock:
        if _restart_scheduled:
            return
        _restart_scheduled = True
        thread = threading.Thread(
            target=_run_restart_after_delay,
            name="systemd-restart",
            daemon=True,
        )
        thread.start()


def run_systemd_restart(*, unit: str | None = None) -> None:
    """Invoke passwordless ``systemctl restart``. Raises ``RestartUnavailableError``."""
    name = ensure_restart_possible(unit=unit)
    systemctl = shutil.which("systemctl")
    assert systemctl is not None
    try:
        completed = subprocess.run(
            ["sudo", "-n", systemctl, "restart", name],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except OSError as exc:
        raise RestartUnavailableError(f"Could not run systemctl restart: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RestartUnavailableError("systemctl restart timed out") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip() or f"exit {completed.returncode}"
        raise RestartUnavailableError(
            f"sudo -n systemctl restart {name} failed: {detail}"
        )
    log.info("Requested systemctl restart of %s", name)


def _run_restart_after_delay() -> None:
    time.sleep(_RESTART_DELAY_SECONDS)
    try:
        run_systemd_restart()
    except RestartUnavailableError:
        log.exception("Scheduled systemd restart failed")
    except Exception:
        log.exception("Unexpected error during scheduled systemd restart")


def maybe_restart_after_newsline_processing(*, want_restart: bool) -> None:
    """Restart after Newsline split when requested, unless transmit is busy."""
    if not want_restart:
        return
    if transmit_blocks_restart():
        log.warning("Newsline restart skipped: transmission in progress")
        from app.notify_email import alert_admins

        alert_admins(
            "Newsline restart skipped",
            "Newsline processing finished, but the application was not restarted "
            + "because a transmission is in progress (COS busy).",
            key="newsline-restart-skipped",
        )
        return
    try:
        prepare_restart()
        schedule_systemd_restart()
        log.info("Scheduled application restart after Newsline processing")
    except RestartBusyError:
        log.warning("Newsline restart skipped: transmission became busy")
        from app.notify_email import alert_admins

        alert_admins(
            "Newsline restart skipped",
            "Newsline processing finished, but the application was not restarted "
            + "because a transmission is in progress (COS busy).",
            key="newsline-restart-skipped",
        )
    except RestartUnavailableError as exc:
        log.exception("Newsline restart could not be scheduled")
        from app.notify_email import alert_admins

        alert_admins(
            "Newsline restart failed",
            f"Newsline processing finished, but the application restart failed: {exc}",
            key="newsline-restart-failed",
        )


def reset_restart_schedule_for_tests() -> None:
    """Test helper: allow another scheduled restart in this process."""
    global _restart_scheduled
    with _restart_lock:
        _restart_scheduled = False
