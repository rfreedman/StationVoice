# Getting started

This guide covers a basic installation, first run, and user roles. For
production radio operation, consult the [hardware documentation](hardware-setup.md)
and [operations and deployment](operations.md).

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) for Python environment and dependency management
- macOS or 64-bit Linux for development and testing without radio hardware, or 64-bit Linux for radio operation
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

Review [`.env.example`](../.env.example) and the
[configuration reference](configuration.md).

StationVoice requires station identification settings such as `STATION_CALL`
and `STATION_NAME` — startup fails if either is missing or blank. Other
configuration is described in the environment reference. Do not commit
credentials, secrets, or station-specific private configuration.

For testing and development without radio interfaces, use the stub radio
backend. For radio operation, review the [hardware setup](hardware-setup.md)
and [radio backend](radio-backend.md) documentation before enabling the DRA
backend.

## Start the web application

```bash
python -m app serve
```

Open:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

## User roles and first setup

StationVoice uses local username/password accounts. The first account created
on a fresh install is always **Admin** — the first visit to the web interface
allows that initial Admin account setup. After setup there are three roles.
An Admin assigns each user's role in **Admin → Users**, or via the CLI:

```bash
python -m app users create USERNAME --role editor
```

Valid `--role` values: `admin`, `editor`, `readonly` (default).

### User roles

| Capability | Admin | Editor | Read-Only |
|---|---|---|---|
| Sign in, Home, Help, Phonemes view | yes | yes | yes |
| Speak preview and Newsline preview | yes | yes | yes |
| Create, edit, delete announcements | yes | yes | no |
| Create, edit, delete schedules | yes | yes | no |
| Trigger now (when enabled) | yes | yes | no |
| Settings (baseline shuffle, slot window) | yes | yes | no |
| Phoneme dictionary edits | yes | yes | no |
| Newsline check / dismiss | yes | yes | no |
| Admin section (Users, Environment, Branding) | yes | no | no |

### Admin section

Only **Admin** users see the Admin nav and can call Admin APIs:

- **Users** — create accounts, change roles and passwords, delete users
- **Environment** — runtime config history, email-alert toggle, application restart
- **Branding** — logo and favicon upload and display size

Editors and Read-Only users are redirected away from `#/admin/*` routes.

The store refuses to demote or delete the last remaining Admin so the
station is never locked out of user management.

## Basic workflow

1. Sign in to the web interface.
2. Create or edit announcement text in the announcement library
   (see [Creating announcements](announcements.md)).
3. Preview speech and adjust text, voice, or timing as needed.
4. Create baseline and/or overlay schedules.
5. Review the schedule and upcoming announcements.

See [How to schedule](how-to-schedule.md) for details, and
[Manual operation](manual-operations.md) for transmitting on demand.

## Command-line interface

StationVoice provides a command-line interface:

```bash
python -m app --help
```

Commands include serving the application, speaking text, listing voices,
downloading Piper voices, and managing users. For command-specific options,
use the relevant command's `--help`.

## Next steps

- [Creating announcements](announcements.md)
- [Scheduling](how-to-schedule.md)
- [Amateur Radio Newsline](arnewsline.md)
- [Radio backend](radio-backend.md)
- [Hardware setup](hardware-setup.md)
- [Configuration reference](configuration.md)
- [Operations and deployment](operations.md)
- [Security](security.md)
