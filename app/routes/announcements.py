"""Announcement library routes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.audio_announcement import (
    audio_path,
    delete_audio_file,
    looks_like_mp3,
    measure_audio_announcement,
)
from app.config import (
    AUDIO_ANNOUNCEMENT_MAX_BYTES,
    DEFAULT_BUSY_GIVE_UP_SECONDS,
    DEFAULT_BUSY_RETRY_SECONDS,
    REPEATER_TIMEOUT_SECONDS,
)
from app.deps import AdminUser, AuthUser
from app.live_notify import notify_home_data_changed
from app.model_common import new_id
from app.models import Announcement, AudioAnnouncement, validate_announcement
from app.pcm_cache import (
    get_pcm_cache,
    measure_announcement,
    warm_announcement,
    warm_announcement_in_background,
)
from app.scheduler import sync_jobs
from app.schemas import AnnouncementIn, AnnouncementsListOut
from app.store import AnnouncementStore, get_store

router = APIRouter()
log = logging.getLogger("app.routes.announcements")


def _warm_in_background(item: Announcement) -> None:
    if item.kind != "tts":
        return
    _ = warm_announcement_in_background(item, warm_announcement)


def _referenced(
    store: AnnouncementStore, announcement_id: str | None, *, role: str, previous: str | None
) -> None:
    if not announcement_id:
        return
    item = store.get(announcement_id)
    if item is None or item.kind != "tts":
        raise HTTPException(status_code=400, detail=f"{role} must be an existing spoken announcement")
    if item.too_long and announcement_id != previous:
        raise HTTPException(
            status_code=400,
            detail=f"{item.name} is too long for the repeater. Shorten it and save it again.",
        )


def _from_request(req: AnnouncementIn, existing: Announcement | None) -> Announcement:
    if req.kind == "audio":
        raise HTTPException(
            status_code=400,
            detail="Use the audio upload endpoints for MP3 announcements",
        )
    store = get_store()
    previous_opening = (
        existing.opening_announcement_id if existing is not None and existing.kind == "newsline" else None
    )
    previous_station = (
        existing.station_id_announcement_id
        if existing is not None and existing.kind == "newsline"
        else None
    )
    previous_closing = (
        existing.closing_announcement_id if existing is not None and existing.kind == "newsline" else None
    )
    previous_resume = (
        existing.resume_announcement_id if existing is not None and existing.kind == "newsline" else None
    )
    if req.kind == "newsline":
        _referenced(store, req.opening_announcement_id, role="Opening", previous=previous_opening)
        _referenced(store, req.station_id_announcement_id, role="Station ID", previous=previous_station)
        _referenced(store, req.closing_announcement_id, role="Closing", previous=previous_closing)
        _referenced(store, req.resume_announcement_id, role="Resume", previous=previous_resume)
        data: dict[str, object] = {
            "name": req.name,
            "kind": "newsline",
            "busy_retry_seconds": req.busy_retry_seconds,
            "busy_give_up_seconds": req.busy_give_up_seconds,
            "opening_announcement_id": req.opening_announcement_id,
            "station_id_announcement_id": req.station_id_announcement_id,
            "closing_announcement_id": req.closing_announcement_id,
            "resume_announcement_id": req.resume_announcement_id,
            "ptt_gap_seconds": req.ptt_gap_seconds,
        }
    else:
        data = {
            "name": req.name,
            "kind": "tts",
            "text": req.text,
            "voice": req.voice,
            "speed": req.speed,
            "sentence_pause": req.sentence_pause,
            "use_phoneme_dictionary": req.use_phoneme_dictionary,
            "busy_retry_seconds": req.busy_retry_seconds,
            "busy_give_up_seconds": req.busy_give_up_seconds,
        }
        if existing is not None and existing.kind == "tts":
            data["play_seconds"] = existing.play_seconds
            data["too_long"] = existing.too_long
    if existing is not None:
        data["id"] = existing.id
    try:
        item = validate_announcement(data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if item.kind != "tts":
        return item
    timeout = REPEATER_TIMEOUT_SECONDS
    try:
        measured = measure_announcement(item, timeout)
    except Exception as exc:
        from app.routes.speak import raise_engine_http

        raise_engine_http(exc, where="announcement timing")
    if measured.kind == "tts" and measured.too_long:
        log.warning(
            "Saved %s as too long (%.1fs)",
            measured.name,
            measured.play_seconds or 0,
        )
    return measured


async def _read_audio_upload(file: UploadFile) -> tuple[bytes, str]:
    data = await file.read(AUDIO_ANNOUNCEMENT_MAX_BYTES + 1)
    filename = Path(file.filename or "upload.mp3").name
    try:
        looks_like_mp3(data, filename=filename, content_type=file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return data, filename


def _format_play_clock(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes}:{secs:02d}"


def _reject_overlong_upload(play_seconds: float, limit: float) -> None:
    raise HTTPException(
        status_code=400,
        detail=(
            f"Audio is {_format_play_clock(play_seconds)}, over the "
            f"{_format_play_clock(limit)} limit. Use a shorter MP3."
        ),
    )


def _build_audio(
    *,
    announcement_id: str,
    name: str,
    busy_retry_seconds: float,
    busy_give_up_seconds: float,
    original_filename: str,
    existing: AudioAnnouncement | None,
    data: bytes | None,
) -> AudioAnnouncement:
    from app.spoken_length import speech_limit_seconds

    try:
        item = AudioAnnouncement(
            id=announcement_id,
            name=name,
            busy_retry_seconds=busy_retry_seconds,
            busy_give_up_seconds=busy_give_up_seconds,
            original_filename=original_filename,
            play_seconds=existing.play_seconds if existing is not None else None,
            too_long=existing.too_long if existing is not None else False,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    timeout = REPEATER_TIMEOUT_SECONDS
    limit = speech_limit_seconds(timeout)
    final_path = audio_path(announcement_id)

    if data is not None:
        # Stage the upload so a too-long or invalid file never replaces a good one.
        from app.audio_announcement import ensure_audio_dir

        _ = ensure_audio_dir()
        staging = final_path.with_suffix(".mp3.upload")
        _ = staging.write_bytes(data)
        try:
            measured = measure_audio_announcement(item, timeout, path=staging)
        except ValueError as exc:
            staging.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except OSError as exc:
            staging.unlink(missing_ok=True)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if measured.too_long:
            play = measured.play_seconds if measured.play_seconds is not None else 0.0
            staging.unlink(missing_ok=True)
            _reject_overlong_upload(play, limit)
        _ = staging.replace(final_path)
        return measured.model_copy(update={"too_long": False})

    if not final_path.is_file():
        raise HTTPException(status_code=400, detail="Audio file is missing; upload an MP3")
    try:
        return measure_audio_announcement(item, timeout, path=final_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/announcements")
def list_announcements(_user: AuthUser) -> AnnouncementsListOut:
    return AnnouncementsListOut(announcements=get_store().list_announcements())


@router.get("/api/announcements/{announcement_id}")
def get_announcement(announcement_id: str, _user: AuthUser) -> Announcement:
    item = get_store().get(announcement_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return item


@router.get("/api/announcements/{announcement_id}/audio")
def get_announcement_audio(announcement_id: str, _user: AuthUser) -> FileResponse:
    item = get_store().get(announcement_id)
    if item is None or item.kind != "audio":
        raise HTTPException(status_code=404, detail="Audio announcement not found")
    path = audio_path(announcement_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")
    filename = item.original_filename or f"{announcement_id}.mp3"
    return FileResponse(path, media_type="audio/mpeg", filename=filename)


@router.post("/api/announcements/audio")
async def create_audio_announcement(
    _admin: AdminUser,
    name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    busy_retry_seconds: Annotated[float, Form()] = DEFAULT_BUSY_RETRY_SECONDS,
    busy_give_up_seconds: Annotated[float, Form()] = DEFAULT_BUSY_GIVE_UP_SECONDS,
) -> Announcement:
    data, filename = await _read_audio_upload(file)
    announcement_id = new_id()
    item = _build_audio(
        announcement_id=announcement_id,
        name=name,
        busy_retry_seconds=busy_retry_seconds,
        busy_give_up_seconds=busy_give_up_seconds,
        original_filename=filename,
        existing=None,
        data=data,
    )
    stored = get_store().save_announcement(item)
    notify_home_data_changed()
    return stored


@router.put("/api/announcements/{announcement_id}/audio")
async def update_audio_announcement(
    announcement_id: str,
    _admin: AdminUser,
    name: Annotated[str, Form()],
    file: Annotated[UploadFile | None, File()] = None,
    busy_retry_seconds: Annotated[float, Form()] = DEFAULT_BUSY_RETRY_SECONDS,
    busy_give_up_seconds: Annotated[float, Form()] = DEFAULT_BUSY_GIVE_UP_SECONDS,
) -> Announcement:
    store = get_store()
    existing = store.get(announcement_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if existing.kind != "audio":
        raise HTTPException(status_code=400, detail="Announcement is not an audio file")
    data: bytes | None = None
    filename = existing.original_filename
    if file is not None and (file.filename or file.content_type or file.size):
        data, filename = await _read_audio_upload(file)
    item = _build_audio(
        announcement_id=announcement_id,
        name=name,
        busy_retry_seconds=busy_retry_seconds,
        busy_give_up_seconds=busy_give_up_seconds,
        original_filename=filename,
        existing=existing,
        data=data,
    )
    stored = store.save_announcement(item)
    sync_jobs()
    notify_home_data_changed()
    return stored


@router.post("/api/announcements")
def create_announcement(req: AnnouncementIn, _admin: AdminUser) -> Announcement:
    item = _from_request(req, None)
    stored = get_store().save_announcement(item)
    _warm_in_background(stored)
    notify_home_data_changed()
    return stored


@router.put("/api/announcements/{announcement_id}")
def update_announcement(
    announcement_id: str, req: AnnouncementIn, _admin: AdminUser
) -> Announcement:
    store = get_store()
    existing = store.get(announcement_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    updated = _from_request(req, existing)
    if existing.kind == "audio" and updated.kind != "audio":
        delete_audio_file(announcement_id)
    stored = store.save_announcement(updated)
    _warm_in_background(stored)
    sync_jobs()
    notify_home_data_changed()
    return stored


@router.delete("/api/announcements/{announcement_id}")
def delete_announcement(announcement_id: str, _admin: AdminUser) -> dict[str, bool]:
    existing = get_store().get(announcement_id)
    try:
        if not get_store().delete_announcement(announcement_id):
            raise HTTPException(status_code=404, detail="Announcement not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    get_pcm_cache().drop(announcement_id)
    if existing is not None and existing.kind == "audio":
        delete_audio_file(announcement_id)
    sync_jobs()
    notify_home_data_changed()
    return {"ok": True}
