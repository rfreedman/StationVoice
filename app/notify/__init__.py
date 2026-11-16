"""Admin notification plugins (drop-in under ``plugins/``)."""

from __future__ import annotations

from app.notify.base import AdminNotifier, NullAdminNotifier
from app.notify.loader import (
    admin_email_plugin_active,
    get_notifier,
    plugins_dir,
    reset_notifier_for_tests,
)

__all__ = [
    "AdminNotifier",
    "NullAdminNotifier",
    "admin_email_plugin_active",
    "get_notifier",
    "plugins_dir",
    "reset_notifier_for_tests",
]
