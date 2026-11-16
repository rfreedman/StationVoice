"""Bird admin-email notifier plugin (example).

Copy this file into ``plugins/`` to enable admin email alerts (any filename works).
Remove it from ``plugins/`` to disable them. ``plugin-examples/`` is never loaded.

Requires messagebird-sdk (not a project dependency). Install into the venv::

    uv pip install 'messagebird-sdk>=0.137.0'

If this file is in ``plugins/`` but the SDK is missing, startup fails after a clear
error (see ``validate_requirements_installed``). Bird credentials and recipients
live in ``.env.secrets`` (``BIRD_API_KEY``, ``EMAIL_FROM``, ``EMAIL_FROM_NAME``,
``ADMIN_EMAILS``). Missing those values soft-fail: log and skip send.
"""

from __future__ import annotations

import html
import logging
import os
import threading
import time
import traceback
from collections.abc import Sequence
from typing import override

from app.notify.base import AdminNotifier

logger = logging.getLogger(__name__)

DEFAULT_FROM_NAME = "Repeater Announcements"
DEFAULT_ALERT_DEBOUNCE_SECONDS = 15 * 60
_SDK_INSTALL_HINT = "uv pip install 'messagebird-sdk>=0.137.0'"

try:
    from bird import APIError, Bird
except ImportError:  # pragma: no cover - validated in validate_requirements_installed
    APIError = Exception  # type: ignore[misc, assignment]
    Bird = None  # type: ignore[misc, assignment]


def _normalize_recipients(recipients: Sequence[str]) -> list[str]:
    return [addr.strip() for addr in recipients if addr.strip()]


def _admin_recipients() -> list[str]:
    return [
        addr.strip()
        for addr in os.environ.get("ADMIN_EMAILS", "").split(",")
        if addr.strip()
    ]


class BirdEmailNotifier(AdminNotifier):
    """Send admin alerts via Bird (MessageBird email API)."""

    def __init__(self) -> None:
        self._debounce_lock = threading.Lock()
        self._last_alert_at: dict[str, float] = {}

    @override
    def validate_requirements_installed(self) -> None:
        if Bird is None:
            raise RuntimeError(
                f"messagebird-sdk is not installed; run: {_SDK_INSTALL_HINT}"
            )

    def send_email(self, subject: str, body: str, recipients: Sequence[str]) -> None:
        if Bird is None:
            logger.error(
                "Skipping email: messagebird-sdk not installed (%s)", _SDK_INSTALL_HINT
            )
            return
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

    def notify_admins(self, subject: str, body: str) -> None:
        recipients = _admin_recipients()
        if not recipients:
            logger.error("Skipping notify: ADMIN_EMAILS is not set")
            return
        self.send_email(subject, body, recipients)

    def notify_admins_lifecycle(self, subject: str, body: str) -> None:
        recipients = _admin_recipients()
        if not recipients:
            logger.info("Skipping lifecycle email: ADMIN_EMAILS is not set")
            return
        self.send_email(subject, body, recipients)

    def _should_send_alert(self, key: str, debounce_seconds: float) -> bool:
        now = time.monotonic()
        with self._debounce_lock:
            last = self._last_alert_at.get(key)
            if last is not None and (now - last) < debounce_seconds:
                return False
            self._last_alert_at[key] = now
            return True

    def alert_admins(
        self,
        subject: str,
        body: str,
        *,
        exc: BaseException | None = None,
        key: str | None = None,
        debounce_seconds: float = DEFAULT_ALERT_DEBOUNCE_SECONDS,
    ) -> None:
        debounce_key = key or subject
        if exc is not None:
            detail = f"{body.rstrip()}\n\n{type(exc).__name__}: {exc}"
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            if tb.strip():
                detail = f"{detail}\n\n{tb}"
        else:
            detail = body

        if not self._should_send_alert(debounce_key, debounce_seconds):
            logger.info(
                "Skipping admin alert (debounced key=%s): %s", debounce_key, subject
            )
            return
        self.notify_admins(subject, detail)

    def clear_alert_debounce_for_tests(self) -> None:
        with self._debounce_lock:
            self._last_alert_at.clear()
