"""Shared FastAPI dependencies for authenticated routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth import require_admin, require_editor, require_user
from app.users import User

AdminUser = Annotated[User, Depends(require_admin)]
EditorUser = Annotated[User, Depends(require_editor)]
AuthUser = Annotated[User, Depends(require_user)]
