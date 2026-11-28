# Architecture

StationVoice combines a web-based management application, text-to-speech,
announcement and schedule data, and a radio backend.

This document is a high-level orientation. For step-by-step use, see the
user documentation ([Getting started](getting-started.md),
[How to schedule](how-to-schedule.md)); for implementation details, consult
the source code and the linked technical references.

## Components

### Web application

The application provides the administrative interface for managing
announcements, schedules, configuration, and users. The application is built
around Python and FastAPI, with browser-based UI components. It runs on the
station's local network (or via VPN / HTTPS reverse proxy — see
[Operations — remote access](operations.md#urls-and-access)) and uses local username/password
accounts with three roles: **Admin**, **Editor**, and **Read-Only**
(see [Getting started — user roles](getting-started.md#user-roles)).

The home screen updates live: the server pushes status (current transmission,
manual triggers, Newsline processing, system stats) to browsers over
Server-Sent Events, with a REST fallback.

### Announcement library

Announcements are managed as library items. Depending on the item, the
content can be synthesized speech, an audio file, or a special item such as
Amateur Radio Newsline. Scheduling refers to library items rather than
duplicating announcement text in schedule entries.

On save, a spoken (or uploaded audio) item is synthesized once and its
measured length stored; the rendered audio is cached as PCM so scheduled
transmissions play without synthesizing again. Items longer than the
**repeater timeout** minus 2 seconds cannot be scheduled
(see [How to schedule — spoken length](how-to-schedule.md#spoken-length)).

### Text-to-speech

StationVoice uses [Piper TTS](https://github.com/OHF-Voice/piper1-gpl) for
speech synthesis. Speech is generated for playback rather than requiring
operators to maintain a collection of recordings for ordinary text
announcements. Voices are downloaded on demand (featured voices are
preloaded at startup), and a pronunciation dictionary supports word and
phrase substitutions, inline [IPA](https://en.wikipedia.org/wiki/International_Phonetic_Alphabet), and `*shortcut*` spellings.

See [Creating announcements — pronunciation](announcements.md#pronunciation)
for pronunciation workarounds and dictionary behavior.

### Scheduler

The scheduler uses a slot-based daily schedule: every hour and half-hour is a
slot, and something is chosen for each slot. Baseline schedules provide
announcements for slots not otherwise claimed, while overlays can override
baseline behavior for recurring or date-related events. The channel-busy
check (Carrier Operated Squelch, a.k.a. 'COS') can defer a transmission until the repeater is clear.

See [How to schedule](how-to-schedule.md) for the operator view.

### Radio backend

Radio control and audio transmission are separated behind a radio backend
interface.

- **stub:** Software backend used for development and testing without radio
  hardware.
- **dra:** Production interface using [Masters Communications DRA-36M](https://www.masterscommunications.com/products/radio-adapter/dra/dra36m.html)
  hardware.

The backend abstraction provides channel-busy detection and PTT control,
along with optional capabilities supported by the implementation.

See [Radio backend](radio-backend.md) for the protocol, the DRA backend's
behavior, and the settings that control it. Hardware wiring, jumpers, and
bench checkout are in [Hardware and radio setup](hardware-setup.md).

### Amateur Radio Newsline processing

StationVoice can retrieve [Amateur Radio Newsline](https://www.arnewsline.org/)
audio and prepare it for playback in story-sized pieces, allowing transmission to be interrupted by
unkeying between segments where required, and to resume after the channel
was busy.

See [Amateur Radio Newsline](arnewsline.md).

## What happens when a slot fires

At the scheduled time the scheduler resolves the slot **at fire time** —
the schedule and announcement are re-resolved when the slot fires, not when
the grid is drawn — then:

1. The announcement's cached PCM audio is loaded (or synthesized if the
   cache is missing).
2. The radio backend checks the channel: if the repeater is busy, the fire
   retries at the announcement's busy-retry interval until the busy give-up
   deadline, then drops.
3. When clear (and any clear hold is satisfied), both radios key together,
   stream the PTT lead silence, play the audio, and unkey in a `finally`
   path — a failed transmit never leaves PTT stuck.
4. The fire is logged (`data/logs/announcements.log`) and the home screen
   is updated.

A manual **Trigger now** runs the same transmit path but never changes slot
jobs. A slot whose fire time passed while the app was down or restarting is
not played late; use **Trigger now** if something did not air.

## Data and configuration

StationVoice uses environment variables for configuration (see
[Configuration reference](configuration.md)). `STATION_CALL` and
`STATION_NAME` are required; most other settings have usable defaults. A
`.env` file in the project root is loaded at startup (see
[`.env.example`](../.env.example)); variables already set in the shell
override that file.

Data files live under `DATA_DIR` (default `./data`):

| Path | Contents |
|---|---|
| `announcements.json` | Announcement library and schedules |
| `users.json` | Local accounts and roles |
| `pcm/` | Pre-rendered announcement PCM cache (written on save and at startup; scheduled fires play this) |
| `arnewsline/` | Downloaded Newsline reports, split stories, and state |
| `logs/` | Daily rotating `announcements.log` and `access.log` (kept 30 days) |
| `.session_secret` | Signs login session cookies (auto-generated) |
| `phonemes.json` | Pronunciation dictionary |

Piper voice models live under `voices/` (gitignored). Review the backup and
operational implications of the data directory before deploying the
application on a production station — the library, schedules, and users are
only in these files. Backups are covered in
[Backup and recovery](backup-recovery.md); deployment in
[Operations and deployment](operations.md).

## Further reading

- [Getting started](getting-started.md) — install, first run, roles
- [Creating announcements](announcements.md) — library items and pronunciation
- [How to schedule](how-to-schedule.md) — baselines and overlays
- [Amateur Radio Newsline](arnewsline.md) — Newsline items and splitting
- [Hardware and radio setup](hardware-setup.md) — DRA-36M, radios, checkout
- [Radio backend](radio-backend.md) — backend protocol and settings
- [Configuration reference](configuration.md) — every setting with defaults
- [Operations and deployment](operations.md) — deploying and restarts
- [API overview](api-overview.md) — HTTP API
- [Development](development.md) — dev workflow, tests, CI
- [Security](security.md) — exposure, accounts, sessions, secrets
