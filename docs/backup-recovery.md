# Backup and recovery

The station's content — announcements, schedules, users, pronunciation
dictionary, Newsline state — lives **only** in the data directory on the
Linux host. The repository does not contain any of it. Back up before
deploys that touch data, before OS changes, and after significant editing.

## What to back up

### Must back up (cannot be recreated)

| Path | Contents | Notes |
|---|---|---|
| `data/announcements.json` | Announcement library and schedules | The station's content |
| `data/users.json` | Local accounts and roles | Losing it means re-creating users and re-assigning roles |
| `data/phonemes.json` | Pronunciation dictionary | Hand-built; not in git |
| `voices/piper/` — extra (non-featured) voices | Custom `.onnx` + `.onnx.json` models | **Featured** voices are re-downloaded automatically; extra voices on disk are **not** |
| `.env` | Station configuration (identity, backend, timings) | Gitignored; contains host-specific settings |
| `.env.secrets` | Plugin credentials (e.g. Bird API key) | Gitignored by design |
| `plugins/` | Installed notifier plugin(s) | Source is in `plugin-examples/`, but any local edits would be lost |
| `scripts-local/` | Station-specific deploy helpers | Gitignored; only on the dev machine |
| Host config (on the Linux host) | udev rules, systemd units + sudoers drop-in, `/etc/caddy/*` (Caddyfile, `dreamhost.env`) | See [Operations](operations.md); `dreamhost.env` holds the DNS API key |

### Worth backing up (cheap insurance)

| Path | Contents | Notes |
|---|---|---|
| `data/arnewsline/state.json` | Current Newsline report number | Small |
| `data/arnewsline/{report}/` | Downloaded reports + split stories | Only useful until the following Thursday (a bulletin airs only through the Thursday after its Friday); a fresh **Check for Newsline now** rebuilds the latest one |
| `data/logs/` | `announcements.log`, `access.log` | Operational history; rotated after 30 days |

### Regenerates automatically (no need to back up)

| Path | How it comes back |
|---|---|
| `data/pcm/` | PCM cache is (re)written when announcements are saved and at startup |
| `data/.session_secret` | Auto-generated; a new one just means everyone signs in again |
| `data/arnewsline/cache/` | Alignment cache, only used during a split and removed afterwards |
| Whisper models (`base.en`, `small.en`) | Downloaded by the first successful split |
| Featured Piper voices | Re-downloaded automatically at startup if missing |
| `data/arnewsline/{report}/stories/` | Rebuildable from the downloaded MP3 by the splitter |

A station-local [CloudFlare R2](https://www.cloudflare.com/products/r2/) backup script exists in gitignored `scripts-local/`; it 
uses the admin email plugin for notifications when that plugin is active, otherwise
logs only. Keep a copy of the data directory **off the host** (e.g. network
storage, CloudFlare R2, Amazon S3, another machine).

## Restoring

1. Fresh checkout on the target host, `uv sync` (see
   [Getting started](getting-started.md)).
2. Restore the **must back up** items: `data/announcements.json`,
   `data/users.json`, `data/phonemes.json`, `voices/piper/` extras, `.env`
   (+ `.env.secrets`, `plugins/` if used).
3. Start the app and confirm **`Startup complete … (radio mode: …)`** in the
   log (see [Radio backend](radio-backend.md)).
4. Sign in, check the announcement library and the home slot clock, and run
   a **Trigger now** (stub-safe check) or a bench `retest` (DRA) before
   trusting on-air operation (see [Manual operation](manual-operations.md)
   and [Hardware setup](hardware-setup.md#bench-checkout)).
5. Restore host config (udev rules, systemd unit + sudoers, Caddy if used) if the OS
   was rebuilt — see [Operations](operations.md) and
   [Hardware setup](hardware-setup.md#linux-host-setup).

## When to back up

- After editing announcements, schedules, users, or the pronunciation
  dictionary (the files are written immediately on save).
- Before OS or hardware changes on the host.
- Before any change that replaces the data directory or that re-installs the app.
- To be _really_ safe, backup nightly or more often.

There is no built-in backup scheduler; use cron or your station's custom backup script
on the host.
