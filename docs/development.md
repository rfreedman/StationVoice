# Development

This document describes the development workflow for StationVoice: the
environment, running locally, tests and static analysis, CI, dependency and
version management, and contributing.

## Development environment

StationVoice requires Python 3.12 or later and uses `uv` to manage
dependencies.

Install dependencies:

```bash
uv sync
```

Run commands with `uv run`, or activate the virtual environment:

```bash
source .venv/bin/activate
```

## Running locally

Start the application:

```bash
python -m app serve
```

Use the stub radio backend when developing without radio hardware. See
[Radio backend](radio-backend.md). On Linux without a Pulse/PipeWire session,
see [Stub backend on headless Linux](radio-backend.md#stub-backend-on-headless-linux).

## Tests and static analysis

Run the test suite:

```bash
uv run pytest -q
```

Run static type analysis:

```bash
uv run basedpyright
```

basedpyright covers `app/` and `tests/` with no baseline, so any new
diagnostic fails the check. Warnings fail CI the same as errors. Fix the
types (or a scoped `# pyright: ignore[rule]` only at a real FFI edge); do
not add a baseline file or weaken the configuration to silence diagnostics.

The test suite sets `SKIP_DOTENV=1` (in `tests/conftest.py`) so a local
`.env` file does not affect test results. Run the full suite before
finishing; it must pass with and without a `.env`.

### End-to-end (browser) tests

Browser tests for the manual-trigger countdown are opt-in locally:

```bash
uv run playwright install chromium   # once
uv run pytest -m e2e
```

On GitHub, run the **E2E** workflow manually from the Actions tab.

## CI

Pushes and pull requests to `main` run the same default suite plus
basedpyright in GitHub Actions (see the **Test** workflow; you can also
re-run it manually from the Actions tab). Before submitting changes, run
the applicable checks locally.

To catch Linux-only test paths before push (macOS dev machines skip some
ALSA/PortAudio code), run `./scripts/ci-local.sh` (Docker + Ubuntu 24.04).
It uses a temporary venv inside the container and does not change your Mac
`.venv`.

Hardware-dependent behavior should be tested on the target platform when
practical.

## Dependencies

Dependencies are managed through `pyproject.toml` and `uv.lock`.

Use `uv add` and `uv remove` to manage dependencies, and commit both files
when dependency changes are intended. Avoid manually installing packages
into the project environment with `pip`.

The Linux host deploys use the committed lock: `./serve.sh` runs
`uv sync --frozen --inexact --no-dev` before starting. See
[Operations and deployment](operations.md) for the deploy workflow and the
pinned `requirements.txt` fallback.

## Versioning

The version is written once, in `pyproject.toml`. The app reads it from the
installed package (`importlib.metadata`), and it appears in the UI header
and the API (`/docs`, `/openapi.json`). Do not add a version literal
anywhere else.

```bash
uv version                 # show the current version
uv version --bump patch    # 0.2.0 -> 0.2.1 (also minor / major); updates pyproject.toml and uv.lock
```

The project is installed in editable mode, but the version is recorded at
install time, so a bump shows up after the next `uv sync`. `./serve.sh` and
any `uv run ...` command do that automatically. If you start the app another
way, run `uv sync` first.
`tests/test_api.py::test_installed_version_matches_pyproject` fails when the
installed version is stale.

## Deployment

Deployment to the station's Linux host is documented in
[Operations and deployment](operations.md). Station-specific helper scripts
and host settings are not necessarily applicable to other installations.

## Contributing

Bug reports, suggestions, and improvements are welcome through GitHub
Issues and pull requests.

Before submitting a change:

1. Describe the problem or proposed change.
2. Keep changes focused where possible.
3. Run the tests and static analysis.
4. Update documentation when behavior, configuration, or user workflows change.
5. Avoid committing station-specific secrets, credentials, or private configuration.

## See also

- [Architecture](architecture.md)
- [Radio backend](radio-backend.md)
- [API overview](api-overview.md)
- [Hardware and radio setup](hardware-setup.md) — bench tests on the Linux host
