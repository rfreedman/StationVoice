#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Refresh the installed project so a version bump in pyproject.toml shows in the UI.
# --frozen does not rewrite uv.lock (a Linux-host rewrite blocks the next deploy).
# --no-dev keeps test packages off production; --inexact leaves them alone on a dev machine.
if command -v uv >/dev/null 2>&1; then
  uv sync --frozen --inexact --no-dev
fi
# Use the venv interpreter directly (avoids activate scripts with stale absolute paths
# after a home-directory rename). Recreate .venv if this binary is missing/broken.
PYTHON="$(pwd)/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Missing or broken $PYTHON" >&2
  echo "Recreate the venv from the project root:" >&2
  echo "  rm -rf .venv && uv sync --frozen --inexact --no-dev" >&2
  exit 1
fi
exec "$PYTHON" -m app serve
