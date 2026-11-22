from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest

from app import notify_email
from app.notify.base import NullAdminNotifier
from app.startup_errors import StartupError
from tests.notify_plugin_util import (
    install_bird_plugin,
    install_stub_bird_env,
    install_stub_bird_sdk,
)


@pytest.fixture(autouse=True)
def _reset_notifier() -> Iterator[None]:
    notify_email.reset_notifier_for_tests()
    yield
    notify_email.reset_notifier_for_tests()


def test_empty_plugins_dir_uses_null_notifier(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PLUGINS_DIR", str(tmp_path))
    notify_email.reset_notifier_for_tests()

    notifier = notify_email.get_notifier()
    assert isinstance(notifier, NullAdminNotifier)
    assert notify_email.admin_email_plugin_active() is False
    notify_email.notify_admins("Subject", "Body")
    notify_email.alert_admins("Alert", "detail")


def test_broken_plugin_file_falls_back_to_null(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bad = tmp_path / "broken.py"
    _ = bad.write_text("this is not valid python {\n", encoding="utf-8")
    monkeypatch.setenv("PLUGINS_DIR", str(tmp_path))
    notify_email.reset_notifier_for_tests()

    assert isinstance(notify_email.get_notifier(), NullAdminNotifier)
    assert notify_email.admin_email_plugin_active() is False


def test_multiple_notifier_plugins_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plugin_a = tmp_path / "a_notify.py"
    plugin_b = tmp_path / "b_notify.py"
    source = """
from app.notify.base import AdminNotifier

class ExtraNotifier(AdminNotifier):
    def validate_requirements_installed(self):
        pass
"""
    _ = plugin_a.write_text(source, encoding="utf-8")
    _ = plugin_b.write_text(source, encoding="utf-8")
    monkeypatch.setenv("PLUGINS_DIR", str(tmp_path))
    notify_email.reset_notifier_for_tests()

    assert isinstance(notify_email.get_notifier(), NullAdminNotifier)


def test_custom_plugin_is_loaded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plugin = tmp_path / "spy_email.py"
    _ = plugin.write_text(
        """
from app.notify.base import AdminNotifier

class SpyNotifier(AdminNotifier):
    def __init__(self):
        self.subjects = []

    def validate_requirements_installed(self):
        pass

    def notify_admins(self, subject, body):
        self.subjects.append(subject)
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PLUGINS_DIR", str(tmp_path))
    notify_email.reset_notifier_for_tests()

    notifier = notify_email.get_notifier()
    assert type(notifier).__name__ == "SpyNotifier"
    assert notify_email.admin_email_plugin_active() is True
    notify_email.notify_admins("Hello", "there")
    subjects = cast(list[str], getattr(notifier, "subjects"))
    assert subjects == ["Hello"]


def test_repo_plugins_dir_empty_means_null_notifier(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Live ``plugins/`` may contain a developer copy; tests use an empty stand-in."""
    monkeypatch.setenv("PLUGINS_DIR", str(tmp_path))
    notify_email.reset_notifier_for_tests()
    notifier = notify_email.get_notifier()
    assert isinstance(notifier, NullAdminNotifier)
    assert notify_email.admin_email_plugin_active() is False


def test_bird_example_activates_when_copied_into_plugins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _ = install_stub_bird_sdk()
    _ = install_bird_plugin(tmp_path)
    monkeypatch.setenv("PLUGINS_DIR", str(tmp_path))
    notify_email.reset_notifier_for_tests()

    notifier = notify_email.get_notifier()
    assert type(notifier).__name__ == "BirdEmailNotifier"
    assert notify_email.admin_email_plugin_active() is True


def test_bird_plugin_missing_sdk_fails_startup_load(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _ = sys.modules.pop("bird", None)
    install_stub_bird_env()
    _ = install_bird_plugin(tmp_path)
    monkeypatch.setenv("PLUGINS_DIR", str(tmp_path))
    notify_email.reset_notifier_for_tests()

    with pytest.raises(StartupError, match="messagebird-sdk"):
        _ = notify_email.get_notifier()


def test_bird_plugin_missing_env_fails_startup_load(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _ = install_stub_bird_sdk()
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    monkeypatch.delenv("BIRD_API_KEY", raising=False)
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    _ = install_bird_plugin(tmp_path)
    monkeypatch.setenv("PLUGINS_DIR", str(tmp_path))
    notify_email.reset_notifier_for_tests()

    with pytest.raises(StartupError, match="Bird email not configured"):
        _ = notify_email.get_notifier()
