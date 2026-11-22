"""Default announcement text: built-in station call vs data-directory override."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import config as app_config
from app.admin_config import ConfigState
from app.default_announcement import (
    builtin_text,
    effective_text,
    has_override,
    override_path,
    save_text,
)
from tests.jsonutil import json_dict


def _state(client: TestClient) -> ConfigState:
    res = client.get("/api/admin/config")
    assert res.status_code == 200
    return ConfigState.model_validate(json_dict(res))


def _values(state: ConfigState) -> dict[str, object]:
    return state.current.values.model_dump()


def _save(
    client: TestClient,
    values: dict[str, object],
    short: str,
    *,
    default_announcement_text: str | None = None,
) -> ConfigState:
    body: dict[str, object] = {
        "values": values,
        "short_description": short,
        "long_description": "",
    }
    if default_announcement_text is not None:
        body["default_announcement_text"] = default_announcement_text
    res = client.post("/api/admin/config", json=body)
    assert res.status_code == 200, res.text
    return ConfigState.model_validate(json_dict(res))


def test_builtin_text_uses_station_call() -> None:
    assert builtin_text() == f"This is {app_config.STATION_CALL}"
    assert effective_text() == builtin_text()
    assert not has_override()


def test_override_file_wins() -> None:
    custom = "Net control, this is a test."
    save_text(custom)
    assert has_override()
    assert override_path().is_file()
    assert effective_text() == custom
    assert builtin_text() == f"This is {app_config.STATION_CALL}"


def test_save_matching_builtin_removes_override() -> None:
    save_text("Custom override script")
    assert has_override()
    save_text(builtin_text())
    assert not has_override()
    assert effective_text() == builtin_text()


def test_voices_payload_includes_default_announcement_text(client: TestClient) -> None:
    payload = json_dict(client.get("/api/voices"))
    assert payload["default_announcement_text"] == builtin_text()

    save_text("From the data directory")
    payload = json_dict(client.get("/api/voices"))
    assert payload["default_announcement_text"] == "From the data directory"


def test_admin_config_returns_and_saves_default_announcement(
    client: TestClient,
) -> None:
    state = _state(client)
    assert state.default_announcement_text == builtin_text()

    values = _values(state)
    custom = "Club net — please check in."
    saved = _save(client, values, "Set default script", default_announcement_text=custom)
    assert saved.default_announcement_text == custom
    assert has_override()
    assert override_path().read_text(encoding="utf-8") == custom

    restored = _save(
        client,
        values,
        "Back to builtin",
        default_announcement_text=f"This is {values['station_call']}",
    )
    assert restored.default_announcement_text == builtin_text()
    assert not has_override()


def test_admin_save_uses_new_call_for_builtin_compare(client: TestClient) -> None:
    state = _state(client)
    values = _values(state)
    values["station_call"] = "W1ABC"
    saved = _save(
        client,
        values,
        "New call and matching default",
        default_announcement_text="This is W1ABC",
    )
    assert saved.current.values.station_call == "W1ABC"
    assert saved.default_announcement_text == "This is W1ABC"
    assert not has_override()


def test_admin_rejects_oversized_default_announcement(client: TestClient) -> None:
    state = _state(client)
    values = _values(state)
    too_long = "x" * (app_config.MAX_TEXT_CHARS + 1)
    res = client.post(
        "/api/admin/config",
        json={
            "values": values,
            "short_description": "Too long",
            "default_announcement_text": too_long,
        },
    )
    assert res.status_code == 400
    assert not has_override()
