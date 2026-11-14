"""Send email via Bird. Soft-fail: log errors, never raise to callers."""

from __future__ import annotations

import html
import logging
import os
from collections.abc import Sequence

from bird import APIError, Bird

logger = logging.getLogger(__name__)

DEFAULT_FROM_NAME = "Repeater Announcements"


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
