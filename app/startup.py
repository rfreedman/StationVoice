"""Application startup checks (DRA hardware, etc.)."""
from __future__ import annotations

import logging
import os
import sys

from app.startup_errors import DraHardwareMissingError, StartupError

__all__ = [
    "DraHardwareMissingError",
    "StartupError",
    "fail_startup",
    "init_radio_at_startup",
]

logger = logging.getLogger(__name__)


def _message_for_os_error(exc: OSError) -> str:
    return (
        "Could not open the DRA USB HID device. "
        "On Linux, check udev rules, replug the DRA, and confirm your user is in the "
        "plugdev group (see docs/linux-host.md). "
        f"({exc})"
    )


def _set_radio_fallback_reason(reason: str | None) -> None:
    from app.runtime import get_runtime

    get_runtime().radio_fallback_reason = reason


def init_radio_at_startup() -> None:
    """Eager DRA/stub radio init so misconfiguration fails before serving traffic.

    When ``TTS_RADIO_BACKEND`` is dra/cm119 but no DRA interfaces are attached,
    fall back to ``StubRadio`` with one admin alert instead of exiting.
    """
    from app.config import DRA_ALSA_SPEAKER_LEVEL, dra_alsa_unmute_enabled, radio_backend
    from app.radio import StubRadio, as_cos_polling, create_radio_from_config, set_radio

    _set_radio_fallback_reason(None)
    backend = radio_backend()
    try:
        if sys.platform.startswith("linux") and backend in ("dra", "cm119"):
            from app.dra_portaudio import refresh_portaudio_device_list

            refresh_portaudio_device_list()
        radio = create_radio_from_config()
        set_radio(radio)
        if (
            sys.platform.startswith("linux")
            and backend in ("dra", "cm119")
            and dra_alsa_unmute_enabled()
        ):
            from app.dra_alsa_mixer import ensure_cm119_speakers_unmuted
            from app.dra_radio import DraRadio

            if isinstance(radio, DraRadio):
                _ = radio.sync_audio_output_indices_if_changed(after_usb_event=True)
                ensure_cm119_speakers_unmuted(
                    radio.audio_device_indices,
                    level=DRA_ALSA_SPEAKER_LEVEL,
                )
        poller = as_cos_polling(radio)
        if poller is not None:
            poller.warm_open_hid()
    except DraHardwareMissingError as exc:
        reason = str(exc).rstrip()
        logger.error("%s", reason)
        _set_radio_fallback_reason(reason)
        set_radio(StubRadio())
        try:
            from app.notify_email import alert_admins

            alert_admins(
                "DRA missing — running stub",
                reason,
                key="dra-startup-missing",
            )
        except Exception:
            logger.debug("alert_admins failed during DRA stub fallback", exc_info=True)
    except StartupError:
        raise
    except (RuntimeError, ValueError) as exc:
        raise StartupError(str(exc)) from None
    except OSError as exc:
        raise StartupError(_message_for_os_error(exc)) from None
    except Exception as exc:
        raise StartupError(f"DRA radio startup failed: {exc}") from None


def fail_startup(message: str) -> None:
    """Log one clear message, optionally email if notify is already up, then exit 0.

    Exit 0 plus systemd ``Restart=no`` keeps the unit inactive (no restart loop).
    """
    text = message.rstrip()
    logger.error("%s", text)
    try:
        from app.notify.loader import notify_startup_failure_if_ready

        notify_startup_failure_if_ready("Startup failed", text)
    except Exception:
        # Never cascade; the original message already explains the failure.
        pass
    os._exit(0)
