# Development

This document describes the development workflow for StationVoice.

## Development environment

StationVoice requires Python 3.12 or later and uses `uv` to manage dependencies.

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

Use the stub radio backend when developing without radio hardware. See [Radio backend](radio-backend.md).

## Tests and static analysis

Run the test suite:

```bash
uv run pytest -q
```

Run static type analysis:

```bash
uv run basedpyright
```

The test suite sets `SKIP_DOTENV=1` so a local `.env` file does not affect test results.

Optional end-to-end tests may require browser dependencies:

```bash
uv run pytest -m e2e
```

Consult the test configuration and test documentation for the current requirements.

## CI

The project CI workflow runs tests and static type checks on the main branch. Before submitting changes, run the applicable checks locally.

For Linux-specific checks, use the project scripts and instructions where available. Hardware-dependent behavior should be tested on the target platform when practical.

## Dependencies

Dependencies are managed through `pyproject.toml` and `uv.lock`.

Use `uv add` and `uv remove` to manage dependencies, and commit both files when dependency changes are intended. Avoid manually installing packages into the project environment with `pip`.

## Deployment

Deployment to the station's Linux host is documented in [deploy.md](deploy.md). Station-specific helper scripts and host settings are not necessarily applicable to other installations.

## Contributing

Bug reports, suggestions, and improvements are welcome through GitHub Issues and pull requests.

Before submitting a change:

1. Describe the problem or proposed change.
2. Keep changes focused where possible.
3. Run the tests and static analysis.
4. Update documentation when behavior, configuration, or user workflows change.
5. Avoid committing station-specific secrets, credentials, or private configuration.
