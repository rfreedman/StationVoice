"""In-memory Piper TTS service with a web UI and CLI."""

from importlib.metadata import PackageNotFoundError, version

# The version lives only in pyproject.toml; bump it with `uv version --bump ...`.
try:
    __version__ = version("stationvoice")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
