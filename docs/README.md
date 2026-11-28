# StationVoice documentation

This folder contains the StationVoice documentation set, consolidated by
subject. Each document covers one topic end to end — background, setup,
operation, and troubleshooting — instead of splitting a subject across
several files.

## User documentation

| Topic | Description |
|---|---|
| [Getting started](getting-started.md) | Installation, first run, user roles, and the basic workflow |
| [Creating announcements](announcements.md) | Spoken (TTS) and audio (MP3) items, length limits, voices, and pronunciation |
| [Scheduling announcements](how-to-schedule.md) | Baselines, overlays, recurring schedules, and timing |
| [Amateur Radio Newsline](arnewsline.md) | Downloading, processing, and transmitting Newsline, including how splitting works |
| [Manual operation](manual-operations.md) | Trigger now, busy/clear-hold status, and recovery after restarts |

## Station setup

| Topic | Description |
|---|---|
| [Hardware and radio setup](hardware-setup.md) | DRA-36M adapters, radios, wiring, host setup, bench checkout, and records |
| [Operations and deployment](operations.md) | Deploying, systemd, remote access (Caddy + Tailscale), and restart behavior |
| [Configuration reference](configuration.md) | Every environment setting with defaults |

## Developer documentation

| Topic | Description |
|---|---|
| [Architecture](architecture.md) | Application components, data flow, and data layout |
| [Radio backend](radio-backend.md) | Backend protocol, stub and DRA backends, and radio-related settings |
| [Development](development.md) | Development environment, tests, quality checks, CI, and versioning |
| [API overview](api-overview.md) | HTTP API overview |

## Operations and administration

| Topic | Description |
|---|---|
| [Troubleshooting](troubleshooting.md) | Symptom-first runbook for startup, transmit, COS, deploy, and UI issues |
| [Backup and recovery](backup-recovery.md) | What to back up, what regenerates, and how to restore |
| [Security](security.md) | Network exposure, accounts, sessions, and secrets handling |