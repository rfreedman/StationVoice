from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app import notify_email


def _patch_bird(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    send = MagicMock(return_value=SimpleNamespace(id="msg_1", status="accepted"))
    client = MagicMock()
    client.email.send = send
    client.__enter__.return_value = client
    client.__exit__.return_value = False
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
