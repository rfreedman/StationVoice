# Getting started

This guide covers a basic installation and running StationVoice. For production radio operation, consult the [hardware documentation](final-hardware/README.md) and [deployment guide](deploy.md).

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) for Python environment and dependency management
- macOS for development and testing without radio hardware, or 64-bit Linux for radio operation
- PortAudio for local/stub audio playback where required

On macOS, install PortAudio using Homebrew:

```bash
brew install portaudio
```

On Ubuntu or Debian-based Linux:

```bash
sudo apt install libportaudio2
```

## Obtain the source

Clone the repository and change to the project directory:

```bash
git clone https://github.com/rfreedman/StationVoice.git
cd StationVoice
```

## Install dependencies

```bash
uv sync
```

You can activate the virtual environment:

```bash
source .venv/bin/activate
```

Activation is optional. Commands can also be run using `uv run`.

## Configuration

Review [`.env.example`](../.env.example) and the [environment reference](env-reference.md).

StationVoice requires station identification settings such as `STATION_CALL` and `STATION_NAME`. Other configuration is described in the environment reference. Do not commit credentials, secrets, or station-specific private configuration.

For testing and development without radio interfaces, use the stub radio backend. For radio operation, review the hardware setup and radio backend documentation before enabling the DRA backend.

## Start the web application

```bash
python -m app serve
```

Open:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

The first visit allows initial Admin account setup. After setup, Admin users have full access. Read-Only users can access the permitted viewing and speech-preview functions.

## Basic workflow

1. Sign in to the web interface.
2. Create or edit announcement text in the announcement library.
3. Preview speech and adjust text, voice, or timing as needed.
4. Create baseline and/or overlay schedules.
5. Review the schedule and upcoming announcements.

See [How to schedule](how-to-schedule.md) for details.

## Command-line interface

StationVoice provides a command-line interface:

```bash
python -m app --help
```

Commands include serving the application, speaking text, listing voices, downloading Piper voices, and managing users. For command-specific options, use the relevant command's `--help`.

## Next steps

- [Scheduling](how-to-schedule.md)
- [Environment reference](env-reference.md)
- [Radio backend](radio-backend.md)
- [Hardware setup](final-hardware/README.md)
- [Deployment](deploy.md)
