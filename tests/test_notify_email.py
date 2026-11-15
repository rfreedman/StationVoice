from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app import notify_email


def _patch_bird(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    send = MagicMock(return_value=SimpleNamespace(id="msg_1", status="accepted"))
    client = MagicMock()
    setattr(client, "email", SimpleNamespace(send=send))
    enter = MagicMock(return_value=client)
    exit_ = MagicMock(return_value=False)
    setattr(client, "__enter__", enter)
    setattr(client, "__exit__", exit_)
    bird_cls = MagicMock(return_value=client)
    monkeypatch.setattr(notify_email, "Bird", bird_cls)
    return send


def test_send_email_passes_recipients(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIRD_API_KEY", "bk_test")
    monkeypatch.setenv("EMAIL_FROM", "repeater@example.com")
    monkeypatch.setenv("EMAIL_FROM_NAME", "Test Station")
    send = _patch_bird(monkeypatch)

    notify_email.send_email(
        "Subject",
        "Body line",
        [" a@example.com ", "", "b@example.com"],
    )

    send.assert_called_once()
    kwargs = send.call_args.kwargs
    assert kwargs["to"] == ["a@example.com", "b@example.com"]
    assert kwargs["subject"] == "Subject"
    assert kwargs["text"] == "Body line"
    assert kwargs["from_"] == {"email": "repeater@example.com", "name": "Test Station"}


def test_notify_admins_uses_admin_emails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIRD_API_KEY", "bk_test")
    monkeypatch.setenv("EMAIL_FROM", "repeater@example.com")
    monkeypatch.setenv("ADMIN_EMAILS", "one@example.com, two@example.com,")
    send = _patch_bird(monkeypatch)

    notify_email.notify_admins("Admin subject", "Admin body")

    send.assert_called_once()
    assert send.call_args.kwargs["to"] == ["one@example.com", "two@example.com"]
    assert send.call_args.kwargs["subject"] == "Admin subject"


def test_notify_admins_skips_when_admin_emails_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIRD_API_KEY", "bk_test")
    monkeypatch.setenv("EMAIL_FROM", "repeater@example.com")
    monkeypatch.setenv("ADMIN_EMAILS", " , ")
    send = _patch_bird(monkeypatch)

    notify_email.notify_admins("Nope", "Nope")

    send.assert_not_called()


def test_send_email_skips_when_no_recipients(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIRD_API_KEY", "bk_test")
    monkeypatch.setenv("EMAIL_FROM", "repeater@example.com")
    send = _patch_bird(monkeypatch)

    notify_email.send_email("Subject", "Body", ["  ", ""])

    send.assert_not_called()


@pytest.fixture(autouse=True)
def _clear_alert_debounce() -> None:
    notify_email.clear_alert_debounce_for_tests()


def test_notify_admins_lifecycle_skips_quietly_without_recipients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIRD_API_KEY", "bk_test")
    monkeypatch.setenv("EMAIL_FROM", "repeater@example.com")
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    send = _patch_bird(monkeypatch)

    notify_email.notify_admins_lifecycle("Started", "ready")

    send.assert_not_called()


def test_notify_admins_lifecycle_sends_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIRD_API_KEY", "bk_test")
    monkeypatch.setenv("EMAIL_FROM", "repeater@example.com")
    monkeypatch.setenv("ADMIN_EMAILS", "ops@example.com")
    send = _patch_bird(monkeypatch)

    notify_email.notify_admins_lifecycle("Started", "ready")

    send.assert_called_once()
    assert send.call_args.kwargs["subject"] == "Started"
    assert send.call_args.kwargs["text"] == "ready"


def test_alert_admins_notifies_and_includes_exc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIRD_API_KEY", "bk_test")
    monkeypatch.setenv("EMAIL_FROM", "repeater@example.com")
    monkeypatch.setenv("ADMIN_EMAILS", "ops@example.com")
    send = _patch_bird(monkeypatch)

    notify_email.alert_admins(
        "Boom",
        "Something broke",
        exc=RuntimeError("nope"),
        key="test-boom",
    )

    send.assert_called_once()
    assert send.call_args.kwargs["subject"] == "Boom"
    assert "Something broke" in send.call_args.kwargs["text"]
    assert "RuntimeError: nope" in send.call_args.kwargs["text"]


def test_alert_admins_debounces_same_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIRD_API_KEY", "bk_test")
    monkeypatch.setenv("EMAIL_FROM", "repeater@example.com")
    monkeypatch.setenv("ADMIN_EMAILS", "ops@example.com")
    send = _patch_bird(monkeypatch)

    notify_email.alert_admins("One", "first", key="same")
    notify_email.alert_admins("Two", "second", key="same")

    send.assert_called_once()
    assert send.call_args.kwargs["subject"] == "One"


def test_alert_admins_debounce_seconds_zero_always_sends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIRD_API_KEY", "bk_test")
    monkeypatch.setenv("EMAIL_FROM", "repeater@example.com")
    monkeypatch.setenv("ADMIN_EMAILS", "ops@example.com")
    send = _patch_bird(monkeypatch)

    notify_email.alert_admins("A", "a", key="startup", debounce_seconds=0)
    notify_email.alert_admins("B", "b", key="startup", debounce_seconds=0)

    assert send.call_count == 2
