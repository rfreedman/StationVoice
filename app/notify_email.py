"""Admin notify facade: log alerts, delegate delivery to a drop-in plugin."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

from app.notify.loader import (
    admin_email_plugin_active,
    get_notifier,
    notify_startup_failure_if_ready,
    reset_notifier_for_tests,
)

logger = logging.getLogger(__name__)

DEFAULT_ALERT_DEBOUNCE_SECONDS = 15 * 60

__all__ = [
    "DEFAULT_ALERT_DEBOUNCE_SECONDS",
    "admin_email_notifications_enabled",
    "admin_email_plugin_active",
    "alert_admins",
    "clear_alert_debounce_for_tests",
    "get_notifier",
    "notify_admins",
    "notify_admins_lifecycle",
    "notify_startup_failure_if_ready",
    "reset_notifier_for_tests",
    "send_email",
]


def admin_email_notifications_enabled() -> bool:
    """True when a plugin is loaded and the operator mute is not engaged."""
    raw = os.environ.get("ADMIN_EMAIL_NOTIFICATIONS", "1").strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return False
    return admin_email_plugin_active()


def send_email(subject: str, body: str, recipients: Sequence[str]) -> None:
    """Send email to the given addresses. Never raises."""
    get_notifier().send_email(subject, body, recipients)


def notify_admins(subject: str, body: str) -> None:
    """Send email to ADMIN_EMAILS when an email plugin is active. Never raises."""
    if not admin_email_notifications_enabled():
        return
    get_notifier().notify_admins(subject, body)


def notify_admins_lifecycle(subject: str, body: str) -> None:
    """Start/stop notices via the active plugin. Never raises."""
    if not admin_email_notifications_enabled():
        return
    get_notifier().notify_admins_lifecycle(subject, body)


def alert_admins(
    subject: str,
    body: str,
    *,
    exc: BaseException | None = None,
    key: str | None = None,
    debounce_seconds: float = DEFAULT_ALERT_DEBOUNCE_SECONDS,
) -> None:
    """Log an operational error, then ask the plugin to deliver (debounced). Never raises."""
    if exc is not None:
        logger.error("%s", body, exc_info=exc)
    else:
        logger.error("%s", body)
    if not admin_email_notifications_enabled():
        return
    get_notifier().alert_admins(
        subject,
        body,
        exc=exc,
        key=key,
        debounce_seconds=debounce_seconds,
    )


def clear_alert_debounce_for_tests() -> None:
    """Reset debounce state on the active notifier (tests only)."""
    get_notifier().clear_alert_debounce_for_tests()
