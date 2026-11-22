"""Admin-only environment history and logo / favicon uploads."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ValidationError

from app.admin_config import (
    ConfigState,
    RuntimeConfigValues,
    apply_admin_email_notifications,
    bump_config_generation,
    clean_long,
    clean_short,
    config_state,
    ensure_history,
    revert_config,
    save_config,
)
from app.branding import (
    MAX_BRANDING_BYTES,
    clear_favicon,
    clear_logo,
    resolve_favicon,
    resolve_logo,
    save_favicon,
    save_logo,
    save_logo_display,
)
from app.deps import AdminUser
from app.notify_email import admin_email_plugin_active
from app.process_restart import (
    RestartBusyError,
    RestartUnavailableError,
    prepare_restart,
    schedule_systemd_restart,
)

router = APIRouter()
log = logging.getLogger(__name__)

_CACHE = {"Cache-Control": "no-cache"}


class ConfigSaveIn(BaseModel):
    values: RuntimeConfigValues
    short_description: str = ""
    long_description: str = ""
    admin_emails: str = ""
    admin_email_notifications: bool | None = None
    # Companion to config (like admin_emails); not stored in history. None = leave as-is.
    default_announcement_text: str | None = None


class ConfigRevertIn(BaseModel):
    id: str


class BrandingResult(BaseModel):
    ok: bool
    generation: int


class LogoDisplayIn(BaseModel):
    width: int
    height: int


class EmailNotificationsIn(BaseModel):
    enabled: bool


class EmailNotificationsOut(BaseModel):
    enabled: bool
    admin_email_plugin: bool


class RestartOut(BaseModel):
    ok: bool
    detail: str


def _validation_detail(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Invalid configuration"
    message = errors[0].get("msg", "Invalid configuration")
    text = str(message)
    prefix = "Value error, "
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


@router.get("/api/admin/config")
def get_admin_config(_admin: AdminUser) -> ConfigState:
    return config_state(ensure_history(), changed=False)


@router.post("/api/admin/config")
def post_admin_config(body: ConfigSaveIn, _admin: AdminUser) -> ConfigState:
    from app.config import enforce_text_limit
    from app.default_announcement import save_text as save_default_announcement_text

    try:
        short = clean_short(body.short_description)
        long = clean_long(body.long_description)
        # Validate before applying config so a too-long script does not leave a partial save.
        if body.default_announcement_text is not None:
            _ = enforce_text_limit(body.default_announcement_text.strip())
        document = save_config(
            body.values,
            short,
            long,
            admin_emails=body.admin_emails,
            admin_email_notifications=body.admin_email_notifications,
        )
        # After apply so builtin compares against the new STATION_CALL when both change.
        if body.default_announcement_text is not None:
            save_default_announcement_text(body.default_announcement_text)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=_validation_detail(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return config_state(document, changed=True)


@router.put("/api/admin/email-notifications")
def put_email_notifications(
    body: EmailNotificationsIn, _admin: AdminUser
) -> EmailNotificationsOut:
    plugin = admin_email_plugin_active()
    if not plugin:
        raise HTTPException(
            status_code=400,
            detail="Email notifications require an admin email plugin under plugins/",
        )
    enabled = apply_admin_email_notifications(body.enabled)
    return EmailNotificationsOut(enabled=enabled, admin_email_plugin=True)


@router.post("/api/admin/restart")
def post_admin_restart(admin: AdminUser) -> JSONResponse:
    try:
        prepare_restart()
        schedule_systemd_restart()
    except RestartBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RestartUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    log.info("Admin %s requested application restart", admin.username)
    body = RestartOut(ok=True, detail="Restart scheduled")
    return JSONResponse(status_code=202, content=body.model_dump())


@router.post("/api/admin/config/revert")
def post_admin_revert(body: ConfigRevertIn, _admin: AdminUser) -> ConfigState:
    try:
        document, changed = revert_config(body.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Saved configuration not found") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=_validation_detail(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return config_state(document, changed=changed)


@router.get("/branding/logo")
def get_logo() -> FileResponse:
    path, media = resolve_logo()
    return FileResponse(path, media_type=media, headers=_CACHE)


@router.get("/branding/favicon")
def get_favicon() -> FileResponse:
    path, media = resolve_favicon()
    return FileResponse(path, media_type=media, headers=_CACHE)


@router.post("/api/admin/branding/display")
def post_logo_display(body: LogoDisplayIn, _admin: AdminUser) -> BrandingResult:
    try:
        _ = save_logo_display(body.width, body.height)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=_validation_detail(exc)) from exc
    return BrandingResult(ok=True, generation=bump_config_generation())


@router.post("/api/admin/branding/logo")
async def upload_logo(
    _admin: AdminUser,
    file: Annotated[UploadFile, File()],
    also_favicon: Annotated[str, Form()] = "true",
) -> BrandingResult:
    data = await _read_upload(file)
    try:
        save_logo(data, also_favicon=_form_flag(also_favicon))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BrandingResult(ok=True, generation=bump_config_generation())


@router.post("/api/admin/branding/favicon")
async def upload_favicon(
    _admin: AdminUser,
    file: Annotated[UploadFile, File()],
) -> BrandingResult:
    data = await _read_upload(file)
    try:
        save_favicon(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BrandingResult(ok=True, generation=bump_config_generation())


@router.delete("/api/admin/branding/logo")
def delete_logo(_admin: AdminUser) -> BrandingResult:
    clear_logo()
    return BrandingResult(ok=True, generation=bump_config_generation())


@router.delete("/api/admin/branding/favicon")
def delete_favicon(_admin: AdminUser) -> BrandingResult:
    clear_favicon()
    return BrandingResult(ok=True, generation=bump_config_generation())


def _form_flag(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(MAX_BRANDING_BYTES + 1)
    if len(data) > MAX_BRANDING_BYTES:
        raise HTTPException(status_code=400, detail="File is larger than 2 MB")
    return data
