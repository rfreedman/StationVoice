"""Helpers to enable the Bird example notifier under a temp plugins dir."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

from app.config import ROOT_DIR

BIRD_EXAMPLE = ROOT_DIR / "plugin-examples" / "bird_email.py"


def install_bird_plugin(plugins_dir: Path) -> Path:
    """Copy the Bird example into ``plugins_dir``; return the destination path."""
    plugins_dir.mkdir(parents=True, exist_ok=True)
    dest = plugins_dir / "bird_email.py"
    _ = shutil.copy2(BIRD_EXAMPLE, dest)
    return dest


def install_stub_bird_env() -> None:
    """Env vars required by BirdEmailNotifier.validate_requirements_installed."""
    os.environ["BIRD_API_KEY"] = "bk_test"
    os.environ["EMAIL_FROM"] = "repeater@example.com"
    os.environ["ADMIN_EMAILS"] = "ops@example.com"


def install_stub_bird_sdk() -> ModuleType:
    """Put a minimal ``bird`` package in ``sys.modules`` so the example can load."""
    install_stub_bird_env()
    send = MagicMock(return_value=SimpleNamespace(id="msg_1", status="accepted"))
    client = MagicMock()
    setattr(client, "email", SimpleNamespace(send=send))
    enter = MagicMock(return_value=client)
    exit_ = MagicMock(return_value=False)
    setattr(client, "__enter__", enter)
    setattr(client, "__exit__", exit_)
    bird_cls = MagicMock(return_value=client)

    module = ModuleType("bird")
    setattr(module, "Bird", bird_cls)
    setattr(module, "APIError", Exception)
    setattr(module, "_test_send", send)
    sys.modules["bird"] = module
    return module
