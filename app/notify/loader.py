"""Load a single AdminNotifier from ``plugins/*.py`` (drop-in activation)."""

from __future__ import annotations

import importlib.util
import inspect
import logging
import os
import sys
import threading
from pathlib import Path
from types import ModuleType

from app.config import ROOT_DIR
from app.notify.base import AdminNotifier, NullAdminNotifier

logger = logging.getLogger(__name__)

_PLUGIN_MODULE_PREFIX = "dvra_plugins."

_lock = threading.Lock()
_notifier: AdminNotifier | None = None


def plugins_dir() -> Path:
    """Directory scanned for drop-in notifier plugins (``TTS_PLUGINS_DIR`` or ``plugins/``)."""
    override = os.environ.get("TTS_PLUGINS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return ROOT_DIR / "plugins"


def reset_notifier_for_tests() -> None:
    """Drop the cached notifier so the next ``get_notifier`` rescans plugins."""
    global _notifier
    with _lock:
        _notifier = None
        stale = [name for name in sys.modules if name.startswith(_PLUGIN_MODULE_PREFIX)]
        for name in stale:
            _ = sys.modules.pop(name, None)


def get_notifier() -> AdminNotifier:
    """Return the process-wide notifier (lazy load from ``plugins/``).

    Raises ``StartupError`` if a plugin is present but fails
    ``validate_requirements_installed``.
    """
    global _notifier
    with _lock:
        if _notifier is None:
            _notifier = _load_notifier()
        return _notifier


def notify_startup_failure_if_ready(subject: str, body: str) -> None:
    """Email a startup failure only if a working plugin is already cached.

    Never calls ``get_notifier`` (that would re-run a failed plugin load).
    """
    with _lock:
        notifier = _notifier
    if notifier is None or isinstance(notifier, NullAdminNotifier):
        return
    notifier.notify_admins(subject, body)


def admin_email_plugin_active() -> bool:
    """True when a non-null admin notifier plugin is loaded."""
    return not isinstance(get_notifier(), NullAdminNotifier)


def _load_notifier() -> AdminNotifier:
    directory = plugins_dir()
    if not directory.is_dir():
        logger.info("No plugins directory at %s; admin email notify disabled", directory)
        return NullAdminNotifier()

    found: list[tuple[Path, type[AdminNotifier]]] = []
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module = _import_plugin_file(path)
        if module is None:
            continue
        for cls in _notifier_classes(module):
            found.append((path, cls))

    if not found:
        logger.info("No AdminNotifier plugin in %s; admin email notify disabled", directory)
        return NullAdminNotifier()

    if len(found) > 1:
        names = ", ".join(f"{path.name}:{cls.__name__}" for path, cls in found)
        message = (
            f"Multiple AdminNotifier plugins found ({names}); "
            "using null notifier (keep only one admin-notifier plugin)"
        )
        logger.error("%s", message)
        return NullAdminNotifier()

    path, cls = found[0]
    try:
        instance = cls()
    except Exception:
        logger.exception("Failed to construct AdminNotifier %s from %s", cls.__name__, path)
        return NullAdminNotifier()

    try:
        instance.validate_requirements_installed()
    except Exception as exc:
        from app.startup_errors import StartupError

        detail = str(exc).strip() or exc.__class__.__name__
        message = (
            f"Admin notify plugin {path.name} ({cls.__name__}) cannot start: {detail}"
        )
        # Single operator-facing message comes from fail_startup; do not log here.
        raise StartupError(message) from None

    logger.info("Loaded admin notifier plugin %s from %s", cls.__name__, path)
    return instance


def _import_plugin_file(path: Path) -> ModuleType | None:
    module_name = f"{_PLUGIN_MODULE_PREFIX}{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            logger.error("Could not load plugin spec for %s", path)
            return None
        module = importlib.util.module_from_spec(spec)
        # Make relative imports and reloads behave; allow tests to patch the module.
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        logger.exception("Failed to import admin notify plugin %s", path)
        _ = sys.modules.pop(module_name, None)
        return None


def _notifier_classes(module: ModuleType) -> list[type[AdminNotifier]]:
    classes: list[type[AdminNotifier]] = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj is AdminNotifier or obj is NullAdminNotifier:
            continue
        if not issubclass(obj, AdminNotifier):
            continue
        if inspect.isabstract(obj):
            continue
        if obj.__module__ != module.__name__:
            continue
        classes.append(obj)
    return classes
