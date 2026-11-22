"""Audio-file library announcements (MP3 upload, length gate, fire chunks)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.audio import PcmChunk
from app.config import AUDIO_ANNOUNCEMENT_MAX_BYTES
from app.models import AudioAnnouncement, validate_announcement
from app.pcm_cache import chunks_for_announcement
from app.spoken_length import blocks_playback, recompute_too_long
from app.store import AnnouncementStore
from tests.jsonutil import json_dict


@pytest.fixture(autouse=True)
def audio_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "announcement_audio"
    root.mkdir()
    monkeypatch.setattr("app.audio_announcement.ANNOUNCEMENT_AUDIO_DIR", root)
    monkeypatch.setattr("app.config.ANNOUNCEMENT_AUDIO_DIR", root)
    return root


def _mp3_bytes() -> bytes:
    # Minimal ID3-prefixed payload; probe/decode are mocked in API tests.
    return b"ID3" + b"\x00" * 64 + b"\xff\xfb" + b"\x00" * 128


def test_audio_announcement_model_roundtrip() -> None:
    item = validate_announcement(
        {
            "name": "Net open",
            "kind": "audio",
            "original_filename": "net.mp3",
            "play_seconds": 12.5,
            "too_long": False,
        }
    )
    assert item.kind == "audio"
    assert item.original_filename == "net.mp3"
    assert item.play_seconds == 12.5


def test_recompute_too_long_and_blocks_playback_for_audio(
    store: AnnouncementStore,
) -> None:
    item = store.save_announcement(
        validate_announcement(
            {
                "name": "Clip",
                "kind": "audio",
                "original_filename": "clip.mp3",
                "play_seconds": 50.0,
                "too_long": False,
            }
        )
    )
    assert item.kind == "audio"
    updated = recompute_too_long(item, timeout_seconds=30)
    assert updated.kind == "audio"
    assert updated.too_long is True
    stored = store.save_announcement(updated)
    assert blocks_playback(store.document(), stored) is True


def test_chunks_for_announcement_dispatches_audio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = validate_announcement(
        {"name": "Clip", "kind": "audio", "original_filename": "clip.mp3"}
    )
    expected = [PcmChunk(pcm_int16=b"\x00\x01" * 100, sample_rate=22050)]

    def fake_chunks(announcement: object) -> list[PcmChunk]:
        assert announcement is item
        return expected

    monkeypatch.setattr(
        "app.audio_announcement.chunks_for_audio_announcement", fake_chunks
    )
    assert chunks_for_announcement(item) is expected


def test_create_audio_announcement_rejects_non_mp3(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:

    def boom(*_args: object, **_kwargs: object) -> float:
        raise AssertionError("probe should not run")

    monkeypatch.setattr("app.routes.announcements.measure_audio_announcement", boom)
    res = client.post(
        "/api/announcements/audio",
        data={"name": "Bad"},
        files={"file": ("clip.wav", b"RIFF" + b"\x00" * 40, "audio/wav")},
    )
    assert res.status_code == 400
    detail = json_dict(res)["detail"]
    assert isinstance(detail, str)
    assert "MP3" in detail


def test_create_audio_announcement_rejects_wrong_ffprobe_format(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, audio_dir: Path
) -> None:

    def measure(
        announcement: AudioAnnouncement, timeout_seconds: int, *, path: Path | None = None
    ) -> AudioAnnouncement:
        _ = announcement, timeout_seconds, path
        raise ValueError("Only MP3 files are allowed")

    monkeypatch.setattr("app.routes.announcements.measure_audio_announcement", measure)

    res = client.post(
        "/api/announcements/audio",
        data={"name": "Renamed"},
        files={"file": ("clip.mp3", _mp3_bytes(), "audio/mpeg")},
    )
    assert res.status_code == 400
    assert "MP3" in str(json_dict(res)["detail"])
    assert list(audio_dir.glob("*.mp3")) == []


def test_create_and_get_and_delete_audio_announcement(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, audio_dir: Path, store: AnnouncementStore
) -> None:

    def measure(
        announcement: AudioAnnouncement, timeout_seconds: int, *, path: Path | None = None
    ) -> AudioAnnouncement:
        _ = timeout_seconds
        assert path is not None and path.is_file()
        return announcement.model_copy(update={"play_seconds": 12.0, "too_long": False})

    monkeypatch.setattr("app.routes.announcements.measure_audio_announcement", measure)

    created = json_dict(
        client.post(
            "/api/announcements/audio",
            data={
                "name": "Net tone",
                "busy_retry_seconds": "5",
                "busy_give_up_seconds": "45",
            },
            files={"file": ("tone.mp3", _mp3_bytes(), "audio/mpeg")},
        )
    )
    assert created["kind"] == "audio"
    assert created["original_filename"] == "tone.mp3"
    assert created["play_seconds"] == 12.0
    announcement_id = created["id"]
    assert isinstance(announcement_id, str)
    assert (audio_dir / f"{announcement_id}.mp3").is_file()

    audio = client.get(f"/api/announcements/{announcement_id}/audio")
    assert audio.status_code == 200
    assert audio.headers["content-type"].startswith("audio/mpeg")
    assert audio.content.startswith(b"ID3")

    deleted = json_dict(client.delete(f"/api/announcements/{announcement_id}"))
    assert deleted["ok"] is True
    assert store.get(announcement_id) is None
    assert not (audio_dir / f"{announcement_id}.mp3").exists()


def test_too_long_upload_is_rejected_and_not_saved(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    audio_dir: Path,
    store: AnnouncementStore,
) -> None:

    def measure(
        announcement: AudioAnnouncement, timeout_seconds: int, *, path: Path | None = None
    ) -> AudioAnnouncement:
        assert path is not None and path.is_file()
        return announcement.model_copy(
            update={"play_seconds": float(timeout_seconds), "too_long": True}
        )

    monkeypatch.setattr("app.routes.announcements.measure_audio_announcement", measure)
    res = client.post(
        "/api/announcements/audio",
        data={"name": "Long"},
        files={"file": ("long.mp3", _mp3_bytes(), "audio/mpeg")},
    )
    assert res.status_code == 400
    detail = str(json_dict(res)["detail"])
    assert "over the" in detail.lower()
    assert ":" in detail  # m:ss clocks, not raw seconds alone
    assert list(audio_dir.glob("*.mp3")) == []
    assert list(audio_dir.glob("*.upload")) == []
    assert store.list_announcements() == []


def test_too_long_replacement_keeps_existing_file(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    audio_dir: Path,
    store: AnnouncementStore,
) -> None:
    good = _mp3_bytes()

    def measure_ok(
        announcement: AudioAnnouncement, timeout_seconds: int, *, path: Path | None = None
    ) -> AudioAnnouncement:
        _ = timeout_seconds
        assert path is not None and path.is_file()
        return announcement.model_copy(update={"play_seconds": 12.0, "too_long": False})

    monkeypatch.setattr("app.routes.announcements.measure_audio_announcement", measure_ok)
    created = json_dict(
        client.post(
            "/api/announcements/audio",
            data={"name": "Keep me"},
            files={"file": ("ok.mp3", good, "audio/mpeg")},
        )
    )
    announcement_id = created["id"]
    assert isinstance(announcement_id, str)
    stored_path = audio_dir / f"{announcement_id}.mp3"
    assert stored_path.read_bytes() == good

    def measure_long(
        announcement: AudioAnnouncement, timeout_seconds: int, *, path: Path | None = None
    ) -> AudioAnnouncement:
        assert path is not None and path.is_file()
        return announcement.model_copy(
            update={"play_seconds": float(timeout_seconds), "too_long": True}
        )

    monkeypatch.setattr("app.routes.announcements.measure_audio_announcement", measure_long)
    res = client.put(
        f"/api/announcements/{announcement_id}/audio",
        data={"name": "Keep me"},
        files={"file": ("long.mp3", b"ID3" + b"\x01" * 80, "audio/mpeg")},
    )
    assert res.status_code == 400
    assert "over the" in str(json_dict(res)["detail"]).lower()
    assert stored_path.read_bytes() == good
    assert store.get(announcement_id) is not None
    assert list(audio_dir.glob("*.upload")) == []


def test_json_create_rejects_audio_kind(client: TestClient) -> None:
    res = client.post(
        "/api/announcements",
        json={"name": "Nope", "kind": "audio", "original_filename": "x.mp3"},
    )
    assert res.status_code == 400
    assert "upload" in str(json_dict(res)["detail"]).lower()


def test_create_rejects_oversize(client: TestClient) -> None:
    big = b"ID3" + b"\x00" * (AUDIO_ANNOUNCEMENT_MAX_BYTES + 10)
    res = client.post(
        "/api/announcements/audio",
        data={"name": "Huge"},
        files={"file": ("huge.mp3", big, "audio/mpeg")},
    )
    assert res.status_code == 400
    assert "larger" in str(json_dict(res)["detail"]).lower()


def test_voices_payload_includes_audio_max_bytes(client: TestClient) -> None:
    payload = json_dict(client.get("/api/voices"))
    assert payload["audio_announcement_max_bytes"] == AUDIO_ANNOUNCEMENT_MAX_BYTES


def test_probe_mp3_requires_format_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    from app import audio_announcement as mod

    path = tmp_path / "clip.mp3"
    _ = path.write_bytes(_mp3_bytes())

    class Result:
        returncode: int = 0
        stdout: str = "wav\n1.5\n"
        stderr: str = ""

    def fake_run(
        *_args: object, **_kwargs: object
    ) -> Result:
        return Result()

    monkeypatch.setattr(mod, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ValueError, match="Only MP3"):
        _ = mod.probe_mp3(path)
