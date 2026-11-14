"""Send email via Bird. Soft-fail: log errors, never raise to callers."""

from __future__ import annotations

import html
import logging
import os
import threading
import time
import traceback
from collections.abc import Sequence

from bird import APIError, Bird

logger = logging.getLogger(__name__)

DEFAULT_FROM_NAME = "Repeater Announcements"
DEFAULT_ALERT_DEBOUNCE_SECONDS = 15 * 60

_debounce_lock = threading.Lock()
_last_alert_at: dict[str, float] = {}


def _normalize_recipients(recipients: Sequence[str]) -> list[str]:
    return [addr.strip() for addr in recipients if addr.strip()]


def send_email(subject: str, body: str, recipients: Sequence[str]) -> None:
    """Send email to the given addresses. Never raises."""
    api_key = os.environ.get("BIRD_API_KEY", "").strip()
    sender = os.environ.get("EMAIL_FROM", "").strip()
    from_name = os.environ.get("EMAIL_FROM_NAME", "").strip() or DEFAULT_FROM_NAME
    to = _normalize_recipients(recipients)

    if not api_key:
        logger.error("Skipping email: BIRD_API_KEY is not set")
        return
    if not sender:
        logger.error("Skipping email: EMAIL_FROM is not set")
        return
    if not to:
        logger.error("Skipping email: no recipients")
        return

    html_body = "<p>" + html.escape(body).replace("\n", "<br>\n") + "</p>"
    try:
        with Bird() as client:
            message = client.email.send(
                from_={"email": sender, "name": from_name},
                to=to,
                subject=subject,
                text=body,
                html=html_body,
            )
        logger.info(
            "Email sent (id=%s status=%s) to %s",
            getattr(message, "id", "?"),
            getattr(message, "status", "?"),
            ", ".join(to),
        )
    except APIError as exc:
        logger.error("Bird email request failed: %s", exc)
    except Exception as exc:
        logger.exception("Bird email send failed: %s", exc)


def notify_admins(subject: str, body: str) -> None:
    """Send email to ADMIN_EMAILS (comma-separated). Never raises."""
    recipients = [
        addr.strip()
        for addr in os.environ.get("ADMIN_EMAILS", "").split(",")
        if addr.strip()
    ]
    if not recipients:
        logger.error("Skipping notify: ADMIN_EMAILS is not set")
        return
    send_email(subject, body, recipients)


def _should_send_alert(key: str, debounce_seconds: float) -> bool:
    """Return True if this key is outside the debounce window; record send time if so."""
    now = time.monotonic()
    with _debounce_lock:
        last = _last_alert_at.get(key)
        if last is not None and (now - last) < debounce_seconds:
            return False
        _last_alert_at[key] = now
        return True


def alert_admins(
    subject: str,
    body: str,
    *,
    exc: BaseException | None = None,
    key: str | None = None,
    debounce_seconds: float = DEFAULT_ALERT_DEBOUNCE_SECONDS,
) -> None:
    """Log an operational error and email admins (debounced). Never raises."""
    debounce_key = key or subject
    if exc is not None:
        logger.error("%s", body, exc_info=exc)
        detail = f"{body.rstrip()}\n\n{type(exc).__name__}: {exc}"
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if tb.strip():
            detail = f"{detail}\n\n{tb}"
    else:
        logger.error("%s", body)
        detail = body

    if not _should_send_alert(debounce_key, debounce_seconds):
        logger.info("Skipping admin alert (debounced key=%s): %s", debounce_key, subject)
        return
    notify_admins(subject, detail)


def clear_alert_debounce_for_tests() -> None:
    """Reset debounce state (tests only)."""
    with _debounce_lock:
        _last_alert_at.clear()
