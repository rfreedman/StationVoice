"""Base admin notifier: no-op delivery. Plugins override to send alerts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import override


class AdminNotifier(ABC):
    """Deliver admin notifications. Core logging stays in the facade."""

    @abstractmethod
    def validate_requirements_installed(self) -> None:
        """Raise if this plugin cannot run (e.g. missing third-party packages).

        The plugin decides what to check; the loader only calls this hook and
        treats any exception as a fatal startup error.
        """

    def send_email(self, subject: str, body: str, recipients: Sequence[str]) -> None:
        """Send email to explicit recipients. Never raises."""
        _ = (subject, body, recipients)

    def notify_admins(self, subject: str, body: str) -> None:
        """Notify configured admin recipients. Never raises."""
        _ = (subject, body)

    def notify_admins_lifecycle(self, subject: str, body: str) -> None:
        """Start/stop notices (quiet when unconfigured). Never raises."""
        _ = (subject, body)

    def alert_admins(
        self,
        subject: str,
        body: str,
        *,
        exc: BaseException | None = None,
        key: str | None = None,
        debounce_seconds: float = 15 * 60,
    ) -> None:
        """Deliver an operational alert (facade already logged). Never raises."""
        _ = (subject, body, exc, key, debounce_seconds)

    def clear_alert_debounce_for_tests(self) -> None:
        """Reset debounce state (tests only)."""


class NullAdminNotifier(AdminNotifier):
    """Default when no admin-notifier plugin is present under ``plugins/``."""

    @override
    def validate_requirements_installed(self) -> None:
        """Null notifier has no third-party requirements."""
